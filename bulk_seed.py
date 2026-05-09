"""
Indian Kanoon Bulk Case Fetcher & Neo4j Seeder
===============================================
Fetches real Supreme Court & High Court judgments from Indian Kanoon
and seeds them into the Neo4j knowledge graph.

Usage:
    pip install requests beautifulsoup4
    python bulk_seed.py

Indian Kanoon Search API (free, no key needed):
    POST https://api.indiankanoon.org/search/
    Body: formInput=<term>&pagenum=<0..N>
"""

import re
import time
import json
import requests
from bs4 import BeautifulSoup
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

IK_SEARCH = "https://api.indiankanoon.org/search/"
IK_DOC    = "https://api.indiankanoon.org/doc/{docid}/"

HEADERS = {
    "User-Agent": "NyayaAI-Research/1.0 (Legal AI Platform)",
    "Content-Type": "application/x-www-form-urlencoded",
}

# Search terms covering all legal domains — 30 terms × 20 pages × ~10 docs = ~6000 judgments
SEARCH_TERMS = [
    # Criminal
    "murder IPC 302 Supreme Court", "bail anticipatory Supreme Court",
    "rape IPC 376 High Court", "kidnapping abduction Supreme Court",
    "cheating IPC 420 High Court", "POCSO child sexual abuse",
    "domestic violence IPC 498A Supreme Court", "arms act conviction High Court",
    "NDPS drug trafficking Supreme Court", "cybercrime IT Act High Court",
    # Civil / Contract
    "breach of contract damages Supreme Court", "specific performance agreement to sell",
    "injunction civil suit High Court", "limitation act time barred",
    "res judicata civil appeal", "consumer forum deficiency service",
    # Property / Rent
    "eviction tenant landlord High Court", "security deposit return tenant",
    "Transfer of Property Act sale deed Supreme Court", "GPA general power of attorney property",
    "rent control Karnataka High Court", "property dispute partition family",
    # Constitutional
    "fundamental rights Article 21 Supreme Court", "Article 14 equality High Court",
    "habeas corpus detention Supreme Court", "writ petition mandamus High Court",
    "Article 19 freedom speech High Court", "public interest litigation PIL",
    # Motor Vehicle / Compensation
    "motor accident compensation Supreme Court MACT",
    "drunk driving section 185 Motor Vehicles Act",
    # Patents / IP
    "patent infringement intellectual property High Court",
    # Family Law
    "divorce maintenance alimony High Court", "child custody guardian ward",
    # Tax
    "income tax evasion High Court", "GST appeal tribunal",
    # Labour
    "wrongful termination labour court reinstatement",
    "workmen compensation act industrial dispute",
]

COURT_AUTHORITY = {
    "Supreme Court of India": 100,
    "High Court": 75,
    "District Court": 50,
    "Tribunal": 25,
    "Commission": 15,
}

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


def guess_authority(court: str) -> int:
    for k, v in COURT_AUTHORITY.items():
        if k.lower() in court.lower():
            return v
    return 50


def extract_year(text: str) -> int:
    m = re.search(r'\b(19[5-9]\d|20[0-2]\d)\b', text)
    return int(m.group(1)) if m else 2000


def search_ik(term: str, pagenum: int) -> list:
    """Hit Indian Kanoon search API and return list of doc metadata."""
    try:
        resp = requests.post(
            IK_SEARCH,
            data={"formInput": term, "pagenum": pagenum},
            headers=HEADERS,
            timeout=15
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("docs", [])
    except Exception as e:
        print(f"  [!] Search error ({term} p{pagenum}): {e}")
        return []


def fetch_doc(docid: str) -> dict:
    """Fetch a single document's full text."""
    try:
        resp = requests.post(IK_DOC.format(docid=docid), headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


def parse_doc(doc_meta: dict) -> dict | None:
    """Convert IK doc metadata into our schema."""
    title = doc_meta.get("title", "").strip()
    if not title:
        return None

    docid  = str(doc_meta.get("tid", doc_meta.get("docid", "")))
    court  = doc_meta.get("docsource", "High Court")
    date   = doc_meta.get("publishdate", "2000-01-01")
    year   = extract_year(date)
    snippet = BeautifulSoup(doc_meta.get("headline", ""), "html.parser").get_text()[:400]

    if year < 1950 or not docid:
        return None

    return {
        "name":          title[:200],
        "year":          year,
        "court":         court,
        "jurisdiction":  "central",
        "verdict":       snippet or "Refer to full judgment.",
        "legal_issue":   title[:150],
        "section":       "See Full Judgment",
        "category":      guess_category(title, snippet),
        "judge":         "See Full Judgment",
        "authority_level": guess_authority(court),
        "docid":         docid,
        "source_url":    f"https://indiankanoon.org/doc/{docid}/",
    }


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
            print(f"  [!] Insert error for '{c['name'][:50]}': {e}")


def main():
    if not NEO4J_URI or not NEO4J_PASSWORD:
        print("[ERROR] Neo4j credentials not set in .env")
        return

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    print(f"[+] Connected to Neo4j as '{NEO4J_USER}'")

    total = 0
    pages_per_term = 20   # 20 pages × ~10 docs = 200 per term × 38 terms ≈ 7,600 docs

    with driver.session() as session:
        # Ensure constraints
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Precedent) REQUIRE c.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (i:LegalIssue) REQUIRE i.name IS UNIQUE")

        for term in SEARCH_TERMS:
            print(f"\n[*] Fetching: '{term}'")
            for page in range(pages_per_term):
                docs = search_ik(term, page)
                if not docs:
                    break

                batch = []
                for d in docs:
                    parsed = parse_doc(d)
                    if parsed:
                        batch.append(parsed)

                if batch:
                    seed_batch(session, batch)
                    total += len(batch)
                    print(f"    Page {page}: +{len(batch)} cases  (total: {total})")

                time.sleep(0.5)   # Be polite to Indian Kanoon servers

            if total >= 10000:
                print("\n[+] Target of 10,000 cases reached. Stopping.")
                break

    count = 0
    with driver.session() as s:
        count = s.run("MATCH (n:Precedent) RETURN count(n) AS c").single()["c"]

    driver.close()
    print(f"\n✅ Seeding complete! {count} total precedents in graph.")


if __name__ == "__main__":
    main()
