"""
Master Synthesizer Agent
========================
Aggregates the individual drafts produced by the parallel expert agents.
Also acts as the reviser if the Critic Agent rejects the draft.
"""

from langchain_groq import ChatGroq
from config import LLM_MASTER, GROQ_API_KEY

def node_master_synthesizer(state: dict) -> dict:
    print("\n" + "=" * 60)
    print(">>> MASTER SYNTHESIZER: Aggregating Expert Drafts")
    print("=" * 60)

    expert_drafts = state.get("expert_drafts", [])
    critic_feedback = state.get("critic_feedback", "")
    query = state.get("user_query", "")

    if not expert_drafts:
        return {"final_draft": "No expert drafts were generated. Please try again."}

    # Combine drafts
    combined_drafts_text = ""
    for idx, ed in enumerate(expert_drafts):
        domain = ed.get("domain", "Unknown Domain")
        draft = ed.get("draft", "")
        combined_drafts_text += f"\n--- EXPERT DRAFT {idx+1} ({domain}) ---\n{draft}\n"

    rag_context = state.get("rag_context", "")
    mode = state.get("mode", "citizen")
    print(f"    [+] Combining {len(expert_drafts)} draft(s). Mode: {mode}")

    if mode == "citizen":
        mode_instruction = (
            "IMPORTANT: Write in extremely simple, plain English for an everyday citizen "
            "with zero legal background. Use short sentences, avoid all jargon, and give "
            "clear practical steps the person can take right now."
        )
    else:
        mode_instruction = (
            "IMPORTANT: Write as a highly formal legal memorandum for senior counsel. "
            "Use precise legal terminology, proper Indian citation formatting (AIR, SCC), "
            "and sophisticated multi-layered legal reasoning with statutory references."
        )

    prompt = f"""You are the Master Legal Synthesizer for an Indian AI legal platform.
Combine the expert opinions below into one cohesive, well-structured Legal Memorandum.

{mode_instruction}

=== USER QUERY ===
{query}

{rag_context}

=== EXPERT OPINIONS ===
{combined_drafts_text}
"""

    if critic_feedback:
        revision_count = state.get('revision_count', 0) + 1
        print(f"    [!] Applying Critic Feedback — Revision #{revision_count}")
        prompt += f"""
=== CRITIC FEEDBACK (MUST ADDRESS) ===
{critic_feedback}
"""

    prompt += """
=== OUTPUT FORMAT ===
1. EXECUTIVE SUMMARY (2-3 clear sentences)
2. APPLICABLE LAWS & PROVISIONS
3. YOUR RIGHTS & LEGAL STANDING
4. RECOMMENDED COURSE OF ACTION (step-by-step)
5. RISKS & WHAT TO WATCH OUT FOR
6. CONCLUSION
"""

    if not GROQ_API_KEY:
        return {
            "final_draft": (
                "⚠️ **Configuration Error**: The GROQ_API_KEY environment variable is not set on this server.\n\n"
                "Please add it in your Railway/Render dashboard under **Environment Variables**:\n"
                "- Key: `GROQ_API_KEY`\n"
                "- Value: your Groq API key from console.groq.com\n\n"
                "Once added, the service will redeploy automatically and this will work."
            )
        }

    try:
        llm = ChatGroq(model=LLM_MASTER, temperature=0.2)  # Mixtral MoE — diverse internal reasoning
        response = llm.invoke(prompt)
        final_text = response.content
        print("    [+] Master Draft complete.")
        return {"final_draft": final_text}
    except Exception as e:
        err = str(e)
        print(f"    [!] Synthesizer LLM error: {err}")
        # Return the actual error so the user can see what went wrong
        return {
            "final_draft": (
                f"⚠️ **AI Engine Error**\n\n"
                f"The language model could not generate a response. "
                f"This is usually caused by an invalid or missing API key, or a rate limit.\n\n"
                f"**Technical Detail:** `{err}`\n\n"
                f"Please check that `GROQ_API_KEY` is correctly set in your deployment environment variables."
            )
        }
