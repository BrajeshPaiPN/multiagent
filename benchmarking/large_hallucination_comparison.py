"""
Large-Scale Comparative Hallucination Benchmark
===============================================
Objective: Run a comparative analysis on the 1,000-case large dataset
comparing "LLM Alone" vs "LLM + AKGP".

Dataset: hallucination_cases_large.csv
"""
import os
import csv
import json
import sys
import time
from langchain_groq import ChatGroq
from dotenv import load_dotenv

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from akgp.graph_manager import AKGPGraphManager

load_dotenv()

SCRIPT_DIR = os.path.dirname(__file__)
DATA_CSV = os.path.join(SCRIPT_DIR, "hallucination_cases_large.csv")
RESULTS_JSON = os.path.join(SCRIPT_DIR, "large_hallucination_comparison_results.json")
BENCHMARK_MODEL = "llama-3.1-8b-instant"

def robust_lookup(gm, name):
    """
    Tries multiple name variations to find a match in the graph.
    Indian case names often vary in 'vs', 'v.', 'And Ors', etc.
    """
    # 1. Exact match
    res = gm.lookup_case(name)
    if res: return res
    
    # 2. Simplified name (Petitioner v Respondent)
    # Handle both 'vs' and 'v.'
    simple_name = name.replace(" vs ", " v. ")
    res = gm.lookup_case(simple_name)
    if res: return res
    
    # 3. Petitioner only
    if " v. " in simple_name:
        petitioner = simple_name.split(" v. ")[0].strip()
        # Only use if petitioner name is substantial
        if len(petitioner) > 10:
            res = gm.lookup_case(petitioner)
            if res: return res
            
    return None

def run_benchmark(limit=100):
    if not os.path.exists(DATA_CSV):
        print(f"[!] Data file not found: {DATA_CSV}")
        return

    # Initialize components
    llm = ChatGroq(model=BENCHMARK_MODEL, temperature=0)
    gm = AKGPGraphManager()
    
    # Load data
    cases = []
    with open(DATA_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["is_real"] = str(row["is_real"]).lower() in ("true", "1", "yes")
            cases.append(row)
    
    # Balanced subset
    real_cases = [c for c in cases if c["is_real"]][:limit//2]
    fake_cases = [c for c in cases if not c["is_real"]][:limit//2]
    test_cases = real_cases + fake_cases
    
    print("\n" + "=" * 90)
    print(">>> LARGE-SCALE COMPARATIVE HALLUCINATION BENCHMARK")
    print(f"    Source: {os.path.basename(DATA_CSV)}")
    print(f"    Cases: {len(test_cases)} ({len(real_cases)} real, {len(fake_cases)} fake)")
    print("=" * 90)
    print(f"{'TYPE':<6} | {'CASE NAME':<40} | {'LLM ALONE':<12} | {'LLM + AKGP':<12} | {'STATUS'}")
    print("-" * 90)

    comparison_results = []
    llm_correct = 0
    akgp_correct = 0

    for i, case in enumerate(test_cases):
        name = case["name"]
        year = case["year"]
        is_real = case["is_real"]
        type_label = "REAL" if is_real else "FAKE"

        # --- MODE 1: LLM ALONE ---
        prompt = (
            "Verify this Indian Supreme Court case. Reply ONLY VERIFIED or HALLUCINATED.\n"
            f"Case: {name} ({year})"
        )
        try:
            llm_raw = llm.invoke(prompt).content.strip().upper()
            llm_verdict = "VERIFIED" if "VERIFIED" in llm_raw else "HALLUCINATED"
        except Exception as e:
            llm_verdict = "ERROR"

        # --- MODE 2: LLM + AKGP ---
        graph_result = robust_lookup(gm, name)
        akgp_verdict = "VERIFIED" if graph_result else "HALLUCINATED"

        # Scoring
        llm_is_correct = (is_real and llm_verdict == "VERIFIED") or (not is_real and llm_verdict == "HALLUCINATED")
        akgp_is_correct = (is_real and akgp_verdict == "VERIFIED") or (not is_real and akgp_verdict == "HALLUCINATED")
        
        if llm_is_correct: llm_correct += 1
        if akgp_is_correct: akgp_correct += 1

        status = "PASS" if akgp_is_correct else "FAIL"
        
        # Truncate name for display
        disp_name = name[:40] + "..." if len(name) > 40 else name
        print(f"{type_label:<6} | {disp_name:<40} | {llm_verdict:<12} | {akgp_verdict:<12} | {status}")
        
        comparison_results.append({
            "case": name,
            "is_real": is_real,
            "llm_verdict": llm_verdict,
            "akgp_verdict": akgp_verdict,
            "llm_correct": llm_is_correct,
            "akgp_correct": akgp_is_correct
        })
        
        time.sleep(1.2) # Avoid rate limits

    # Summary
    total = len(test_cases)
    print("-" * 90)
    print(f"RESULTS SUMMARY (N={total})")
    print(f"  LLM ALONE ACCURACY:  {(llm_correct/total)*100:.1f}%")
    print(f"  LLM + AKGP ACCURACY: {(akgp_correct/total)*100:.1f}%")
    print(f"  NET PERFORMANCE GAIN: {((akgp_correct - llm_correct)/total)*100:+.1f}%")
    print("=" * 90)

    # Metrics Breakdown
    real_processed = len(real_cases)
    fake_processed = len(fake_cases)
    
    llm_fake_detected = sum(1 for r in comparison_results if not r["is_real"] and r["llm_verdict"] == "HALLUCINATED")
    akgp_fake_detected = sum(1 for r in comparison_results if not r["is_real"] and r["akgp_verdict"] == "HALLUCINATED")
    
    print(f"  Fakes Detected by LLM:  {llm_fake_detected}/{fake_processed} ({(llm_fake_detected/fake_processed)*100:.1f}%)")
    print(f"  Fakes Detected by AKGP: {akgp_fake_detected}/{fake_processed} ({(akgp_fake_detected/fake_processed)*100:.1f}%)")
    print(f"  [!] Hallucination Prevention Rate (AKGP): {(akgp_fake_detected/fake_processed)*100:.1f}%")

    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "dataset": "hallucination_cases_large.csv",
            "model": BENCHMARK_MODEL,
            "metrics": {
                "total": total,
                "llm_accuracy": llm_correct/total,
                "akgp_accuracy": akgp_correct/total,
                "hallucination_prevention_rate": akgp_fake_detected/fake_processed
            },
            "details": comparison_results
        }, f, indent=2)

    gm.close()

if __name__ == "__main__":
    # Running 100 cases for a definitive large-scale comparison
    run_benchmark(limit=100)
