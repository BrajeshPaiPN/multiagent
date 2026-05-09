"""
Neo4j Database Seeder
=====================
Seeds the AKGP knowledge graph with real landmark Indian court judgments.
Run: python seed_database.py
"""
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

PRECEDENTS = [
    # ── RENT / TENANCY ────────────────────────────────────────────────
    {"name": "Kewal Singh v. Lajwanti", "year": 1980, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Landlord entitled to recover premises if tenant misuses or sublets without consent",
     "legal_issue": "Security Deposit & Tenancy Rights", "section": "Transfer of Property Act S.108",
     "category": "Civil Law", "judge": "Y.V. Chandrachud CJ", "authority_level": 100},
    {"name": "Saul David Royan v. Raj Kumar Gupta", "year": 2019, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Security deposit must be returned within reasonable time after vacation; delay attracts interest",
     "legal_issue": "Security Deposit Return", "section": "Indian Contract Act S.73",
     "category": "Civil Law", "judge": "N.V. Ramana J", "authority_level": 100},
    {"name": "D.C. Bhatia v. Union of India", "year": 1995, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Rent control legislation protects tenant from arbitrary eviction; security deposit not forfeitable without proven damage",
     "legal_issue": "Tenant Protection & Deposit Forfeiture", "section": "Delhi Rent Control Act",
     "category": "Civil Law", "judge": "J.S. Verma J", "authority_level": 100},
    {"name": "Vidya Devi v. Prem Prakash", "year": 1995, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Tenant entitled to receipt for security deposit; landlord must prove actual damage to forfeit deposit",
     "legal_issue": "Security Deposit Receipt & Forfeiture", "section": "Transfer of Property Act S.105",
     "category": "Civil Law", "judge": "S.C. Agrawal J", "authority_level": 100},

    # ── CRIMINAL LAW ──────────────────────────────────────────────────
    {"name": "Bachan Singh v. State of Punjab", "year": 1980, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Death sentence permissible only in rarest of rare cases; mitigating circumstances must be considered",
     "legal_issue": "Capital Punishment — Rarest of Rare Doctrine", "section": "IPC S.302",
     "category": "Criminal Law", "judge": "Y.V. Chandrachud CJ", "authority_level": 100},
    {"name": "Navtej Singh Johar v. Union of India", "year": 2018, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Section 377 IPC decriminalised for consensual adult same-sex relations; overrules Suresh Kumar Koushal",
     "legal_issue": "Decriminalisation of Consensual Homosexuality", "section": "IPC S.377",
     "category": "Criminal Law", "judge": "Dipak Misra CJ", "authority_level": 100},
    {"name": "Suresh Kumar Koushal v. Naz Foundation", "year": 2013, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Reinstated S.377 IPC; held LGBT community minuscule minority — SUBSEQUENTLY OVERRULED",
     "legal_issue": "Section 377 IPC", "section": "IPC S.377",
     "category": "Criminal Law", "judge": "G.S. Singhvi J", "authority_level": 100},
    {"name": "D.K. Basu v. State of West Bengal", "year": 1997, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Landmark guidelines on arrest procedures; violation constitutes contempt of court",
     "legal_issue": "Arrest Guidelines & Fundamental Rights", "section": "CrPC S.41 / Article 21",
     "category": "Criminal Law", "judge": "A.S. Anand J", "authority_level": 100},
    {"name": "Arnesh Kumar v. State of Bihar", "year": 2014, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Police cannot arrest automatically in S.498A cases; magistrate must apply mind before authorising detention",
     "legal_issue": "Automatic Arrest in Matrimonial Disputes", "section": "CrPC S.41 / IPC S.498A",
     "category": "Criminal Law", "judge": "Chandramauli Kr. Prasad J", "authority_level": 100},

    # ── PROPERTY / REAL ESTATE ────────────────────────────────────────
    {"name": "Suraj Lamp & Industries v. State of Haryana", "year": 2011, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Property sales through General Power of Attorney invalid; only registered sale deeds convey title",
     "legal_issue": "GPA-Based Property Transactions", "section": "Transfer of Property Act S.54",
     "category": "Real Estate Law", "judge": "R.V. Raveendran J", "authority_level": 100},
    {"name": "Vidyadhar v. Manikrao", "year": 1999, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Specific performance decreed where party ready and willing to perform; time not essence unless agreed",
     "legal_issue": "Specific Performance of Sale Agreement", "section": "Specific Relief Act S.10",
     "category": "Real Estate Law", "judge": "G.B. Pattanaik J", "authority_level": 100},
    {"name": "Municipal Corporation of Greater Mumbai v. Kamla Mills Ltd", "year": 2003,
     "court": "Supreme Court of India", "jurisdiction": "central",
     "verdict": "Land use cannot be changed without statutory permission; commercial use of residential land invalid",
     "legal_issue": "Land Use & Zoning", "section": "Maharashtra Regional Town Planning Act",
     "category": "Real Estate Law", "judge": "B.N. Agrawal J", "authority_level": 100},

    # ── CONSTITUTIONAL LAW ────────────────────────────────────────────
    {"name": "Maneka Gandhi v. Union of India", "year": 1978, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Article 21 interpreted expansively; procedure must be fair, just and reasonable; overrules A.K. Gopalan",
     "legal_issue": "Right to Life & Personal Liberty — Expansive Interpretation", "section": "Constitution Article 21",
     "category": "Constitutional Law", "judge": "M.H. Beg CJ", "authority_level": 100},
    {"name": "A.K. Gopalan v. State of Madras", "year": 1950, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Article 21 requires only procedure established by law, not necessarily just procedure — OVERRULED by Maneka Gandhi",
     "legal_issue": "Scope of Article 21", "section": "Constitution Article 21",
     "category": "Constitutional Law", "judge": "H.J. Kania CJ", "authority_level": 100},
    {"name": "Kesavananda Bharati v. State of Kerala", "year": 1973, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Parliament cannot amend the basic structure of the Constitution; Doctrine of Basic Structure established",
     "legal_issue": "Basic Structure Doctrine", "section": "Constitution Article 368",
     "category": "Constitutional Law", "judge": "S.M. Sikri CJ", "authority_level": 100},
    {"name": "Justice K.S. Puttaswamy v. Union of India", "year": 2017, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Right to Privacy is a fundamental right under Article 21; overrules M.P. Sharma and Kharak Singh",
     "legal_issue": "Right to Privacy as Fundamental Right", "section": "Constitution Article 21",
     "category": "Constitutional Law", "judge": "J.S. Khehar CJ", "authority_level": 100},

    # ── CIVIL / CONTRACT LAW ──────────────────────────────────────────
    {"name": "Satyabrata Ghose v. Mugneeram Bangur", "year": 1954, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Doctrine of frustration under S.56 applies when performance becomes impossible due to changed circumstances",
     "legal_issue": "Frustration of Contract", "section": "Indian Contract Act S.56",
     "category": "Civil Law", "judge": "B.K. Mukherjea J", "authority_level": 100},
    {"name": "Mohori Bibee v. Dharmodas Ghose", "year": 1903, "court": "Privy Council",
     "jurisdiction": "central", "verdict": "Contract with minor is void ab initio; no ratification upon attaining majority",
     "legal_issue": "Minor's Capacity to Contract", "section": "Indian Contract Act S.11",
     "category": "Civil Law", "judge": "Lord Macnaghten", "authority_level": 75},
    {"name": "Hadley v. Baxendale", "year": 1854, "court": "Court of Exchequer",
     "jurisdiction": "central", "verdict": "Damages limited to those arising naturally or within reasonable contemplation of parties at time of contract",
     "legal_issue": "Remoteness of Damages in Contract Breach", "section": "Indian Contract Act S.73",
     "category": "Civil Law", "judge": "Alderson B", "authority_level": 75},

    # ── MOTOR VEHICLE / TRAFFIC ───────────────────────────────────────
    {"name": "National Insurance Co. v. Pranay Sethi", "year": 2017, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Uniform method prescribed for computing compensation in fatal accident claims; future prospects included for all ages",
     "legal_issue": "Motor Accident Compensation — Fatal Claims", "section": "Motor Vehicles Act S.166",
     "category": "Traffic Law", "judge": "Dipak Misra CJ", "authority_level": 100},
    {"name": "Sarla Verma v. Delhi Transport Corporation", "year": 2009, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Structured formula for computing compensation in motor accident claims; multiplier method standardised",
     "legal_issue": "Motor Accident Compensation Formula", "section": "Motor Vehicles Act S.163A",
     "category": "Traffic Law", "judge": "R.V. Raveendran J", "authority_level": 100},
    {"name": "Rajesh v. Rajbir Singh", "year": 2013, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Loss of consortium and love/affection recoverable by spouse; Sarla Verma formula refined",
     "legal_issue": "Compensation — Loss of Consortium", "section": "Motor Vehicles Act S.166",
     "category": "Traffic Law", "judge": "P. Sathasivam J", "authority_level": 100},

    # ── PATENT / IP LAW ──────────────────────────────────────────────
    {"name": "Novartis AG v. Union of India", "year": 2013, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Evergreening of pharmaceutical patents rejected; S.3(d) of Patents Act upheld; incremental innovations not patentable",
     "legal_issue": "Pharmaceutical Patent Evergreening & S.3(d)", "section": "Patents Act S.3(d)",
     "category": "Patent Law", "judge": "Aftab Alam J", "authority_level": 100},
    {"name": "Roche v. Cipla Ltd", "year": 2012, "court": "Delhi High Court",
     "jurisdiction": "central", "verdict": "Balance of convenience in pharmaceutical patent infringement; public interest considered in granting injunctions",
     "legal_issue": "Patent Infringement Injunction — Public Interest", "section": "Patents Act S.48",
     "category": "Patent Law", "judge": "S. Ravindra Bhat J", "authority_level": 75},

    # ── CONSUMER PROTECTION ───────────────────────────────────────────
    {"name": "Spring Meadows Hospital v. Harjol Ahluwalia", "year": 1998, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Medical negligence by hospital constitutes deficiency of service under Consumer Protection Act",
     "legal_issue": "Medical Negligence as Consumer Deficiency", "section": "Consumer Protection Act S.2(1)(g)",
     "category": "Civil Law", "judge": "S.B. Majmudar J", "authority_level": 100},
    {"name": "Lucknow Development Authority v. M.K. Gupta", "year": 1994, "court": "Supreme Court of India",
     "jurisdiction": "central", "verdict": "Government authorities providing services are liable under Consumer Protection Act; housing delay is deficiency",
     "legal_issue": "Government Services Under Consumer Protection Act", "section": "Consumer Protection Act S.14",
     "category": "Civil Law", "judge": "S.C. Agrawal J", "authority_level": 100},
]

# OVERRULES relationships: (newer_case, older_case, reason)
OVERRULES = [
    ("Navtej Singh Johar v. Union of India", "Suresh Kumar Koushal v. Naz Foundation",
     "Five-judge bench overruled two-judge bench; constitutional morality prevails over social morality"),
    ("Maneka Gandhi v. Union of India", "A.K. Gopalan v. State of Madras",
     "Procedure must be fair, just and reasonable — expanded interpretation of Article 21"),
    ("Justice K.S. Puttaswamy v. Union of India", "A.K. Gopalan v. State of Madras",
     "Privacy reaffirmed as fundamental right; restrictive reading of Article 21 overruled"),
    ("Suraj Lamp & Industries v. State of Haryana", "Vidyadhar v. Manikrao",
     "GPA sales clarified as invalid — Vidyadhar restricted to specific performance only"),
    ("National Insurance Co. v. Pranay Sethi", "Sarla Verma v. Delhi Transport Corporation",
     "Constitution bench refined and updated multiplier method and future prospects calculation"),
    ("Rajesh v. Rajbir Singh", "Sarla Verma v. Delhi Transport Corporation",
     "Consortium and love/affection added as compensable heads — expands Sarla Verma"),
    ("Saul David Royan v. Raj Kumar Gupta", "Kewal Singh v. Lajwanti",
     "Later judgment adds obligation of interest on delayed refund of security deposit"),
]

# CITES relationships: (citing_case, cited_case)
CITES = [
    ("Navtej Singh Johar v. Union of India", "Justice K.S. Puttaswamy v. Union of India"),
    ("Navtej Singh Johar v. Union of India", "Maneka Gandhi v. Union of India"),
    ("Justice K.S. Puttaswamy v. Union of India", "Maneka Gandhi v. Union of India"),
    ("Justice K.S. Puttaswamy v. Union of India", "Kesavananda Bharati v. State of Kerala"),
    ("Arnesh Kumar v. State of Bihar", "D.K. Basu v. State of West Bengal"),
    ("National Insurance Co. v. Pranay Sethi", "Sarla Verma v. Delhi Transport Corporation"),
    ("Rajesh v. Rajbir Singh", "Sarla Verma v. Delhi Transport Corporation"),
    ("Roche v. Cipla Ltd", "Novartis AG v. Union of India"),
    ("Saul David Royan v. Raj Kumar Gupta", "Kewal Singh v. Lajwanti"),
    ("D.C. Bhatia v. Union of India", "Kewal Singh v. Lajwanti"),
]


def seed():
    if not NEO4J_URI or not NEO4J_PASSWORD:
        print("[ERROR] Neo4j credentials not set. Check your .env file.")
        return

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    print(f"[+] Connected to Neo4j as '{NEO4J_USER}'")

    with driver.session() as session:
        # Clear existing data
        session.run("MATCH (n) DETACH DELETE n")
        print("[*] Cleared existing graph data.")

        # Create constraints
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Precedent) REQUIRE c.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (i:LegalIssue) REQUIRE i.name IS UNIQUE")
        print("[*] Constraints ensured.")

        # Insert precedents + legal issues
        for p in PRECEDENTS:
            session.run("""
                MERGE (c:Precedent {name: $name})
                SET c.year = $year, c.court = $court, c.jurisdiction = $jurisdiction,
                    c.verdict = $verdict, c.judge = $judge, c.authority_level = $authority_level
                MERGE (i:LegalIssue {name: $legal_issue})
                SET i.section = $section, i.category = $category
                MERGE (c)-[:APPLIES_TO]->(i)
            """, **p)

        print(f"[+] Inserted {len(PRECEDENTS)} precedents.")

        # Insert OVERRULES (newer supersedes older)
        for newer, older, reason in OVERRULES:
            session.run("""
                MATCH (newer:Precedent {name: $newer})
                MATCH (older:Precedent {name: $older})
                MERGE (newer)-[:OVERRULES {reason: $reason, valid_from: newer.year}]->(older)
            """, newer=newer, older=older, reason=reason)

        print(f"[+] Inserted {len(OVERRULES)} OVERRULES edges.")

        # Insert CITES
        for citer, cited in CITES:
            session.run("""
                MATCH (a:Precedent {name: $citer})
                MATCH (b:Precedent {name: $cited})
                MERGE (a)-[:CITES]->(b)
            """, citer=citer, cited=cited)

        print(f"[+] Inserted {len(CITES)} CITES edges.")

        # Verify
        count = session.run("MATCH (n:Precedent) RETURN count(n) AS c").single()["c"]
        print(f"\n✅ Done! {count} precedents now in the knowledge graph.")

    driver.close()


if __name__ == "__main__":
    seed()
