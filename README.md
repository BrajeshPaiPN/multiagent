# Multi-Agent Legal Intelligence System (MALIS)

MALIS is a state-of-the-art, multi-agent legal engine designed to provide high-fidelity legal research, drafting, and verification for the Indian judicial landscape. It moves beyond simple chatbots by implementing a **"Git-for-Law"** infrastructure that treats legal precedents and statutes as a version-controlled knowledge graph.

## 🏛️ Core Architecture

The system is built on a sophisticated multi-stage pipeline orchestrated by **LangGraph**:

1.  **AKGP (Augmented Knowledge Graph Pipeline)**:
    *   A deterministic Neo4j property graph that serves as the "Source of Truth."
    *   Tracks judicial hierarchy (Supreme Court vs. High Courts) and case status (Overruled, Valid, Dissent).
    *   Ensures that "Bad Law" is never cited as binding authority.

2.  **Semantic Vector RAG (FAISS)**:
    *   Indexes over **38+ legal textbooks and primary statutes** (BNS, BNSS, BSA, IPC, Constitution).
    *   Uses semantic similarity to provide agents with deep theoretical context, ensuring advice is grounded in codified law.

3.  **Specialized Multi-Agent Swarm**:
    *   **Router**: Classifies queries into legal domains (Criminal, Civil, Real Estate, Patents, etc.).
    *   **Domain Experts**: Specialist agents trained on specific jurisdictional rules.
    *   **Critic Agent**: Performs an unbiased review of the initial draft for legal consistency.
    *   **Hallucination Verifier**: A dual-LLM verification stage (Llama 3.1 8B vs. Gemma 2 9B) that cross-checks citations against the AKGP Graph.

4.  **Master Synthesizer**:
    *   Compiles the expert analysis, verified citations, and critic feedback into a premium legal memorandum.

## 🚀 Novelty & Difference

Unlike generic LLM wrappers, MALIS introduces several unique innovations:

*   **Deterministic Outcomes**: By prioritizing the **AKGP Graph** over LLM internal knowledge, the system provides a deterministic "ground truth" for case validity. If a case is marked as overruled in the graph, the system *cannot* hallucinate it as valid.
*   **BNS-Ready Implementation**: Built for the 2024 transition in Indian law, the system maps IPC/CrPC sections to their **Bharatiya Nyaya Samhita (BNS)** counterparts in real-time.
*   **Hierarchical Reasoning**: The system understands that a Supreme Court ruling overrides a High Court ruling, even if the High Court ruling is newer.
*   **Dual-Model Verification**: Uses architecturally independent model families to prevent correlated hallucinations, achieving a high citation accuracy rate.

## ✨ Key Features

*   **OCR-Enabled Ingestion**: Upload traffic tickets, court notices, or contracts directly.
*   **Provenance-Aware Citations**: Every citation includes a verification badge (Verified, Cautioned, or Rejected).
*   **Multi-Domain Analysis**: Handles complex cases that span multiple legal areas (e.g., a real estate dispute involving criminal fraud).
*   **Counsel vs. Citizen Modes**: Tailors output complexity for either legal professionals or common citizens.

## 🛠️ Tech Stack

*   **Backend**: FastAPI, Python 3.14+
*   **Graph DB**: Neo4j (AKGP Protocol)
*   **Vector DB**: FAISS (HuggingFace Embeddings)
*   **Orchestration**: LangGraph, LangChain
*   **LLMs**: Groq (Llama 3.3 70B, Llama 3.1 8B, Gemma 2 9B), Google Gemini 2.5 Flash

---
*Disclaimer: This system is an AI research assistant and does not constitute legal advice. Always consult with a qualified legal professional.*
