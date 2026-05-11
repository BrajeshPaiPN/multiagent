"""
Criminal Law Specialist Agent
===============================
A self-contained agent that handles criminal law queries end-to-end:
  1. Extracts criminal-law-specific entities (IPC/BNS sections, FIR details, bail concepts)
  2. Queries the Neo4j knowledge graph for criminal precedents
  3. Shepardizes (verifies) retrieved cases using deterministic AKGP rules
  4. Synthesizes a criminal-law-specific legal opinion

Specialization keywords: mens rea, actus reus, bail, anticipatory bail,
IPC, BNS, BNSS, CrPC, FIR, chargesheet, sentencing, parole.
"""

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from typing import List
from config import LLM_ANALYZER, LLM_SYNTHESIZER
from akgp.graph_manager import AKGPGraphManager
from akgp.hierarchy import compute_hierarchy_score


# ---------------------------------------------------------------------------
# 1. Extraction schema tailored to criminal law
# ---------------------------------------------------------------------------
class CriminalQueryAnalysis(BaseModel):
    """Structured extraction for criminal-law queries."""
    offences: List[str] = Field(
        default_factory=list,
        description="Criminal offences mentioned (e.g., 'Murder', 'Theft', 'Cheating')"
    )
    statutes: List[str] = Field(
        default_factory=list,
        description="Penal statutes / sections (e.g., 'IPC 302', 'BNS 103', 'BNSS 482')"
    )
    case_names: List[str] = Field(
        default_factory=list,
        description="Case citations (e.g., 'State v. Sharma')"
    )
    bail_type: str = Field(
        default="",
        description="Type of bail if applicable: 'regular', 'anticipatory', 'interim', or empty"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Other criminal-law keywords (e.g., 'FIR', 'chargesheet', 'mens rea')"
    )
    severity: str = Field(
        default="High",
        description="Severity: 'Critical' (life/liberty), 'High', 'Medium', 'Low'"
    )
    jurisdiction_hint: str = Field(
        default="central",
        description="Likely jurisdiction (state name or 'central')"
    )


# ---------------------------------------------------------------------------
# 2. Main node function
# ---------------------------------------------------------------------------
def node_criminal_agent(state: dict) -> dict:
    """Full criminal-law pipeline: extract → research → verify → synthesize."""
    print("\n" + "=" * 60)
    print(">>> CRIMINAL LAW SPECIALIST AGENT")
    print("=" * 60)
    query = state["user_query"]
    print(f'    Query: "{query}"')

    # ── STEP 1: Domain-specific entity extraction ─────────────────────────
    print("\n    [1/4] Extracting criminal-law entities …")
    try:
        llm = ChatGroq(model=LLM_ANALYZER, temperature=0)
        structured_llm = llm.with_structured_output(CriminalQueryAnalysis)

        extraction_prompt = (
            "You are an expert criminal-law NLP system specialised in Indian "
            "criminal law (IPC, BNS, CrPC, BNSS). Extract all criminal-law "
            "entities from the following query.\n\n"
            f"Query: '{query}'"
        )
        analysis = structured_llm.invoke(extraction_prompt)

        all_entities = list(set(
            analysis.offences + analysis.statutes +
            analysis.case_names + analysis.keywords
        ))
        if analysis.bail_type:
            all_entities.append(analysis.bail_type + " bail")

        print(f"          Entities: {all_entities}")
        print(f"          Severity: {analysis.severity}")
    except Exception as e:
        print(f"    [!] Extraction error: {e}")
        all_entities = [query]
        analysis = None

    # ── STEP 2: Knowledge-graph research ──────────────────────────────────
    print("\n    [2/4] Querying Neo4j knowledge graph …")
    graph = AKGPGraphManager()
    try:
        raw_results = graph.search_by_entities(all_entities)
        category_results = graph.search_by_category("Criminal Law")

        existing = {r["case_name"] for r in raw_results}
        category_results = [r for r in category_results if r["case_name"] not in existing]
        all_results = raw_results + category_results
        print(f"          Found {len(all_results)} case(s)")

        conflict_chains = []
        for rec in raw_results:
            if rec.get("overrulers"):
                chain = graph.get_conflict_chain(rec["case_name"])
                if chain:
                    conflict_chains.extend(chain)

        statute_amendments = []
        if analysis:
            for statute in analysis.statutes:
                amends = graph.get_statute_amendments(statute)
                if amends:
                    statute_amendments.extend(amends)
    finally:
        graph.close()

    # ── STEP 3: Shepardize (deterministic verification) ───────────────────
    print("\n    [3/4] Shepardizing retrieved cases …")
    query_jurisdiction = (analysis.jurisdiction_hint if analysis else "central")
    verified, rejected, cautioned = [], [], []
    error_log, hierarchy_scores = [], {}

    for record in all_results:
        case_name = record.get("case_name")
        if not case_name:
            continue

        h_score = compute_hierarchy_score(
            court=record.get("court", "District Court"),
            year=record.get("year", 2020),
            case_jurisdiction=record.get("jurisdiction", "central"),
            query_jurisdiction=query_jurisdiction,
        )
        hierarchy_scores[case_name] = round(h_score, 2)
        enriched = {**record, "hierarchy_score": round(h_score, 2)}

        if record.get("overrulers"):
            enriched["recommendation"] = "DO_NOT_CITE"
            rejected.append(enriched)
            ovr = record["overrulers"][0]
            error_log.append(
                f"REJECTED: '{case_name}' overruled by '{ovr.get('name')}' "
                f"(Reason: {ovr.get('reason', 'N/A')})"
            )
        elif record.get("dissenters"):
            enriched["recommendation"] = "CITE_WITH_CAUTION"
            cautioned.append(enriched)
        else:
            enriched["recommendation"] = "SAFE_TO_CITE"
            verified.append(enriched)

    verified.sort(key=lambda x: x["hierarchy_score"], reverse=True)
    print(f"          Verified: {len(verified)}, Cautioned: {len(cautioned)}, Rejected: {len(rejected)}")

    # ── STEP 4: Synthesize criminal-law opinion ───────────────────────────
    print("\n    [4/4] Generating criminal-law opinion …")
    verified_str = _format_cases(verified, "SAFE_TO_CITE")
    cautioned_str = _format_cases(cautioned, "CITE_WITH_CAUTION") or "None."
    rejection_str = "\n".join(error_log) or "None."

    prompt = f"""You are a senior criminal-law advocate with 25+ years specialising in Indian criminal law.
Write a COMPREHENSIVE, DETAILED legal opinion answering the user's query.
This must be thorough — at least 800-1000 words. Cover every angle.

=== CRITICAL: NEW CRIMINAL LAW REGIME (effective 1 July 2024) ===
India has replaced its colonial-era criminal statutes:
  • Indian Penal Code (IPC, 1860) → replaced by **Bharatiya Nyaya Sanhita (BNS, 2023)**
  • Code of Criminal Procedure (CrPC, 1973) → replaced by **Bharatiya Nagarik Suraksha Sanhita (BNSS, 2023)**
  • Indian Evidence Act (1872) → replaced by **Bharatiya Sakshya Adhiniyam (BSA, 2023)**

YOU MUST:
  1. Cite BNS/BNSS/BSA sections as the PRIMARY current law in all analysis.
  2. Include the corresponding old IPC/CrPC/Evidence Act section in parentheses
     for cross-reference, e.g.: "BNS Section 103 (formerly IPC Section 302) — Murder"
  3. When discussing older landmark cases that used IPC sections, cite the IPC section
     as used in the judgment BUT note the current BNS equivalent.
  4. Highlight any substantive differences between old and new provisions where relevant.

=== DOMAIN FOCUS ===
Focus on: mens rea, actus reus, bail conditions (regular / anticipatory / interim),
BNS/BNSS sections (and their IPC/CrPC equivalents), evidentiary burden under BSA,
FIR procedures under BNSS, chargesheet timelines, sentencing guidelines, and parole.

=== STRICT RULES ===
1. Cite cases marked SAFE_TO_CITE as binding authority. If none are provided or if additional landmark cases are relevant, YOU MUST proactively cite landmark judgments from your own knowledge. Always provide the full case name and year (e.g., "Kesavananda Bharati v. State of Kerala (1973)").
2. Explain in detail why DO_NOT_CITE cases are bad law and what replaced them.
3. Discuss both sides for CITE_WITH_CAUTION cases with balanced analysis.
4. Include Hierarchy Score (H) when citing cases.
5. Provide specific, actionable criminal-defence / prosecution strategy with step-by-step guidance.
6. If the query relates to a famous ongoing/pending criminal case or a constitutional
   challenge in criminal law (e.g., marital rape exception, death penalty
   moratorium, sedition law repeal under BNS), discuss the ONGOING STATUS with arguments
   from both sides and current procedural position before the court.

=== USER QUERY ===
{query}

=== VERIFIED PRECEDENTS (SAFE_TO_CITE) ===
{verified_str or 'No valid precedents found.'}

=== CAUTIONED PRECEDENTS ===
{cautioned_str}

=== REJECTION WARNINGS ===
{rejection_str}

=== OUTPUT FORMAT ===
1. EXECUTIVE SUMMARY (thorough 4-5 sentences, not a one-liner)
2. APPLICABLE CRIMINAL PROVISIONS — cite BNS/BNSS/BSA as primary, IPC/CrPC in parentheses
3. DETAILED CASE ANALYSIS (for each case: facts, ratio, how it applies here)
4. REJECTED PRECEDENTS (why they were overruled and what replaced them)
5. CRIMINAL DEFENCE / PROSECUTION STRATEGY (specific, step-by-step)
6. BAIL ANALYSIS (if applicable — type, conditions, likely outcome, precedents)
7. ONGOING APPEALS & DEVELOPMENTS (if any related landmark matter is pending before SC/HC)
8. RISK ASSESSMENT (honest assessment of strengths and weaknesses)
9. CONCLUSION (clear recommendation with next steps)
"""

    try:
        synth_llm = ChatGroq(model=LLM_SYNTHESIZER, temperature=0)
        response = synth_llm.invoke(prompt)
        final_text = response.content
    except Exception as e:
        print(f"    [!] Synthesis error: {e}")
        final_text = f"[ERROR] Could not generate criminal-law opinion: {e}"

    print("    Draft complete.")
    return {
        "expert_drafts": [{
            "domain": "Criminal Law",
            "draft": final_text,
            "verified_cases": verified,
            "rejected_cases": rejected,
            "error_log": error_log
        }]
    }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _format_cases(cases: list, label: str) -> str:
    out = ""
    for c in cases:
        out += (
            f"- {c['case_name']} ({c.get('court', '?')}, {c.get('year', '?')}) "
            f"[H={c.get('hierarchy_score', 'N/A')}] [{label}]\n"
            f"  Verdict: {c.get('verdict', 'N/A')}\n"
            f"  Issue: {c.get('legal_issue', 'N/A')} ({c.get('section', '')})\n\n"
        )
    return out
