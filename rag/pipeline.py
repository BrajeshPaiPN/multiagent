"""
RAG Pipeline (Semantic Legal Knowledge Retrieval)
=================================================
Retrieves context from the FAISS vector database using semantic similarity.
This allows the AI to ground its legal advice in the actual text of 
uploaded textbooks and statutes.
"""
import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

INDEX_PATH = os.path.join(os.path.dirname(__file__), "faiss_index")

# Global variables for caching the vector store
_VECTOR_STORE = None
_EMBEDDINGS = None

def _get_vector_store():
    """Lazily loads the FAISS index and embedding model."""
    global _VECTOR_STORE, _EMBEDDINGS
    
    if _VECTOR_STORE is not None:
        return _VECTOR_STORE
        
    try:
        if not os.path.exists(INDEX_PATH):
            print(f"[RAG] FAISS index not found at {INDEX_PATH}. Falling back to empty context.")
            return None
            
        if _EMBEDDINGS is None:
            _EMBEDDINGS = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            
        _VECTOR_STORE = FAISS.load_local(
            INDEX_PATH, 
            _EMBEDDINGS, 
            allow_dangerous_deserialization=True
        )
        print("[RAG] Semantic Vector Store loaded successfully.")
        return _VECTOR_STORE
        
    except Exception as e:
        print(f"[RAG Error] Failed to load vector store: {e}")
        return None


def retrieve_rag_context(query: str, k: int = 4) -> str:
    """
    Retrieves semantic context from the indexed legal documents.
    """
    try:
        vectorstore = _get_vector_store()
        if not vectorstore:
            return "No relevant legal textbook knowledge found (Index missing)."

        # Perform semantic search
        docs = vectorstore.similarity_search(query, k=k)
        
        if not docs:
            return "No relevant legal knowledge found in uploaded documents."

        context = "=== CONSTITUTIONAL & STATUTORY KNOWLEDGE (RAG) ===\n"
        for i, doc in enumerate(docs):
            src = doc.metadata.get("source", "Unknown")
            context += f"{i+1}. [Source: {src}]: {doc.page_content}\n"

        print(f"[RAG] Retrieved {len(docs)} relevant chunks from indexed documents.")
        return context

    except Exception as e:
        print(f"[RAG Error] Retrieval failed: {e}")
        return ""
