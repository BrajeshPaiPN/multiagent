"""
Default / General Legal Agent
================================
Fallback agent for queries that don't match a specific domain
(e.g., constitutional law, tax law, cyber law, family law, environmental law).
Runs a full generic legal pipeline.
"""

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from typing import List
from config import LLM_ANALYZER, LLM_SYNTHESIZER
from akgp.graph_manager import AKGPGraphManager
from akgp.hierarchy import compute_hierarchy_score


class GeneralQueryAnalysis(BaseModel):
    """Structured extraction for general legal queries."""
    legal_concepts: List[str] = Field(
        default_factory=list,
        description="Core legal concepts or doctrines mentioned"
    )
    statutes: List[str] = Field(
        default_factory=list,
        description="Statutes or sections referenced"
    )
    case_names: List[str] = Field(
        default_factory=list,
        description="Specific case citations mentioned"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Other relevant legal keywords"
    )
    primary_category: str = Field(
        default="General",
        description="Best-guess category: Constitutional, Tax, Cyber, Family, Environmental, Corporate, or General"
    )
    jurisdiction_hint: str = Field(
        default="central",
        description="Likely jurisdiction (state name or 'central')"
    )


def node_default_agent(state: dict) -> dict:
    """Full general-law pipeline: extract → research → verify → synthesize."""
    print("\n" + "=" * 60)
    print(">>> DEFAULT / GENERAL LEGAL AGENT")
    print("=" * 60)
    query = state["user_query"]
    print(f'    Query: "{query}"')

    # ── STEP 1: Entity extraction ─────────────────────────────────────────
    print("\n    [1/4] Extracting legal entities …")
    try:
        llm = ChatGroq(model=LLM_ANALYZER, temperature=0)
        structured_llm = llm.with_structured_output(GeneralQueryAnalysis)

        extraction_prompt = (
            "You are an expert legal NLP system specialised in Indian law. "
            "Extract all relevant legal entities from the following query.\n\n"
            f"Query: '{query}'"
        )
        analysis = structured_llm.invoke(extraction_prompt)

        all_entities = list(set(
            analysis.legal_concepts + analysis.statutes +
            analysis.case_names + analysis.keywords
        ))
        print(f"          Entities: {all_entities}")
    except Exception as e:
        print(f"    [!] Extraction error: {e}")
        all_entities = [query]
        analysis = None

    # ── STEP 2: Knowledge-graph research ──────────────────────────────────
    print("\n    [2/4] Querying Neo4j knowledge graph …")
    category = analysis.primary_category if analysis else "General"
    graph = AKGPGraphManager()
    try:
        raw_results = graph.search_by_entities(all_entities)
        category_results = graph.search_by_category(category)

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

    # ── STEP 4: Synthesize general opinion ────────────────────────────────
    print("\n    [4/4] Generating general legal opinion …")
    verified_str = _format_cases(verified, "SAFE_TO_CITE")
    cautioned_str = _format_cases(cautioned, "CITE_WITH_CAUTION") or "None."
    rejection_str = "\n".join(error_log) or "None."

    prompt = f"""You are a senior legal advocate specialising in Indian law.
Write a detailed legal opinion answering the user's query.

=== STRICT RULES ===
1. Cite ONLY cases marked SAFE_TO_CITE as binding authority.
2. Explain why DO_NOT_CITE cases are bad law.
3. Discuss both sides for CITE_WITH_CAUTION cases.
4. Include Hierarchy Score (H) when citing cases.
5. Provide specific, actionable legal strategy.

=== USER QUERY ===
{query}

=== VERIFIED PRECEDENTS (SAFE_TO_CITE) ===
{verified_str or 'No valid precedents found.'}

=== CAUTIONED PRECEDENTS ===
{cautioned_str}

=== REJECTION WARNINGS ===
{rejection_str}

=== OUTPUT FORMAT ===
1. EXECUTIVE SUMMARY
2. APPLICABLE LEGAL PROVISIONS
3. CASE ANALYSIS
4. REJECTED PRECEDENTS
5. LEGAL STRATEGY
6. RISK ASSESSMENT
7. CONCLUSION
"""

    try:
        synth_llm = ChatGroq(model=LLM_SYNTHESIZER, temperature=0)
        response = synth_llm.invoke(prompt)
        final_text = response.content
    except Exception as e:
        print(f"    [!] Synthesis error: {e}")
        final_text = f"[ERROR] Could not generate legal opinion: {e}"

    print("    Draft complete.")
    return {
        "expert_drafts": [{
            "domain": category,
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
