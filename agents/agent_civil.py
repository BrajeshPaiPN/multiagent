"""
Civil Law Specialist Agent
============================
A self-contained agent that handles civil law queries end-to-end:
  1. Extracts civil-law-specific entities (contract clauses, torts, CPC sections)
  2. Queries the Neo4j knowledge graph for civil precedents
  3. Shepardizes (verifies) retrieved cases using deterministic AKGP rules
  4. Synthesizes a civil-law-specific legal opinion

Specialization keywords: torts, contracts, breach, damages, specific performance,
injunction, CPC, limitation period, consumer disputes, negligence.
"""

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from typing import List
from config import LLM_ANALYZER, LLM_SYNTHESIZER
from akgp.graph_manager import AKGPGraphManager
from akgp.hierarchy import compute_hierarchy_score


# ---------------------------------------------------------------------------
# 1. Extraction schema tailored to civil law
# ---------------------------------------------------------------------------
class CivilQueryAnalysis(BaseModel):
    """Structured extraction for civil-law queries."""
    cause_of_action: List[str] = Field(
        default_factory=list,
        description="Causes of action (e.g., 'breach of contract', 'negligence', 'defamation')"
    )
    statutes: List[str] = Field(
        default_factory=list,
        description="Civil statutes / sections (e.g., 'CPC Order 39', 'Indian Contract Act S.73')"
    )
    case_names: List[str] = Field(
        default_factory=list,
        description="Case citations (e.g., 'Hadley v. Baxendale')"
    )
    relief_sought: List[str] = Field(
        default_factory=list,
        description="Reliefs sought (e.g., 'damages', 'injunction', 'specific performance')"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Other civil-law keywords (e.g., 'limitation period', 'res judicata')"
    )
    severity: str = Field(
        default="Medium",
        description="Severity: 'Critical', 'High', 'Medium', 'Low'"
    )
    jurisdiction_hint: str = Field(
        default="central",
        description="Likely jurisdiction (state name or 'central')"
    )


# ---------------------------------------------------------------------------
# 2. Main node function
# ---------------------------------------------------------------------------
def node_civil_agent(state: dict) -> dict:
    """Full civil-law pipeline: extract → research → verify → synthesize."""
    print("\n" + "=" * 60)
    print(">>> CIVIL LAW SPECIALIST AGENT")
    print("=" * 60)
    query = state["user_query"]
    print(f'    Query: "{query}"')

    # ── STEP 1: Domain-specific entity extraction ─────────────────────────
    print("\n    [1/4] Extracting civil-law entities …")
    try:
        llm = ChatGroq(model=LLM_ANALYZER, temperature=0)
        structured_llm = llm.with_structured_output(CivilQueryAnalysis)

        extraction_prompt = (
            "You are an expert civil-law NLP system specialised in Indian "
            "civil law (CPC, Indian Contract Act, Specific Relief Act, "
            "Limitation Act, Consumer Protection Act). Extract all civil-law "
            "entities from the following query.\n\n"
            f"Query: '{query}'"
        )
        analysis = structured_llm.invoke(extraction_prompt)

        all_entities = list(set(
            analysis.cause_of_action + analysis.statutes +
            analysis.case_names + analysis.relief_sought +
            analysis.keywords
        ))
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
        category_results = graph.search_by_category("Civil Law")

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

    # ── STEP 4: Synthesize civil-law opinion ──────────────────────────────
    print("\n    [4/4] Generating civil-law opinion …")
    verified_str = _format_cases(verified, "SAFE_TO_CITE")
    cautioned_str = _format_cases(cautioned, "CITE_WITH_CAUTION") or "None."
    rejection_str = "\n".join(error_log) or "None."

    prompt = f"""You are a senior civil-law advocate with 25+ years specialising in Indian civil law.
Write a COMPREHENSIVE, DETAILED legal opinion answering the user's query.
This must be thorough — at least 800-1000 words. Cover every angle.

=== DOMAIN FOCUS ===
Focus on: causes of action, breach of contract, tortious liability, 
specific performance (Specific Relief Act), injunctions (CPC Order 39), 
limitation periods (Limitation Act), consumer disputes (Consumer Protection Act),
damages computation, res judicata, and civil procedure.

=== STRICT RULES ===
1. Cite cases marked SAFE_TO_CITE as binding authority. If none are provided or if additional landmark cases are relevant, YOU MUST proactively cite landmark judgments from your own knowledge. Always provide the full case name and year (e.g., "Kesavananda Bharati v. State of Kerala (1973)").
2. Explain in detail why DO_NOT_CITE cases are bad law and what replaced them.
3. Discuss both sides for CITE_WITH_CAUTION cases with balanced analysis.
4. Include Hierarchy Score (H) when citing cases.
5. Provide specific, actionable litigation strategy with step-by-step guidance.
6. If the query relates to a famous ongoing/pending civil matter or constitutional
   challenge (e.g., Places of Worship Act challenges, property rights disputes under
   Article 300A, consumer protection evolution), discuss the ONGOING STATUS with
   arguments from both sides and current procedural position.

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
2. APPLICABLE CIVIL PROVISIONS (explain each section's relevance)
3. CAUSE OF ACTION ANALYSIS (detailed breakdown)
4. DETAILED CASE ANALYSIS (for each case: facts, ratio, application)
5. REJECTED PRECEDENTS (why overruled and what replaced them)
6. RELIEF & DAMAGES ASSESSMENT (types of relief available, quantum estimation)
7. LITIGATION STRATEGY (step-by-step with courts, documents, timelines)
8. ONGOING APPEALS & DEVELOPMENTS (if any related landmark matter is pending)
9. LIMITATION & PROCEDURAL RISKS (honest assessment)
10. CONCLUSION (clear recommendation with next steps)
"""

    try:
        synth_llm = ChatGroq(model=LLM_SYNTHESIZER, temperature=0)
        response = synth_llm.invoke(prompt)
        final_text = response.content
    except Exception as e:
        print(f"    [!] Synthesis error: {e}")
        final_text = f"[ERROR] Could not generate civil-law opinion: {e}"

    print("    Draft complete.")
    return {
        "expert_drafts": [{
            "domain": "Civil Law",
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
