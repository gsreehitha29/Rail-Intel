"""Consistency audit of the edges G5 and G6 added.

G5 ran before G6's alignment test existed, so some of its 150 added edges may be the
very defect G5 itself removes: a direct edge standing in for a run that really goes
through intermediate stations. Bahadurgarh - Shakurbasti is the tell - 20 km, added on
official adjacency, now carrying no trains at all, because G6 added Bahadurgarh -
Ghevra and the real route goes that way.

The test, run with each added edge taken back out so it cannot vouch for itself: the
edge is redundant when the remaining path keeps close to the straight line between its
two ends AND is no longer than it by more than `RATIO`. Both halves matter. Ratnagiri
- Thivim is 193 km against a 192.67 km chain on the same alignment: it buys nothing
except a way to skip every station on the Konkan line between them. An edge whose
alternative runs a third longer is doing real work and stays.

Run:  python audit_added_edges.py <Rail-Intell root> <output dir>
"""
import json, math, sys
from pathlib import Path

import networkx as nx
import pandas as pd

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from railgraph_repaired import load_graph                            # noqa: E402

ALIGN_KM, ALIGN_FRAC, RATIO = 2.0, 0.25, 1.15

G, meta = load_graph(ROOT)
pos = {n: (d["lon"], d["lat"]) for n, d in G.nodes(data=True) if pd.notna(d.get("lon"))}
nm = {n: d.get("name") for n, d in G.nodes(data=True)}
svc = pd.read_csv(OUT / "edge_service_2024.csv") if (OUT / "edge_service_2024.csv").exists() \
    else None
load = dict(zip(svc.edge_id, svc.service_load_2024)) if svc is not None else {}

def offset(p, a, b):
    k = math.cos(math.radians(a[1])) * 111.32
    ax, ay, bx, by, px, py = (a[0]*k, a[1]*111.32, b[0]*k, b[1]*111.32, p[0]*k, p[1]*111.32)
    dx, dy = bx - ax, by - ay
    L2 = dx*dx + dy*dy
    if L2 == 0: return math.hypot(px-ax, py-ay)
    t = max(0.0, min(1.0, ((px-ax)*dx + (py-ay)*dy) / L2))
    return math.hypot(px - (ax + t*dx), py - (ay + t*dy))

rows = []
for u, v, d in [(u, v, d) for u, v, d in G.edges(data=True) if d["origin"] != "v1.3"]:
    G.remove_edge(u, v)
    try:
        km, p = nx.single_source_dijkstra(G, u, v, weight="km", cutoff=d["km"] * 6)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        km, p = None, None
    G.add_edge(u, v, **d)
    verdict, worst = "keep", None
    if p and len(p) > 2 and u in pos and v in pos:
        mid = [pos[x] for x in p[1:-1] if x in pos]
        if mid:
            worst = max(offset(x, pos[u], pos[v]) for x in mid)
            lim = max(ALIGN_KM, d["km"] * ALIGN_FRAC)
            if worst <= lim and km <= d["km"] * RATIO:
                verdict = "redundant: a real chain already runs this"
    rows.append(dict(edge_id=d["eid"], origin=d["origin"], name=f"{nm[u]} - {nm[v]}",
                     km=round(d["km"], 2),
                     alt_km=round(km, 2) if km else None,
                     ratio=round(km / d["km"], 2) if km else None,
                     max_offset_km=round(worst, 2) if worst is not None else None,
                     via=" > ".join(nm[x] for x in (p or [])[1:-1][:5]),
                     service_load_2024=load.get(d["eid"], load.get(f"{d['origin']}:{u}|{v}", 0)),
                     verdict=verdict))

a = pd.DataFrame(rows).sort_values(["verdict", "km"], ascending=[False, False])
a.to_csv(OUT / "added_edge_audit.csv", index=False)
red = a[a.verdict != "keep"]
rep = dict(added_edges=len(a), redundant=len(red),
           redundant_by_origin={k: int(v) for k, v in red.origin.value_counts().items()},
           redundant_km=round(float(red.km.sum()), 1),
           redundant_carrying_no_trains=int((red.service_load_2024 == 0).sum()),
           worst=red.head(12)[["name", "origin", "km", "alt_km", "max_offset_km", "via",
                               "service_load_2024"]].to_dict("records"))
json.dump(rep, open(OUT / "added_edge_audit.json", "w"), indent=2, default=str)
print(json.dumps({k: v for k, v in rep.items() if k != "worst"}, indent=1, default=str))
print(red.head(10)[["name", "origin", "km", "alt_km", "max_offset_km",
                    "service_load_2024"]].to_string(index=False))
