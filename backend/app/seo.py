# backend/app/seo.py
from fastapi import APIRouter, HTTPException
from typing import Optional
import requests
from bs4 import BeautifulSoup
import re
import math
import os
import openai

router = APIRouter()
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")


# --- small utility functions (kept local to this module) ---
STOPWORDS = {
    # small English stopword set (add more if needed)
    "the","and","a","an","of","to","in","is","it","that","this","for","on","with","as","are",
    "was","were","be","by","or","from","at","which","you","your","I","we","they","their","has",
    "have","but","not","we","he","she","his","her","its","will","can"
}

def extract_text_and_meta(html: str):
    soup = BeautifulSoup(html, "html.parser")

    title = (soup.title.string.strip() if soup.title and soup.title.string else "") or ""
    meta_desc = ""
    desc_tag = soup.find("meta", attrs={"name":"description"}) or soup.find("meta", attrs={"property":"og:description"})
    if desc_tag and desc_tag.get("content"):
        meta_desc = desc_tag.get("content").strip()

    # collect headings
    headings = []
    for htag in ("h1","h2","h3"):
        for el in soup.find_all(htag):
            txt = el.get_text(separator=" ", strip=True)
            if txt:
                headings.append({"tag": htag, "text": txt})

    # main textual content (simple approach)
    for script in soup(["script","style","noscript"]):
        script.decompose()
    body_text = soup.get_text(separator=" ")
    # collapse whitespace
    body_text = re.sub(r"\s+", " ", body_text).strip()

    return {
        "title": title,
        "meta_description": meta_desc,
        "headings": headings,
        "text": body_text,
    }

def tokenize_words(text: str):
    # split on non-word, keep words longer than 1 char
    words = re.findall(r"[A-Za-z']{2,}", text.lower())
    return words

def top_keywords(words, top_n=20):
    freqs = {}
    total = 0
    for w in words:
        if w in STOPWORDS: 
            continue
        freqs[w] = freqs.get(w,0) + 1
        total += 1
    items = sorted(freqs.items(), key=lambda x: x[1], reverse=True)
    return [{"keyword": k, "count": c, "density": round((c/total)*100, 3) if total>0 else 0} for k,c in items[:top_n]]

def count_sentences(text: str):
    # simple sentence split
    sents = re.split(r'[.!?]+', text)
    sents = [s.strip() for s in sents if s.strip()]
    return max(1, len(sents))

def count_syllables_in_word(word: str):
    # heuristic syllable estimate: count vowel groups, subtract some endings
    w = word.lower()
    if len(w) <= 3:
        return 1
    w = re.sub(r'[^a-z]',"", w)
    groups = re.findall(r'[aeiouy]+', w)
    count = len(groups)
    # common silent e
    if w.endswith("e"):
        count -= 1
    # ensure at least 1
    if count <= 0:
        count = 1
    return count

def flesch_reading_ease(text: str):
    words = tokenize_words(text)
    num_words = max(1, len(words))
    num_sentences = count_sentences(text)
    syllables = sum(count_syllables_in_word(w) for w in words)
    # Flesch Reading Ease
    score = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (syllables / num_words)
    return round(score, 2), num_words, num_sentences, syllables

def generate_suggestions(analysis: dict):
    suggestions = []
    # title length
    title = analysis.get("title","") or ""
    if len(title) < 30:
        suggestions.append("Title is short — consider adding descriptive keywords (30–70 chars recommended).")
    if len(title) > 70:
        suggestions.append("Title is long — keep it under ~70 characters for search engines.")

    meta = analysis.get("meta_description","") or ""
    if not meta:
        suggestions.append("Missing meta description — add a 50–160 char summary for better CTR.")
    elif len(meta) < 50:
        suggestions.append("Meta description is short — aim for 50–160 characters.")
    elif len(meta) > 160:
        suggestions.append("Meta description is long — trim to 50–160 characters.")

    # headings
    if not analysis.get("headings"):
        suggestions.append("No H1/H2/H3 headings found — use headings to structure content.")

    # keyword density quick checks
    top = analysis.get("top_keywords",[])
    if top:
        primary = top[0]
        if primary["density"] < 0.3:
            suggestions.append(f"Primary keyword '{primary['keyword']}' has low density ({primary['density']}%) — consider mentioning it in title/meta.")
        if primary["density"] > 5:
            suggestions.append(f"Primary keyword '{primary['keyword']}' is used heavily ({primary['density']}%) — avoid keyword stuffing.")
    return suggestions

def ai_rewrite_if_available(text: str, prompt_prefix="Rewrite the following text for clarity and SEO in 2-3 short paragraphs:\n\n"):
    if not OPENAI_KEY:
        return None
    try:
        openai.api_key = OPENAI_KEY
        resp = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt_prefix + text,
            max_tokens=400,
            temperature=0.3,
        )
        return resp.choices[0].text.strip()
    except Exception:
        return None


# --- main analysis function ---
def analyze_html(html: str):
    data = extract_text_and_meta(html)
    words = tokenize_words(data["text"])
    top = top_keywords(words, top_n=15)
    readability_score, num_words, num_sentences, syllables = flesch_reading_ease(data["text"])
    analysis = {
        "title": data["title"],
        "meta_description": data["meta_description"],
        "headings": data["headings"],
        "top_keywords": top,
        "readability": {
            "flesch_reading_ease": readability_score,
            "words": num_words,
            "sentences": num_sentences,
            "syllables": syllables
        },
        "suggestions": [],  # filled below
    }
    analysis["suggestions"] = generate_suggestions(analysis)
    return analysis

# --- router endpoints ---
@router.post("/", summary="Analyze URL for SEO", status_code=200)
def analyze_url(payload: dict):
    """
    POST payload: {"url": "https://example.com/article", "ai_rewrite": true}
    Returns analysis JSON.
    """
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing url")
    ai_rewrite = bool(payload.get("ai_rewrite", False))
    try:
        resp = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=12)
        resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch URL: {str(e)}")

    analysis = analyze_html(resp.text)

    # optionally produce an AI rewrite of the first 2-3 paragraphs if requested
    if ai_rewrite:
        # pick a portion to rewrite (first 600 chars)
        excerpt = analysis.get("title","") + "\n\n" + " ".join(tokenize_words(analysis.get("meta_description",""))[:100])
        # fallback: use first 800 chars of body text
        if len(excerpt.strip()) < 30:
            excerpt = (analysis.get("title","") or "") + "\n\n" + (resp.text[:800] if resp else "")
        rewritten = ai_rewrite_if_available(excerpt, prompt_prefix="Rewrite for SEO and clarity:\n\n")
        analysis["ai_rewrite"] = rewritten
    else:
        analysis["ai_rewrite"] = None

    return analysis
