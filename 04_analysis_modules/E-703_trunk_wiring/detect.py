"""G5 - find and fix trunk-wiring defects: spurious shortcut edges.

The defect, as found at Aligarh. The graph carries an edge SOMNA-DAUD KHAN of 28.8 km
with no measured geometry and no train running it, while the real line runs
SOMNA - KALUA - MAHRAWAL - ALIGARH JN - DAUD KHAN (30.8 km, 128+ trains). Being 2 km
shorter, the phantom edge wins every shortest path, so Aligarh Jn - a junction 200
trains a day call at - sits off the Delhi-Kanpur trunk in the graph. Criticality,
betweenness and delay all land on the wrong track.

The pattern, stated generally: an edge no train traverses, duplicating a parallel
chain of stations that trains do traverse, lying along the same alignment.

Detector - an edge E=(U,V) is a spurious shortcut when all four hold:
  1. no train runs U-V as consecutive stops (service_direct == 0), in 2017 or 2024;
  2. without E, U and V are still joined by a path no more than `bypass_max_ratio`
     times its length - so E adds no reach, only a shortcut;
  3. every intermediate station on that path lies along the U-V alignment (small
     perpendicular offset, and not doubling back), so the two are the same line
     rather than a genuine alternative route;
  4. that path carries real service, so it is the line the trains actually use.

Confirmed by a second, independent detector run on the timetables alone: stations
that trains stop at which do not lie on the graph's own path between the stops either
side of them. The two agree on the same places.

Run:  python detect.py <Rail-Intell root> <output dir>
"""
import json, math, sys
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "04_analysis_modules/E-702_station_code_crosswalk"))
from resolve import load_resolver                                    # noqa: E402

TH = dict(bypass_max_ratio=1.35, offset_frac=0.30, offset_max_km=10.0,
          min_edge_km=3.0, detour_min_km=2.0, min_trains=4)

nodes = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/nodes.csv")
edges = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/edges.csv")
res = load_resolver(ROOT)
pos = {r.node_id: (r.longitude, r.latitude) for r in nodes.itertuples()}
nm = dict(zip(nodes.node_id, nodes.node_name))

def hav(a, b):
    (lo1, la1), (lo2, la2) = a, b
    p = math.pi / 180
    h = (math.sin((la2 - la1) * p / 2) ** 2 + math.cos(la1 * p) * math.cos(la2 * p) *
         math.sin((lo2 - lo1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(min(1, h)))

def offset_km(p, a, b):
    """Perpendicular distance of p from the segment a-b, in km (flat approx)."""
    k = math.cos(math.radians(a[1])) * 111.32
    ax, ay = a[0] * k, a[1] * 111.32
    bx, by = b[0] * k, b[1] * 111.32
    px, py = p[0] * k, p[1] * 111.32
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0: return math.hypot(px - ax, py - ay), 0.0
    t = ((px - ax) * dx + (py - ay) * dy) / L2
    proj = (ax + t * dx, ay + t * dy)
    return math.hypot(px - proj[0], py - proj[1]), t

G = nx.Graph()
for r in edges.itertuples():
    if G.has_edge(r.from_node, r.to_node) and G[r.from_node][r.to_node]["km"] <= r.length_km:
        continue
    G.add_edge(r.from_node, r.to_node, km=float(r.length_km), eid=r.edge_id,
               direct=int(r.service_direct), load=int(r.service_load),
               src=r.length_source, lb=bool(r.length_is_lower_bound),
               corridor=r.corridor_id, tracks=r.n_tracks)

# ---------------------------------------------------------------- timetable adjacency
# consecutive stop pairs, 2017 and 2024, mapped through the G1 crosswalk
def consecutive(df, code_col, train_col, seq_col):
    df = df.sort_values([train_col, seq_col])
    pairs = defaultdict(int)
    stops = defaultdict(list)
    for t, g in df.groupby(train_col, sort=False):
        seq = [res.node(c) for c in g[code_col]]
        seq = [s for s in seq if s]
        seq = [s for i, s in enumerate(seq) if i == 0 or s != seq[i - 1]]
        for a, b in zip(seq, seq[1:]):
            pairs[(a, b) if a < b else (b, a)] += 1
        stops[t] = seq
    return pairs, stops

t17 = pd.read_csv(ROOT / "external_data/timetable_2017_datagovin/Train_details_22122017.csv",
                  dtype=str)
t17["seq"] = pd.to_numeric(t17.SEQ, errors="coerce")
t17["code"] = t17["Station Code"].str.strip()
p17, _ = consecutive(t17, "code", "Train No", "seq")

r24 = pd.read_csv(ROOT / "external_data/iitkgp_rstgcn_network_2024/"
                  "Indian-Railway-Network-and-Delays/train_routes_Sep2024.csv", dtype=str)
r24["seq"] = r24.stnSerialNumber.astype(int)
r24["tno"] = r24.trainNumber.str.zfill(5)
p24, stops24 = consecutive(r24, "station_code", "tno", "seq")
adjacency = defaultdict(int)
for d in (p17, p24):
    for k, v in d.items(): adjacency[k] += v

# ---------------------------------------------------------------- detector 1: shortcuts
def bypass(u, v):
    d = G[u][v]
    G.remove_edge(u, v)
    try:
        km, path = nx.single_source_dijkstra(G, u, v, weight="km")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        km, path = None, None
    G.add_edge(u, v, **d)
    return km, path

cand = []
for u, v in list(G.edges()):
    d = G[u][v]
    if d["km"] < TH["min_edge_km"]: continue
    if adjacency.get((u, v) if u < v else (v, u), 0) > 0: continue   # trains do run it
    if d["direct"] > 0: continue
    km, path = bypass(u, v)
    if km is None or km > d["km"] * TH["bypass_max_ratio"]: continue
    mid = path[1:-1]
    if not mid: continue
    lim = min(TH["offset_max_km"], max(2.0, d["km"] * TH["offset_frac"]))
    offs = [offset_km(pos[x], pos[u], pos[v]) for x in mid if x in pos]
    if not offs or max(o for o, _ in offs) > lim: continue
    if min(t for _, t in offs) < -0.15 or max(t for _, t in offs) > 1.15: continue  # doubles back
    legs = [G[a][b] for a, b in zip(path, path[1:])]
    if min(l["direct"] for l in legs) <= 0: continue                 # chain must carry trains
    cand.append(dict(edge_id=d["eid"], u=u, v=v, name=f"{nm[u]} - {nm[v]}",
                     km=round(d["km"], 2), bypass_km=round(km, 2),
                     ratio=round(km / d["km"], 3), length_source=d["src"],
                     lower_bound=d["lb"], load=d["load"], tracks=d["tracks"],
                     via=" > ".join(nm[x] for x in mid),
                     via_ids="|".join(mid), stations_restored=len(mid),
                     min_leg_trains=int(min(l["direct"] for l in legs)),
                     max_offset_km=round(max(o for o, _ in offs), 2)))
sc = pd.DataFrame(cand)

# ---------------------------------------------------------------- detector 2: off-spine
# purely timetable-driven: a station trains stop at that the graph routes around
_sp = {}
def spkm(a, b):
    k = (a, b) if a < b else (b, a)
    if k not in _sp:
        try: _sp[k] = nx.shortest_path_length(G, a, b, weight="km")
        except (nx.NetworkXNoPath, nx.NodeNotFound): _sp[k] = None
    return _sp[k]

det = defaultdict(list)
for t, seq in stops24.items():
    for p, s, n in zip(seq, seq[1:], seq[2:]):
        if p == n: continue
        a, b, c = spkm(p, s), spkm(s, n), spkm(p, n)
        if None in (a, b, c): continue
        det[s].append(a + b - c)
off = pd.DataFrame([dict(node=s, name=nm[s], trains=len(v),
                         median_detour_km=round(float(np.median(v)), 2))
                    for s, v in det.items() if len(v) >= TH["min_trains"]])
off = off[off.median_detour_km >= TH["detour_min_km"]].sort_values(
    ["trains", "median_detour_km"], ascending=False)
off.to_csv(OUT / "off_spine_stations.csv", index=False)

# do the two detectors point at the same places?
restored = set()
for r in sc.itertuples(): restored.update(r.via_ids.split("|"))
off["explained_by_shortcut"] = off.node.isin(restored)
sc["fixes_off_spine_stations"] = [
    sum(1 for x in r.via_ids.split("|") if x in set(off.node)) for r in sc.itertuples()]
sc = sc.sort_values(["fixes_off_spine_stations", "load"], ascending=False)
sc.to_csv(OUT / "shortcut_edges.csv", index=False)
off.to_csv(OUT / "off_spine_stations.csv", index=False)

rep = dict(experiment="E-703 / gap G5", thresholds=TH,
           edges_tested=G.number_of_edges(),
           shortcut_edges=len(sc),
           shortcut_km=round(float(sc.km.sum()), 1) if len(sc) else 0,
           stations_restored=len(restored),
           off_spine_stations=len(off),
           off_spine_explained_by_a_shortcut=int(off.explained_by_shortcut.sum()),
           off_spine_trains_affected=int(off.trains.sum()),
           top_shortcuts=sc.head(20)[["edge_id", "name", "km", "bypass_km", "ratio",
                                      "length_source", "via", "min_leg_trains",
                                      "fixes_off_spine_stations"]].to_dict("records"),
           top_off_spine=off.head(20)[["node", "name", "trains", "median_detour_km",
                                       "explained_by_shortcut"]].to_dict("records"))
json.dump(rep, open(OUT / "detect_report.json", "w"), indent=2, default=str)
print(json.dumps({k: v for k, v in rep.items()
                  if k not in ("top_shortcuts", "top_off_spine")}, indent=1, default=str))
