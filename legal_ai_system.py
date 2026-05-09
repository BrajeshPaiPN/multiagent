"""
Cloud-API Legal Intelligence System - Main Entry Point
=======================================================
State-Machine-Based Semantic Reasoning Engine for Legal Research.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import build_legal_graph, create_initial_state

BANNER = """
+====================================================+
|     CLOUD-API LEGAL INTELLIGENCE SYSTEM            |
|     Multi-Agent | LangGraph | Neo4j | Gemini       |
|----------------------------------------------------|
|  Architecture: Router -> Domain Specialist Agent   |
|  Specialists: Criminal, Civil, Patent, Real Estate,|
|               Traffic, General                     |
|  Protocol: AKGP (Adaptive Knowledge Graph)         |
|  Scoring: H = (A * J) / T                          |
+====================================================+
"""

EXAMPLE_QUERIES = [
    "My client made a verbal threat online and the police are looking for him. "
    "Can we get Anticipatory Bail based on the State v. Sharma precedent?",

    "Is the right to privacy a fundamental right under Article 21? "
    "What are the latest Supreme Court rulings?",

    "My client is accused of online defamation. Can criminal defamation "
    "charges under BNS 356 be challenged as unconstitutional?",

    "A property dispute between two parties where the original sale deed "
    "from 2018 conflicts with a newer mutation entry from 2023.",
]


def run_interactive():
    """Run the system in interactive mode with example queries."""
    print(BANNER)

    app = build_legal_graph()

    while True:
        print("\n" + "-" * 50)
        print("Choose a query:")
        print("-" * 50)
        for i, q in enumerate(EXAMPLE_QUERIES, 1):
            print(f"  [{i}] {q[:80]}...")
        print(f"  [5] Enter custom query")
        print(f"  [0] Exit")
        print("-" * 50)

        choice = input("\nYour choice: ").strip()

        if choice == "0":
            print("Goodbye!")
            break
        elif choice in ["1", "2", "3", "4"]:
            query = EXAMPLE_QUERIES[int(choice) - 1]
        elif choice == "5":
            query = input("Enter your legal query: ").strip()
            if not query:
                continue
        else:
            print("Invalid choice.")
            continue

        print(f"\nUSER QUERY:\n    \"{query}\"\n")
        print("=" * 60)
        print("STARTING MULTI-AGENT PIPELINE...")
        print("=" * 60)

        try:
            initial_state = create_initial_state(query)
            final_state = app.invoke(initial_state)

            print("\n" + "=" * 60)
            print("FINAL LEGAL OPINION:")
            print("=" * 60)
            print(final_state["final_draft"])
            print("\n" + "=" * 60)

            # Print pipeline summary
            v, c, r = 0, 0, 0
            for ed in final_state.get("expert_drafts", []):
                v += len(ed.get("verified_cases", []))
                c += len(ed.get("cautioned_cases", []))
                r += len(ed.get("rejected_cases", []))
                
            print(f"Pipeline Summary: {v} verified, {c} cautioned, {r} rejected cases")
            print("[+] Pipeline complete.")

        except Exception as e:
            print(f"\n[!] Error: {e}")
            import traceback
            traceback.print_exc()


def run_single(query: str):
    """Run a single query through the pipeline."""
    print(BANNER)
    print(f"USER QUERY:\n    \"{query}\"\n")
    print("=" * 60)

    app = build_legal_graph()
    initial_state = create_initial_state(query)
    final_state = app.invoke(initial_state)

    print("\n" + "=" * 60)
    print("FINAL LEGAL OPINION:")
    print("=" * 60)
    print(final_state["final_draft"])
    print("\n" + "=" * 60)
    print("[+] Pipeline complete.")
    return final_state


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_single(" ".join(sys.argv[1:]))
    else:
        run_interactive()
