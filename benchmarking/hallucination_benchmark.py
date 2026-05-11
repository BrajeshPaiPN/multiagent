"""
Hallucination Detection Benchmark
==================================
Evaluates the system's ability to distinguish between real and hallucinated legal citations.
"""

import os
import json
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from agents.hallucination_verifier import verify_cases_in_drafts

load_dotenv()

# Test cases: mix of real landmark cases and plausible-sounding hallucinations
TEST_CASES = [
    # REAL CASES
    {"case": "Kesavananda Bharati v. State of Kerala (1973)", "is_real": True},
    {"case": "Maneka Gandhi v. Union of India (1978)", "is_real": True},
    {"case": "Arnesh Kumar v. State of Bihar (2014)", "is_real": True},
    {"case": "Navtej Singh Johar v. Union of India (2018)", "is_real": True},
    {"case": "Lalita Kumari v. Govt. of U.P. (2014)", "is_real": True},
    
    # HALLUCINATED CASES (Fake but sound real)
    {"case": "Rajesh Gupta v. Registrar of Companies (2021)", "is_real": False},
    {"case": "Amit Shah v. State of Maharashtra (1995)", "is_real": False}, # Confusing real names with fake contexts
    {"case": "Sunil Varma v. Digital India Authority (2022)", "is_real": False}, # Non-existent authority
    {"case": "National Legal Services v. Union of India (2025)", "is_real": False}, # Future date
    {"case": "State of Punjab v. Harpreet Singh (2019) 4 SCC 999", "is_real": False}, # Fake citation suffix
]

def run_hallucination_benchmark():
    print("="*60)
    print(">>> HALLUCINATION DETECTION BENCHMARK")
    print("="*60)
    
    # We simulate an expert draft containing these cases
    cases_to_test = [t["case"] for t in TEST_CASES]
    
    # The verifier expects a list of drafts
    mock_drafts = [{
        "domain": "Benchmarking",
        "draft": f"The following cases are cited: {', '.join(cases_to_test)}"
    }]
    
    print(f"[*] Verifying {len(TEST_CASES)} citations...")
    verified, hallucinated, uncertain = verify_cases_in_drafts(mock_drafts)
    
    # Calculate Metrics
    tp = 0 # True Positives (Real cases verified)
    fp = 0 # False Positives (Hallucinated cases verified)
    tn = 0 # True Negatives (Hallucinated cases caught)
    fn = 0 # False Negatives (Real cases caught as hallucinations)
    
    verified_names = [v["case_name"] for v in verified]
    hallucinated_names = [h["case_name"] for h in hallucinated]
    uncertain_names = [u["case_name"] for u in uncertain]

    print("\n[RESULTS DETAIL]")
    for test in TEST_CASES:
        name = test["case"]
        real = test["is_real"]
        
        status = "UNKNOWN"
        if any(v in name for v in verified_names): status = "VERIFIED"
        elif any(h in name for h in hallucinated_names): status = "HALLUCINATED"
        elif any(u in name for u in uncertain_names): status = "UNCERTAIN"
        
        is_correct = False
        if real and status == "VERIFIED":
            tp += 1
            is_correct = True
        elif not real and status == "HALLUCINATED":
            tn += 1
            is_correct = True
        elif real and status == "HALLUCINATED":
            fn += 1
        elif not real and status == "VERIFIED":
            fp += 1
            
        print(f"[{'√' if is_correct else 'X'}] {name[:40]:<40} | Actual: {'Real' if real else 'Fake':<5} | System: {status}")

    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print(f"True Positives:  {tp}")
    print(f"True Negatives:  {tn}")
    print(f"False Positives: {fp}")
    print(f"False Negatives: {fn}")
    
    accuracy = (tp + tn) / len(TEST_CASES) * 100
    precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
    
    print(f"Accuracy:        {accuracy:.2f}%")
    print(f"Precision:       {precision:.2f}%")
    print(f"Recall:          {recall:.2f}%")
    print("="*60)

    # Save results
    with open("benchmarking/hallucination_results.json", "w") as f:
        json.dump({
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "tp": tp, "tn": tn, "fp": fp, "fn": fn
        }, f, indent=4)
    print(f"\nDetailed metrics saved to benchmarking/hallucination_results.json")

if __name__ == "__main__":
    run_hallucination_benchmark()
