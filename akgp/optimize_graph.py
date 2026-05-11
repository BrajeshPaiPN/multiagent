"""
Neo4j Performance Optimizer
==========================
Ensures critical indexes are present for fast benchmarking.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from akgp.graph_manager import AKGPGraphManager

def optimize():
    gm = AKGPGraphManager()
    if not gm.verify_connection():
        return
    
    with gm.driver.session() as session:
        print("[*] Creating index on Precedent(name) for fast lookups...")
        try:
            session.run("CREATE INDEX precedent_name_idx IF NOT EXISTS FOR (c:Precedent) ON (c.name)")
            print("[+] Index created/verified.")
        except Exception as e:
            print(f"[!] Failed to create index: {e}")
    
    gm.close()

if __name__ == "__main__":
    optimize()
