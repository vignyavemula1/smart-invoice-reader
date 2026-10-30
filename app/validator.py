"""Step 3 of the pipeline: check the extracted data with business rules.

LLMs can make mistakes (hallucinate), so we never trust the output blindly.
Anything that fails a rule is marked "needs_review" for a human to check.
"""
from datetime import date, datetime
from typing import List, Optional, Tuple

from app.schemas import InvoiceData

DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d",
                "%d/%m/%y", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y"]


def parse_date(value: str) -> Optional[date]:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def validate(data: InvoiceData) -> Tuple[InvoiceData, List[str]]:
    """Returns the (cleaned) data and a list of problems. An empty list means valid."""
    issues: List[str] = []

    # Rule 1: the important fields must be present
    for field in ["invoice_number", "invoice_date", "vendor_name", "total_amount"]:
        if getattr(data, field) in (None, ""):
            issues.append(f"Missing {field.replace('_', ' ')}.")

    # Rule 2: the date must be a real date, not in the future; store it as YYYY-MM-DD
    if data.invoice_date:
        parsed = parse_date(data.invoice_date)
        if parsed is None:
            issues.append(f"Could not understand the date '{data.invoice_date}'.")
        elif parsed > date.today():
            issues.append("Invoice date is in the future.")
        else:
            data.invoice_date = parsed.isoformat()

    # Rule 3: the total must not be negative
    if data.total_amount is not None and data.total_amount < 0:
        issues.append("Total amount is negative.")

    # Rule 4: quantity x unit price should equal each line's amount
    for item in data.line_items:
        if None not in (item.quantity, item.unit_price, item.amount):
            if abs(item.quantity * item.unit_price - item.amount) > 1:
                issues.append(f"Line '{item.description}': quantity x price does not match amount.")

    # Rule 5: line items should add up to the total (allowing up to 30% for tax)
    amounts = [item.amount for item in data.line_items if item.amount is not None]
    if amounts and data.total_amount is not None:
        items_sum = sum(amounts)
        if not (items_sum - 1 <= data.total_amount <= items_sum * 1.30 + 1):
            issues.append(f"Line items add up to {items_sum:.2f} but the total is "
                          f"{data.total_amount:.2f}.")

    return data, issues