"""
Hierarchy Scoring Engine
========================
Implements the mathematical conflict resolution formula:

    H = (A * J) / T

Where:
    A = Authority Level (Supreme Court=100, High Court=75, District=50, Tribunal=25)
    J = Jurisdiction Match (same_state=1.0, different_state=0.5, central=1.0)
    T = Recency (Current Year - Year of Ruling), minimum 1 to avoid division by zero

Higher H score = stronger legal authority. When two cases conflict,
the one with the higher H score is the binding authority.
"""

from config import AUTHORITY_LEVELS, JURISDICTION_MATCH, CURRENT_YEAR


def compute_authority_level(court: str) -> int:
    """Map a court name to its authority level score.
    
    Handles partial matching so 'Karnataka High Court' maps to 'High Court'.
    """
    court_lower = court.lower()
    
    if "supreme" in court_lower:
        return AUTHORITY_LEVELS["Supreme Court of India"]
    elif "high court" in court_lower:
        return AUTHORITY_LEVELS["High Court"]
    elif "district" in court_lower:
        return AUTHORITY_LEVELS["District Court"]
    elif "tribunal" in court_lower:
        return AUTHORITY_LEVELS["Tribunal"]
    elif "commission" in court_lower:
        return AUTHORITY_LEVELS["Commission"]
    else:
        return 10  # Unknown court, lowest priority


def compute_jurisdiction_match(case_jurisdiction: str, query_jurisdiction: str) -> float:
    """Compute jurisdiction match score between a case and the user's query context.
    
    Args:
        case_jurisdiction: The jurisdiction of the case (state name or 'central')
        query_jurisdiction: The jurisdiction of the user's query context
    
    Returns:
        1.0 for same state or central, 0.5 for different state
    """
    if case_jurisdiction.lower() == "central" or query_jurisdiction.lower() == "central":
        return JURISDICTION_MATCH["central"]
    elif case_jurisdiction.lower() == query_jurisdiction.lower():
        return JURISDICTION_MATCH["same_state"]
    else:
        return JURISDICTION_MATCH["different_state"]


def compute_recency(year_of_ruling: int) -> int:
    """Compute the recency factor T = Current Year - Year of Ruling.
    
    Returns minimum 1 to avoid division by zero.
    """
    delta = CURRENT_YEAR - year_of_ruling
    return max(delta, 1)


def compute_hierarchy_score(
    court: str,
    year: int,
    case_jurisdiction: str = "central",
    query_jurisdiction: str = "central",
) -> float:
    """Compute the full Hierarchy Score: H = (A * J) / T
    
    Args:
        court: Name of the court that issued the ruling
        year: Year of the ruling
        case_jurisdiction: Jurisdiction of the case
        query_jurisdiction: Jurisdiction of the query context
    
    Returns:
        The hierarchy score as a float. Higher = more authoritative.
    """
    a = compute_authority_level(court)
    j = compute_jurisdiction_match(case_jurisdiction, query_jurisdiction)
    t = compute_recency(year)
    
    return (a * j) / t


def compare_cases(
    case_a: dict, case_b: dict, query_jurisdiction: str = "central"
) -> dict:
    """Compare two cases and determine which is the stronger authority.
    
    Args:
        case_a: Dict with keys: name, court, year, jurisdiction
        case_b: Dict with keys: name, court, year, jurisdiction
    
    Returns:
        Dict with winner, loser, scores, and reasoning
    """
    score_a = compute_hierarchy_score(
        case_a["court"], case_a["year"],
        case_a.get("jurisdiction", "central"), query_jurisdiction
    )
    score_b = compute_hierarchy_score(
        case_b["court"], case_b["year"],
        case_b.get("jurisdiction", "central"), query_jurisdiction
    )
    
    if score_a >= score_b:
        winner, loser = case_a, case_b
        w_score, l_score = score_a, score_b
    else:
        winner, loser = case_b, case_a
        w_score, l_score = score_b, score_a
    
    return {
        "winner": winner["name"],
        "winner_score": round(w_score, 2),
        "loser": loser["name"],
        "loser_score": round(l_score, 2),
        "score_ratio": round(w_score / max(l_score, 0.01), 2),
        "reasoning": (
            f"'{winner['name']}' (H={round(w_score, 2)}) has higher authority than "
            f"'{loser['name']}' (H={round(l_score, 2)}). "
            f"Score ratio: {round(w_score / max(l_score, 0.01), 2)}x stronger."
        ),
    }
