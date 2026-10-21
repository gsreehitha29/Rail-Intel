"""G5 verification - apply the repairs and measure, class by class.

Three measures, because one alone would not be honest:

  independent  agreement with the IIT KGP IRN edge distances, the reference this
               project already uses for exactly this purpose (E-600). It never fed
               any length in the graph, so a `set_length` repair cannot flatter it.
  route error  graph route km against the timetable's own cumulative km. Partly
               circular for `set_length` (those lengths come from the timetables)
               and reported as such; it is a fair test of the topology repairs,
               which change which track a train runs over, not how long it is.
  structure    off-spine stations - stations trains stop at that the graph routes
               around - plus connectivity and the physical invariant that no edge
               may be shorter than the straight line between its ends.

Each class is applied on its own and then together, so a class that makes things
worse can be dropped rather than carried along by the others.

Run:  python verify.py <Rail-Intell root> <repairs dir> <output dir>
"""
import json, math, sys
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT, REP, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "04_analysis_modules/E-702_station_code_crosswalk"))
from resolve import load_resolver                                    # noqa: E402

nodes = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/nodes.csv")
edges = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/edges.csv")
rp = pd.read_csv(REP / "repairs_proposed.csv")
res = load_resolver(ROOT)
nm = dict(zip(nodes.node_id, nodes.node_name))
pos = {r.node_id: (r.longitude, r.latitude) for r in nodes.itertuples()}

def hav(pa, pb):
    if pa is None or pb is None: return None
    (lo1, la1), (lo2, la2) = pa, pb
    p = math.pi / 180
    h = (math.sin((la2 - la1) * p / 2) ** 2 + math.cos(la1 * p) * math.cos(la2 * p) *
         math.sin((lo2 - lo1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(min(1, h)))

SETS = {
    "remove_edge":     lambda r: r.action == "remove_edge",
    "add_edge":        lambda r: r.action == "add_edge",
    "move_node":       lambda r: r.action == "move_node",
    "set_len_all":     lambda r: r.action == "set_length",
    "set_len_raise_lb": lambda r: r.action == "set_length" and r.raises_lower_bound is True,
    "set_len_safe":    lambda r: r.action == "set_length" and r.invariant_safe is True,
}

def build(apply=()):
    """Graph plus coordinates, with the named repair sets applied."""
    G = nx.Graph()
    for r in edges.itertuples():
        if G.has_edge(r.from_node, r.to_node) and G[r.from_node][r.to_node]["km"] <= r.length_km:
            continue
        G.add_edge(r.from_node, r.to_node, km=float(r.length_km), eid=r.edge_id)
    P = dict(pos)
    preds = [SETS[a] for a in apply]
    for r in rp.itertuples():
        if not any(p(r) for p in preds): continue
        if r.action == "remove_edge":
            if G.has_edge(r.a, r.b): G.remove_edge(r.a, r.b)
        elif r.action == "set_length":
            if G.has_edge(r.a, r.b): G[r.a][r.b]["km"] = float(r.new)
        elif r.action == "add_edge":
            if not G.has_edge(r.a, r.b):
                G.add_edge(r.a, r.b, km=float(r.new), eid=f"G5:{r.a}|{r.b}")
        elif r.action == "move_node":
            lon, lat = str(r.new).split(",")
            P[r.item] = (float(lon), float(lat))
    return G, P

# ---------------------------------------------------------------- references
irn = pd.read_csv(ROOT / "external_data/iitkgp_rstgcn_network_2024/"
                  "Indian-Railway-Network-and-Delays/IRN_edges.csv")
irn["a"] = irn["from"].map(res.node); irn["b"] = irn["to"].map(res.node)
irn = irn.dropna(subset=["a", "b"])
irn = irn[irn.a != irn.b]
irn_pairs = {}
for r in irn.itertuples():
    k = (r.a, r.b) if r.a < r.b else (r.b, r.a)
    irn_pairs.setdefault(k, []).append(float(r.distance))
irn_pairs = {k: float(np.median(v)) for k, v in irn_pairs.items() if np.median(v) > 0}

def trains_from(df, code, train, seq, dist):
    df = df.sort_values([train, seq])
    out = []
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

# ---------------------------------------------------------------- measures
def measure(GP, label):
    G, P = GP
    cache = {}
    def sp(a, b):
        k = (a, b) if a < b else (b, a)
        if k not in cache:
            try: cache[k] = nx.shortest_path_length(G, a, b, weight="km")
            except (nx.NetworkXNoPath, nx.NodeNotFound): cache[k] = None
        return cache[k]

    out = dict(label=label, nodes=G.number_of_nodes(), edges=G.number_of_edges(),
               components=nx.number_connected_components(G),
               route_km=round(sum(d["km"] for *_, d in G.edges(data=True)), 1))

    # physical invariant
    bad = sum(1 for u, v, d in G.edges(data=True)
              if (c := hav(P.get(u), P.get(v))) is not None and d["km"] < c - 0.3)
    out["edges_shorter_than_straight_line"] = bad

    # independent reference
    diffs, within = [], 0
    for (a, b), km in irn_pairs.items():
        d = sp(a, b)
        if d is None: continue
        diffs.append(abs(d - km) / km)
        if abs(d - km) <= max(1.0, 0.05 * km): within += 1
    out["irn_pairs_compared"] = len(diffs)
    out["irn_agreement_within_5pct"] = round(within / len(diffs), 4) if diffs else None
    out["irn_median_abs_error"] = round(float(np.median(diffs)), 4) if diffs else None

    # route error
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
        out[f"route_{tag}_median_abs_err"] = round(e.abs().median(), 4)
        out[f"route_{tag}_within_5pct"] = round((e.abs() <= .05).mean(), 4)
        out[f"route_{tag}_unroutable"] = failed

    # structure: stations trains stop at but the graph routes around
    det, tot = 0, 0.0
    for stops in T24:
        s = [x for x, _ in stops]
        for p, m, n in zip(s, s[1:], s[2:]):
            if p == n: continue
            a, b, c = sp(p, m), sp(m, n), sp(p, n)
            if None in (a, b, c): continue
            d = a + b - c
            if d >= 2.0: det += 1; tot += d
    out["off_spine_triples"] = det
    out["off_spine_detour_km"] = round(tot, 1)
    return out

PLAN = [
    ("baseline", ()),
    ("remove_edge", ("remove_edge",)),
    ("add_edge + move_node", ("add_edge", "move_node")),
    ("set_length: raise lower bounds only", ("set_len_raise_lb", "move_node")),
    ("set_length: invariant-safe only", ("set_len_safe", "move_node")),
    ("set_length: all", ("set_len_all", "move_node")),
    ("topology only (remove + add + move)", ("remove_edge", "add_edge", "move_node")),
    ("topology + raise lower bounds", ("remove_edge", "add_edge", "move_node",
                                       "set_len_raise_lb")),
    ("everything", ("remove_edge", "add_edge", "move_node", "set_len_all")),
    ("ACCEPTED: remove + add", ("remove_edge", "add_edge")),
]
runs = [measure(build(sets), label) for label, sets in PLAN]

df = pd.DataFrame(runs)
df.to_csv(OUT / "verification_by_class.csv", index=False)
base, full = runs[0], runs[-1]
verdict = []
for r in runs[1:]:
    better_ind = (r["irn_agreement_within_5pct"] or 0) >= (base["irn_agreement_within_5pct"] or 0)
    better_str = r["off_spine_detour_km"] <= base["off_spine_detour_km"]
    safe = (r["edges_shorter_than_straight_line"] <= base["edges_shorter_than_straight_line"]
            and r["components"] <= base["components"]
            and r["route_2024_unroutable"] <= base["route_2024_unroutable"])
    verdict.append(dict(run=r["label"], independent_ok=better_ind, structure_ok=better_str,
                        safe=safe,
                        irn_within_5pct=r["irn_agreement_within_5pct"],
                        route_2024=r["route_2024_median_abs_err"],
                        off_spine_detour_km=r["off_spine_detour_km"],
                        components=r["components"]))
out = dict(experiment="E-703 verification",
           repairs={k: int(v) for k, v in rp.action.value_counts().items()},
           baseline=base, runs=runs, verdict=verdict)
json.dump(out, open(OUT / "verification.json", "w"), indent=2, default=str)
print(df[["label", "edges", "components", "irn_agreement_within_5pct", "irn_median_abs_error",
          "route_2024_median_abs_err", "route_2017_median_abs_err", "off_spine_triples",
          "off_spine_detour_km", "edges_shorter_than_straight_line",
          "route_2024_unroutable"]].to_string(index=False))
