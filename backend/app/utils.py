# utils.py
import os
import re
from typing import Optional, Tuple
import openai

OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")

# --- Summarization helper (keeps your existing behavior) ---
def maybe_summarize(text: str) -> Optional[str]:
    """
    If OPENAI_API_KEY is set, call OpenAI (text-davinci-003) to produce
    a 3-5 bullet point summary. If key not present or API call fails,
    fall back to a lightweight heuristic: first 3 sentences (max ~800 chars).
    """
    if not OPENAI_KEY:
        # fallback simple heuristic: return first 3 sentences
        sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        short = " ".join(sents[:3])
        return short[:800]
    openai.api_key = OPENAI_KEY
    try:
        resp = openai.Completion.create(
            model="text-davinci-003",
            prompt=f"Summarize the following content in 3-5 short bullet points:\n\n{text}",
            max_tokens=200,
            temperature=0.2
        )
        return resp.choices[0].text.strip()
    except Exception:
        sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        return " ".join(sents[:3])[:800]


# --- Price parsing helpers ---
CURRENCY_SYMBOLS = {
    "$": "USD",
    "₹": "INR",
    "₹": "INR",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₩": "KRW",
    "₽": "RUB",
    "₺": "TRY",
    "₫": "VND",
    "฿": "THB",
    "₴": "UAH"
}

# Regex to find common currency symbols followed by numbers (with optional spaces)
CURRENCY_SYMBOL_REGEX = re.compile(r"(?P<sym>[₹$€£¥₩₽₺₫฿₴])\s*(?P<num>[0-9][0-9\.,\s]+[0-9])")
# Regex to find ISO currency codes like "USD 19.99" or "19.99 USD"
ISO_CURRENCY_REGEX = re.compile(r"(?P<cur>[A-Z]{3})\s*(?P<num>[0-9][0-9\.,\s]+[0-9])|(?P<num2>[0-9][0-9\.,\s]+[0-9])\s*(?P<cur2>[A-Z]{3})")

# Fallback number extraction: finds first reasonable number group
NUMBER_REGEX = re.compile(r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]+)?)")

def _normalize_number_string(s: str) -> Optional[str]:
    """
    Normalize a numeric string that may use either '.' or ',' as thousands/decimal separators.
    Returns a string suitable for float(...) or None if cannot parse.
    Strategy:
      - Strip whitespace.
      - If both '.' and ',' are present, determine which is decimal by position:
          - If last '.' comes after last ',', treat '.' as decimal and remove ',' thousands.
          - Else treat ',' as decimal and remove '.' thousands.
      - If only ',' present:
          - If there are exactly 1 or 2 digits after the last comma, treat it as decimal separator.
          - Else remove commas (thousands separators).
      - If only '.' present: standard float (remove any thousands separators if necessary).
    """
    if not s:
        return None
    s = s.strip()
    # remove non-number but keep ., and commas
    s = re.sub(r"[^\d\.,\-]", "", s)
    if s == "":
        return None

    if "." in s and "," in s:
        # decide which is decimal by last occurrence
        if s.rfind(".") > s.rfind(","):
            # . is decimal, remove commas
            s = s.replace(",", "")
        else:
            # , is decimal, remove dots and replace comma with dot
            s = s.replace(".", "").replace(",", ".")
    elif "," in s and "." not in s:
        # only comma present - guess if comma is decimal
        parts = s.split(",")
        if len(parts[-1]) in (1, 2):  # likely decimal
            s = s.replace(".", "")  # remove any stray dots (unlikely)
            s = s.replace(",", ".")
        else:
            # treat commas as thousand separators
            s = s.replace(",", "")
    else:
        # only dots or only digits - remove any stray commas (shouldn't be any)
        s = s.replace(",", "")

    # final cleanup: remove multiple dots except last (defensive)
    if s.count(".") > 1:
        # remove all but last dot
        parts = s.split(".")
        s = "".join(parts[:-1]).replace(".", "") + "." + parts[-1]

    # remove leading/trailing non-digit artifacts
    s = s.strip(".-")
    try:
        return s
    except Exception:
        return None

def parse_price_text(text: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Attempt to parse a price out of a textual string.
    Returns (value: float or None, currency: str or None).
    This is intentionally conservative: it tries symbol -> ISO code -> fallback numeric.
    """
    if not text or not isinstance(text, str):
        return None, None

    # collapse whitespace
    t = " ".join(text.split())

    # 1) symbol-based match
    m = CURRENCY_SYMBOL_REGEX.search(t)
    if m:
        sym = m.group("sym")
        num = m.group("num")
        normalized = _normalize_number_string(num)
        if normalized:
            try:
                value = float(normalized)
                return value, CURRENCY_SYMBOLS.get(sym, None)
            except Exception:
                pass

    # 2) ISO currency code matches (USD 19.99 or 19.99 USD)
    m2 = ISO_CURRENCY_REGEX.search(t)
    if m2:
        cur = m2.group("cur") or m2.group("cur2")
        num = m2.group("num") or m2.group("num2")
        if num:
            normalized = _normalize_number_string(num)
            if normalized:
                try:
                    value = float(normalized)
                    return value, cur
                except Exception:
                    pass

    # 3) common currency words/symbols (like "Rs.", "INR", "USD")
    # try to find a nearby  number if a currency code word exists
    word_cur = None
    word_match = re.search(r"\b(Rs\.?|INR|USD|EUR|GBP|AUD|CAD|JPY|CNY)\b", t, flags=re.I)
    if word_match:
        word_cur = word_match.group(0).upper().replace("RS.", "INR")
        # find first number after/before
        num_match = NUMBER_REGEX.search(t)
        if num_match:
            normalized = _normalize_number_string(num_match.group(1))
            if normalized:
                try:
                    value = float(normalized)
                    return value, word_cur
                except Exception:
                    pass

    # 4) meta-like patterns e.g. "19.99" or "1,299.00" - grab first number
    num_match = NUMBER_REGEX.search(t)
    if num_match:
        normalized = _normalize_number_string(num_match.group(1))
        if normalized:
            try:
                value = float(normalized)
                return value, None
            except Exception:
                pass

    return None, None


def format_price(value: Optional[float], currency: Optional[str]) -> str:
    """
    Nicely format a price for display. Safe to call with None values.
    """
    if value is None:
        return ""
    # currency best-effort formatting (no locale)
    cur = f"{currency} " if currency else ""
    # format with 2 decimal places, strip .00 if integer
    if abs(value - int(value)) < 0.005:
        return f"{cur}{int(value)}"
    return f"{cur}{value:,.2f}"

def normalize_paragraphs(pars):
    out = []
    seen = set()
    for p in pars:
        t = " ".join(p.split())[:2000]  # collapse whitespace, limit length
        if not t:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out

