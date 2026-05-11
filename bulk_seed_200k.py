"""
KanoonGPT Bulk Case Fetcher & Neo4j Seeder
===============================================
Fetches 200,000 real judgments from KanoonGPT/indian-case-laws HuggingFace dataset
and seeds them into the Neo4j knowledge graph.
"""

import time
import logging
from datasets import load_dataset
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logging.disable(logging.CRITICAL)

CATEGORY_MAP = {
    "murder": "Criminal Law", "rape": "Criminal Law", "bail": "Criminal Law",
    "kidnapping": "Criminal Law", "cheating": "Criminal Law", "NDPS": "Criminal Law",
    "498A": "Criminal Law", "POCSO": "Criminal Law", "cybercrime": "Criminal Law",
    "arms": "Criminal Law", "drunk driving": "Traffic Law", "motor accident": "Traffic Law",
    "MACT": "Traffic Law", "Motor Vehicles": "Traffic Law",
    "breach of contract": "Civil Law", "specific performance": "Civil Law",
    "injunction": "Civil Law", "consumer": "Civil Law", "damages": "Civil Law",
    "eviction": "Real Estate Law", "tenant": "Real Estate Law", "rent": "Real Estate Law",
    "property": "Real Estate Law", "GPA": "Real Estate Law", "Transfer of Property": "Real Estate Law",
    "fundamental rights": "Constitutional Law", "Article 21": "Constitutional Law",
    "habeas corpus": "Constitutional Law", "PIL": "Constitutional Law",
    "writ petition": "Constitutional Law", "Article 19": "Constitutional Law",
    "patent": "Patent Law", "intellectual property": "Patent Law",
    "divorce": "Civil Law", "maintenance": "Civil Law", "custody": "Civil Law",
    "income tax": "Civil Law", "GST": "Civil Law",
    "termination": "Civil Law", "labour": "Civil Law", "workmen": "Civil Law",
}

def guess_category(title: str, snippet: str) -> str:
    text = (title + " " + snippet).lower()
    for keyword, cat in CATEGORY_MAP.items():
        if keyword.lower() in text:
            return cat
    return "Civil Law"

def seed_batch(session, cases: list):
    """Upsert a batch of cases into Neo4j."""
    for c in cases:
        try:
            session.run("""
                MERGE (p:Precedent {name: $name})
                SET p.year = $year,
                    p.court = $court,
                    p.jurisdiction = $jurisdiction,
                    p.verdict = $verdict,
                    p.judge = $judge,
                    p.authority_level = $authority_level,
                    p.source_url = $source_url,
                    p.ik_docid = $docid,
                    p.verified = false
                MERGE (i:LegalIssue {name: $legal_issue})
                SET i.section = $section,
                    i.category = $category
                MERGE (p)-[:APPLIES_TO]->(i)
            """, **c)
        except Exception as e:
            pass

def main():
    if not NEO4J_URI or not NEO4J_PASSWORD:
        print("[ERROR] Neo4j credentials not set in .env")
        return

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    print(f"[+] Connected to Neo4j as '{NEO4J_USER}'")

    print("[*] Loading large KanoonGPT dataset from HuggingFace...")
    ds = load_dataset('KanoonGPT/indian-case-laws', split='train', streaming=True)
    
    total = 0
    batch = []
    batch_size = 500  # Larger batch size for faster insertion

    with driver.session() as session:
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Precedent) REQUIRE c.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (i:LegalIssue) REQUIRE i.name IS UNIQUE")

        for row in ds:
            title = str(row.get("case_title", "")).strip()
            if not title or title == 'None':
                continue
                
            year_str = str(row.get("decision_year", ""))
            try:
                year = int(year_str)
            except:
                year = 2000

            verdict = str(row.get("disposition_text", ""))
            if not verdict or verdict == 'None':
                verdict = "Refer to full judgment."

            judge = str(row.get("presiding_judge", ""))
            if not judge or judge == 'None':
                judge = "See Full Judgment"

            docid = str(row.get("id", ""))
            court = str(row.get("court_name", "High Court"))
            
            authority = 75
            if "supreme" in court.lower():
                authority = 100
            
            parsed = {
                "name":          title[:200],
                "year":          year,
                "court":         court[:100],
                "jurisdiction":  "central",
                "verdict":       verdict[:200],
                "legal_issue":   title[:150],
                "section":       "See Full Judgment",
                "category":      guess_category(title, verdict),
                "judge":         judge[:100],
                "authority_level": authority,
                "docid":         docid,
                "source_url":    str(row.get("source_pdf_s3_url", ""))[:200] or "N/A",
            }
            
            batch.append(parsed)
            
            if len(batch) >= batch_size:
                seed_batch(session, batch)
                total += len(batch)
                batch = []
                print(f"    Inserted batch. Total: {total}")
                
            if total >= 200000:
                print("\n[+] Target of 200,000 cases reached. Stopping.")
                break
                
        if batch and total < 200000:
            seed_batch(session, batch)
            total += len(batch)

    count = 0
    with driver.session() as s:
        count = s.run("MATCH (n:Precedent) RETURN count(n) AS c").single()["c"]

    driver.close()
    print(f"\n✅ Seeding complete! {count} total precedents in graph.")

if __name__ == "__main__":
    main()
