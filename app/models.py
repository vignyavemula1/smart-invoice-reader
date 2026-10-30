"""The database table (ORM model). One row per uploaded invoice."""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    raw_text: Mapped[str] = mapped_column(Text)           # what OCR read, kept for debugging
    invoice_number: Mapped[str | None] = mapped_column(String(100))
    invoice_date: Mapped[str | None] = mapped_column(String(20))
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    currency: Mapped[str | None] = mapped_column(String(10))
    total_amount: Mapped[float | None] = mapped_column(Float)
    line_items: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20))       # "valid" or "needs_review"
    method: Mapped[str] = mapped_column(String(10))       # "llm" or "rules"
    issues: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))