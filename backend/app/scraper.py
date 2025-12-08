import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List
import csv
import io
import os
import json
from .crud import set_job_status
from .utils import maybe_summarize
from .utils import parse_price_text

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ScraperBot/1.0)"}

def scrape_page(url: str, selectors: Dict[str,str]=None) -> Dict[str,Any]:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    data = {}

    # Always try to get title and meta description
    data["title"] = soup.title.string.strip() if soup.title and soup.title.string else ""
    desc = soup.find("meta", attrs={"name":"description"}) or soup.find("meta", attrs={"property":"og:description"})
    data["description"] = desc["content"].strip() if desc and desc.has_attr("content") else ""

    if selectors:
        # selectors expected as a dict: {"content": "article", "author": ".author"}
        for key, sel in selectors.items():
            try:
                elems = soup.select(sel)
            except Exception:
                elems = []
            if elems:
                # store texts array and first occurrence as scalar
                texts = [e.get_text(" ", strip=True) for e in elems if e.get_text(strip=True)]
                data[key] = texts
                if key == "content" and not data.get("paragraphs"):
                    # split the content text into paragraphs (fallback)
                    joined = "\n\n".join(texts)
                    paras = [p.strip() for p in joined.split("\n\n") if p.strip()]
                    data["paragraphs"] = paras[:50]
            else:
                # fallback: try find by tag name
                found = soup.find_all(sel)
                if found:
                    texts = [f.get_text(" ", strip=True) for f in found]
                    data[key] = texts
                else:
                    data[key] = []
    else:
        # No selector provided -> default extraction
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
        data["paragraphs"] = paragraphs[:50]
        links = [a.get("href") for a in soup.find_all("a", href=True)]
        data["links"] = links[:200]

    return data


def save_csv(data: Dict[str,Any], job_id: int) -> str:
    folder = os.getenv("SCRAPE_OUTPUT_DIR", "./backend/app/outputs")
    os.makedirs(folder, exist_ok=True)
    filename = f"{folder}/scrape_{job_id}.csv"
    # flatten into rows: each key becomes column with joined values
    rows = []
    maxlen = 0
    cols = list(data.keys())
    arrays = []
    for c in cols:
        v = data.get(c)
        if isinstance(v, list):
            arrays.append(v)
            maxlen = max(maxlen, len(v))
        else:
            arrays.append([v])
            maxlen = max(maxlen, 1)
    # pad arrays
    padded = []
    for arr in arrays:
        arr2 = arr + [""] * (maxlen - len(arr))
        padded.append(arr2)
    # write rows
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for i in range(maxlen):
            row = [padded[j][i] for j in range(len(cols))]
            writer.writerow(row)
    return filename

def run_scrape_job(job_id: int, url: str, selectors: Dict[str,str]=None, save_csv_flag: bool=False, ai_summary: bool=False):
    try:
        set_job_status(job_id, "running")
        data = scrape_page(url, selectors)
        output = {"url": url, "data": data}
        csv_path = None
        if save_csv_flag:
            csv_path = save_csv(data, job_id)
            output["csv"] = csv_path
        if ai_summary:
            summary = maybe_summarize("\n\n".join(data.get("paragraphs", [])))
            output["ai_summary"] = summary
        set_job_status(job_id, "done", result=output)
    except Exception as e:
        set_job_status(job_id, "failed", error=str(e))

def extract_price_from_soup(soup):
    # 1) Microdata / schema.org: itemprop="price"
    el = soup.select_one('[itemprop="price"], meta[itemprop="price"]')
    if el:
        # meta tag: <meta itemprop="price" content="19.99" />
        text = el.get("content") or el.get_text()
        val, cur = parse_price_text(text)
        if val:
            # try currency from itemprop currency or meta
            currency = None
            cur_el = soup.select_one('[itemprop="priceCurrency"], meta[itemprop="priceCurrency"]')
            if cur_el:
                currency = cur_el.get("content") or cur_el.get_text()
            return val, currency

    # 2) Common classes/ids
    selectors = [
        ".price", ".product-price", ".price-current", ".priceSale", "#price", "#priceblock_ourprice",
        ".offer-price", ".product-price__amount"
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            val, cur = parse_price_text(el.get_text())
            if val:
                return val, cur

    # 3) meta tags (og:price:amount or product:price:amount)
    meta_price = soup.select_one('meta[property="product:price:amount"], meta[property="og:price:amount"]')
    if meta_price and meta_price.get("content"):
        val, cur = parse_price_text(meta_price["content"])
        if val:
            # try currency meta
            meta_cur = soup.select_one('meta[property="product:price:currency"], meta[property="og:price:currency"]')
            cur_val = meta_cur["content"] if meta_cur and meta_cur.get("content") else None
            return val, cur_val

    # 4) fallback: scan top N elements for currency pattern
    text = soup.get_text(" ", strip=True)
    val, cur = parse_price_text(text)
    return val, cur