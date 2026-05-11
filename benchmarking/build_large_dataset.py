"""
Large-Scale Hallucination Dataset Builder
==========================================
Scrapes thousands of real Supreme Court cases from indiankanoon.org
and generates an equal number of synthetic fake cases for a balanced
research-grade hallucination benchmark dataset.

Source: indiankanoon.org — India's primary open-access legal database
Target: ~1000+ cases (500 real + 500 synthetic)
"""
import os
import csv
import json
import re
import time
import random
import requests
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(__file__)
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "hallucination_cases_large.csv")
OUTPUT_JSON = os.path.join(SCRIPT_DIR, "hallucination_cases_large_meta.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

# ─── Fake case name generators ─────────────────────────────────────────────────
FAKE_PETITIONERS = [
    "Digital Rights Foundation", "Citizens Forum for Transparency",
    "National Farmers Welfare Association", "Indian Civil Liberties Union",
    "All India Women's Rights Council", "Tech Freedom Initiative",
    "Environment Action Group", "Consumer Rights Federation",
    "Rural Development Society", "Urban Residents Welfare Board",
    "National Human Rights Commission (Petitioner)", "People's Union for Democracy",
    "Association of Democratic Reforms", "Internet Freedom Foundation",
    "Tribal Rights Alliance", "Small Traders Federation of India",
    "National Parents Association", "Healthcare Workers Union",
    "Migrant Labour Protection Forum", "Indian Journalists Association",
]

FAKE_RESPONDENTS = [
    "Union of India", "State of Maharashtra", "State of Karnataka",
    "State of Uttar Pradesh", "Ministry of Finance", "Ministry of Home Affairs",
    "Election Commission of India", "Reserve Bank of India",
    "Securities and Exchange Board of India", "Central Bureau of Investigation",
    "National Investigation Agency", "Ministry of Environment",
    "Food Corporation of India", "National Highway Authority",
    "Department of Telecommunications", "Central Vigilance Commission",
    "State of Delhi", "State of Kerala", "State of Tamil Nadu",
    "State of West Bengal",
]

FAKE_SUBJECTS = [
    "right to internet access under Article 21",
    "arbitrary internet shutdowns in conflict zones",
    "mandatory Aadhaar linkage for pension disbursement",
    "electoral bond scheme transparency",
    "farm loan waiver scheme constitutionality",
    "digital surveillance by intelligence agencies",
    "right to be forgotten in the digital age",
    "mandatory COVID-19 vaccination policy",
    "overnight bail restrictions for journalists",
    "retrospective environmental clearance for highways",
    "pension rights for contract government employees",
    "right to protest in public spaces",
    "sedition charges against students",
    "cryptocurrency regulation by RBI",
    "mandatory biometric attendance in schools",
    "reservation in private sector employment",
    "right to water as a fundamental right",
    "anti-defection law interpretation",
    "hate speech regulation on social media",
    "uniform civil code implementation in Goa",
]


def generate_fake_citation(year):
    """Generate a plausible-looking but fake SCC citation."""
    vol = random.randint(1, 16)
    page = random.randint(1, 999)
    return f"({year}) {vol} SCC {page}"


def generate_fake_cases(count):
    """Generate synthetic fake Supreme Court cases programmatically."""
    fakes = []
    for i in range(count):
        year = random.randint(1990, 2024)
        petitioner = random.choice(FAKE_PETITIONERS)
        respondent = random.choice(FAKE_RESPONDENTS)
        subject = random.choice(FAKE_SUBJECTS)
        name = f"{petitioner} v. {respondent}"
        citation = generate_fake_citation(year)
        fakes.append({
            "name": name,
            "year": str(year),
            "citation": citation,
            "snippet": f"Petition challenging {subject}, filed under Article 32 of the Constitution.",
            "is_real": False,
            "source": "synthetic-researcher-generated",
            "url": "N/A",
        })
    return fakes


def scrape_cases_from_indiankanoon(target_count=500):
    """
    Scrape real Supreme Court case titles and years from indiankanoon.org.
    Uses multiple search queries to get diverse case types.
    """
    real_cases = []
    seen_names = set()

    search_queries = [
        "constitutional validity fundamental rights",
        "article 21 right to life liberty",
        "criminal appeal conviction sentence",
        "writ petition habeas corpus",
        "property dispute land acquisition",
        "service law government employment",
        "tax income tax appeal",
        "environmental pollution article 21",
        "election petition corrupt practices",
        "motor accident compensation claim",
        "consumer protection deficiency service",
        "family law matrimonial dispute",
        "contract breach specific performance",
        "copyright trademark intellectual property",
        "bail anticipatory bail criminal",
        "transfer petition high court",
        "suo motu contempt of court",
        "public interest litigation PIL",
        "judicial review administrative law",
        "arbitration award enforcement",
    ]

    base_url = "https://indiankanoon.org/search/"

    for query in search_queries:
        if len(real_cases) >= target_count:
            break

        for page in range(0, 10):  # 10 pages per query = ~100 cases per query
            if len(real_cases) >= target_count:
                break

            params = {
                "formInput": f"{query} doctypes:supremecourt",
                "pagenum": page,
            }

            try:
                r = requests.get(base_url, params=params, headers=HEADERS, timeout=15)
                if r.status_code != 200:
                    print(f"  [!] HTTP {r.status_code} for query='{query}' page={page}")
                    break

                soup = BeautifulSoup(r.text, "html.parser")

                # Find all result items
                result_titles = soup.find_all("a", href=re.compile(r"/docfragment/\d+/"))
                if not result_titles:
                    # Try direct doc links
                    result_titles = soup.find_all("a", href=re.compile(r"/doc/\d+/"))

                if not result_titles:
                    print(f"  [!] No results for query='{query}' page={page}")
                    break

                for a_tag in result_titles:
                    title = a_tag.get_text(strip=True)
                    href = a_tag.get("href", "")

                    # Extract year from title "... on DD Month, YYYY"
                    year_match = re.search(r"on \d+ \w+, (\d{4})", title)
                    if not year_match:
                        year_match = re.search(r",\s*(\d{4})\s*$", title)
                    year = year_match.group(1) if year_match else "Unknown"

                    # Clean case name (remove date suffix)
                    clean_name = re.sub(r"\s+on\s+\d+\s+\w+,\s+\d{4}$", "", title).strip()
                    if not clean_name or clean_name in seen_names:
                        continue
                    if len(clean_name) < 10:
                        continue

                    seen_names.add(clean_name)
                    full_url = f"https://indiankanoon.org{href}" if href.startswith("/") else href

                    real_cases.append({
                        "name": clean_name,
                        "year": year,
                        "citation": f"({year}) Supreme Court of India",
                        "snippet": f"Supreme Court judgment. Query category: {query}.",
                        "is_real": True,
                        "source": "indiankanoon.org",
                        "url": full_url,
                    })

                    if len(real_cases) >= target_count:
                        break

                count_so_far = len(real_cases)
                print(f"  [+] query='{query[:30]}' page={page} -> {count_so_far} total real cases")
                time.sleep(0.8)  # Respectful delay

            except Exception as e:
                print(f"  [!] Error on query='{query}' page={page}: {e}")
                time.sleep(2)

    return real_cases


def build_large_dataset(real_target=500, fake_ratio=1.0):
    """Build a large balanced dataset with real and synthetic cases."""
    print("=" * 65)
    print("LARGE-SCALE HALLUCINATION DATASET BUILDER")
    print(f"Target: {real_target} real + {int(real_target * fake_ratio)} synthetic")
    print("=" * 65)

    # Step 1: Scrape real cases
    print(f"\n[*] Scraping real cases from indiankanoon.org (target: {real_target})...")
    real_cases = scrape_cases_from_indiankanoon(target_count=real_target)
    print(f"    -> Scraped {len(real_cases)} real cases")

    # Step 2: Generate synthetic fakes
    fake_count = int(len(real_cases) * fake_ratio)
    print(f"\n[*] Generating {fake_count} synthetic fake cases...")
    fake_cases = generate_fake_cases(fake_count)
    print(f"    -> Generated {len(fake_cases)} fake cases")

    # Step 3: Combine and shuffle
    all_cases = real_cases + fake_cases
    random.shuffle(all_cases)

    # Step 4: Save CSV
    fieldnames = ["name", "year", "citation", "snippet", "is_real", "source", "url"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in all_cases:
            writer.writerow({k: c.get(k, "") for k in fieldnames})

    # Step 5: Save metadata JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "total": len(all_cases),
            "real_count": len(real_cases),
            "fake_count": len(fake_cases),
            "real_source": "indiankanoon.org",
            "fake_source": "researcher-generated synthetic",
            "output_csv": OUTPUT_CSV,
        }, f, indent=2)

    print(f"\n{'=' * 65}")
    print(f"DATASET COMPLETE")
    print(f"  Total cases:  {len(all_cases)}")
    print(f"  Real (PASS):  {len(real_cases)}")
    print(f"  Fake (FAIL):  {len(fake_cases)}")
    print(f"  CSV:  {OUTPUT_CSV}")
    print(f"  Meta: {OUTPUT_JSON}")
    print(f"{'=' * 65}")
    return all_cases


if __name__ == "__main__":
    build_large_dataset(real_target=500, fake_ratio=1.0)
