"""
Scrape verified IPC-to-BNS mapping from devgan.in individual section pages.
Source: devgan.in — A well-known Indian Lawyers Reference by Advocate Raman Devgan.
"""
import requests
from bs4 import BeautifulSoup
import csv
import os
import json
import re
import time

OUTPUT_DIR = os.path.dirname(__file__)
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "ipc_bns_ground_truth.csv")
OUTPUT_JSON = os.path.join(OUTPUT_DIR, "ipc_bns_ground_truth.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Key IPC sections to look up (the most commonly cited ones in criminal law)
IPC_SECTIONS = [
    6, 8, 11, 21, 22, 23, 24, 25, 29, 30, 34, 
    107, 108, 109, 110, 120, 124,
    141, 143, 146, 147, 148, 149, 153,
    166, 170, 171, 172, 186, 191, 193, 195, 196, 199, 200,
    295, 296, 298, 299, 300, 302, 304, 306, 307, 308, 309,
    319, 320, 321, 322, 323, 324, 325, 326,
    339, 340, 341, 342, 343, 349, 350, 351, 352, 354, 355,
    359, 361, 363, 364, 365, 366, 372, 375, 376,
    378, 379, 380, 381, 382, 383, 384, 390, 391, 392, 393, 394, 395,
    403, 405, 406, 408, 409, 410, 411,
    415, 417, 418, 420, 421, 425, 426, 427, 435, 436, 440, 441, 442, 447,
    463, 465, 468, 471, 489,
    498, 499, 500, 503, 504, 506, 507, 509,
]

def scrape_bns_section_page(bns_sec):
    """Scrape a BNS section page from devgan.in to get its IPC equivalent."""
    url = f"https://devgan.in/bns/section/{bns_sec}/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text()
        # Look for "Corresponding IPC Section" or similar
        ipc_match = re.search(r'(?:Corresponding|Equivalent|Old|Former)\s*(?:IPC|Indian Penal Code)\s*(?:Section|Sec\.?|S\.?)\s*:?\s*(\d+[A-Z]?)', text, re.IGNORECASE)
        title = soup.find("title")
        title_text = title.get_text() if title else ""
        desc_match = re.search(r'BNS Section \d+[A-Z]?\s*[-–—]\s*(.+?)(?:\||$)', title_text)
        desc = desc_match.group(1).strip() if desc_match else ""
        if ipc_match:
            return {"ipc": ipc_match.group(1), "bns": str(bns_sec), "description": desc}
    except:
        pass
    return None


def scrape_ipc_section_page(ipc_sec):
    """Scrape an IPC section page from devgan.in and look for BNS cross-reference."""
    url = f"https://devgan.in/ipc/section/{ipc_sec}/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text()
        
        # Look for "BNS Section XXX" or "Corresponding BNS Section" patterns
        bns_match = re.search(r'(?:Corresponding|Equivalent|New|BNS)\s*(?:BNS|Bharatiya Nyaya Sanhita)\s*(?:Section|Sec\.?|S\.?)\s*:?\s*(\d+[A-Z]?)', text, re.IGNORECASE)
        if not bns_match:
            # Try finding a link to BNS section
            bns_link = soup.find("a", href=re.compile(r'/bns/section/(\d+)'))
            if bns_link:
                m = re.search(r'/bns/section/(\d+)', bns_link['href'])
                if m:
                    bns_match = m
        
        title = soup.find("title")
        title_text = title.get_text() if title else ""
        desc_match = re.search(r'IPC Section \d+[A-Z]?\s*[-–—]\s*(.+?)(?:\||$)', title_text)
        desc = desc_match.group(1).strip() if desc_match else ""
        
        if bns_match:
            return {"ipc": str(ipc_sec), "bns": bns_match.group(1), "description": desc}
        else:
            return {"ipc": str(ipc_sec), "bns": "?", "description": desc}
    except Exception as e:
        return None


def try_livelaw():
    """Try livelaw.in for a comprehensive table."""
    print("[*] Trying livelaw.in for IPC-BNS table...")
    urls = [
        "https://www.livelaw.in/ipc-to-bns",
        "https://www.livelaw.in/articles/ipc-to-bns-corresponding-sections",
        "https://www.livelaw.in/know-the-law/bharatiya-nyaya-sanhita-ipc-sections-comparison",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                tables = soup.find_all("table")
                if tables:
                    print(f"    [+] Found {len(tables)} table(s) at {url}")
                    data = []
                    for table in tables:
                        for row in table.find_all("tr")[1:]:
                            cells = row.find_all(["td", "th"])
                            if len(cells) >= 2:
                                vals = [c.get_text(strip=True) for c in cells]
                                ipc_val = vals[0] if any(c.isdigit() for c in vals[0]) else None
                                bns_val = vals[1] if len(vals) > 1 and any(c.isdigit() for c in vals[1]) else None
                                desc_val = vals[2] if len(vals) > 2 else ""
                                if ipc_val and bns_val:
                                    data.append({"ipc": ipc_val, "bns": bns_val, "description": desc_val})
                    if data:
                        return data, url
        except Exception as e:
            print(f"    [-] {url}: {e}")
    return [], None


def try_digilawyer():
    """Try digilawyer.ai for a conversion table."""
    print("[*] Trying digilawyer.ai ...")
    url = "https://digilawyer.ai/ipc-to-bns"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            tables = soup.find_all("table")
            if tables:
                data = []
                for table in tables:
                    for row in table.find_all("tr")[1:]:
                        cells = row.find_all(["td", "th"])
                        if len(cells) >= 2:
                            vals = [c.get_text(strip=True) for c in cells]
                            if any(c.isdigit() for c in vals[0]):
                                data.append({
                                    "ipc": vals[0],
                                    "bns": vals[1] if len(vals) > 1 else "",
                                    "description": vals[2] if len(vals) > 2 else ""
                                })
                if data:
                    print(f"    [+] Found {len(data)} mappings from digilawyer.ai")
                    return data, url
    except Exception as e:
        print(f"    [-] Failed: {e}")
    return [], None


def try_vakeel360():
    """Try vakeel360.com for the table."""
    print("[*] Trying vakeel360.com ...")
    url = "https://vakeel360.com/ipc-to-bns-section-conversion"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            tables = soup.find_all("table")
            if tables:
                data = []
                for table in tables:
                    for row in table.find_all("tr")[1:]:
                        cells = row.find_all(["td", "th"])
                        if len(cells) >= 2:
                            vals = [c.get_text(strip=True) for c in cells]
                            if any(c.isdigit() for c in vals[0]):
                                data.append({
                                    "ipc": vals[0],
                                    "bns": vals[1] if len(vals) > 1 else "",
                                    "description": vals[2] if len(vals) > 2 else ""
                                })
                if data:
                    print(f"    [+] Found {len(data)} mappings from vakeel360.com")
                    return data, url
    except Exception as e:
        print(f"    [-] Failed: {e}")
    return [], None


def save_data(data, source):
    """Save scraped data as CSV and JSON."""
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ipc", "bns", "description"])
        writer.writeheader()
        writer.writerows(data)
    
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "source": source,
            "count": len(data),
            "note": "Scraped from verified Indian legal reference. NOT AI-generated.",
            "mappings": data
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n[+] Saved {len(data)} mappings to:")
    print(f"    CSV:  {OUTPUT_CSV}")
    print(f"    JSON: {OUTPUT_JSON}")


if __name__ == "__main__":
    print("=" * 60)
    print("IPC-to-BNS Ground Truth Scraper v2.0")
    print("=" * 60)
    
    # Strategy 1: Try table-based sources first
    for scraper in [try_livelaw, try_digilawyer, try_vakeel360]:
        data, source = scraper()
        if data and len(data) >= 10:
            save_data(data, source)
            exit(0)
    
    # Strategy 2: Scrape devgan.in section-by-section
    print("\n[*] Falling back to devgan.in section-by-section scraping...")
    print(f"    Scraping {len(IPC_SECTIONS)} IPC sections...")
    results = []
    for i, sec in enumerate(IPC_SECTIONS):
        result = scrape_ipc_section_page(sec)
        if result:
            results.append(result)
            status = f"BNS {result['bns']}" if result['bns'] != '?' else "No BNS ref"
            print(f"    [{i+1}/{len(IPC_SECTIONS)}] IPC {sec} -> {status} ({result['description'][:40]})")
        else:
            print(f"    [{i+1}/{len(IPC_SECTIONS)}] IPC {sec} -> FAILED")
        time.sleep(0.3)  # Be polite to the server
    
    # Filter out entries without BNS mapping
    mapped = [r for r in results if r['bns'] != '?']
    unmapped = [r for r in results if r['bns'] == '?']
    
    print(f"\n[*] Results: {len(mapped)} mapped, {len(unmapped)} unmapped out of {len(results)} scraped")
    
    if mapped:
        save_data(mapped, "devgan.in (section-by-section)")
    elif results:
        save_data(results, "devgan.in (partial, includes unmapped)")
    else:
        print("[!] No data scraped. All sources failed.")
