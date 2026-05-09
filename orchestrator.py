"""
LangGraph Orchestrator
======================
Defines the DAG state machine that orchestrates the multi-agent pipeline.

Architecture (Advanced Multi-Agent):
  START → router → (parallel experts) → master_synthesizer → critic
                                                ↑             |
                                                +----[REVISE]-+
                                                              |
                                                           [APPROVE]
                                                              ↓
                                                             END

The Router Agent dynamically selects ONE OR MORE expert domains. The selected
expert agents run in parallel (fan-out). Then the graph fans-in to the 
Master Synthesizer, which combines all expert drafts. Finally, the Critic
reviews the master draft, and forces a revision loop if the quality is poor.
"""

from typing import TypedDict, List, Annotated
import operator
from langgraph.graph import StateGraph, START, END

from agents.router import node_router, route_to_specialists
from agents.agent_criminal import node_criminal_agent
from agents.agent_civil import node_civil_agent
from agents.agent_patents import node_patents_agent
from agents.agent_real_estate import node_real_estate_agent
from agents.agent_traffic import node_traffic_agent
from agents.agent_default import node_default_agent
from agents.master_synthesizer import node_master_synthesizer
from agents.critic import node_critic
from agents.rag_retriever import node_rag_retriever


class LegalState(TypedDict):
    user_query: str
    mode: str
    rag_context: str
    routed_domains: List[str]
    
    # Collected from parallel expert nodes via operator.add
    expert_drafts: Annotated[List[dict], operator.add]
    
    # Combined outputs
    final_draft: str
    
    # Critic Loop
    critic_feedback: str
    needs_revision: bool
    revision_count: int


def should_revise(state: LegalState) -> str:
    """Conditional edge from critic."""
    if state.get("needs_revision", False) and state.get("revision_count", 0) < 3:
        print("\n    >> CRITIC REJECTED: Routing back to Master Synthesizer for Revision.")
        return "master_synthesizer"
    else:
        print("\n    >> CRITIC APPROVED (or max retries reached): Ending.")
        return END


def build_legal_graph():
    workflow = StateGraph(LegalState)

    # ── Nodes ─────────────────────────────────────────────────────────────
    workflow.add_node("rag_retriever", node_rag_retriever)
    workflow.add_node("router", node_router)
    workflow.add_node("criminal_agent", node_criminal_agent)
    workflow.add_node("civil_agent", node_civil_agent)
    workflow.add_node("patents_agent", node_patents_agent)
    workflow.add_node("real_estate_agent", node_real_estate_agent)
    workflow.add_node("traffic_agent", node_traffic_agent)
    workflow.add_node("default_agent", node_default_agent)
    
    workflow.add_node("master_synthesizer", node_master_synthesizer)
    workflow.add_node("critic", node_critic)

    # ── Edges ─────────────────────────────────────────────────────────────
    workflow.add_edge(START, "rag_retriever")
    workflow.add_edge("rag_retriever", "router")

    # Fan-out
    workflow.add_conditional_edges(
        "router",
        route_to_specialists,
        {
            "criminal_agent": "criminal_agent",
            "civil_agent": "civil_agent",
            "patents_agent": "patents_agent",
            "real_estate_agent": "real_estate_agent",
            "traffic_agent": "traffic_agent",
            "default_agent": "default_agent",
        },
    )

    # Fan-in
    workflow.add_edge("criminal_agent", "master_synthesizer")
    workflow.add_edge("civil_agent", "master_synthesizer")
    workflow.add_edge("patents_agent", "master_synthesizer")
    workflow.add_edge("real_estate_agent", "master_synthesizer")
    workflow.add_edge("traffic_agent", "master_synthesizer")
    workflow.add_edge("default_agent", "master_synthesizer")

    # Synthesis -> Critic
    workflow.add_edge("master_synthesizer", "critic")
    
    # Critic -> Conditional (Revise or End)
    workflow.add_conditional_edges(
        "critic",
        should_revise,
        {
            "master_synthesizer": "master_synthesizer",
            END: END
        }
    )

    return workflow.compile()


def create_initial_state(query: str, mode: str = "citizen") -> LegalState:
    return {
        "user_query": query,
        "mode": mode,
        "rag_context": "",
        "routed_domains": [],
        "expert_drafts": [],
        "final_draft": "",
        "critic_feedback": "",
        "needs_revision": False,
        "revision_count": 0,
    }
