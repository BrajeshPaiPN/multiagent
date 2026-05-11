"""
Master Benchmarking Suite
=========================
Runs all system benchmarks and generates a unified report.
"""

import os
import subprocess
import sys

def run_script(script_name):
    print(f"\n[RUNNING] {script_name}...")
    try:
        # Run the script and capture output
        result = subprocess.run([sys.executable, script_name], capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"[!] Failed to run {script_name}: {e}")
        return False

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("="*60)
    print("MALIS BENCHMARKING SUITE")
    print("="*60)
    
    scripts = [
        "bns_mapping_test.py",
        "hallucination_benchmark.py"
    ]
    
    success_count = 0
    for script in scripts:
        if run_script(script):
            success_count += 1
            
    print("\n" + "="*60)
    print(f"BENCHMARKING COMPLETE: {success_count}/{len(scripts)} passed")
    print("="*60)

if __name__ == "__main__":
    main()
