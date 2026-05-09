"""
PDF Ingestion & OCR for Indian Legal Documents
==============================================
Reads PDFs and images, extracts text (with PyTesseract fallback for OCR).
FAISS vector storage has been removed in favour of the lightweight in-memory
keyword retriever in rag/pipeline.py to stay within cloud RAM limits.
"""

import os
from PyPDF2 import PdfReader
import pytesseract
from pdf2image import convert_from_path

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")


def extract_text_from_pdf(pdf_path: str) -> str:
    """Try standard PDF text extraction, fallback to OCR if empty."""
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        print(f"[!] PyPDF2 extraction failed for {pdf_path}: {e}")

    # If PyPDF2 returns very little text, assume it's a scanned PDF and run OCR
    if len(text.strip()) < 100:
        print(f"[*] Running OCR on {os.path.basename(pdf_path)}...")
        try:
            images = convert_from_path(pdf_path)
            for image in images:
                text += pytesseract.image_to_string(image) + "\n"
        except Exception as e:
            print(f"[!] OCR failed: {e}")

    return text
