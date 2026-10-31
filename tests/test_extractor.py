from app import config
from app.extractor import extract_fields, extract_with_rules, parse_json

SAMPLE_TEXT = """Sri Lakshmi Traders
TAX INVOICE
Invoice No: INV-2026-0142
Invoice Date: 14/10/2026
Subtotal 5850.00
GST 18% 1053.00
Total (INR) 6,903.00
"""


def test_rules_extract_main_fields():
    data = extract_with_rules(SAMPLE_TEXT)
    assert data.invoice_number == "INV-2026-0142"
    assert data.invoice_date == "14/10/2026"
    assert data.vendor_name == "Sri Lakshmi Traders"
    assert data.currency == "INR"
    assert data.total_amount == 6903.0   # grand total, not the subtotal


def test_parse_json_strips_code_fences():
    assert parse_json('```json\n{"invoice_number": "A1"}\n```') == {"invoice_number": "A1"}


def test_falls_back_to_rules_without_api_key(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    data, method = extract_fields(SAMPLE_TEXT)
    assert method == "rules"
    assert data.invoice_number == "INV-2026-0142"


def test_falls_back_to_rules_when_llm_fails(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-key")

    def broken_llm(text):
        raise RuntimeError("network down")

    monkeypatch.setattr("app.extractor.extract_with_llm", broken_llm)
    data, method = extract_fields(SAMPLE_TEXT)
    assert method == "rules"
    assert data.total_amount == 6903.0


def test_llm_response_is_parsed(monkeypatch):
    """Fake the Gemini HTTP reply so we can test our parsing without calling the real API."""
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-key")
    reply_text = ('{"invoice_number": "INV-9", "invoice_date": "14/10/2026", "vendor_name": "ABC Ltd", '
                  '"currency": "INR", "total_amount": 1180, "line_items": '
                  '[{"description": "Service", "quantity": 1, "unit_price": 1000, "amount": 1000}]}')

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": reply_text}]}}]}

    monkeypatch.setattr("app.extractor.requests.post", lambda *args, **kwargs: FakeResponse())
    data, method = extract_fields("any text")
    assert method == "llm"
    assert data.invoice_number == "INV-9"
    assert data.line_items[0].amount == 1000
