"""
RAG Pipeline (India-Specific Legal Knowledge)
==============================================
Uses FAISS and local embeddings to search a curated database of the
Indian Constitution, IPC/BNS, and standard legal textbooks.
"""
import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

RAG_DB_PATH = os.path.join(os.path.dirname(__file__), "faiss_index")

# We use a lightweight, fast, local embedding model
# Initialized lazily to prevent server boot timeouts.
_EMBEDDINGS = None

def get_embeddings():
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        print("[RAG] Loading Embedding Model...")
        _EMBEDDINGS = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _EMBEDDINGS

# Mock Dataset: Excerpts from Indian Constitution and Legal Textbooks
KNOWLEDGE_BASE = [
    Document(
        page_content="Article 21 of the Indian Constitution: No person shall be deprived of his life or personal liberty except according to procedure established by law. This encompasses the right to privacy, right to speedy trial, and right to bail.",
        metadata={"source": "Constitution of India", "section": "Article 21"}
    ),
    Document(
        page_content="Article 14 of the Indian Constitution: The State shall not deny to any person equality before the law or the equal protection of the laws within the territory of India.",
        metadata={"source": "Constitution of India", "section": "Article 14"}
    ),
    Document(
        page_content="Article 19(1)(a) guarantees to all citizens the right to freedom of speech and expression, subject to reasonable restrictions under Article 19(2) such as public order, decency, or morality.",
        metadata={"source": "Constitution of India", "section": "Article 19"}
    ),
    Document(
        page_content="Ratanlal & Dhirajlal on the Law of Crimes (IPC): Section 302 of the IPC (now BNS) prescribes punishment for murder. It is a non-bailable and cognizable offense, requiring establishing mens rea (criminal intent).",
        metadata={"source": "Indian Penal Code Textbook", "section": "Murder"}
    ),
    Document(
        page_content="Anticipatory Bail under Section 438 of the CrPC (now Section 482 of BNSS) is an extraordinary remedy. It is granted only in exceptional cases where the applicant has reason to believe they may be arrested on false accusations.",
        metadata={"source": "Criminal Procedure Textbook", "section": "Bail"}
    ),
    Document(
        page_content="Mulla on the Transfer of Property Act: Section 54 defines a 'Sale' as a transfer of ownership in exchange for a price paid. A registered instrument is mandatory for immovable property worth Rs. 100 or upwards.",
        metadata={"source": "Transfer of Property Act Textbook", "section": "Section 54"}
    ),
    Document(
        page_content="Indian Contract Act (Section 73): Compensation for loss or damage caused by breach of contract. Damages must naturally arise in the usual course of things from such breach, or which the parties knew to be likely to result.",
        metadata={"source": "Indian Contract Act Textbook", "section": "Breach of Contract"}
    ),
]

def init_vector_store():
    """Initializes the FAISS vector store with our knowledge base."""
    print("[RAG] Initializing local FAISS Vector Store...")
    vector_store = FAISS.from_documents(KNOWLEDGE_BASE, get_embeddings())
    vector_store.save_local(RAG_DB_PATH)
    print("[RAG] FAISS initialized successfully.")
    return vector_store

def get_vector_store():
    """Loads the vector store, creating it if it doesn't exist."""
    if os.path.exists(RAG_DB_PATH):
        return FAISS.load_local(RAG_DB_PATH, get_embeddings(), allow_dangerous_deserialization=True)
    else:
        return init_vector_store()

def retrieve_rag_context(query: str, k: int = 3) -> str:
    """
    Given a legal query, retrieves the most relevant textbook/constitutional
    excerpts via semantic vector search.
    """
    try:
        store = get_vector_store()
        results = store.similarity_search(query, k=k)
        
        if not results:
            return "No relevant constitutional or textbook knowledge found."
            
        context = "=== CONSTITUTIONAL & TEXTBOOK KNOWLEDGE (RAG) ===\n"
        for i, res in enumerate(results):
            src = res.metadata.get("source", "Unknown")
            sec = res.metadata.get("section", "Unknown")
            context += f"{i+1}. [{src} - {sec}]: {res.page_content}\n"
        
        return context
    except Exception as e:
        print(f"[RAG Error] {e}")
        return ""
