"""
BNS Mapping Accuracy Benchmark
==============================
Evaluates how accurately the system maps old IPC sections to new BNS sections.
"""

import os
import json
import sys
from langchain_groq import ChatGroq
from dotenv import load_dotenv

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import LLM_ANALYZER

load_dotenv()

# GROUND TRUTH: BNS-IPC-CrossMap-2024
# Curated mapping of major Indian Penal Code (IPC) sections to 
# Bharatiya Nyaya Sanhita (BNS), 2023.
GROUND_TRUTH = {
    "IPC 302": "BNS 103",   # Murder
    "IPC 307": "BNS 109",   # Attempt to murder
    "IPC 304B": "BNS 80",   # Dowry death
    "IPC 376": "BNS 64",    # Rape
    "IPC 379": "BNS 303",   # Theft
    "IPC 380": "BNS 305",   # Theft in dwelling house
    "IPC 392": "BNS 309",   # Robbery
    "IPC 395": "BNS 310",   # Dacoity
    "IPC 406": "BNS 316",   # Criminal breach of trust
    "IPC 420": "BNS 318",   # Cheating
    "IPC 498A": "BNS 85",   # Cruelty by husband or relatives
    "IPC 124A": "BNS 152",  # Sedition / Acts endangering sovereignty
    "IPC 143": "BNS 189",   # Unlawful assembly
    "IPC 295A": "BNS 299",  # Religious insults
    "IPC 506": "BNS 351",   # Criminal intimidation
    "IPC 34": "BNS 3",      # Common intention
    "IPC 120B": "BNS 61",   # Criminal conspiracy
    "IPC 323": "BNS 115",   # Voluntarily causing hurt
    "IPC 326": "BNS 117",   # Grievous hurt by dangerous weapons
    "IPC 354": "BNS 74",    # Outraging modesty of a woman
    "IPC 363": "BNS 137",   # Kidnapping
    "IPC 411": "BNS 317",   # Receiving stolen property
    "IPC 441": "BNS 329",   # Criminal trespass
    "IPC 499": "BNS 356",   # Defamation
    "IPC 509": "BNS 79",    # Word, gesture or act intended to insult modesty of a woman
}

def test_mapping_accuracy():
    print("="*60)
    print(">>> BNS MAPPING ACCURACY BENCHMARK")
    print("="*60)
    
    llm = ChatGroq(model=LLM_ANALYZER, temperature=0)
    
    correct = 0
    total = len(GROUND_TRUTH)
    results = []

    for ipc, expected_bns in GROUND_TRUTH.items():
        prompt = (
            f"Identify the corresponding section in the Bharatiya Nyaya Sanhita (BNS), 2023 "
            f"for the old Indian Penal Code (IPC) section: {ipc}.\n\n"
            "Return ONLY the BNS section number (e.g., 'BNS 103'). Do not explain."
        )
        
        try:
            response = llm.invoke(prompt).content.strip()
            # Clean response to handle variations like "BNS Section 103"
            actual = response.replace("Section", "").replace("  ", " ").strip()
            
            is_correct = (actual.lower() == expected_bns.lower())
            if is_correct:
                correct += 1
            
            results.append({
                "ipc": ipc,
                "expected": expected_bns,
                "actual": actual,
                "status": "PASS" if is_correct else "FAIL"
            })
            print(f"[{'√' if is_correct else 'X'}] {ipc} -> {actual} (Expected: {expected_bns})")
        except Exception as e:
            print(f"[!] Error testing {ipc}: {e}")

    accuracy = (correct / total) * 100
    print("\n" + "="*60)
    print(f"BENCHMARK SUMMARY")
    print(f"Total Tested: {total}")
    print(f"Correct:      {correct}")
    print(f"Accuracy:     {accuracy:.2f}%")
    print("="*60)
    
    # Save results
    output_path = os.path.join(os.path.dirname(__file__), "bns_mapping_results.json")
    with open(output_path, "w") as f:
        json.dump({
            "accuracy": accuracy,
            "details": results
        }, f, indent=4)
    print(f"\nDetailed results saved to {output_path}")

if __name__ == "__main__":
    test_mapping_accuracy()
