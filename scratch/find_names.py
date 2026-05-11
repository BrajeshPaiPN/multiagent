import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from akgp.graph_manager import AKGPGraphManager

gm = AKGPGraphManager()
with gm.driver.session() as s:
    res = s.run("MATCH (c:Precedent) RETURN c.name LIMIT 50")
    for r in res:
        print(r["c.name"])
gm.close()
