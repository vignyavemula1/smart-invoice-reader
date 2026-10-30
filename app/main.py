"""FastAPI app: the web API and the pipeline that ties everything together.

Upload -> extract text (OCR) -> extract fields (LLM or rules) -> validate -> save -> return
"""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import config
from app.database import Base, engine, get_db
from app.extractor import extract_fields
from app.models import Invoice
from app.ocr import extract_text
from app.schemas import InvoiceData, InvoiceOut
from app.validator import validate

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)   # create the table the first time the app starts
    yield


app = FastAPI(title="Smart Invoice Reader", version="1.0", lifespan=lifespan)


def to_out(row: Invoice) -> InvoiceOut:
    """Convert a database row into the API response shape."""
    return InvoiceOut(
        id=row.id,
        filename=row.filename,
        status=row.status,
        method=row.method,
        issues=row.issues or [],
        created_at=row.created_at,
        data=InvoiceData(
            invoice_number=row.invoice_number,
            invoice_date=row.invoice_date,
            vendor_name=row.vendor_name,
            currency=row.currency,
            total_amount=row.total_amount,
            line_items=row.line_items or [],
        ),
    )


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "llm_enabled": bool(config.GEMINI_API_KEY)}


@app.post("/api/invoices", response_model=InvoiceOut, status_code=201)
async def upload_invoice(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # 1. Check the file type and size
    extension = Path(file.filename or "").suffix.lower()
    if extension not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Please upload a PDF, PNG or JPG file.")
    data = await file.read()
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(400, f"File is larger than {config.MAX_UPLOAD_MB} MB.")

    # 2. Get the text (OCR for images and scanned PDFs)
    try:
        text = extract_text(file.filename, data)
    except Exception as error:
        raise HTTPException(422, f"Could not read the file: {error}")
    if not text.strip():
        raise HTTPException(422, "No text found in the file.")

    # 3. Pull out the fields, then 4. validate them
    fields, method = extract_fields(text)
    fields, issues = validate(fields)

    # 5. Save to the database
    row = Invoice(
        filename=file.filename,
        raw_text=text,
        invoice_number=fields.invoice_number,
        invoice_date=fields.invoice_date,
        vendor_name=fields.vendor_name,
        currency=fields.currency,
        total_amount=fields.total_amount,
        line_items=[item.model_dump() for item in fields.line_items],
        status="valid" if not issues else "needs_review",
        method=method,
        issues=issues,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return to_out(row)


@app.get("/api/invoices", response_model=List[InvoiceOut])
def list_invoices(db: Session = Depends(get_db)):
    rows = db.query(Invoice).order_by(Invoice.id.desc()).all()
    return [to_out(row) for row in rows]


@app.get("/api/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    row = db.get(Invoice, invoice_id)
    if row is None:
        raise HTTPException(404, "Invoice not found.")
    return to_out(row)


@app.delete("/api/invoices/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    row = db.get(Invoice, invoice_id)
    if row is None:
        raise HTTPException(404, "Invoice not found.")
    db.delete(row)
    db.commit()