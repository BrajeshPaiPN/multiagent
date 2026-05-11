"""
Contract Analyzer Agent
=======================
A standalone LLM pipeline to review uploaded legal contracts.
Identifies pitfalls, hidden risks, one-sided clauses, and provides
an overall recommendation on whether it is safe to sign.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from typing import List
from config import GEMINI_MODEL

class ClauseAnalysis(BaseModel):
    clause_snippet: str = Field(description="A short quote or summary of the clause in question.")
    risk_level: str = Field(description="'High', 'Medium', or 'Low'")
    explanation: str = Field(description="Why this clause is risky or problematic.")
    mitigation: str = Field(description="Suggested edit or mitigation for this risk.")

class ContractReview(BaseModel):
    summary: str = Field(description="A 2-3 sentence summary of what this contract is.")
    is_safe_to_sign: bool = Field(description="Overall recommendation: True if broadly acceptable, False if highly risky.")
    overall_recommendation: str = Field(description="Detailed concluding advice.")
    critical_pitfalls: List[ClauseAnalysis] = Field(description="List of specific risky clauses found in the document.")

def analyze_contract_text(contract_text: str, mode: str = "citizen") -> dict:
    """Passes the raw contract text to the LLM for rigorous review."""
    print("\n" + "=" * 60)
    print(f">>> CONTRACT ANALYZER: Reviewing Legal Document (Mode: {mode})")
    print("=" * 60)
    print(f"    [*] Extracted {len(contract_text)} characters for analysis.")
    
    if len(contract_text.strip()) < 50:
        return {
            "error": "Extracted text is too short or illegible. Please upload a clearer document."
        }
        
    if mode == "citizen":
        mode_instruction = "IMPORTANT: Write the summary, explanations, and mitigations in very simple, plain English. Explain legal concepts so an everyday citizen can understand the risks without needing a law degree."
    else:
        mode_instruction = "IMPORTANT: Write the analysis for a senior attorney. Use precise legal terminology, cite relevant acts if applicable, and maintain a highly professional, rigorous legal tone."
        
    prompt = f"""You are a highly experienced Indian Contract and Corporate Lawyer.
Your client has asked you to review the following contract/agreement before they sign it.

Your job is to strictly analyze the contract and identify:
1. Hidden pitfalls or 'gotcha' clauses.
2. Severely one-sided terms (e.g., unfair indemnity, unreasonable non-competes, skewed termination rights).
3. Ambiguities that could lead to litigation.

{mode_instruction}

=== RAW CONTRACT TEXT ===
{contract_text}
=========================

Provide a highly structured and professional review. Be ruthless in finding risks.
"""

    try:
        # We use Gemini due to Groq's 6000 TPM limit for free tiers being too small for full contracts
        llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.1)
        structured_llm = llm.with_structured_output(ContractReview)
        
        review = structured_llm.invoke(prompt)
        print("    [+] Contract successfully analyzed.")
        
        return {
            "summary": review.summary,
            "is_safe_to_sign": review.is_safe_to_sign,
            "overall_recommendation": review.overall_recommendation,
            "pitfalls": [
                {
                    "clause": c.clause_snippet,
                    "risk_level": c.risk_level,
                    "explanation": c.explanation,
                    "mitigation": c.mitigation
                } for c in review.critical_pitfalls
            ]
        }
    except Exception as e:
        print(f"    [!] Contract Analyzer LLM error: {e}")
        return {"error": str(e)}
