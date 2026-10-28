"""Step 1 of the pipeline: get plain text out of a PDF or an image."""
import cv2
import numpy as np
import pymupdf
import pytesseract

from app import config

if config.TESSERACT_CMD:  # on Windows, point pytesseract at tesseract.exe
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD


def preprocess(image: np.ndarray) -> np.ndarray:
    """Clean the image so OCR reads it more accurately."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)          # colour -> grayscale
    gray = cv2.resize(gray, None, fx=1.5, fy=1.5,            # enlarge small text
                      interpolation=cv2.INTER_CUBIC)
    gray = cv2.medianBlur(gray, 3)                           # remove speckle noise
    _, binary = cv2.threshold(gray, 0, 255,                  # pure black text on white
                              cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def ocr_image(image: np.ndarray) -> str:
    # --psm 6 tells Tesseract to read the page as one block of text, line by line,
    # which keeps table rows like "Total (INR) ... 6903.00" together on one line
    return pytesseract.image_to_string(preprocess(image), config="--psm 6")


def image_bytes_to_text(data: bytes) -> str:
    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not read the image file.")
    return ocr_image(image)


def pdf_bytes_to_text(data: bytes) -> str:
    """Digital PDFs already contain text, so read it directly (fast and exact).
    Only scanned pages with no text layer are rendered to an image and OCR'd."""
    parts = []
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text = page.get_text().strip()
            if len(text) > 20:
                parts.append(text)
            else:
                pix = page.get_pixmap(dpi=200)
                image = cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8), cv2.IMREAD_COLOR)
                parts.append(ocr_image(image))
    return "\n".join(parts)


def extract_text(filename: str, data: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        return pdf_bytes_to_text(data)
    return image_bytes_to_text(data)