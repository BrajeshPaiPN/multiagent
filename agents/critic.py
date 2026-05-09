"""
Critic Agent
============
Evaluates the Master Synthesizer's output to ensure it accurately addresses the user's
query, does not contain hallucinations, and properly warns about rejected cases.
If the draft fails, it triggers a revision loop.
"""

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from config import LLM_ANALYZER

class CriticReview(BaseModel):
    is_approved: bool = Field(description="True if the draft is perfect, False if it needs revision.")
    feedback: str = Field(description="If rejected, detailed instructions on what needs to be fixed. If approved, say 'Approved'.")

def node_critic(state: dict) -> dict:
    print("\n" + "=" * 60)
    print(">>> CRITIC AGENT: Reviewing Final Draft")
    print("=" * 60)
    
    query = state.get("user_query", "")
    draft = state.get("final_draft", "")
    expert_drafts = state.get("expert_drafts", [])
    
    # Collect all error logs / rejections to make sure the draft warns about them
    rejections = []
    for ed in expert_drafts:
        if ed.get("error_log"):
            rejections.extend(ed["error_log"])
            
    rejection_str = "\n".join(rejections) if rejections else "None."

    prompt = f"""You are a Senior Legal Critic. Your job is to strictly review a legal memorandum.

=== USER'S ORIGINAL QUERY ===
{query}

=== MEMORANDUM TO REVIEW ===
{draft}

=== BAD LAW (THESE MUST BE WARNED ABOUT IF MENTIONED) ===
{rejection_str}

=== EVALUATION CRITERIA ===
1. Does the memorandum directly and completely answer the User's Query?
2. Is the tone highly professional and structured?
3. Does it clearly outline the Legal Strategy?
4. If there are 'BAD LAW' cases listed above, did the memorandum properly warn the user about them (if they were mentioned)?

If the draft is excellent, set `is_approved` to True. 
If it is missing a key strategy, has poor structure, or fails to answer the query, set `is_approved` to False and provide highly specific `feedback` on what the Master Synthesizer must rewrite.
"""

    try:
        llm = ChatGroq(model=LLM_ANALYZER, temperature=0)
        structured_llm = llm.with_structured_output(CriticReview)
        review = structured_llm.invoke(prompt)
        
        needs_revision = not review.is_approved
        feedback = review.feedback
        
        if needs_revision:
            print("    [!] CRITIC REJECTED DRAFT.")
            print(f"        Feedback: {feedback}")
        else:
            print("    [+] CRITIC APPROVED DRAFT.")
            
    except Exception as e:
        print(f"    [!] Critic LLM error: {e}. Auto-approving.")
        needs_revision = False
        feedback = ""

    current_revisions = state.get("revision_count", 0)
    
    return {
        "needs_revision": needs_revision,
        "critic_feedback": feedback,
        "revision_count": current_revisions + 1 if needs_revision else current_revisions
    }
