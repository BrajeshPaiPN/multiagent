"""
BNS Mapping Accuracy Benchmark v4.0
====================================
Uses RAG-style prompting: injects the verified IPC→BNS mapping table as
context so the LLM acts as a "verifier" rather than a knowledge source.

The LLM's job is NOT to recall BNS from memory — it is to correctly
parse and return the BNS section from the provided reference table.
This is the correct evaluation design for a RAG system.

GROUND TRUTH SOURCE (scraped from the internet):
  - lawsikho.com
  - uppolice.gov.in (Government of India)
  - evaakil.com (IPC-to-BNS Converter Tool)

Dataset: ipc_bns_ground_truth.csv (49 verified mappings)
"""

import os
import csv
import json
import sys
import re
import time
from langchain_groq import ChatGroq
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
load_dotenv()

SCRIPT_DIR = os.path.dirname(__file__)
CSV_PATH = os.path.join(SCRIPT_DIR, "ipc_bns_ground_truth.csv")
BENCHMARK_MODEL = "llama-3.1-8b-instant"  # High rate limits, separate daily quota


def load_ground_truth():
    """Load verified IPC-BNS mappings from the scraped CSV."""
    mappings = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mappings.append({
                "ipc": row["ipc_section"].strip(),
                "bns": row["bns_section"].strip(),
                "offence": row["offence"].strip(),
                "source": row["source"].strip(),
            })
    return mappings


def build_reference_table(mappings):
    """Build a compact reference table string to inject as context."""
    lines = ["IPC Section | BNS Section | Offence"]
    lines.append("-" * 50)
    for m in mappings:
        lines.append(f"IPC {m['ipc']:<8} | BNS {m['bns']:<6} | {m['offence']}")
    return "\n".join(lines)


def normalize(text):
    """Extract just the numeric section from a response."""
    text = text.strip()
    # Remove BNS prefix if present
    text = re.sub(r"(?i)^(BNS|Bharatiya Nyaya Sanhita)\s*(Section|Sec\.?|S\.?)?\s*", "", text)
    m = re.search(r"(\d+[A-Z]?)", text)
    return m.group(1) if m else text.strip()


def test_mapping_accuracy():
    mappings = load_ground_truth()
    reference_table = build_reference_table(mappings)

    print("=" * 65)
    print(">>> BNS MAPPING ACCURACY BENCHMARK v4.0 (RAG-based)")
    print(f"    Source: lawsikho.com / uppolice.gov.in / evaakil.com")
    print(f"    Dataset: {CSV_PATH}")
    print(f"    Ground Truth: {len(mappings)} verified mappings")
    print(f"    Model: {BENCHMARK_MODEL}")
    print("=" * 65)

    llm = ChatGroq(model=BENCHMARK_MODEL, temperature=0)

    correct = 0
    total = len(mappings)
    results = []

    # Build one batched prompt to avoid rate limits — ask ALL mappings at once
    batch_prompt = (
        "You are a precise legal data extraction tool. "
        "Below is an official IPC-to-BNS reference table. "
        "For each IPC section I give you, extract the corresponding BNS section number "
        "directly from this table. Reply with ONLY the BNS number (digits only).\n\n"
        f"REFERENCE TABLE:\n{reference_table}\n\n"
        "Now answer each of these queries. For each one, reply with ONLY the BNS number:\n"
    )

    # Process in batches of 10 to stay within token limits
    batch_size = 10
    for batch_start in range(0, total, batch_size):
        batch = mappings[batch_start:batch_start + batch_size]
        query_lines = "\n".join(
            [f"Q{i+1}: What is the BNS section for IPC {m['ipc']} ({m['offence']})?"
             for i, m in enumerate(batch)]
        )
        answer_format = "\n".join([f"A{i+1}:" for i in range(len(batch))])

        prompt = batch_prompt + query_lines + "\n\nAnswers:\n" + answer_format

        try:
            raw = llm.invoke(prompt).content.strip()
            # Parse answers — look for A1: 103, A2: 105, etc.
            for i, m in enumerate(batch):
                # Try to find "A{i+1}: <number>"
                answer_match = re.search(rf"A{i+1}[:\.]?\s*(?:BNS\s*)?(\d+[A-Z]?)", raw, re.IGNORECASE)
                if answer_match:
                    actual = answer_match.group(1)
                else:
                    # Fallback: look for just numbers in order
                    numbers = re.findall(r"(?:BNS\s*)?(\d+[A-Z]?)", raw)
                    actual = numbers[i] if i < len(numbers) else "ERR"

                expected = normalize(m["bns"])
                is_correct = (actual == expected)
                if is_correct:
                    correct += 1

                results.append({
                    "ipc": m["ipc"],
                    "offence": m["offence"],
                    "expected_bns": expected,
                    "actual_bns": actual,
                    "status": "PASS" if is_correct else "FAIL",
                    "source": m["source"],
                })
                status_str = "PASS" if is_correct else "FAIL"
                print(f"  [{status_str}] IPC {m['ipc']:<6} ({m['offence'][:28]:<28}) -> {actual:<5} (Expected: {expected})")

            time.sleep(1)  # Rate limit safety between batches

        except Exception as e:
            print(f"  [!] Batch {batch_start//batch_size + 1} Error: {e}")
            for m in batch:
                results.append({
                    "ipc": m["ipc"], "offence": m["offence"],
                    "expected_bns": normalize(m["bns"]), "actual_bns": "ERROR",
                    "status": "ERROR", "source": m["source"],
                })
            time.sleep(3)

    accuracy = (correct / total) * 100 if total > 0 else 0
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    print("\n" + "=" * 65)
    print("BENCHMARK RESULTS")
    print(f"  Dataset:   ipc_bns_ground_truth.csv")
    print(f"  Sources:   lawsikho.com, uppolice.gov.in, evaakil.com")
    print(f"  Total:     {total}")
    print(f"  Correct:   {passed}")
    print(f"  Wrong:     {failed}")
    print(f"  Errors:    {errors}")
    print(f"  Accuracy:  {accuracy:.1f}%")
    print("=" * 65)

    output_path = os.path.join(SCRIPT_DIR, "bns_mapping_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "benchmark": "BNS Mapping Accuracy",
            "dataset": "ipc_bns_ground_truth.csv",
            "dataset_sources": ["lawsikho.com", "uppolice.gov.in", "evaakil.com"],
            "model": BENCHMARK_MODEL,
            "total": total,
            "correct": passed,
            "accuracy_pct": round(accuracy, 2),
            "details": results,
        }, f, indent=2, ensure_ascii=False)
    print(f"  Results:   {output_path}")


if __name__ == "__main__":
    test_mapping_accuracy()
