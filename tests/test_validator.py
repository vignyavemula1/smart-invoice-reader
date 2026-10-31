from app.schemas import InvoiceData, LineItem
from app.validator import validate


def make(**overrides):
    base = dict(invoice_number="INV-1", invoice_date="14/10/2026",
                vendor_name="Sri Lakshmi Traders", currency="INR", total_amount=6903.0)
    base.update(overrides)
    return InvoiceData(**base)


def test_valid_invoice_has_no_issues():
    data, issues = validate(make())
    assert issues == []
    assert data.invoice_date == "2026-10-14"   # date is normalised to YYYY-MM-DD


def test_missing_fields_are_reported():
    _, issues = validate(make(invoice_number=None, total_amount=None))
    assert "Missing invoice number." in issues
    assert "Missing total amount." in issues


def test_bad_date_is_reported():
    _, issues = validate(make(invoice_date="32/13/2026"))
    assert any("Could not understand the date" in i for i in issues)


def test_future_date_is_reported():
    _, issues = validate(make(invoice_date="01/01/2099"))
    assert "Invoice date is in the future." in issues


def test_line_items_must_add_up_to_total():
    items = [LineItem(description="Paper", quantity=5, unit_price=450, amount=2250),
             LineItem(description="Toner", quantity=2, unit_price=1800, amount=3600)]
    _, ok_issues = validate(make(line_items=items, total_amount=6903))      # 5850 + 18% tax
    _, bad_issues = validate(make(line_items=items, total_amount=20000))
    assert ok_issues == []
    assert any("add up to" in i for i in bad_issues)


def test_quantity_times_price_must_match_amount():
    items = [LineItem(description="Paper", quantity=5, unit_price=450, amount=9999)]
    _, issues = validate(make(line_items=items, total_amount=9999))
    assert any("does not match" in i for i in issues)
