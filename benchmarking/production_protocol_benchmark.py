"""
Production Protocol Hallucination Benchmark
===========================================
Comparing:
1. SOTA LLM Alone (Llama 3.3 70B)
2. Dual LLM Consensus (Llama 8B + 70B)
3. AKGP Alone (Deterministic Graph)
4. AKGP + Dual LLM (The Combined Production Protocol)

Dataset: All 1,000 cases
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
from config import LLM_VERIFIER_V1, LLM_VERIFIER_V2

load_dotenv()

SCRIPT_DIR = os.path.dirname(__file__)
DATA_CSV = os.path.join(SCRIPT_DIR, "hallucination_cases_large.csv")
RESULTS_JSON = os.path.join(SCRIPT_DIR, "production_protocol_results.json")

def robust_lookup(gm, name):
    res = gm.lookup_case(name)
    if res: return res
    simple_name = name.replace(" vs ", " v. ")
    res = gm.lookup_case(simple_name)
    if res: return res
    return None

def run_production_benchmark(limit=100):
    llm_v1 = ChatGroq(model=LLM_VERIFIER_V1, temperature=0) # 8B
    llm_v2 = ChatGroq(model=LLM_VERIFIER_V2, temperature=0) # 70B SOTA
    gm = AKGPGraphManager()
    
    # Load data
    cases = []
    if not os.path.exists(DATA_CSV):
        print(f"File not found: {DATA_CSV}")
        return
        
    with open(DATA_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["is_real"] = str(row["is_real"]).lower() in ("true", "1", "yes")
            cases.append(row)
    
    # Balanced subset
    real_cases = [c for c in cases if c["is_real"]][:limit//2]
    fake_cases = [c for c in cases if not c["is_real"]][:limit//2]
    test_cases = real_cases + fake_cases
    
    print("\n" + "=" * 135)
    print(">>> PRODUCTION PROTOCOL BENCHMARK (AKGP + DUAL LLM)")
    print(f"    Cases: {len(test_cases)} | SOTA Model: {LLM_VERIFIER_V2}")
    print("=" * 135)
    print(f"{'TYPE':<5} | {'CASE NAME':<40} | {'SOTA 70B':<10} | {'DUAL-LLM':<10} | {'AKGP':<10} | {'HYBRID':<10} | {'STATUS'}")
    print("-" * 135)

    stats = {
        "sota": {"correct": 0},
        "dual": {"correct": 0},
        "akgp": {"correct": 0},
        "hybrid": {"correct": 0}
    }

    try:
        for i, case in enumerate(test_cases):
            name = case["name"]
            is_real = case["is_real"]
            type_label = "REAL" if is_real else "FAKE"
            print(f"[*] Processing {i+1}/{len(test_cases)}: {name[:40]}...")

            # 1. SOTA LLM (70B)
            prompt = f"Verify this Indian Supreme Court case. Reply ONLY VERIFIED or HALLUCINATED: {name}"
            try:
                v2_raw = llm_v2.invoke(prompt).content.strip().upper()
                sota_exists = "VERIFIED" in v2_raw
            except: sota_exists = False

            # 2. Dual LLM Consensus (8B + 70B)
            try:
                v1_raw = llm_v1.invoke(prompt).content.strip().upper()
                v1_exists = "VERIFIED" in v1_raw
            except: v1_exists = False
            dual_exists = v1_exists and sota_exists

            # 3. AKGP Alone
            graph_record = robust_lookup(gm, name)
            akgp_exists = True if graph_record else False

            # 4. Hybrid (The Production Protocol)
            # Logic: If graph confirms it, it's verified. Else, check Dual-LLM.
            hybrid_exists = akgp_exists or dual_exists

            # Scoring
            if sota_exists == is_real: stats["sota"]["correct"] += 1
            if dual_exists == is_real: stats["dual"]["correct"] += 1
            if akgp_exists == is_real: stats["akgp"]["correct"] += 1
            if hybrid_exists == is_real: stats["hybrid"]["correct"] += 1

            sota_str = "VERIFIED" if sota_exists else "HALLUC."
            dual_str = "VERIFIED" if dual_exists else "HALLUC."
            akgp_str = "VERIFIED" if akgp_exists else "HALLUC."
            hybrid_str = "VERIFIED" if hybrid_exists else "HALLUC."
            
            status = "PASS" if hybrid_exists == is_real else "FAIL"
            disp_name = name[:40] + "..." if len(name) > 40 else name
            print(f"{type_label:<5} | {disp_name:<40} | {sota_str:<10} | {dual_str:<10} | {akgp_str:<10} | {hybrid_str:<10} | {status}")
            
            time.sleep(1.5)

    except KeyboardInterrupt:
        pass

    processed = i + 1

    print("-" * 135)
    print(f"FINAL COMPARISON SUMMARY (N={processed})")
    print(f"  SOTA LLM (70B) Accuracy:    {(stats['sota']['correct']/processed)*100:.1f}%")
    print(f"  DUAL LLM Consensus:         {(stats['dual']['correct']/processed)*100:.1f}%")
    print(f"  AKGP Alone (Graph):         {(stats['akgp']['correct']/processed)*100:.1f}%")
    print(f"  HYBRID (AKGP + DUAL LLM):   {(stats['hybrid']['correct']/processed)*100:.1f}%")
    print("=" * 135)

    gm.close()

if __name__ == "__main__":
    run_production_benchmark(limit=30)
