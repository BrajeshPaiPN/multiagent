"""
Master Synthesizer Agent
========================
Aggregates the individual drafts produced by the parallel expert agents
into a comprehensive, high-quality Legal Memorandum.

Key features:
- Deep, long-form analysis (not bullet-point summaries)
- Mandatory section on ongoing/pending landmark cases when relevant
- Unbiased two-sided argument analysis for controversial matters
- Proper Indian legal citation format
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
            "AUDIENCE: An everyday Indian citizen with zero legal background.\n"
            "- Use simple, plain English. Explain every legal term in parentheses.\n"
            "- Use short paragraphs and numbered steps.\n"
            "- Be empathetic and practical — tell them exactly what to do next.\n"
            "- Despite simplicity, be THOROUGH and COMPREHENSIVE. Cover every angle."
        )
    else:
        mode_instruction = (
            "AUDIENCE: A senior advocate or corporate counsel.\n"
            "- Use precise legal terminology and proper Indian citation format (AIR, SCC, SCR).\n"
            "- Employ sophisticated multi-layered legal reasoning with statutory cross-references.\n"
            "- Include dissenting opinions and minority views where relevant.\n"
            "- Be COMPREHENSIVE and AUTHORITATIVE — this should read like a top-tier legal opinion."
        )

    prompt = f"""You are the Chief Legal Synthesizer for India's most advanced AI legal platform.
Your job is to produce a COMPREHENSIVE, AUTHORITATIVE, and DETAILED Legal Memorandum that a
senior advocate or an everyday citizen (depending on mode) would find genuinely valuable.

THIS IS NOT A SUMMARY. This is a full legal memorandum. Be thorough, detailed, and exhaustive.
Write at least 1500-2000 words. Cover every relevant angle, precedent, and statutory provision.

=== CRITICAL: NEW CRIMINAL LAW REGIME (effective 1 July 2024) ===
India replaced its colonial-era criminal statutes. When discussing criminal law:
  • IPC (1860) → cite **Bharatiya Nyaya Sanhita (BNS, 2023)** as primary
  • CrPC (1973) → cite **Bharatiya Nagarik Suraksha Sanhita (BNSS, 2023)** as primary
  • Indian Evidence Act (1872) → cite **Bharatiya Sakshya Adhiniyam (BSA, 2023)** as primary
Always include the old IPC/CrPC section in parentheses for cross-reference.
Example: "BNS Section 103 (formerly IPC Section 302) — Murder"
When citing older case law that used IPC, note the IPC section as used in the judgment
but always mention the current BNS equivalent.

{mode_instruction}

=== USER QUERY ===
{query}

{rag_context}

=== EXPERT OPINIONS FROM SPECIALIST AGENTS ===
{combined_drafts_text}
"""

    if critic_feedback:
        revision_count = state.get('revision_count', 0) + 1
        print(f"    [!] Applying Critic Feedback — Revision #{revision_count}")
        prompt += f"""
=== CRITIC FEEDBACK (YOU MUST ADDRESS EVERY POINT) ===
{critic_feedback}
"""

    prompt += """
=== OUTPUT FORMAT (FOLLOW THIS STRUCTURE PRECISELY) ===

# Legal Memorandum

## 1. Executive Summary
Write a clear, comprehensive 4-5 sentence summary of the legal position. Include the key
conclusion, the most important precedent, and the practical bottom line.

## 2. Applicable Laws & Statutory Provisions
List and EXPLAIN every relevant statute, section, and sub-section. Don't just list them —
explain what each provision says and how it applies to this specific situation.
Include the full text of critical sections where possible.

## 3. Landmark Precedents & Case Analysis
For each cited case, provide:
- Full case name with citation (e.g., *Kesavananda Bharati v. State of Kerala*, (1973) 4 SCC 225)
- The court and year
- The key legal question the court addressed
- The court's holding/ratio decidendi
- How it directly applies to the user's situation
- The Hierarchy Score [H=X.XX] if available

## 4. Your Legal Rights & Standing
Explain in detail what rights the user has under Indian law. Reference specific
constitutional articles (Part III Fundamental Rights, Part IV DPSP) and statutory
provisions. Be specific — not vague generalities.

## 5. Detailed Course of Action
Provide a step-by-step, actionable plan. Each step should include:
- What to do
- Which court/authority to approach
- What documents/evidence to prepare
- Approximate timelines and costs
- Alternative approaches if the primary route fails

## 6. Risks & Counter-Arguments
Present the strongest arguments the opposing side could make.
Explain how each risk can be mitigated or countered.
Be honest about weak points in the user's position.

## 7. Ongoing Appeals & Landmark Developments
**CRITICAL INSTRUCTION**: Think carefully about whether the user's query relates to ANY
of these categories of ongoing/recent landmark legal developments in India:

- Cases referred to larger constitutional benches (5-judge, 7-judge, 9-judge, 11-judge)
- Review petitions pending on major judgments
- Recent legislative amendments that override or modify earlier court positions
- Cases where the Supreme Court has expressed intent to reconsider earlier rulings
- Matters where there is a live constitutional challenge

FAMOUS EXAMPLES (non-exhaustive):
- Sabarimala Temple Entry — 2018 verdict allowing women; review petitions referred to 9-judge bench
  on the broader question of Essential Religious Practices doctrine
- Section 377 / LGBTQ+ Marriage — Navtej Singh Johar (2018) decriminalized; Supriyo v. Union of India
  (2023) denied marriage equality; ongoing legislative/judicial developments
- Marital Rape Exception — Exception 2 to Section 375 IPC; split verdict in Delhi HC; pending before SC
- Electoral Bonds — struck down in 2024; ongoing compliance and disclosure proceedings
- EWS Reservation — Janhit Abhiyan v. Union of India (2022); challenges and implementation disputes
- Citizenship Amendment Act (CAA) — multiple challenges pending before SC
- Places of Worship Act 1991 — challenges pending; Gyanvapi, Mathura mosque disputes
- Bulldozer Justice / Demolition of properties — multiple PILs pending before SC
- Sub-classification of SC/ST Reservations — State of Punjab v. Davinder Singh (2024, 7-judge)

**IF the query relates to any ongoing/pending matter:**
Include this section with:
  a) **Current Status**: What is the exact procedural status? (pending, referred, reserved, listed)
  b) **The Original Decision**: Summarize the judgment that is now under review/challenge
  c) **Arguments FOR** (Petitioner/Appellant side): Present their strongest 3-4 legal arguments
     with supporting precedents. Assess validity of each argument.
  d) **Arguments AGAINST** (Respondent/Government side): Present their strongest 3-4 legal
     arguments with supporting precedents. Assess validity of each argument.
  e) **Impact Assessment**: What happens if the case goes one way vs. the other?
     What is the practical impact on the user and on Indian law broadly?
  f) **Expert Analysis**: Based on constitutional principles, which side has the stronger argument?
     Present this as an UNBIASED assessment, not advocacy.

**IF the query does NOT relate to any ongoing matter**, simply OMIT this section entirely.
Do not include it with "No ongoing cases found" — just skip it.

## 8. Conclusion & Final Recommendation
Provide a clear, definitive conclusion. State the user's best path forward.
If the law is unsettled (due to ongoing appeals), say so explicitly and advise
the user on how to navigate the uncertainty.

=== QUALITY REQUIREMENTS ===
- Be THOROUGH. A 3-paragraph response is UNACCEPTABLE. Aim for 1500-2000+ words.
- Cite specific case names, sections, and articles — not vague references.
- Every legal claim must be backed by a precedent or statutory provision.
- Use markdown formatting (headers, bold, italics, lists) for readability.
- If you mention a case, provide the full citation the first time.
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
        llm = ChatGroq(model=LLM_MASTER, temperature=0.25)
        response = llm.invoke(prompt)
        final_text = response.content
        print("    [+] Master Draft complete.")
        return {"final_draft": final_text}
    except Exception as e:
        err = str(e)
        print(f"    [!] Synthesizer LLM error: {err}")
        return {
            "final_draft": (
                f"⚠️ **AI Engine Error**\n\n"
                f"The language model could not generate a response. "
                f"This is usually caused by an invalid or missing API key, or a rate limit.\n\n"
                f"**Technical Detail:** `{err}`\n\n"
                f"Please check that `GROQ_API_KEY` is correctly set in your deployment environment variables."
            )
        }
