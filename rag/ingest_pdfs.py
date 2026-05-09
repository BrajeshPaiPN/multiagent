"""
PDF Ingestion & OCR for Indian Legal Documents
==============================================
Reads PDFs from rag/uploads/, extracts text (with PyTesseract fallback for OCR),
splits into chunks, and adds them to the FAISS RAG database.
"""

import os
import glob
from PyPDF2 import PdfReader
import pytesseract
from pdf2image import convert_from_path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from pipeline import get_vector_store, EMBEDDINGS, RAG_DB_PATH

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")

# Configure tesseract path if needed for Windows
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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
        print(f"[*] Text too short or missing in {os.path.basename(pdf_path)}. Running OCR...")
        try:
            # Note: This requires Poppler to be installed on the system path
            images = convert_from_path(pdf_path)
            for i, image in enumerate(images):
                ocr_text = pytesseract.image_to_string(image)
                text += ocr_text + "\n"
        except Exception as e:
            print(f"[!] OCR failed. Ensure Poppler and Tesseract are installed on Windows. Error: {e}")
            
    return text

def ingest_all_pdfs():
    """Reads all PDFs in rag/uploads, splits them, and stores in FAISS."""
    pdf_files = glob.glob(os.path.join(UPLOAD_DIR, "*.pdf"))
    
    if not pdf_files:
        print("[*] No PDFs found in rag/uploads/. Add Indian Constitution or textbook PDFs there.")
        return

    print(f"[*] Found {len(pdf_files)} PDF(s). Starting extraction...")
    
    all_chunks = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        print(f"    -> Processing {filename}...")
        
        raw_text = extract_text_from_pdf(pdf_path)
        if not raw_text.strip():
            print(f"    [!] Could not extract any text from {filename}.")
            continue
            
        chunks = text_splitter.split_text(raw_text)
        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={"source": filename, "chunk": i}
            )
            all_chunks.append(doc)
            
    if all_chunks:
        print(f"[*] Generating embeddings for {len(all_chunks)} chunks and adding to FAISS...")
        store = get_vector_store()
        store.add_documents(all_chunks)
        store.save_local(RAG_DB_PATH)
        print("[+] Vector database updated successfully!")

if __name__ == "__main__":
    ingest_all_pdfs()
