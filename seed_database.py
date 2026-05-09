"""
Neo4j Database Seeder - Rich AKGP Schema
==========================================
Populates Neo4j with a complex legal knowledge graph including:
- Multiple case categories (Criminal, Constitutional, Civil, Family)
- OVERRULES edges (conflict-preservation)
- DISSENTS edges (disagreement tracking)
- CITES edges (citation networks)
- AMENDS edges (statute amendments)
- Temporal versioning (valid_from on edges)
- Court hierarchy and jurisdiction metadata
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

CLEAR_QUERY = "MATCH (n) DETACH DELETE n"

SEED_QUERIES = [
# ---- LEGAL ISSUES ----
"""
CREATE (:LegalIssue {name: "Anticipatory Bail", section: "BNSS 482", category: "Criminal Law", description: "Pre-arrest bail to prevent arrest"})
CREATE (:LegalIssue {name: "Right to Privacy", section: "Article 21", category: "Constitutional Law", description: "Fundamental right under Part III"})
CREATE (:LegalIssue {name: "Defamation", section: "BNS 356", category: "Criminal Law", description: "Criminal defamation provisions"})
CREATE (:LegalIssue {name: "Property Dispute", section: "Transfer of Property Act", category: "Civil Law", description: "Disputes regarding property ownership"})
CREATE (:LegalIssue {name: "Divorce", section: "HMA Section 13", category: "Family Law", description: "Grounds for divorce under Hindu Marriage Act"})
CREATE (:LegalIssue {name: "Cyber Crime", section: "IT Act Section 66", category: "Cyber Law", description: "Computer related offences"})
CREATE (:LegalIssue {name: "Writ Petition", section: "Article 226", category: "Constitutional Law", description: "High Court power to issue writs"})
CREATE (:LegalIssue {name: "Murder", section: "BNS 103", category: "Criminal Law", description: "Punishment for murder"})
""",

# ---- PRECEDENTS: Criminal Law ----
"""
CREATE (s1:Precedent {name: "State v. Sharma", year: 2022, court: "High Court", jurisdiction: "Karnataka", authority_level: 75, judge: "Justice Rao", verdict: "Granted anticipatory bail based on verbal threat. Held that verbal threats alone constitute sufficient grounds for apprehension of arrest."})
CREATE (s2:Precedent {name: "Union v. Singh", year: 2024, court: "Supreme Court of India", jurisdiction: "central", authority_level: 100, judge: "Justice Chandrachud", verdict: "Denied anticipatory bail. Verbal threats without corroborating evidence are insufficient. Overruled the lower standard set by State v. Sharma."})
CREATE (s3:Precedent {name: "Arnesh Kumar v. State of Bihar", year: 2014, court: "Supreme Court of India", jurisdiction: "central", authority_level: 100, judge: "Justice Sinha", verdict: "Police must follow checklist before arrest in cases with punishment less than 7 years. Section 41A CrPC compliance mandatory."})

WITH s1, s2, s3
MATCH (issue:LegalIssue {name: "Anticipatory Bail"})
CREATE (s1)-[:APPLIES_TO]->(issue)
CREATE (s2)-[:APPLIES_TO]->(issue)
CREATE (s3)-[:APPLIES_TO]->(issue)
CREATE (s2)-[:OVERRULES {reason: "Insufficient evidentiary standard in lower court", valid_from: 2024, source_hash: "sha256_union_v_singh_2024"}]->(s1)
CREATE (s2)-[:CITES {context: "Followed the procedural safeguards established in Arnesh Kumar", page_number: 12}]->(s3)
""",

# ---- PRECEDENTS: Constitutional Law ----
"""
CREATE (p1:Precedent {name: "Puttaswamy v. Union of India", year: 2017, court: "Supreme Court of India", jurisdiction: "central", authority_level: 100, judge: "Justice Chandrachud", verdict: "Right to privacy is a fundamental right under Article 21. Nine-judge bench unanimous decision."})
CREATE (p2:Precedent {name: "ADM Jabalpur v. Shivkant Shukla", year: 1976, court: "Supreme Court of India", jurisdiction: "central", authority_level: 100, judge: "Justice Beg", verdict: "During Emergency, fundamental rights including Article 21 stand suspended. Citizens have no locus standi."})
CREATE (p3:Precedent {name: "Kharak Singh v. State of UP", year: 1963, court: "Supreme Court of India", jurisdiction: "central", authority_level: 100, judge: "Justice Ayyangar", verdict: "Right to privacy is NOT a fundamental right. Only partial recognition of personal liberty under Article 21."})

WITH p1, p2, p3
MATCH (issue:LegalIssue {name: "Right to Privacy"})
CREATE (p1)-[:APPLIES_TO]->(issue)
CREATE (p2)-[:APPLIES_TO]->(issue)
CREATE (p3)-[:APPLIES_TO]->(issue)
CREATE (p1)-[:OVERRULES {reason: "Nine-judge bench explicitly overruled the narrow interpretation of Article 21 in Kharak Singh", valid_from: 2017, source_hash: "sha256_puttaswamy_2017"}]->(p3)
CREATE (p1)-[:OVERRULES {reason: "Puttaswamy bench held that ADM Jabalpur was incorrectly decided and fundamental rights cannot be suspended", valid_from: 2017, source_hash: "sha256_puttaswamy_2017_adm"}]->(p2)
""",

# ---- PRECEDENTS: Defamation ----
"""
CREATE (d1:Precedent {name: "Subramanian Swamy v. Union of India", year: 2016, court: "Supreme Court of India", jurisdiction: "central", authority_level: 100, judge: "Justice Misra", verdict: "Criminal defamation under Section 499 IPC is constitutionally valid. Right to reputation is part of Article 21."})
CREATE (d2:Precedent {name: "R. Rajagopal v. State of TN", year: 1994, court: "Supreme Court of India", jurisdiction: "central", authority_level: 100, judge: "Justice Jeevan Reddy", verdict: "Right to privacy and press freedom must be balanced. Public officials have reduced privacy expectations."})
CREATE (d3:Precedent {name: "Shreya Singhal v. Union of India", year: 2015, court: "Supreme Court of India", jurisdiction: "central", authority_level: 100, judge: "Justice Nariman", verdict: "Struck down Section 66A of IT Act as unconstitutional. Online speech cannot be criminalized vaguely."})

WITH d1, d2, d3
MATCH (issue:LegalIssue {name: "Defamation"})
CREATE (d1)-[:APPLIES_TO]->(issue)
CREATE (d2)-[:APPLIES_TO]->(issue)
CREATE (d3)-[:APPLIES_TO]->(issue)
CREATE (d1)-[:CITES {context: "Referenced the balance between free speech and reputation", page_number: 23}]->(d2)
CREATE (d3)-[:DISSENTS {reason: "Justice Rohinton Nariman noted potential conflict between criminal defamation and free speech online", dissenting_judge: "Justice Nariman"}]->(d1)
""",

# ---- PRECEDENTS: Civil Law (Property) ----
"""
CREATE (c1:Precedent {name: "Suraj Lamp v. State of Haryana", year: 2012, court: "Supreme Court of India", jurisdiction: "central", authority_level: 100, judge: "Justice Raveendran", verdict: "Sale agreements through GPA (General Power of Attorney) and SA (Sale Agreement) do not convey title. Only registered sale deeds transfer property ownership."})
CREATE (c2:Precedent {name: "Baldev Singh v. Manohar Singh", year: 2006, court: "High Court", jurisdiction: "Punjab", authority_level: 75, judge: "Justice Saron", verdict: "GPA-based property transfers are valid if accompanied by possession and part performance."})

WITH c1, c2
MATCH (issue:LegalIssue {name: "Property Dispute"})
CREATE (c1)-[:APPLIES_TO]->(issue)
CREATE (c2)-[:APPLIES_TO]->(issue)
CREATE (c1)-[:OVERRULES {reason: "Supreme Court held that GPA/SA transactions are not legally recognized modes of transfer", valid_from: 2012, source_hash: "sha256_suraj_lamp_2012"}]->(c2)
""",

# ---- PRECEDENTS: Family Law ----
"""
CREATE (f1:Precedent {name: "Shayara Bano v. Union of India", year: 2017, court: "Supreme Court of India", jurisdiction: "central", authority_level: 100, judge: "Justice Nariman", verdict: "Triple talaq (instant divorce) is unconstitutional and void. Muslim women have equal right to dignity."})
CREATE (f2:Precedent {name: "Shamim Ara v. State of UP", year: 2002, court: "Supreme Court of India", jurisdiction: "central", authority_level: 100, judge: "Justice Doraiswamy Raju", verdict: "Talaq must be for reasonable cause and preceded by attempts at reconciliation."})

WITH f1, f2
MATCH (issue:LegalIssue {name: "Divorce"})
CREATE (f1)-[:APPLIES_TO]->(issue)
CREATE (f2)-[:APPLIES_TO]->(issue)
CREATE (f1)-[:CITES {context: "Built upon the requirement of reasonable cause established in Shamim Ara", page_number: 45}]->(f2)
""",

# ---- PRECEDENTS: Cyber Law ----
"""
CREATE (cy1:Precedent {name: "Shreya Singhal v. Union of India", year: 2015, court: "Supreme Court of India", jurisdiction: "central", authority_level: 100, judge: "Justice Nariman", verdict: "Section 66A of IT Act struck down. Online speech restrictions must be narrowly tailored."})

WITH cy1
MATCH (issue:LegalIssue {name: "Cyber Crime"})
CREATE (cy1)-[:APPLIES_TO]->(issue)
""",

# ---- STATUTES AND AMENDMENTS ----
"""
CREATE (s_old:Statute {name: "Indian Penal Code", section: "IPC 499", year_enacted: 1860, status: "Repealed"})
CREATE (s_new:Statute {name: "Bharatiya Nyaya Sanhita", section: "BNS 356", year_enacted: 2023, status: "Active"})
CREATE (s_new)-[:AMENDS {amendment_details: "BNS 356 replaces IPC 499 with updated language for defamation. Substance largely unchanged but procedure modified.", valid_from: 2024, valid_to: null}]->(s_old)

CREATE (c_old:Statute {name: "Code of Criminal Procedure", section: "CrPC 438", year_enacted: 1973, status: "Repealed"})
CREATE (c_new:Statute {name: "Bharatiya Nagarik Suraksha Sanhita", section: "BNSS 482", year_enacted: 2023, status: "Active"})
CREATE (c_new)-[:AMENDS {amendment_details: "BNSS 482 replaces CrPC 438 for anticipatory bail with stricter conditions and mandatory hearing within 7 days.", valid_from: 2024, valid_to: null}]->(c_old)
""",
]


def seed_database():
    print("[*] Connecting to Neo4j AuraDB...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        driver.verify_connectivity()
        print("[+] Connected!\n")

        with driver.session() as session:
            print("[*] Clearing existing data...")
            session.run(CLEAR_QUERY)
            print("[+] Done.\n")

            for i, query in enumerate(SEED_QUERIES, 1):
                print(f"[*] Executing seed query {i}/{len(SEED_QUERIES)}...")
                session.run(query)
                print(f"[+] Done.")

            # Verification
            print("\n[*] Verifying graph...")
            r = session.run("MATCH (n:LegalIssue) RETURN count(n) AS c")
            print(f"    Legal Issues: {r.single()['c']}")
            r = session.run("MATCH (n:Precedent) RETURN count(n) AS c")
            print(f"    Precedents:   {r.single()['c']}")
            r = session.run("MATCH (n:Statute) RETURN count(n) AS c")
            print(f"    Statutes:     {r.single()['c']}")
            r = session.run("MATCH ()-[r:OVERRULES]->() RETURN count(r) AS c")
            print(f"    OVERRULES:    {r.single()['c']}")
            r = session.run("MATCH ()-[r:CITES]->() RETURN count(r) AS c")
            print(f"    CITES:        {r.single()['c']}")
            r = session.run("MATCH ()-[r:DISSENTS]->() RETURN count(r) AS c")
            print(f"    DISSENTS:     {r.single()['c']}")
            r = session.run("MATCH ()-[r:AMENDS]->() RETURN count(r) AS c")
            print(f"    AMENDS:       {r.single()['c']}")

        print("\n" + "=" * 50)
        print("[+] Database seeded successfully!")
        print("    Run: python legal_ai_system.py")
        print("=" * 50)

    except Exception as e:
        print(f"\n[!] Error: {e}")
        raise
    finally:
        driver.close()


if __name__ == "__main__":
    seed_database()
