"""
RAG Pipeline (India-Specific Legal Knowledge)
==============================================
Provides relevant constitutional and legal textbook context for queries.

MEMORY OPTIMISATION: This module uses a lightweight in-memory keyword/TF-IDF
search instead of FAISS + PyTorch embeddings. This reduces RAM usage from
~1.5 GB to under 50 MB, making it compatible with Render's Free Tier.
External Google Embedding API calls are avoided entirely at query time.
"""
import os
import re
from langchain_core.documents import Document

# ──────────────────────────────────────────────────────────────────────────────
# Static Knowledge Base: Excerpts from Indian Constitution & Legal Textbooks
# ──────────────────────────────────────────────────────────────────────────────
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
    Document(
        page_content="Motor Vehicles Act 1988 (Section 185): Driving under influence of alcohol or drugs is a cognizable offence. If the blood alcohol content exceeds 30mg per 100ml, a fine of Rs 10,000 and/or up to 6 months imprisonment applies for first offence.",
        metadata={"source": "Motor Vehicles Act", "section": "Section 185 - Drunk Driving"}
    ),
    Document(
        page_content="Indian Patent Act 1970 (Section 48): A patent grants the patentee the exclusive right to prevent others from making, using, offering for sale, selling or importing the patented product in India without consent.",
        metadata={"source": "Patents Act Textbook", "section": "Section 48"}
    ),
    Document(
        page_content="Consumer Protection Act 2019: A consumer can file a complaint before the District Commission for goods/services worth up to Rs 1 crore. Deficiency in service and unfair trade practices are actionable under this Act.",
        metadata={"source": "Consumer Protection Act", "section": "District Commission"}
    ),
]


def _tokenize(text: str) -> set:
    """Simple word tokenizer — lowercase, strip punctuation."""
    return set(re.findall(r'\b[a-z]{3,}\b', text.lower()))


def retrieve_rag_context(query: str, k: int = 3) -> str:
    """
    Retrieves the most relevant textbook/constitutional excerpts using
    lightweight keyword overlap scoring (no ML models required).
    """
    try:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return ""

        scored = []
        for doc in KNOWLEDGE_BASE:
            doc_tokens = _tokenize(doc.page_content)
            overlap = len(query_tokens & doc_tokens)
            if overlap > 0:
                scored.append((overlap, doc))

        # Sort by overlap score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        top_docs = [doc for _, doc in scored[:k]]

        if not top_docs:
            return "No relevant constitutional or textbook knowledge found."

        context = "=== CONSTITUTIONAL & TEXTBOOK KNOWLEDGE (RAG) ===\n"
        for i, res in enumerate(top_docs):
            src = res.metadata.get("source", "Unknown")
            sec = res.metadata.get("section", "Unknown")
            context += f"{i+1}. [{src} - {sec}]: {res.page_content}\n"

        print(f"[RAG] Retrieved {len(top_docs)} relevant context chunks.")
        return context

    except Exception as e:
        print(f"[RAG Error] {e}")
        return ""
