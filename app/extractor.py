"""Step 2 of the pipeline: turn raw invoice text into structured fields.

Uses Google Gemini (an LLM) when an API key is set. If there is no key, or the
call fails, it falls back to simple regex rules so the app still works.
"""
import json
import re
from typing import Optional, Tuple

import requests

from app import config
from app.schemas import InvoiceData

PROMPT = """You are an invoice data extraction assistant.
Read the invoice text below and return ONLY a JSON object with these keys:
  invoice_number (string or null)
  invoice_date   (string exactly as written on the invoice, or null)
  vendor_name    (the company that issued the invoice, or null)
  currency       (3-letter code such as INR or USD, or null)
  total_amount   (number: the final amount due, or null)
  line_items     (list of objects with description, quantity, unit_price, amount)
Use null for anything you cannot find. Do not invent values.

Invoice text:
\"\"\"
{text}
\"\"\"
"""

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def parse_json(raw: str) -> dict:
    """LLMs sometimes wrap JSON in ```json fences; strip them before parsing."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned)
    return json.loads(cleaned)


def extract_with_llm(text: str) -> InvoiceData:
    response = requests.post(
        GEMINI_URL.format(model=config.GEMINI_MODEL),
            headers={"x-goog-api-key": config.GEMINI_API_KEY},  # key in a header, so it never appears in URLs or error messages
        json={
            "contents": [{"parts": [{"text": PROMPT.format(text=text[:12000])}]}],
            "generationConfig": {
                "temperature": 0,                          # same input -> same output
                "responseMimeType": "application/json",    # ask for pure JSON back
            },
        },
        timeout=60,
    )
    response.raise_for_status()
    raw = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    return InvoiceData(**parse_json(raw))


# ---------- fallback: plain regex rules (no AI) ----------

def _to_number(value: str) -> Optional[float]:
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def extract_with_rules(text: str) -> InvoiceData:
    number = re.search(r"invoice\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]*)",
                       text, re.IGNORECASE)
    date = re.search(r"date\s*[:\-]?\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2}"
                     r"|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})", text, re.IGNORECASE)
    # every line that says "total" but not "subtotal"; the last one is the grand total
    totals = re.findall(r"^(?!.*sub\s*-?\s*total).*\btotal\b[^0-9\n]*([0-9][0-9,]*(?:\.[0-9]+)?)",
                        text, re.IGNORECASE | re.MULTILINE)

    currency = None
    if re.search(r"₹|\bINR\b|\bRs\.?", text):
        currency = "INR"
    elif re.search(r"\$|\bUSD\b", text):
        currency = "USD"
    elif re.search(r"€|\bEUR\b", text):
        currency = "EUR"

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    vendor = next((line for line in lines if "invoice" not in line.lower()), None)

    return InvoiceData(
        invoice_number=number.group(1) if number else None,
        invoice_date=date.group(1) if date else None,
        vendor_name=vendor,
        currency=currency,
        total_amount=_to_number(totals[-1]) if totals else None,
        line_items=[],
    )


def extract_fields(text: str) -> Tuple[InvoiceData, str]:
    """Returns the extracted data and which method produced it ("llm" or "rules")."""
    if config.GEMINI_API_KEY:
        try:
            return extract_with_llm(text), "llm"
        except Exception as error:  # network error, bad key, unparseable reply...
            print(f"LLM extraction failed, using rules instead: {error}")
    return extract_with_rules(text), "rules"