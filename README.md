# ☁️ Cloud-API Legal Intelligence System

A **production-ready multi-agent legal research system** that uses AI to analyze legal queries, search a massive Neo4j knowledge graph of case law (200,000+ real court judgments), detect overruled precedents, and generate verified legal opinions.

## Architecture

```
[User Query] → Extractor → Searcher → Shepardizer → Drafter → [Legal Opinion]
                                           ↓ (bad law detected)
                                        Error Log → Drafter (with warnings)
```

### Advanced Multi-Agent Orchestration
The system has evolved to include an **Orchestrator** (LangGraph) that manages specialized agents:
- **Router:** Dynamically assigns queries to specialized domain agents (Criminal, Civil, Patents, Real Estate, Traffic).
- **Master Synthesizer:** Aggregates multi-domain legal research into a single brief.
- **Contract Analyzer:** Uses Gemini (1 Million token context) to ingest full contracts and flag hidden pitfalls, severely one-sided terms, and legal ambiguities.
- **Critic:** Evaluates the Master Synthesizer's draft and forces a revision loop if the output lacks rigorous legal citation.

### Key Technologies

- **FastAPI** — Robust REST backend powering the system and static frontend.
- **LangGraph** — Deterministic multi-agent state machine orchestration.
- **Neo4j** — Adaptive Knowledge Graph Protocol (AKGP) storing 200,000+ Indian Court judgments with conflict-preserving memory.
- **Gemini 2.5 Flash / Groq (Llama 3)** — Heterogeneous LLM swarm used across different agents to optimize speed and context windows.

---

## Prerequisites

1. **Python 3.10+**
2. **Google Gemini API Key** — For large-context Contract Analysis and RAG Embeddings.
3. **Groq API Key** — For lightning-fast reasoning agents.
4. **Neo4j AuraDB Instance** — Graph database hosting the legal case corpus.

---

## Setup & Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Credentials
Copy the example env file and fill in your credentials:
```bash
cp .env.example .env
```

### 3. Ingesting the Database
To hydrate the Neo4j database with 200,000 real Supreme Court and High Court judgments, we use the `KanoonGPT/indian-case-laws` HuggingFace dataset.
```bash
# Streams and ingests up to 200,000 cases into Neo4j
python bulk_seed_200k.py
```

### 4. Running the Web Server
Start the FastAPI server:
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```
Navigate to `http://localhost:8000/` to access the modern web interface.

---

## Project Structure

```text
multiagent/
├── api.py                  # FastAPI Backend & Orchestration entry point
├── orchestrator.py         # LangGraph DAG state machine
├── config.py               # Shared configuration and API keys
├── agents/                 # Specialized domain agents & Contract Analyzer
├── frontend/               # Vanilla JS/HTML/CSS web interface
├── rag/                    # Ingestion and chunking logic for PDF contracts
├── bulk_seed_200k.py       # Massive Neo4j ingester (200k cases)
└── requirements.txt        # Python dependencies
```

---

## How the AKGP Works

The **Adaptive Knowledge Graph Protocol** is the core innovation. Instead of just storing cases, the Neo4j graph stores *conflict relationships* between cases:

```text
(Union v. Singh 2024) --[OVERRULES]--> (State v. Sharma 2022)
                                         ↑
                                    reason: "Insufficient evidentiary
                                             standard in lower court"
```

When the Searcher queries for cases, it also retrieves these `OVERRULES` edges. The Shepardizer then uses pure deterministic logic (no AI) to block any overruled case from reaching the Drafter. This makes hallucination about bad law **structurally impossible**.

---

## License

This project is for educational and research purposes.
