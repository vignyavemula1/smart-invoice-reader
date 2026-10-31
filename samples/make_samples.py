"""Creates test invoices for trying out the app and for the automated tests.

Run:  python samples/make_samples.py

Files created:
  sample_invoice.pdf / .png   clean invoice (digital PDF, and the same page as an image for OCR)
  invoice_cloudnine.pdf       a second vendor, USD, three line items -> valid
  invoice_scanned.jpg         looks like a phone photo/scan (tilted, grey, noisy) -> tests OCR
  invoice_wrong_total.pdf     line items do not add up to the total -> needs_review
  invoice_future_date.pdf     dated in the future -> needs_review
"""
from pathlib import Path

import cv2
import numpy as np
import pymupdf

HERE = Path(__file__).parent

SRI_LAKSHMI = [
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

CLOUDNINE = [
    ("CloudNine Hosting LLC", 16),
    ("500 Market Street, San Francisco, CA 94105", 10),
    ("", 10),
    ("INVOICE", 14),
    ("Invoice No: CN-88412", 11),
    ("Invoice Date: 03/09/2026", 11),
    ("Bill To: Acme Software Pvt Ltd", 11),
    ("", 10),
    ("Description              Qty    Rate      Amount", 11),
    ("Cloud server (monthly)     2    120.00     240.00", 11),
    ("Managed database           1     85.00      85.00", 11),
    ("SSL certificate            1     15.00      15.00", 11),
    ("", 10),
    ("Subtotal                                   340.00", 11),
    ("Tax 8%                                      27.20", 11),
    ("Total (USD)                                367.20", 12),
]

DECCAN_STATIONERY = [
    ("Deccan Stationery Mart", 16),
    ("Road No. 3, Banjara Hills, Hyderabad 500034", 10),
    ("", 10),
    ("TAX INVOICE", 14),
    ("Invoice No: DSM-2026-0907", 11),
    ("Invoice Date: 21/08/2026", 11),
    ("Bill To: Acme Software Pvt Ltd", 11),
    ("", 10),
    ("Description              Qty    Rate      Amount", 11),
    ("Notebooks (pack of 10)     4    300.00    1200.00", 11),
    ("Whiteboard markers         6     60.00     360.00", 11),
    ("Stapler                    2    250.00     500.00", 11),
    ("", 10),
    ("Subtotal                                  2060.00", 11),
    ("GST 18%                                    370.80", 11),
    ("Total (INR)                               2430.80", 12),
]

# Mistake on purpose: the items add up to 1500, but the total says 9500
WRONG_TOTAL = [
    ("Ravi Electricals", 16),
    ("Kukatpally, Hyderabad 500072", 10),
    ("", 10),
    ("TAX INVOICE", 14),
    ("Invoice No: RE-5531", 11),
    ("Invoice Date: 02/10/2026", 11),
    ("", 10),
    ("Description              Qty    Rate      Amount", 11),
    ("LED tube light            10    120.00    1200.00", 11),
    ("Extension board            2    150.00     300.00", 11),
    ("", 10),
    ("Total (INR)                               9500.00", 12),
]

# Mistake on purpose: the date is in the future
FUTURE_DATE = [
    ("Hitech Office Supplies", 16),
    ("Gachibowli, Hyderabad 500032", 10),
    ("", 10),
    ("TAX INVOICE", 14),
    ("Invoice No: HOS-2099-001", 11),
    ("Invoice Date: 15/01/2099", 11),
    ("", 10),
    ("Description              Qty    Rate      Amount", 11),
    ("Office chair               1   4500.00    4500.00", 11),
    ("", 10),
    ("GST 18%                                    810.00", 11),
    ("Total (INR)                               5310.00", 12),
]


def make_doc(lines) -> pymupdf.Document:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4 in points
    y = 70
    for text, size in lines:
        if text:
            page.insert_text((60, y), text, fontsize=size, fontname="cour")
        y += size + 10
    return doc


def save_pdf(lines, name):
    make_doc(lines).save(HERE / name)


def save_scanned_jpg(lines, name):
    """Render the invoice, then make it look like a scan: grey paper, noise, slight tilt."""
    pix = make_doc(lines)[0].get_pixmap(dpi=200)
    img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
    img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
    img = img * 0.82 + 30                                   # greyish paper, lower contrast
    rng = np.random.default_rng(7)
    img += rng.normal(0, 12, img.shape)                     # sensor noise
    img = np.clip(img, 0, 255).astype(np.uint8)
    h, w = img.shape
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), 1.2, 1.0)   # tilted by 1.2 degrees
    img = cv2.warpAffine(img, matrix, (w, h), borderValue=200)
    cv2.imwrite(str(HERE / name), img, [cv2.IMWRITE_JPEG_QUALITY, 80])


def main():
    doc = make_doc(SRI_LAKSHMI)
    doc.save(HERE / "sample_invoice.pdf")
    doc[0].get_pixmap(dpi=200).save(HERE / "sample_invoice.png")  # same invoice as an image
    save_pdf(CLOUDNINE, "invoice_cloudnine.pdf")
    save_scanned_jpg(DECCAN_STATIONERY, "invoice_scanned.jpg")
    save_pdf(WRONG_TOTAL, "invoice_wrong_total.pdf")
    save_pdf(FUTURE_DATE, "invoice_future_date.pdf")
    print("Created 6 sample invoices in the samples folder.")


if __name__ == "__main__":
    main()
