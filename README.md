# ☁️ Cloud-API Legal Intelligence System

A **multi-agent legal research system** that uses AI to analyze legal queries, search a knowledge graph of case law, detect overruled precedents, and generate verified legal opinions.

## Architecture

```
[User Query] → Extractor → Searcher → Shepardizer → Drafter → [Legal Opinion]
                                           ↓ (bad law detected)
                                        Error Log → Drafter (with warnings)
```

### Agents

| Agent | Role | Technology |
|-------|------|-----------|
| **Extractor** | Extracts legal entities (concepts, statutes, case names) from the user query | Gemini 1.5 Pro + Pydantic Structured Output |
| **Searcher** | Queries the Neo4j knowledge graph for relevant precedents and conflicts | Neo4j Cypher |
| **Shepardizer** | Deterministic verifier — blocks overruled cases (NO AI, pure Python FSM) | Python Logic |
| **Drafter** | Generates final legal opinion using ONLY verified precedents | Gemini 1.5 Pro |

### Key Technologies

- **LangGraph** — Deterministic multi-agent state machine orchestration
- **Neo4j** — Adaptive Knowledge Graph Protocol (AKGP) with conflict-preserving memory
- **Gemini 1.5 Pro** — LLM with Pydantic structured outputs for strict instruction following
- **Pydantic** — Enforces JSON schema contracts on AI outputs

---

## Prerequisites

1. **Python 3.10+**
2. **Google Gemini API Key** — Get from [Google AI Studio](https://aistudio.google.com)
3. **Neo4j AuraDB Instance** — Free tier at [Neo4j Aura](https://console.neo4j.io)

---

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize the Neo4j Database

Open your **Neo4j Workspace console** (or Neo4j Browser) and run the Cypher script in `setup_database.cypher`. This creates:

- A `LegalIssue` node for "Anticipatory Bail" (BNSS 482)
- Two `Precedent` nodes: *State v. Sharma* (2022) and *Union v. Singh* (2024)
- An `OVERRULES` edge from *Singh* → *Sharma* (marking Sharma as bad law)

### 3. Configure Credentials

Copy the example env file and fill in your credentials:

```bash
cp .env.example .env
```

Then either:
- **Option A:** Set environment variables before running:
  ```bash
  export GOOGLE_API_KEY="your-gemini-key"
  export NEO4J_URI="neo4j+s://xxxxx.databases.neo4j.io"
  export NEO4J_USER="neo4j"
  export NEO4J_PASSWORD="your-password"
  ```
- **Option B:** Edit the values directly in `legal_ai_system.py` (for quick testing only — don't commit secrets!)

---

## Running the System

```bash
python legal_ai_system.py
```

### What Happens

1. **Extractor** uses Gemini to isolate "Anticipatory Bail" and "State v. Sharma" into a strict JSON list.
2. **Searcher** queries Neo4j and finds both *Sharma* and *Singh*. It also detects the `OVERRULES` relationship.
3. **Shepardizer** (pure Python FSM) sees the overrule edge, **blocks** *Sharma* as "bad law," and appends a rejection to the error log.
4. **Drafter** writes the final opinion. Because of the LangGraph state, it **cannot** cite *Sharma* as good law. It informs the user that *Sharma* was overruled by *Union v. Singh*.

### Example Output

```
📋 USER QUERY:
   "My client made a verbal threat online and the police are looking for him.
    Can we get Anticipatory Bail based on the State v. Sharma precedent?"

🔍 AGENT 1: Extracting entities...
   Extracted: ["Anticipatory Bail", "State v. Sharma", "BNSS 482"]

🗄️  AGENT 2: Querying knowledge graph...
   Found 2 case record(s)
   [⚠️ OVERRULED] State v. Sharma
   [✅ VALID] Union v. Singh

⚖️  AGENT 3: Verifying precedents...
   ❌ REJECTED: 'State v. Sharma' is BAD LAW.
   ✅ VERIFIED: 'Union v. Singh' is GOOD LAW.

📝 AGENT 4: Drafting legal opinion...

═══════════════════════════════════════
📄 FINAL LEGAL OPINION:
═══════════════════════════════════════
The State v. Sharma precedent CANNOT be relied upon as it has been
overruled by Union v. Singh (2024)...
```

---

## Project Structure

```
multiagent/
├── legal_ai_system.py      # Main multi-agent system (all 4 agents + LangGraph)
├── setup_database.cypher    # Neo4j initialization script
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
└── README.md                # This file
```

---

## How the AKGP Works

The **Adaptive Knowledge Graph Protocol** is the core innovation. Instead of just storing cases, the Neo4j graph stores *conflict relationships* between cases:

```
(Union v. Singh 2024) --[OVERRULES]--> (State v. Sharma 2022)
                                         ↑
                                    reason: "Insufficient evidentiary
                                             standard in lower court"
```

When the Searcher queries for cases, it also retrieves these `OVERRULES` edges. The Shepardizer then uses pure deterministic logic (no AI) to block any overruled case from reaching the Drafter. This makes hallucination about bad law **structurally impossible**.

---

## License

This project is for educational and research purposes.
