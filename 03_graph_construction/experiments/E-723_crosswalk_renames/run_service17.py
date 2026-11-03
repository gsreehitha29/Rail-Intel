"""E-723: the 2017 service layer under the v2.0 crosswalk and under v2.0 + aliases_v2_1.csv.

Read-only on the release. Mirrors E-716 service17.py (v14._resolver, v14._timetables walk,
Dijkstra with cutoff 400 km) but reads only the 2017 timetable and writes only to ./out.
"""
import csv, json, pathlib
from collections import defaultdict
import networkx as nx
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REL = ROOT / "03_graph_construction/release/rail-intel-v2.0-open"
OUT = HERE / "out"

nodes = pd.read_csv(REL / "graph/nodes.csv"); edges = pd.read_csv(REL / "graph/edges.csv")
G = nx.Graph()
for r in edges.itertuples(): G.add_edge(r.from_node, r.to_node, km=float(r.length_km), eid=r.edge_id)
G.add_nodes_from(nodes.node_id)
ids = set(nodes.node_id)
cw0 = pd.read_csv(REL / "graph/station_code_crosswalk.csv")
add = pd.read_csv(HERE / "aliases_v2_1.csv")
assert not set(add.code) & (set(cw0.code) | ids), "an added code already resolves"
assert set(add.graph_node) <= ids, "alias target missing from graph"

t17 = pd.read_csv(ROOT / "external_data/timetable_2017_datagovin/Train_details_22122017.csv", dtype=str)
t17["seq"] = pd.to_numeric(t17.SEQ, errors="coerce"); t17["km"] = pd.to_numeric(t17.Distance, errors="coerce")
t17["code"] = t17["Station Code"].str.strip()
t17 = t17.sort_values(["Train No", "seq"])

def run(cw):
    alias = dict(zip(cw.loc[cw.resolution == "alias", "code"], cw.loc[cw.resolution == "alias", "graph_node"]))
    node = lambda c: c if c in ids else alias.get(c)
    trains = []
    for t, g in t17.groupby("Train No", sort=False):
        stops = []
        for c, v in zip(g.code, g.km):
            nd = node(c)
            if nd is None or pd.isna(v): continue
            if not stops or stops[-1][0] != nd: stops.append((nd, v))
        if len(stops) >= 2: trains.append((t, stops))
    pairs = defaultdict(set); tkm = {}
    for t, stops in trains:
        for (a, ka), (b, kb) in zip(stops, stops[1:]):
            pairs[(a, b)].add(t); tkm.setdefault((a, b), abs(kb - ka))
    cache, rows, cnt = {}, {}, defaultdict(set)
    for (a, b) in pairs:
        k = (a, b) if a < b else (b, a)
        if k not in cache:
            try: cache[k] = nx.single_source_dijkstra(G, k[0], k[1], weight="km", cutoff=400)
            except (nx.NetworkXNoPath, nx.NodeNotFound): cache[k] = (None, None)
        km, path = cache[k]
        rows[(a, b)] = dict(n=len(pairs[(a, b)]), km=km, tt_km=tkm[(a, b)])
        if path:
            for u, v in zip(path, path[1:]): cnt[G[u][v]["eid"]] |= pairs[(a, b)]
    unroutable_trains = {t for (a, b), r in rows.items() if r["km"] is None for t in pairs[(a, b)]}
    return dict(trains=len(trains), rows=rows, edge=cnt, unroutable_trains=unroutable_trains,
                served={x for p in pairs for x in p})

base = run(cw0)
cand = run(pd.concat([cw0, add], ignore_index=True))

# baseline must reproduce the release
rel = {(r["from_station"], r["to_station"]): r for r in csv.DictReader(open(REL / "service_2017/station_pairs.csv"))}
rel_e = dict(zip(edges.edge_id, edges.trains_2017))
repro = dict(
    pairs_equal=set(rel) == set(base["rows"]),
    n_trains_equal=all(int(rel[k]["n_trains_2017"]) == v["n"] for k, v in base["rows"].items() if k in rel),
    edge_trains_equal=all(int(rel_e[e]) == len(base["edge"].get(e, ())) for e in edges.edge_id),
)

def err(r):  # graph path against the timetable's own distance
    return abs(r["km"] - r["tt_km"]) / r["tt_km"] if r["km"] is not None and r["tt_km"] and r["tt_km"] > 0 else None
new_pairs = {k: v for k, v in cand["rows"].items() if k not in base["rows"]}
errs = sorted(e for e in map(err, new_pairs.values()) if e is not None)

watch = ["MMCT", "DDU", "PRYJ", "RKMP", "AYC", "MBDP", "BSBS", "SHRN", "PRRB", "SBDR"]
st_trains = lambda R, s: len({t for (a, b), r in R["rows"].items() if s in (a, b) for t in [None]} and
                             set().union(*[set() for _ in [0]]))
def trains_at(R, s):
    return max([len(R["edge"].get(e, ())) for e in edges.loc[(edges.from_node == s) | (edges.to_node == s), "edge_id"]] or [0])
report = dict(
    reproduces_release=repro,
    aliases_added=len(add), rejected=len(pd.read_csv(HERE / "rejected.csv")),
    trains_routed=dict(base=base["trains"], candidate=cand["trains"]),
    station_pairs=dict(base=len(base["rows"]), candidate=len(cand["rows"]), new=len(new_pairs)),
    unroutable_pairs=dict(base=sum(r["km"] is None for r in base["rows"].values()),
                          candidate=sum(r["km"] is None for r in cand["rows"].values())),
    unroutable_trains=dict(base=len(base["unroutable_trains"]), candidate=len(cand["unroutable_trains"])),
    served_stations=dict(base=len(base["served"]), candidate=len(cand["served"])),
    edges_with_service=dict(base=sum(1 for e in edges.edge_id if base["edge"].get(e)),
                            candidate=sum(1 for e in edges.edge_id if cand["edge"].get(e))),
    edges_trains_changed=sum(1 for e in edges.edge_id if len(base["edge"].get(e, ())) != len(cand["edge"].get(e, ()))),
    edges_trains_decreased=sum(1 for e in edges.edge_id if len(cand["edge"].get(e, ())) < len(base["edge"].get(e, ()))),
    new_pairs_route_error=dict(n=len(errs), median=round(errs[len(errs)//2], 4) if errs else None,
                               within_5pct=round(sum(e <= 0.05 for e in errs) / len(errs), 3) if errs else None),
    station_max_edge_trains={s: dict(base=trains_at(base, s), candidate=trains_at(cand, s)) for s in watch},
)
report["new_pairs_route_error"]["within_2km_or_5pct"] = round(sum(1 for (a, b), r in new_pairs.items() if r["km"] is not None and r["tt_km"] and (abs(r["km"] - r["tt_km"]) <= 2 or err(r) <= 0.05)) / max(1, len(errs)), 3)
json.dump(report, open(OUT / "e723_report.json", "w"), indent=1)
with open(OUT / "new_station_pairs.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["from_station", "to_station", "n_trains_2017", "path_km", "timetable_km", "abs_error"])
    for (a, b), r in sorted(new_pairs.items()):
        e = err(r); w.writerow([a, b, r["n"], round(r["km"], 4) if r["km"] is not None else "", r["tt_km"], round(e, 4) if e is not None else ""])
print(json.dumps(report, indent=1))
