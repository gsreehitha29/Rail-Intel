"""G6 verification - measure v1.3 raw, +G5, +G5+G6 on the same five measures.

Same instruments as G5, so the three rows are directly comparable:
  independent  agreement with the IIT KGP IRN edge distances (fed no length here)
  route error  graph route km against the timetables' own cumulative km, both years
  structure    off-spine stations, connectivity, and the physical invariant that no
               edge may be shorter than the straight line between its ends

Run:  python verify.py <Rail-Intell root> <G5 dir> <G6 dir> <output dir>
"""
import json, math, sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT, G5DIR, G6DIR, OUT = (Path(sys.argv[1]), Path(sys.argv[2]),
                           Path(sys.argv[3]), Path(sys.argv[4]))
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "04_analysis_modules/E-702_station_code_crosswalk"))
from resolve import load_resolver                                    # noqa: E402

nodes = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/nodes.csv")
edges = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/edges.csv")
g5 = pd.read_csv(G5DIR / "repairs_proposed.csv")
g6 = pd.read_csv(G6DIR / "links_added.csv")
res = load_resolver(ROOT)
pos = {r.node_id: (r.longitude, r.latitude) for r in nodes.itertuples()}

def hav(pa, pb):
    if pa is None or pb is None: return None
    (lo1, la1), (lo2, la2) = pa, pb
    p = math.pi / 180
    h = (math.sin((la2 - la1) * p / 2) ** 2 + math.cos(la1 * p) * math.cos(la2 * p) *
         math.sin((lo2 - lo1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(min(1, h)))

def build(g5on, g6on):
    G = nx.Graph()
    for r in edges.itertuples():
        if G.has_edge(r.from_node, r.to_node) and G[r.from_node][r.to_node]["km"] <= r.length_km:
            continue
        G.add_edge(r.from_node, r.to_node, km=float(r.length_km))
    if g5on:
        for r in g5.itertuples():
            if r.action == "remove_edge" and G.has_edge(r.a, r.b): G.remove_edge(r.a, r.b)
            elif r.action == "add_edge" and not G.has_edge(r.a, r.b):
                G.add_edge(r.a, r.b, km=float(r.new))
    if g6on:
        for r in g6.itertuples():
            if not G.has_edge(r.a, r.b): G.add_edge(r.a, r.b, km=float(r.length_km))
    return G

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
    out["irn_median_abs_err"] = round(float(np.median(diffs)), 4)
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
        out[f"route_{tag}_within_5pct"] = round((e.abs() <= .05).mean(), 4)
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

runs = [measure(build(False, False), "v1.3 raw"),
        measure(build(True, False), "+G5"),
        measure(build(True, True), "+G5 +G6")]
df = pd.DataFrame(runs)
df.to_csv(OUT / "verification.csv", index=False)
json.dump(runs, open(OUT / "verification.json", "w"), indent=2, default=str)
print(df[["label", "edges", "components", "irn_within_5pct", "irn_median_abs_err",
          "route_2024_err", "route_2017_err", "off_spine_triples", "off_spine_detour_km",
          "edges_shorter_than_straight_line", "route_2024_unroutable"]].to_string(index=False))
