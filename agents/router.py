"""
Router Agent
============
A dedicated LLM-powered agent that receives the user's raw prompt and
determines which specialized domain agent should handle it.

Routing targets:
  - criminal_agent   → Criminal Law queries
  - civil_agent      → Civil Law queries
  - patents_agent    → Patent / IP Law queries
  - real_estate_agent→ Real Estate / Property Law queries
  - traffic_agent    → Traffic Ticket / Motor Vehicle queries
  - default_agent    → Anything else (fallback)
"""

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from typing import List
from config import LLM_ANALYZER


class RoutingDecision(BaseModel):
    """Structured output schema for the Router Agent."""
    domains: List[str] = Field(
        description=(
            "List of legal domains this query touches upon. Choose one or more from: "
            "'criminal', 'civil', 'patents', 'real_estate', 'traffic', 'general'."
        )
    )
    reasoning: str = Field(
        description="Brief explanation of why these domains were chosen."
    )


def node_router(state: dict) -> dict:
    """Analyze the user query and decide which specialized agents handle it."""
    print("\n" + "=" * 60)
    print(">>> ROUTER AGENT: Classifying query domains")
    print("=" * 60)
    print(f'    Input: "{state["user_query"]}"')

    try:
        llm = ChatGroq(model=LLM_ANALYZER, temperature=0)
        structured_llm = llm.with_structured_output(RoutingDecision)

        prompt = (
            "You are a legal query router for an Indian AI legal platform. "
            "Read the user's legal question and decide which specialist agents "
            "should handle it.\n\n"
            "Valid domains:\n"
            "  • 'criminal'     — IPC, BNS, FIR, bail, arrest, criminal charges\n"
            "  • 'civil'        — contracts, torts, consumer disputes, injunctions\n"
            "  • 'patents'      — patents, trademarks, copyright, IP\n"
            "  • 'real_estate'  — property, RERA, land, rent, title deeds\n"
            "  • 'traffic'      — traffic tickets, challans, MVA, driving\n"
            "  • 'general'      — constitutional law, family law, tax, cyber, anything else\n\n"
            "RULES:\n"
            "1. If the query clearly belongs to ONE domain, return ONLY that domain.\n"
            "2. If the query genuinely spans MULTIPLE domains (e.g., a road accident "
            "involves both 'criminal' charges AND 'civil' compensation AND 'traffic' "
            "violations), return ALL relevant domains (max 3).\n"
            "3. Do NOT add domains that are only tangentially related. Be precise.\n"
            "4. 'general' should be used for constitutional, family, tax, cyber, "
            "environmental law, or when no specialist fits.\n\n"
            f"User query: \"{state['user_query']}\"\n\n"
            "Return the relevant domain(s) and a brief reasoning."
        )

        result = structured_llm.invoke(prompt)
        domains = [d.lower().strip() for d in result.domains]

        # Validate domains
        valid_domains = {"criminal", "civil", "patents", "real_estate", "traffic", "general"}
        domains = [d for d in domains if d in valid_domains]
        
        # Cap at 3 domains for rate-limit safety, deduplicate
        if not domains:
            domains = ["general"]
        else:
            domains = list(dict.fromkeys(domains))[:3]

        print(f"    Routed to: {domains}")
        print(f"    Reason:    {result.reasoning}")

    except Exception as e:
        print(f"    [!] Router LLM error: {e}. Falling back to 'general'.")
        domains = ["general"]
        result = None

    return {
        "routed_domains": domains
    }


def route_to_specialists(state: dict) -> List[str]:
    """LangGraph conditional-edge function.
    Returns a LIST of node names to execute in parallel.
    """
    domains = state.get("routed_domains", ["general"])

    mapping = {
        "criminal":    "criminal_agent",
        "civil":       "civil_agent",
        "patents":     "patents_agent",
        "real_estate": "real_estate_agent",
        "traffic":     "traffic_agent",
        "general":     "default_agent",
    }

    targets = [mapping.get(d, "default_agent") for d in domains]
    # Remove duplicates
    targets = list(set(targets))
    
    print(f"\n    >> ROUTER EDGE: Spawning parallel nodes → {targets}")
    return targets
