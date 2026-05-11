"""
Traffic Law Specialist Agent
===============================
A self-contained agent that handles traffic-law / motor-vehicle queries end-to-end:
  1. Extracts traffic-specific entities (MVA sections, challan types, violations)
  2. Queries the Neo4j knowledge graph for traffic/MVA precedents
  3. Shepardizes (verifies) retrieved cases using deterministic AKGP rules
  4. Synthesizes a traffic-law-specific legal opinion

Specialization keywords: Motor Vehicles Act, challan, traffic violation,
driving licence, hit-and-run, drunken driving, over-speeding, road accident.
"""

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from typing import List
from config import LLM_ANALYZER, LLM_SYNTHESIZER
from akgp.graph_manager import AKGPGraphManager
from akgp.hierarchy import compute_hierarchy_score


# ---------------------------------------------------------------------------
# 1. Extraction schema tailored to traffic law
# ---------------------------------------------------------------------------
class TrafficQueryAnalysis(BaseModel):
    """Structured extraction for traffic-law queries."""
    violation_type: str = Field(
        default="",
        description="Type of violation: 'speeding', 'drunken_driving', 'signal_jump', 'no_licence', 'hit_and_run', 'other'"
    )
    statutes: List[str] = Field(
        default_factory=list,
        description="MVA / traffic statutes (e.g., 'MVA S.185', 'MVA S.184', 'MVA S.134')"
    )
    case_names: List[str] = Field(
        default_factory=list,
        description="Case citations"
    )
    challan_details: str = Field(
        default="",
        description="Challan or fine details if mentioned"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Other traffic keywords (e.g., 'e-challan', 'penalty', 'suspension')"
    )
    jurisdiction_hint: str = Field(
        default="central",
        description="Likely jurisdiction (state name or 'central')"
    )


# ---------------------------------------------------------------------------
# 2. Main node function
# ---------------------------------------------------------------------------
def node_traffic_agent(state: dict) -> dict:
    """Full traffic-law pipeline: extract → research → verify → synthesize."""
    print("\n" + "=" * 60)
    print(">>> TRAFFIC LAW SPECIALIST AGENT")
    print("=" * 60)
    query = state["user_query"]
    print(f'    Query: "{query}"')

    # ── STEP 1: Domain-specific entity extraction ─────────────────────────
    print("\n    [1/4] Extracting traffic-law entities …")
    try:
        llm = ChatGroq(model=LLM_ANALYZER, temperature=0)
        structured_llm = llm.with_structured_output(TrafficQueryAnalysis)

        extraction_prompt = (
            "You are an expert traffic-law NLP system specialised in the Indian "
            "Motor Vehicles Act 1988 (as amended 2019), traffic rules, and "
            "road-safety regulations. Extract all traffic-law entities from "
            "the following query.\n\n"
            f"Query: '{query}'"
        )
        analysis = structured_llm.invoke(extraction_prompt)

        all_entities = list(set(
            analysis.statutes + analysis.case_names + analysis.keywords
        ))
        if analysis.violation_type:
            all_entities.append(analysis.violation_type)
        print(f"          Entities: {all_entities}")
    except Exception as e:
        print(f"    [!] Extraction error: {e}")
        all_entities = [query]
        analysis = None

    # ── STEP 2: Knowledge-graph research ──────────────────────────────────
    print("\n    [2/4] Querying Neo4j knowledge graph …")
    graph = AKGPGraphManager()
    try:
        raw_results = graph.search_by_entities(all_entities)
        category_results = graph.search_by_category("Traffic Law")

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

    # ── STEP 3: Shepardize ────────────────────────────────────────────────
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

    # ── STEP 4: Synthesize traffic-law opinion ────────────────────────────
    print("\n    [4/4] Generating traffic-law opinion …")
    verified_str = _format_cases(verified, "SAFE_TO_CITE")
    cautioned_str = _format_cases(cautioned, "CITE_WITH_CAUTION") or "None."
    rejection_str = "\n".join(error_log) or "None."

    prompt = f"""You are a senior advocate with 25+ years specialising in Indian motor-vehicle and traffic law.
Write a COMPREHENSIVE, DETAILED legal opinion answering the user's query.
This must be thorough — at least 800-1000 words. Cover every angle.

NOTE: When criminal charges arise from traffic incidents (rash driving, hit-and-run,
causing death by negligence), cite **BNS (Bharatiya Nyaya Sanhita, 2023)** sections
as primary law (not IPC). Include old IPC section in parentheses for reference.
E.g.: "BNS Section 106 (formerly IPC Section 304A) — Death by Negligence"

=== DOMAIN FOCUS ===
Focus on: Motor Vehicles Act 1988 (as amended 2019), traffic violations and
penalties, e-challan procedures, compounding of offences,
driving licence suspension / revocation, drunken driving (S.185),
dangerous driving (S.184), hit-and-run provisions (S.134/161),
accident compensation under Motor Accident Claims Tribunal (MACT),
and procedures for contesting traffic tickets.

=== STRICT RULES ===
1. Cite ONLY cases marked SAFE_TO_CITE as binding authority. Give full citations.
2. Explain in detail why DO_NOT_CITE cases are bad law and what replaced them.
3. Discuss both sides for CITE_WITH_CAUTION cases with balanced analysis.
4. Include Hierarchy Score (H) when citing cases.
5. Provide specific, actionable advice with step-by-step guidance.
6. If the query relates to ongoing/pending matters (e.g., road safety regulations,
   MVA 2019 implementation challenges), discuss the ONGOING STATUS.

=== USER QUERY ===
{query}

=== VERIFIED PRECEDENTS (SAFE_TO_CITE) ===
{verified_str or 'No valid precedents found.'}

=== CAUTIONED PRECEDENTS ===
{cautioned_str}

=== REJECTION WARNINGS ===
{rejection_str}

=== OUTPUT FORMAT ===
1. EXECUTIVE SUMMARY (thorough 4-5 sentences)
2. APPLICABLE TRAFFIC / MVA PROVISIONS (explain each section)
3. VIOLATION ANALYSIS & PENALTIES (detailed breakdown)
4. DETAILED CASE ANALYSIS (for each case: facts, ratio, application)
5. REJECTED PRECEDENTS (why overruled and what replaced them)
6. CONTESTING STRATEGY (step-by-step with courts, documents, timelines)
7. LICENCE & INSURANCE IMPLICATIONS (detailed)
8. ONGOING DEVELOPMENTS (if any related MVA/traffic matter is pending)
9. RISK ASSESSMENT (honest analysis)
10. CONCLUSION (clear recommendation with next steps)
"""

    try:
        synth_llm = ChatGroq(model=LLM_SYNTHESIZER, temperature=0)
        response = synth_llm.invoke(prompt)
        final_text = response.content
    except Exception as e:
        print(f"    [!] Synthesis error: {e}")
        final_text = f"[ERROR] Could not generate traffic-law opinion: {e}"

    print("    Draft complete.")
    return {
        "expert_drafts": [{
            "domain": "Traffic Law",
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
