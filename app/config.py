"""Reads settings from environment variables (and the .env file)."""
import os

from dotenv import load_dotenv

load_dotenv()  # loads values from .env into os.environ

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./invoices.db")

MAX_UPLOAD_MB = 10
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}