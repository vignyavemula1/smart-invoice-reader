"""End-to-end tests of the API using FastAPI's TestClient and a temporary database."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import config
from app.database import Base, get_db
from app.main import app
from samples.make_samples import main as make_samples

SAMPLES = Path(__file__).parent.parent / "samples"


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")   # tests never call the real LLM
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)        # in-memory DB, fresh for each test
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    if not (SAMPLES / "invoice_scanned.jpg").exists():
        make_samples()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_upload_pdf_extracts_and_saves(client):
    with open(SAMPLES / "sample_invoice.pdf", "rb") as f:
        res = client.post("/api/invoices", files={"file": ("sample_invoice.pdf", f, "application/pdf")})
    assert res.status_code == 201
    body = res.json()
    assert body["data"]["invoice_number"] == "INV-2026-0142"
    assert body["data"]["invoice_date"] == "2026-10-14"
    assert body["data"]["total_amount"] == 6903.0
    assert body["status"] == "valid"

    listed = client.get("/api/invoices").json()
    assert len(listed) == 1 and listed[0]["id"] == body["id"]


def test_upload_image_uses_ocr(client):
    with open(SAMPLES / "sample_invoice.png", "rb") as f:
        res = client.post("/api/invoices", files={"file": ("sample_invoice.png", f, "image/png")})
    assert res.status_code == 201
    assert res.json()["data"]["invoice_number"] == "INV-2026-0142"
    assert res.json()["data"]["total_amount"] == 6903.0


def test_scanned_jpg_is_read_with_ocr(client):
    with open(SAMPLES / "invoice_scanned.jpg", "rb") as f:
        res = client.post("/api/invoices", files={"file": ("invoice_scanned.jpg", f, "image/jpeg")})
    assert res.status_code == 201
    assert res.json()["data"]["invoice_number"] == "DSM-2026-0907"
    assert res.json()["data"]["total_amount"] == 2430.8


def test_future_date_needs_review(client):
    with open(SAMPLES / "invoice_future_date.pdf", "rb") as f:
        res = client.post("/api/invoices", files={"file": ("invoice_future_date.pdf", f, "application/pdf")})
    assert res.status_code == 201
    assert res.json()["status"] == "needs_review"
    assert "Invoice date is in the future." in res.json()["issues"]


def test_rejects_wrong_file_type(client):
    res = client.post("/api/invoices", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert res.status_code == 400


def test_get_and_delete(client):
    with open(SAMPLES / "sample_invoice.pdf", "rb") as f:
        new_id = client.post("/api/invoices", files={"file": ("a.pdf", f, "application/pdf")}).json()["id"]
    assert client.get(f"/api/invoices/{new_id}").status_code == 200
    assert client.delete(f"/api/invoices/{new_id}").status_code == 204
    assert client.get(f"/api/invoices/{new_id}").status_code == 404
