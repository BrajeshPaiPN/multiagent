"""
Contract Analyzer Agent
=======================
A standalone LLM pipeline to review uploaded legal contracts.
Identifies pitfalls, hidden risks, one-sided clauses, and provides
an overall recommendation on whether it is safe to sign.

Balances risk identification with industry-standard context — so the
user understands which risks are normal/accepted across the industry
vs. which are genuinely unusual or dangerous.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from typing import List
from config import GEMINI_MODEL


class ClauseAnalysis(BaseModel):
    clause_snippet: str = Field(
        description="A short quote or summary of the clause in question."
    )
    is_industry_standard: bool = Field(
        description="True if this clause is commonly found in similar contracts across the industry. False if it is unusual, one-sided, or genuinely concerning."
    )
    industry_context: str = Field(
        description="Explain whether this is a normal clause in this type of contract and what the industry standard typically looks like. If it is standard, say so clearly."
    )
    risk_level: str = Field(
        description="'High' (unusual/dangerous), 'Medium' (standard but with caveats), or 'Low' (routine, industry standard)."
    )
    explanation: str = Field(
        description="Why this clause matters, what risk it carries, and importantly whether that risk is one that ALL signatories in this industry typically accept."
    )
    mitigation: str = Field(
        description="If the clause is non-standard or High risk, suggest a specific edit. If it is industry-standard, state that it is generally acceptable but explain any negotiation tips."
    )


class ContractReview(BaseModel):
    contract_type: str = Field(
        description="Identify the type of contract (e.g., Employment Agreement, SaaS Subscription, Real Estate Lease, Service Agreement, etc.)"
    )
    summary: str = Field(
        description="A 2-3 sentence summary of what this contract is and its primary purpose."
    )
    industry_standard_assessment: str = Field(
        description="A 2-3 sentence assessment of how this contract compares to industry norms overall. Is it broadly standard? Overly aggressive? Unusually fair to the other party?"
    )
    is_safe_to_sign: bool = Field(
        description="Overall recommendation: True if this is broadly acceptable even considering the flagged risks, False only if there are genuinely dangerous non-standard clauses that require renegotiation before signing."
    )
    overall_recommendation: str = Field(
        description="Balanced concluding advice. Acknowledge what is standard, what the user should watch out for, and any specific clauses they should push back on."
    )
    clause_analysis: List[ClauseAnalysis] = Field(
        description="Analysis of notable clauses. Include BOTH standard clauses (so the user understands they are normal) AND genuinely risky or non-standard ones."
    )


def analyze_contract_text(contract_text: str, mode: str = "citizen") -> dict:
    """Passes the raw contract text to the LLM for a balanced, industry-aware review."""
    print("\n" + "=" * 60)
    print(f">>> CONTRACT ANALYZER: Reviewing Legal Document (Mode: {mode})")
    print("=" * 60)
    print(f"    [*] Extracted {len(contract_text)} characters for analysis.")

    if len(contract_text.strip()) < 50:
        return {
            "error": "Extracted text is too short or illegible. Please upload a clearer document."
        }

    if mode == "citizen":
        mode_instruction = (
            "IMPORTANT: Write in very simple, plain English. Explain legal concepts so an everyday "
            "citizen can understand them without a law degree. Clearly separate 'this is normal — everyone "
            "signs this' from 'this is unusual and you should be worried about this specifically'."
        )
    else:
        mode_instruction = (
            "IMPORTANT: Write for a senior attorney. Use precise legal terminology, cite relevant Indian "
            "Contract Act provisions or industry standards where applicable, and maintain a professional, "
            "rigorous legal tone. Distinguish clearly between boilerplate/standard clauses and materially "
            "non-standard terms."
        )

    prompt = f"""You are a highly experienced Indian Contract and Corporate Lawyer with 20+ years of practice.
Your client has asked you to review the following contract/agreement before they sign it.

Your CORE PHILOSOPHY is to give BALANCED, PRACTICAL advice:
- First, identify what type of contract this is and what industry it belongs to.
- Then assess each notable clause against what is INDUSTRY STANDARD for that contract type.
- If a clause is completely normal and routinely accepted across the industry (e.g., limitation of liability in a SaaS contract, non-solicitation in an employment agreement), say so EXPLICITLY. Do NOT flag standard clauses as red flags.
- Only flag as HIGH risk clauses that are genuinely unusual, one-sided beyond industry norms, or contain hidden dangers that the other party would NOT typically accept.
- Your goal is to INFORM, not to scare. A client who is told everything is dangerous is poorly served.

Think about these questions for each major clause:
1. Is this clause found in 80%+ of similar contracts in this industry? → Industry Standard (Low risk)
2. Is this clause one-sided but commonly accepted in this type of agreement? → Standard with caveats (Medium risk)
3. Is this clause unusual, aggressive beyond norms, or potentially exploitative? → Flag it (High risk)

{mode_instruction}

=== RAW CONTRACT TEXT ===
{contract_text}
=========================

Provide a structured, professional, and BALANCED review. Help the client understand what is normal in this type of contract and what genuinely deserves attention.
"""

    try:
        # We use Gemini due to Groq's 6000 TPM limit for free tiers being too small for full contracts
        llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.2)
        structured_llm = llm.with_structured_output(ContractReview)

        review = structured_llm.invoke(prompt)
        print("    [+] Contract successfully analyzed.")

        return {
            "contract_type": review.contract_type,
            "summary": review.summary,
            "industry_standard_assessment": review.industry_standard_assessment,
            "is_safe_to_sign": review.is_safe_to_sign,
            "overall_recommendation": review.overall_recommendation,
            "pitfalls": [
                {
                    "clause": c.clause_snippet,
                    "is_industry_standard": c.is_industry_standard,
                    "industry_context": c.industry_context,
                    "risk_level": c.risk_level,
                    "explanation": c.explanation,
                    "mitigation": c.mitigation,
                }
                for c in review.clause_analysis
            ],
        }
    except Exception as e:
        print(f"    [!] Contract Analyzer LLM error: {e}")
        return {"error": str(e)}
