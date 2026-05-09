"""
Graph Manager - Neo4j AKGP Operations
======================================
Manages all interactions with the Neo4j Property Graph Database.
Implements the Adaptive Knowledge Graph Protocol:
    - Provenance tracking (source hash, page numbers)
    - Temporal versioning (valid_from, valid_to on edges)
    - Conflict-preserving storage (OVERRULES/DISSENTS edges never deleted)

RESILIENCE: All methods gracefully degrade to empty results if Neo4j
credentials are missing or the connection fails, preventing server crashes.
"""

from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


class AKGPGraphManager:
    """Manages the Neo4j knowledge graph with AKGP protocol enforcement."""
    
    def __init__(self):
        self.driver = None
        self._available = False
        if not NEO4J_URI or not NEO4J_PASSWORD:
            print("[AKGPGraphManager] Neo4j credentials missing — skipping graph queries.")
            return
        try:
            self.driver = GraphDatabase.driver(
                NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            self._available = True
            print(f"[AKGPGraphManager] Connected to Neo4j as '{NEO4J_USER}'.")
        except Exception as e:
            print(f"[AKGPGraphManager] Connection failed (non-fatal): {e}")
    
    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
    
    def verify_connection(self) -> bool:
        """Test the Neo4j connection."""
        if not self._available:
            return False
        try:
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            print(f"[!] Neo4j connection failed: {e}")
            return False

    # ==========================================
    # QUERY OPERATIONS (Read)
    # ==========================================
    
    def search_by_entities(self, entities: list) -> list:
        """Search the graph for cases related to the given legal entities."""
        if not self._available:
            print("    [!] Neo4j unavailable — returning empty case list.")
            return []
        with self.driver.session() as session:
            query = """
            MATCH (c:Precedent)-[:APPLIES_TO]->(issue:LegalIssue)
            WHERE issue.name IN $entities 
               OR issue.section IN $entities
               OR c.name IN $entities
            RETURN c.name AS case_name,
                   c.year AS year,
                   c.verdict AS verdict,
                   c.court AS court,
                   c.jurisdiction AS jurisdiction,
                   c.authority_level AS authority_level,
                   c.judge AS judge,
                   issue.name AS legal_issue,
                   issue.section AS section,
                   [(overruler:Precedent)-[ovr:OVERRULES]->(c) | {name: overruler.name, reason: ovr.reason, date: ovr.valid_from}] AS overrulers,
                   [(c)-[cites:CITES]->(cited:Precedent) | cited.name] AS citations,
                   [(dissenter:Precedent)-[dis:DISSENTS]->(c) | {name: dissenter.name, reason: dis.reason}] AS dissenters
            ORDER BY c.year DESC
            """
            results = session.run(query, entities=entities)
            return [record.data() for record in results]
    
    def search_by_category(self, category: str) -> list:
        """Search for all cases under a legal category."""
        if not self._available:
            return []
        with self.driver.session() as session:
            query = """
            MATCH (c:Precedent)-[:APPLIES_TO]->(issue:LegalIssue)
            WHERE issue.category = $category
            RETURN c.name AS case_name,
                   c.year AS year,
                   c.verdict AS verdict,
                   c.court AS court,
                   c.jurisdiction AS jurisdiction,
                   c.authority_level AS authority_level,
                   issue.name AS legal_issue,
                   issue.section AS section,
                   issue.category AS category,
                   [(overruler:Precedent)-[ovr:OVERRULES]->(c) | {name: overruler.name, reason: ovr.reason}] AS overrulers,
                   [(dissenter:Precedent)-[dis:DISSENTS]->(c) | {name: dissenter.name, reason: dis.reason}] AS dissenters
            ORDER BY c.year DESC
            LIMIT 10
            """
            results = session.run(query, category=category)
            return [record.data() for record in results]

    def get_conflict_chain(self, case_name: str) -> list:
        """Retrieve the full conflict chain for a case."""
        if not self._available:
            return []
        with self.driver.session() as session:
            query = """
            MATCH path = (latest:Precedent)-[:OVERRULES*]->(oldest:Precedent)
            WHERE latest.name = $case_name OR oldest.name = $case_name
            UNWIND nodes(path) AS node
            UNWIND relationships(path) AS rel
            WITH DISTINCT node, rel,
                 startNode(rel).name AS overruler,
                 endNode(rel).name AS overruled
            RETURN overruler, overruled, rel.reason AS reason
            """
            results = session.run(query, case_name=case_name)
            return [record.data() for record in results]
    
    def get_statute_amendments(self, statute_section: str) -> list:
        """Retrieve amendment history for a statute section."""
        if not self._available:
            return []
        with self.driver.session() as session:
            query = """
            MATCH (new_statute:Statute)-[a:AMENDS]->(old_statute:Statute)
            WHERE old_statute.section = $section OR new_statute.section = $section
            RETURN new_statute.name AS new_version,
                   new_statute.section AS new_section,
                   new_statute.year_enacted AS new_year,
                   old_statute.name AS old_version,
                   old_statute.section AS old_section,
                   a.amendment_details AS details,
                   a.valid_from AS effective_date
            ORDER BY new_statute.year_enacted DESC
            """
            results = session.run(query, section=statute_section)
            return [record.data() for record in results]
    
    def get_citing_cases(self, case_name: str) -> list:
        """Find all cases that cite a given case."""
        if not self._available:
            return []
        with self.driver.session() as session:
            query = """
            MATCH (citer:Precedent)-[r:CITES]->(cited:Precedent)
            WHERE cited.name = $case_name
            RETURN citer.name AS citing_case,
                   citer.year AS year,
                   citer.court AS court,
                   r.context AS citation_context
            ORDER BY citer.year DESC
            """
            results = session.run(query, case_name=case_name)
            return [record.data() for record in results]
    
    def get_graph_statistics(self) -> dict:
        """Get summary statistics about the knowledge graph."""
        if not self._available:
            return {"precedents": 0, "legal_issues": 0, "statutes": 0,
                    "overrules_edges": 0, "citation_edges": 0, "dissent_edges": 0}
        with self.driver.session() as session:
            stats = {}
            result = session.run("MATCH (n:Precedent) RETURN count(n) AS count")
            stats["precedents"] = result.single()["count"]
            result = session.run("MATCH (n:LegalIssue) RETURN count(n) AS count")
            stats["legal_issues"] = result.single()["count"]
            result = session.run("MATCH (n:Statute) RETURN count(n) AS count")
            stats["statutes"] = result.single()["count"]
            result = session.run("MATCH ()-[r:OVERRULES]->() RETURN count(r) AS count")
            stats["overrules_edges"] = result.single()["count"]
            result = session.run("MATCH ()-[r:CITES]->() RETURN count(r) AS count")
            stats["citation_edges"] = result.single()["count"]
            result = session.run("MATCH ()-[r:DISSENTS]->() RETURN count(r) AS count")
            stats["dissent_edges"] = result.single()["count"]
            return stats

    # ==========================================
    # WRITE OPERATIONS
    # ==========================================
    
    def add_precedent(self, case_data: dict) -> bool:
        """Add a new legal precedent to the knowledge graph."""
        if not self._available:
            return False
        with self.driver.session() as session:
            query = """
            MERGE (c:Precedent {name: $name})
            SET c.year = $year,
                c.court = $court,
                c.verdict = $verdict,
                c.jurisdiction = $jurisdiction,
                c.authority_level = $authority_level,
                c.judge = $judge,
                c.source_hash = $source_hash,
                c.valid_from = $valid_from
            RETURN c.name AS created
            """
            result = session.run(query, **case_data)
            record = result.single()
            return record is not None
