"""Does pruning the redundant added edges cost anything?

Compares v1.3 raw, the full repair set, and the pruned repair set on the same measures
G5 and G6 used. If the pruned graph holds the gains, it is strictly better: the same
routing, 2,797 km fewer invented edges, and no reintroduction of the shortcut defect.

Run:  python verify_pruned.py <Rail-Intell root> <audit csv> <output dir>
"""
import json, math, sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT, AUDIT, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "04_analysis_modules/E-702_station_code_crosswalk"))
from resolve import load_resolver                                    # noqa: E402
from railgraph_repaired import load_graph                            # noqa: E402

res = load_resolver(ROOT)
nodes = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/nodes.csv")
pos = {r.node_id: (r.longitude, r.latitude) for r in nodes.itertuples()}

def hav(pa, pb):
    if pa is None or pb is None: return None
    (lo1, la1), (lo2, la2) = pa, pb
    p = math.pi / 180
    h = (math.sin((la2-la1)*p/2)**2 + math.cos(la1*p)*math.cos(la2*p)*math.sin((lo2-lo1)*p/2)**2)
    return 12742 * math.asin(math.sqrt(min(1, h)))

irn = pd.read_csv(ROOT / "external_data/iitkgp_rstgcn_network_2024/"
                  "Indian-Railway-Network-and-Delays/IRN_edges.csv")
irn["a"] = irn["from"].map(res.node); irn["b"] = irn["to"].map(res.node)
irn = irn.dropna(subset=["a", "b"]); irn = irn[irn.a != irn.b]
ip = {}
for r in irn.itertuples():
    k = (r.a, r.b) if r.a < r.b else (r.b, r.a)
    ip.setdefault(k, []).append(float(r.distance))
ip = {k: float(np.median(v)) for k, v in ip.items() if np.median(v) > 0}

def trains_from(df, code, train, seq, dist):
    df = df.sort_values([train, seq]); out = []
    for t, g in df.groupby(train, sort=False):
        stops = []
        for r in g.itertuples():
            nd = res.node(getattr(r, code)); d = getattr(r, dist)
            if nd is None or pd.isna(d): continue
            if not stops or stops[-1][0] != nd: stops.append((nd, d))
        if len(stops) >= 2: out.append(stops)
    return out

t17 = pd.read_csv(ROOT / "external_data/timetable_2017_datagovin/Train_details_22122017.csv",
                  dtype=str)
t17["seq"] = pd.to_numeric(t17.SEQ, errors="coerce")
t17["km"] = pd.to_numeric(t17.Distance, errors="coerce")
t17["code"] = t17["Station Code"].str.strip()
T17 = trains_from(t17, "code", "Train No", "seq", "km")
r24 = pd.read_csv(ROOT / "external_data/iitkgp_rstgcn_network_2024/"
                  "Indian-Railway-Network-and-Delays/train_routes_Sep2024.csv", dtype=str)
r24["seq"] = r24.stnSerialNumber.astype(int)
r24["km"] = pd.to_numeric(r24.distance, errors="coerce")
r24["tno"] = r24.trainNumber.str.zfill(5)
T24 = trains_from(r24, "station_code", "tno", "seq", "km")

def measure(G, label):
    cache = {}
    def sp(a, b):
        k = (a, b) if a < b else (b, a)
        if k not in cache:
            try: cache[k] = nx.shortest_path_length(G, a, b, weight="km")
            except (nx.NetworkXNoPath, nx.NodeNotFound): cache[k] = None
        return cache[k]
    out = dict(label=label, edges=G.number_of_edges(),
               components=nx.number_connected_components(G),
               route_km=round(sum(d["km"] for *_, d in G.edges(data=True)), 1),
               edges_shorter_than_straight_line=sum(
                   1 for u, v, d in G.edges(data=True)
                   if (c := hav(pos.get(u), pos.get(v))) is not None and d["km"] < c - 0.3))
    diffs, within = [], 0
    for (a, b), km in ip.items():
        d = sp(a, b)
        if d is None: continue
        diffs.append(abs(d - km) / km)
        if abs(d - km) <= max(1.0, 0.05 * km): within += 1
    out["irn_within_5pct"] = round(within / len(diffs), 4)
    for tag, TT in (("2024", T24), ("2017", T17)):
        errs, failed = [], 0
        for stops in TT:
            km, ok = 0.0, True
            for (a, _), (b, _) in zip(stops, stops[1:]):
                d = sp(a, b)
                if d is None: ok = False; break
                km += d
            if not ok: failed += 1; continue
            t = stops[-1][1] - stops[0][1]
            if pd.notna(t) and t >= 20: errs.append((km - t) / t)
        e = pd.Series(errs)
        out[f"route_{tag}_err"] = round(e.abs().median(), 4)
        out[f"route_{tag}_unroutable"] = failed
    det, tot = 0, 0.0
    for stops in T24:
        s = [x for x, _ in stops]
        for p, m, n in zip(s, s[1:], s[2:]):
            if p == n: continue
            a, b, c = sp(p, m), sp(m, n), sp(p, n)
            if None in (a, b, c): continue
            if (d := a + b - c) >= 2.0: det += 1; tot += d
    out["off_spine_triples"] = det
    out["off_spine_detour_km"] = round(tot, 1)
    return out

runs = [measure(load_graph(ROOT, with_repairs=False)[0], "v1.3 raw"),
        measure(load_graph(ROOT, prune=False)[0], "+G5 +G6 (all added)"),
        measure(load_graph(ROOT, prune=True, audit_file=AUDIT)[0], "+G5 +G6 (pruned)")]
df = pd.DataFrame(runs)
df.to_csv(OUT / "verification_pruned.csv", index=False)
json.dump(runs, open(OUT / "verification_pruned.json", "w"), indent=2, default=str)
print(df.to_string(index=False))
