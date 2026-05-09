"""
RAG Retriever Agent
===================
Runs before the routing and specialist agents to retrieve relevant context
from the local FAISS database (Indian Constitution, IPC, textbooks, etc.).
This context is added to the state so all subsequent LLMs are grounded in
the actual legal texts.
"""

from rag.pipeline import retrieve_rag_context

def node_rag_retriever(state: dict) -> dict:
    print("\n" + "=" * 60)
    print(">>> RAG RETRIEVER: Searching Local Document Database")
    print("=" * 60)
    
    query = state.get("user_query", "")
    print(f"    [*] Extracting context for: '{query}'")
    
    # Retrieve top 4 relevant chunks
    rag_context = retrieve_rag_context(query, k=4)
    
    print("    [+] Context retrieved successfully.")
    
    return {
        "rag_context": rag_context
    }
