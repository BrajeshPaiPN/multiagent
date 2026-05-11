"""
PDF Ingestion & Vector Storage for Indian Legal Knowledge
=========================================================
Extracts text from all PDFs in the uploads directory, chunks them,
and stores them in a local FAISS vector database for semantic retrieval.
"""

import os
import shutil
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

# OCR fallback libraries
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
INDEX_PATH = os.path.join(os.path.dirname(__file__), "faiss_index")


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts text using PyPDF2 with a fallback to OCR for scanned documents."""
    text = ""
    try:
        # Disable strict mode to handle PDFs with missing EOF markers or other minor corruptions
        reader = PdfReader(pdf_path, strict=False)
        for page in reader.pages:
            try:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            except Exception as e_page:
                print(f"    [!] Page extraction error in {os.path.basename(pdf_path)}: {e_page}")
    except Exception as e:
        print(f"    [!] PyPDF2 failed for {os.path.basename(pdf_path)}: {e}")

    # Fallback to OCR if text extraction is poor
    if len(text.strip()) < 100:
        print(f"    [*] Running OCR on {os.path.basename(pdf_path)}...")
        try:
            images = convert_from_path(pdf_path)
            for image in images:
                text += pytesseract.image_to_string(image) + "\n"
        except Exception as e:
            print(f"    [!] OCR failed: {e}")

    return text


def run_ingestion():
    """Processes all files in uploads/ and builds/updates the FAISS index."""
    print("\n" + "=" * 60, flush=True)
    print(">>> LEGAL DOCUMENT INGESTION PIPELINE", flush=True)
    print("=" * 60, flush=True)

    if not os.path.exists(UPLOAD_DIR):
        print(f"[!] Upload directory '{UPLOAD_DIR}' not found.")
        return

    pdf_files = [f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith((".pdf", ".txt"))]
    if not pdf_files:
        print("[!] No documents found in uploads directory.")
        return

    print(f"[*] Found {len(pdf_files)} legal documents to process.", flush=True)

    all_docs = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        length_function=len,
    )

    for filename in pdf_files:
        path = os.path.join(UPLOAD_DIR, filename)
        print(f"[*] Extracting: {filename} ...", flush=True)
        
        if filename.lower().endswith(".pdf"):
            raw_text = extract_text_from_pdf(path)
        else:
            # Handle plain text files
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    raw_text = f.read()
            except Exception as e:
                print(f"    [!] Failed to read {filename}: {e}")
                continue
        if not raw_text.strip():
            print(f"    [!] Skipped {filename}: No text content.")
            continue

        # Split into chunks
        chunks = text_splitter.split_text(raw_text)
        print(f"    [+] Created {len(chunks)} semantic chunks.", flush=True)

        for i, chunk in enumerate(chunks):
            all_docs.append(Document(
                page_content=chunk,
                metadata={"source": filename, "chunk": i}
            ))

    if not all_docs:
        print("[!] No documents to index.")
        return

    print(f"[*] Generating embeddings and building FAISS index for {len(all_docs)} chunks...", flush=True)
    
    # Use a lightweight local embedding model (no API calls required)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    vectorstore = FAISS.from_documents(all_docs, embeddings)
    
    # Save index locally
    vectorstore.save_local(INDEX_PATH)
    print(f"\n[SUCCESS] Vector Database created successfully at: {INDEX_PATH}", flush=True)
    print("=" * 60 + "\n", flush=True)


if __name__ == "__main__":
    run_ingestion()
