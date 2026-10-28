"""Pydantic models: the shape of the data we extract and return from the API."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class LineItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class InvoiceData(BaseModel):
    """The fields we want to pull out of every invoice."""
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None      # kept as text; the validator checks the format
    vendor_name: Optional[str] = None
    currency: Optional[str] = None
    total_amount: Optional[float] = None
    line_items: List[LineItem] = []


class InvoiceOut(BaseModel):
    """What the API sends back for a saved invoice."""
    model_config = ConfigDict(from_attributes=True)  # lets us build it from a database row

    id: int
    filename: str
    status: str                 # "valid" or "needs_review"
    method: str                 # "llm" or "rules": which extractor was used
    issues: List[str]
    data: InvoiceData
    created_at: datetime