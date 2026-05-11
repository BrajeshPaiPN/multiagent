<div align="center">

<img src="frontend/hero_scales.png" alt="NyayaAI Logo" width="160"/>

# ⚖️ NyayaAI — India's Legal Intelligence Engine

**A production-ready, multi-agent AI platform for Indian legal research, case law analysis, and contract risk auditing.**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestrated-blueviolet?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![Neo4j](https://img.shields.io/badge/Neo4j-Knowledge_Graph-008CC1?style=for-the-badge&logo=neo4j)](https://neo4j.com)
[![Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4?style=for-the-badge&logo=google)](https://ai.google.dev)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.1-F54748?style=for-the-badge)](https://groq.com)
[![Railway](https://img.shields.io/badge/Deployed_on-Railway-0B0D0E?style=for-the-badge&logo=railway)](https://railway.app)

</div>

---

## 🌟 What is NyayaAI?

NyayaAI is a **production-grade Multi-Agent Legal Intelligence System** tailored for Indian law. It combines a large-scale **Neo4j knowledge graph** of 200,000+ real court judgments with a swarm of specialized AI agents to deliver:

- ⚡ **Instant legal memoranda** in plain English or formal legal language
- 🔍 **Real case law citations** from the Supreme Court and High Courts of India
- 📄 **Contract risk auditing** with industry-standard benchmarking
- 🚫 **Hallucination prevention** via a deterministic Shepardizer that blocks overruled cases

---

## 🏛️ System Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (api.py)                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              LangGraph Orchestrator (orchestrator.py)                │
│                                                                      │
│  START → [RAG Retriever] → [Router Agent]                           │
│                                    │                                 │
│              ┌─────────────────────┼─────────────────────────┐      │
│              ▼         ▼           ▼           ▼             ▼      │
│        [Criminal]  [Civil]   [Patents]  [Real Estate]  [Traffic]   │
│              └─────────────────────┬─────────────────────────┘      │
│                                    ▼                                 │
│                      [Hallucination Verifier]                        │
│                      (Blocks overruled cases)                        │
│                                    ▼                                 │
│                      [Master Synthesizer]                            │
│                                    ▼                                 │
│                      [Critic Agent] ──► [Revise?] ──┐               │
│                              │                       │               │
│                           [APPROVE]         ◄────────┘               │
│                              ▼                                       │
│                           END                                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 Agent Roster

| Agent | Role | Model |
|---|---|---|
| **RAG Retriever** | Fetches relevant precedents from Neo4j knowledge graph | Neo4j Cypher |
| **Router** | Classifies query into legal domains and fans out to specialists | Llama 3.1-8b (Groq) |
| **Criminal Agent** | Analyzes IPC, CrPC, NDPS, POCSO, bail, and criminal cases | Llama 3.1-8b (Groq) |
| **Civil Agent** | Handles contracts, consumer disputes, property, family law | Llama 3.1-8b (Groq) |
| **Patents Agent** | Specializes in IP, trademarks, Section 3(d) pharmaceutical patents | Llama 3.1-8b (Groq) |
| **Real Estate Agent** | GPA sales, tenancy, eviction, RERA, stamp duty | Llama 3.1-8b (Groq) |
| **Traffic Agent** | MACT, Motor Vehicle Act, drunk driving, accident compensation | Llama 3.1-8b (Groq) |
| **Hallucination Verifier** | Deterministic FSM — blocks overruled/bad-law cases from drafts | Pure Python |
| **Master Synthesizer** | Combines multi-domain expert drafts into a unified memorandum | Llama 3.1-8b (Groq) |
| **Critic Agent** | Quality-checks the memorandum and triggers revision loop if needed | Llama 3.1-8b (Groq) |
| **Contract Analyzer** | Full-document contract risk audit with industry benchmarking | Gemini 2.5 Flash |

---

## 📚 Knowledge Graph — 200,000+ Real Judgments

The Neo4j database is hydrated with **real, non-synthetic** Indian court judgments sourced from:

- 🏛️ [`labofsahil/Indian-Supreme-Court-Judgments`](https://huggingface.co/datasets/labofsahil/Indian-Supreme-Court-Judgments) — 42,846 Supreme Court judgments (1950–2025)
- ⚖️ [`KanoonGPT/indian-case-laws`](https://huggingface.co/datasets/KanoonGPT/indian-case-laws) — 17.1 Million Indian court cases (Supreme Court + all High Courts)

### Graph Schema

```
(:Precedent)──[:APPLIES_TO]──►(:LegalIssue)
(:Precedent)──[:OVERRULES]───►(:Precedent)
(:Precedent)──[:CITES]───────►(:Precedent)
```

The `OVERRULES` relationship is the core of the Adaptive Knowledge Graph Protocol (AKGP) — it makes citing bad law **structurally impossible**.

---

## 📄 Contract Analyzer — Industry-Aware Risk Auditing

Unlike naive contract analyzers that flag everything as "high risk", NyayaAI's contract analyzer:

1. **Identifies the contract type** (Employment, NDA, SaaS, Lease, Service Agreement, etc.)
2. **Benchmarks each clause against industry standards** for that contract type
3. **Labels clauses as** `🏭 Industry Standard` or `⚠️ Non-Standard`
4. **Only raises High risk** for genuinely unusual or exploitative terms
5. **Provides an overall industry assessment** before clause-level analysis

Supports: **PDF, PNG, JPG, JPEG** uploads.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [Neo4j AuraDB](https://console.neo4j.io) (free tier)
- [Google AI Studio API Key](https://aistudio.google.com) (for Gemini)
- [Groq API Key](https://console.groq.com) (for Llama 3.1)

### 1. Clone & Install
```bash
git clone https://github.com/BrajeshPaiPN/multiagent.git
cd multiagent
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```

Edit `.env`:
```env
GOOGLE_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### 3. Seed the Knowledge Graph

**Quick seed (landmark cases only):**
```bash
python seed_database.py
```

**Full seed — 5,000 Supreme Court judgments from HuggingFace:**
```bash
python bulk_seed_hf.py
```

**Massive seed — up to 200,000 Supreme Court + High Court judgments:**
```bash
python bulk_seed_200k.py
```
> ⚠️ The 200k seed streams from a 53GB dataset and will take several hours. Monitor progress in Neo4j: `MATCH (n:Precedent) RETURN count(n)`

### 4. Run the Server
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Navigate to `http://localhost:8000`

---

## 🐳 Docker / Railway Deployment

```bash
docker build -t nyayaai .
docker run -p 8080:8080 --env-file .env nyayaai
```

For Railway, set all environment variables in your service settings and connect the GitHub repo for automatic deploys.

---

## 📁 Project Structure

```text
multiagent/
│
├── api.py                      # FastAPI backend, REST endpoints
├── orchestrator.py             # LangGraph DAG state machine
├── config.py                   # Centralized config & credentials
│
├── agents/
│   ├── router.py               # Domain classifier & fan-out logic
│   ├── agent_criminal.py       # Criminal law specialist
│   ├── agent_civil.py          # Civil law specialist
│   ├── agent_patents.py        # IP/Patent law specialist
│   ├── agent_real_estate.py    # Real estate law specialist
│   ├── agent_traffic.py        # Traffic/MACT specialist
│   ├── agent_default.py        # General fallback agent
│   ├── hallucination_verifier.py  # Deterministic bad-law blocker
│   ├── master_synthesizer.py   # Multi-domain memo combiner
│   ├── critic.py               # Quality critic with revision loop
│   ├── rag_retriever.py        # Neo4j RAG context fetcher
│   └── contract_analyzer.py    # Industry-aware contract auditor
│
├── frontend/
│   ├── index.html              # Single-page premium UI
│   ├── app.js                  # Frontend logic (fetch, rendering)
│   └── style.css               # Dark glassmorphism design system
│
├── rag/
│   └── ingest_pdfs.py          # PDF text extraction utility
│
├── seed_database.py            # Landmark case seeder (manual)
├── bulk_seed_hf.py             # HuggingFace 5k Supreme Court seeder
├── bulk_seed_200k.py           # KanoonGPT 200k case seeder
├── bulk_seed.py                # Indian Kanoon API seeder (legacy)
├── setup_database.cypher       # Neo4j constraints & indexes
├── requirements.txt
├── Dockerfile
└── .env.example
```

---

## ⚙️ Key Design Decisions

| Decision | Rationale |
|---|---|
| **LangGraph over plain LangChain** | Enables deterministic fan-out/fan-in with typed state — no hallucinated routing |
| **Groq for specialist agents** | Sub-second latency for 8B models; keeps pipeline fast |
| **Gemini for contract analysis** | 1M token context window handles full contracts that would exceed Groq's free-tier TPM |
| **Neo4j graph over vector DB** | Enables `OVERRULES` traversal — structurally impossible with flat embeddings |
| **Streaming HuggingFace datasets** | Avoids downloading 53GB locally; processes row-by-row directly into Neo4j |
| **Industry-aware contract review** | Prevents false alarms on boilerplate clauses; builds user trust |

---

## 📜 License

This project is for educational and research purposes. Not a substitute for professional legal advice.

---

<div align="center">
Built with ❤️ for the Indian legal ecosystem
</div>
