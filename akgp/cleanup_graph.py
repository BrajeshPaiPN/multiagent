import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from akgp.graph_manager import AKGPGraphManager

gm = AKGPGraphManager()
with gm.driver.session() as s:
    print("[*] Deleting 2000 nodes to ensure benchmark room...")
    s.run("MATCH (n) WITH n LIMIT 2000 DETACH DELETE n")
    print("[+] Done.")
gm.close()
