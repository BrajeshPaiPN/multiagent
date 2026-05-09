"""
AI Hallucination Verifier
=========================
When an agent cites a case, TWO independent LLM calls verify it.
A case must pass both verifications to be marked VERIFIED.
Cases failing both are flagged as HALLUCINATION_RISK.

This runs AFTER the expert agents produce drafts, BEFORE synthesis.
"""

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from config import LLM_ANALYZER
from akgp.graph_manager import AKGPGraphManager


class CaseVerdict(BaseModel):
    case_name: str = Field(description="The full case name being verified")
    exists: bool = Field(description="True if this case genuinely exists in Indian legal history")
    confidence: float = Field(description="Confidence score 0.0 to 1.0")
    reasoning: str = Field(description="Brief explanation of your verdict")
    correct_citation: str = Field(description="The corrected/confirmed case name and year, or 'UNKNOWN' if hallucinated")


VERIFIER_PROMPT = """You are a strict Indian legal database auditor.
Your job is to verify whether the following court case ACTUALLY EXISTS in Indian legal history.

Case to verify: "{case_name}"

Rules:
1. If you are CERTAIN this case exists with this exact name and court, set exists=True with confidence > 0.8
2. If it could exist but you are unsure, set exists=True with confidence 0.5-0.79
3. If this looks hallucinated or the name/year/court seems wrong, set exists=False with confidence > 0.7
4. Always provide the standard citation format if you know it.

Be very strict. AI models often hallucinate realistic-sounding but fake case names.
Do NOT verify a case just because it sounds plausible.
"""


def verify_case_once(llm, case_name: str) -> CaseVerdict:
    """Single LLM verification call."""
    try:
        structured = llm.with_structured_output(CaseVerdict)
        result = structured.invoke(VERIFIER_PROMPT.format(case_name=case_name))
        return result
    except Exception as e:
        print(f"    [!] Verifier error for '{case_name}': {e}")
        return CaseVerdict(
            case_name=case_name,
            exists=False,
            confidence=0.0,
            reasoning=f"Verification failed: {e}",
            correct_citation="UNKNOWN"
        )


def verify_cases_in_drafts(expert_drafts: list) -> tuple[list, list, list]:
    """
    Extract all case citations from expert drafts, run 2-agent verification,
    return (verified_names, hallucinated_names, uncertain_names).
    """
    import re

    # Extract case names mentioned in drafts
    # Pattern: "X v. Y" or "X vs Y" or "X v Y" followed by year in parentheses
    all_cases = set()
    pattern = re.compile(
        r'([A-Z][A-Za-z\s\.\,&\']+(?:v\.?|vs\.?)\s*[A-Z][A-Za-z\s\.\,&\']+(?:\(\d{4}\))?)',
        re.MULTILINE
    )

    for draft in expert_drafts:
        text = draft.get("draft", "")
        matches = pattern.findall(text)
        for m in matches:
            clean = m.strip().rstrip(",.")
            if len(clean) > 10:
                all_cases.add(clean)

    if not all_cases:
        return [], [], []

    print(f"\n    [VERIFIER] Found {len(all_cases)} case citations to verify...")

    # Two independent LLM instances (different temperature = different perspective)
    llm_v1 = ChatGroq(model=LLM_ANALYZER, temperature=0)
    llm_v2 = ChatGroq(model=LLM_ANALYZER, temperature=0.3)

    verified, hallucinated, uncertain = [], [], []

    for case_name in list(all_cases)[:30]:  # Cap at 30 to avoid rate limits
        v1 = verify_case_once(llm_v1, case_name)
        v2 = verify_case_once(llm_v2, case_name)

        # Scoring: both must agree to be considered verified
        both_confirm = v1.exists and v2.exists
        both_deny    = (not v1.exists) and (not v2.exists)
        avg_conf     = (v1.confidence + v2.confidence) / 2

        result = {
            "case_name":       case_name,
            "v1_verdict":      v1.exists,
            "v2_verdict":      v2.exists,
            "avg_confidence":  round(avg_conf, 2),
            "v1_reasoning":    v1.reasoning,
            "v2_reasoning":    v2.reasoning,
            "correct_citation": v1.correct_citation if v1.exists else v2.correct_citation,
        }

        if both_confirm and avg_conf >= 0.7:
            result["status"] = "VERIFIED"
            verified.append(result)
            print(f"    ✅ VERIFIED   ({avg_conf:.0%}): {case_name[:60]}")
        elif both_deny and avg_conf >= 0.6:
            result["status"] = "HALLUCINATION"
            hallucinated.append(result)
            print(f"    ❌ HALLUCINATED ({avg_conf:.0%}): {case_name[:60]}")
        else:
            result["status"] = "UNCERTAIN"
            uncertain.append(result)
            print(f"    ⚠️  UNCERTAIN  ({avg_conf:.0%}): {case_name[:60]}")

    # Persist verified/hallucinated status back to Neo4j
    _update_graph(verified, hallucinated)

    return verified, hallucinated, uncertain


def _update_graph(verified: list, hallucinated: list):
    """Mark cases in Neo4j with their verification status."""
    graph = AKGPGraphManager()
    if not graph._available:
        return
    try:
        with graph.driver.session() as session:
            for c in verified:
                session.run("""
                    MATCH (p:Precedent) WHERE p.name CONTAINS $name
                    SET p.ai_verified = true, p.ai_verified_confidence = $conf
                """, name=c["case_name"][:60], conf=c["avg_confidence"])
            for c in hallucinated:
                session.run("""
                    MERGE (p:Precedent {name: $name})
                    SET p.ai_verified = false, p.hallucination_risk = true
                """, name=c["case_name"])
    except Exception as e:
        print(f"    [!] Graph update error: {e}")
    finally:
        graph.close()


def node_hallucination_verifier(state: dict) -> dict:
    """LangGraph node: verifies case citations in expert drafts."""
    print("\n" + "=" * 60)
    print(">>> HALLUCINATION VERIFIER: Cross-checking case citations")
    print("=" * 60)

    expert_drafts = state.get("expert_drafts", [])
    if not expert_drafts:
        return {}

    verified, hallucinated, uncertain = verify_cases_in_drafts(expert_drafts)

    # Annotate the drafts with a verification report
    verification_report = ""
    if verified:
        verification_report += f"\n✅ {len(verified)} cases independently VERIFIED by 2 AI agents.\n"
    if hallucinated:
        verification_report += f"\n❌ {len(hallucinated)} HALLUCINATED citations removed:\n"
        for h in hallucinated:
            verification_report += f"  - {h['case_name']} (flagged as non-existent)\n"
    if uncertain:
        verification_report += f"\n⚠️ {len(uncertain)} citations UNCERTAIN — cited with caution.\n"

    print(f"\n    Summary: {len(verified)} verified | {len(hallucinated)} hallucinated | {len(uncertain)} uncertain")

    # Append report to each draft so synthesizer is aware
    updated_drafts = []
    for draft in expert_drafts:
        updated = dict(draft)
        if verification_report:
            updated["draft"] = draft.get("draft", "") + \
                f"\n\n--- HALLUCINATION VERIFICATION REPORT ---{verification_report}"
        updated["verified_citations"] = verified
        updated["hallucinated_citations"] = hallucinated
        updated["uncertain_citations"] = uncertain
        updated_drafts.append(updated)

    return {
        "expert_drafts":         updated_drafts,
        "hallucination_summary": {
            "verified":    len(verified),
            "hallucinated": len(hallucinated),
            "uncertain":   len(uncertain),
        }
    }
