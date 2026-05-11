"""
Contract Analyzer Agent
=======================
A standalone LLM pipeline to review uploaded legal contracts.
Produces a full risk profile with numeric scores, category breakdowns,
negotiation priorities, charts data, and a final sign/negotiate/reject verdict.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from typing import List, Optional
from config import GEMINI_MODEL


class ClauseAnalysis(BaseModel):
    clause_snippet: str = Field(description="A short quote or summary of the clause.")
    clause_category: str = Field(
        description="Category of this clause. Choose from: 'Liability', 'Payment & Fees', 'Termination', 'Intellectual Property', 'Confidentiality', 'Non-Compete / Non-Solicitation', 'Dispute Resolution', 'Indemnity', 'Data & Privacy', 'Governance', 'Other'."
    )
    is_industry_standard: bool = Field(
        description="True if this clause is commonly found in similar contracts across the industry."
    )
    industry_context: str = Field(
        description="What the industry standard looks like for this clause type. Be specific."
    )
    risk_level: str = Field(description="'High', 'Medium', or 'Low'.")
    risk_score: int = Field(
        description="Numeric risk score for this clause: 1-33 (Low), 34-66 (Medium), 67-100 (High). Calibrate against industry norms — a standard limitation of liability clause should score 15-25, not 70."
    )
    explanation: str = Field(description="What this clause means and what risk it carries.")
    mitigation: str = Field(
        description="Specific negotiation tip or suggested edit if risky. If standard, state it is acceptable."
    )


class NegotiationPoint(BaseModel):
    priority: str = Field(description="'Critical', 'Important', or 'Nice-to-have'.")
    clause: str = Field(description="Name or short description of the clause to negotiate.")
    ask: str = Field(description="Exactly what the user should ask the other party to change.")
    leverage: str = Field(description="Why the other party might agree to this change.")


class ContractReview(BaseModel):
    contract_type: str = Field(description="Type of contract (e.g., Employment Agreement, SaaS Subscription, Real Estate Lease).")
    parties: str = Field(description="Briefly identify the two parties (e.g., 'Employee and Employer', 'Vendor and Client').")
    summary: str = Field(description="2-3 sentence plain-language summary of what this contract is.")
    industry_standard_assessment: str = Field(
        description="2-3 sentence assessment of how this contract compares to industry norms overall."
    )

    # Decision
    decision: str = Field(
        description="Your final verdict. EXACTLY one of: 'SIGN', 'NEGOTIATE', or 'REJECT'. Use 'SIGN' if broadly fair. Use 'NEGOTIATE' if some clauses need tweaking but it is salvageable. Use 'REJECT' only for contracts with multiple exploitative, non-standard clauses that no reasonable party should accept."
    )
    decision_reason: str = Field(
        description="2-3 sentence explanation of why you gave this specific verdict."
    )

    # Numeric scoring
    overall_risk_score: int = Field(
        description="Overall contract risk score from 0 (completely safe) to 100 (extremely dangerous). Weight non-standard clauses heavily. A typical employment contract should score 20-40."
    )
    liability_score: int = Field(description="Risk score 0-100 for Liability clauses.")
    payment_score: int = Field(description="Risk score 0-100 for Payment & Fee clauses.")
    termination_score: int = Field(description="Risk score 0-100 for Termination clauses.")
    ip_score: int = Field(description="Risk score 0-100 for Intellectual Property clauses.")
    confidentiality_score: int = Field(description="Risk score 0-100 for Confidentiality / NDA clauses.")
    dispute_score: int = Field(description="Risk score 0-100 for Dispute Resolution clauses.")

    overall_recommendation: str = Field(
        description="Balanced concluding advice for the user. What is standard, what needs attention, what to negotiate."
    )

    clause_analysis: List[ClauseAnalysis] = Field(
        description="Analysis of all notable clauses. Include BOTH standard and non-standard ones."
    )

    negotiation_priorities: List[NegotiationPoint] = Field(
        description="Ordered list of specific negotiation asks for the user. Start with the most critical."
    )

    red_flags: List[str] = Field(
        description="Short bullet-point list of the most serious non-standard or dangerous items. Empty list if none."
    )

    green_flags: List[str] = Field(
        description="Short bullet-point list of clauses that are notably fair or beneficial to the user. Empty list if none."
    )


def analyze_contract_text(contract_text: str, mode: str = "citizen") -> dict:
    """Full risk-profile contract analysis with charts data and sign/negotiate/reject verdict."""
    print("\n" + "=" * 60)
    print(f">>> CONTRACT ANALYZER: Reviewing Legal Document (Mode: {mode})")
    print("=" * 60)
    print(f"    [*] Extracted {len(contract_text)} characters for analysis.")

    if len(contract_text.strip()) < 50:
        return {"error": "Extracted text is too short or illegible. Please upload a clearer document."}

    if mode == "citizen":
        mode_instruction = (
            "Write in very simple, plain English. Explain legal concepts so an everyday citizen "
            "can understand. Clearly distinguish 'this is normal' from 'this is genuinely risky'."
        )
    else:
        mode_instruction = (
            "Write for a senior attorney. Use precise legal terminology, cite Indian Contract Act or "
            "relevant statutes where applicable. Distinguish boilerplate from materially non-standard terms."
        )

    prompt = f"""You are a highly experienced Indian Contract and Corporate Lawyer with 20+ years of practice.
Your client needs a COMPLETE RISK PROFILE of the following contract before deciding whether to sign it.

Your CORE PHILOSOPHY — CALIBRATED, BALANCED analysis:
- First identify the contract type and industry.
- Benchmark EVERY notable clause against industry norms for that contract type.
- Standard, boilerplate clauses (limitation of liability, non-solicitation, IP assignment in employment, governing law) must get LOW risk scores (10-30) and be flagged as industry standard.
- Only assign HIGH risk scores (67+) to clauses that are genuinely unusual, one-sided beyond norms, or that a reasonable attorney would advise against accepting.
- The overall_risk_score must reflect the TRUE risk — a standard employment agreement should be 20-40, not 70-90.
- Your DECISION must be:
  • SIGN — if the contract is broadly fair with only minor, standard risks
  • NEGOTIATE — if some clauses need tweaking but the contract is salvageable
  • REJECT — ONLY if the contract has multiple genuinely exploitative, non-standard terms

{mode_instruction}

=== CONTRACT TEXT ===
{contract_text}
====================

Provide a complete structured risk profile with numeric scores for all categories and specific negotiation asks.
"""

    try:
        llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.15)
        structured_llm = llm.with_structured_output(ContractReview)
        review = structured_llm.invoke(prompt)
        print("    [+] Contract successfully analyzed.")

        # Build risk breakdown for charts
        high_count = sum(1 for c in review.clause_analysis if c.risk_level.lower() == "high")
        medium_count = sum(1 for c in review.clause_analysis if c.risk_level.lower() == "medium")
        low_count = sum(1 for c in review.clause_analysis if c.risk_level.lower() == "low")
        standard_count = sum(1 for c in review.clause_analysis if c.is_industry_standard)
        non_standard_count = len(review.clause_analysis) - standard_count

        return {
            "contract_type": review.contract_type,
            "parties": review.parties,
            "summary": review.summary,
            "industry_standard_assessment": review.industry_standard_assessment,

            # Decision verdict
            "decision": review.decision,
            "decision_reason": review.decision_reason,

            # Scores for charts
            "overall_risk_score": review.overall_risk_score,
            "category_scores": {
                "Liability": review.liability_score,
                "Payment & Fees": review.payment_score,
                "Termination": review.termination_score,
                "Intellectual Property": review.ip_score,
                "Confidentiality": review.confidentiality_score,
                "Dispute Resolution": review.dispute_score,
            },
            "risk_breakdown": {
                "high": high_count,
                "medium": medium_count,
                "low": low_count,
            },
            "standard_breakdown": {
                "standard": standard_count,
                "non_standard": non_standard_count,
            },

            # Flags
            "red_flags": review.red_flags,
            "green_flags": review.green_flags,

            # Recommendations
            "overall_recommendation": review.overall_recommendation,
            "negotiation_priorities": [
                {
                    "priority": n.priority,
                    "clause": n.clause,
                    "ask": n.ask,
                    "leverage": n.leverage,
                }
                for n in review.negotiation_priorities
            ],

            # Clause-level detail
            "pitfalls": [
                {
                    "clause": c.clause_snippet,
                    "clause_category": c.clause_category,
                    "is_industry_standard": c.is_industry_standard,
                    "industry_context": c.industry_context,
                    "risk_level": c.risk_level,
                    "risk_score": c.risk_score,
                    "explanation": c.explanation,
                    "mitigation": c.mitigation,
                }
                for c in review.clause_analysis
            ],
        }
    except Exception as e:
        print(f"    [!] Contract Analyzer LLM error: {e}")
        return {"error": str(e)}
