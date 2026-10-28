"""Creates two test invoices: a digital PDF and a PNG image (for OCR).

Run:  python samples/make_samples.py
"""
from pathlib import Path

import pymupdf

HERE = Path(__file__).parent

LINES = [
    ("Sri Lakshmi Traders", 16),
    ("Plot 12, Madhapur, Hyderabad 500081", 10),
    ("", 10),
    ("TAX INVOICE", 14),
    ("Invoice No: INV-2026-0142", 11),
    ("Invoice Date: 14/10/2026", 11),
    ("Bill To: Acme Software Pvt Ltd", 11),
    ("", 10),
    ("Description              Qty    Rate      Amount", 11),
    ("Printer paper A4 (box)     5    450.00    2250.00", 11),
    ("Toner cartridge            2   1800.00    3600.00", 11),
    ("", 10),
    ("Subtotal                                  5850.00", 11),
    ("GST 18%                                   1053.00", 11),
    ("Total (INR)                               6903.00", 12),
]


def build_page(doc: pymupdf.Document) -> pymupdf.Page:
    page = doc.new_page(width=595, height=842)  # A4 in points
    y = 70
    for text, size in LINES:
        if text:
            page.insert_text((60, y), text, fontsize=size, fontname="cour")
        y += size + 10
    return page


def main():
    doc = pymupdf.open()
    page = build_page(doc)
    doc.save(HERE / "sample_invoice.pdf")
    page.get_pixmap(dpi=200).save(HERE / "sample_invoice.png")  # same invoice as an image
    print("Created samples/sample_invoice.pdf and samples/sample_invoice.png")


if __name__ == "__main__":
    main()