"""E-724: score O3m builds (out/on, out/on_r1) against the flag-off build (out/off = v2.0-open)
on D-073's predictions and gates.  python eval_o3m.py"""
import csv, json, pathlib, collections
import networkx as nx
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OFFICIAL_KM = 69439
FLAGS = [f for f in ("off", "on", "on_r1") if (HERE / "out" / f / "open" / "edges.csv").exists()]

def graph(flag, places=False):
    d = HERE / "out" / flag / "open" / ("places" if places else "")
    n = pd.read_csv(d / "nodes.csv", dtype=str); e = pd.read_csv(d / "edges.csv")
    u, v = ("from_node", "to_node") if "from_node" in e else ("from_place", "to_place")
    G = nx.Graph(); G.add_nodes_from(n[n.columns[0]])
    for a, b, km in zip(e[u], e[v], e.length_km): G.add_edge(a, b, km=float(km))
    return n, e, G

def short_cycles(G, lim=0.5):
    """Distinct cycles shorter than lim km (each must contain an edge shorter than lim)."""
    G = G.copy(); out = {}
    for u, v, d in list(G.edges(data=True)):
        if d["km"] >= lim: continue
        G.remove_edge(u, v)
        try:
            L, p = nx.single_source_dijkstra(G, u, v, cutoff=lim - d["km"], weight="km")
            out[frozenset(p)] = round(L + d["km"], 3)
        except nx.NetworkXNoPath: pass
        G.add_edge(u, v, **d)
    return out

def sp(G, a, b):
    try: return round(nx.shortest_path_length(G, a, b, weight="km"), 4)
    except (nx.NetworkXNoPath, nx.NodeNotFound): return None

PAIRS = [("CSMT", "MSD"), ("CSMT", "SNRD"), ("CSMT", "BY"), ("CSMT", "DR"), ("CSMT", "KYN"), ("MAS", "BBQ"),
         ("HWH", "TPKR"), ("JND", "TORA"), ("MJ", "MRWS"), ("SPN", "SZN"), ("NDLS", "CSMT"), ("NDLS", "HWH"), ("NDLS", "MAS")]
WATCH = ["CSMT", "MSD", "HWH", "MAS", "MMCT", "SDAH", "CCG", "MDP", "CRP", "KGP", "SZM", "BHS", "TMR", "RPM", "RJT", "JND", "MJ", "SPN"]
SPOT = ["NDLS", "CSMT", "HWH", "SBC", "SC", "BZA", "PUNE", "JP", "LKO", "BPL", "NGP", "ADI", "PNBE", "GHY", "TVC", "ERS",
        "KYQ", "JAT", "ASR", "CDG", "BBS", "RNC", "R", "DDN", "MAO", "VSKP", "CAPE", "SHM", "DBRG", "NJP", "SML", "MAS"]
d1 = list(csv.DictReader(open(ROOT / "03_graph_construction/experiments/E-722_v2_scope_scan/out/degree1_stations.csv")))
THROUGH = [r["station"] for r in d1 if r["class"] == "through_station_as_leaf"]

rep, cyc = {}, {}
for f in FLAGS:
    n, e, G = graph(f); pn, pe, PG = graph(f, places=True)
    st = set(n.node_id[n.node_type == "station"])
    comps = nx.number_connected_components(G)
    errs = []
    for i, a in enumerate(SPOT):
        for b in SPOT[i + 1:i + 6]:
            x, y = sp(G, a, b), sp(PG, a, b)
            if x and y: errs.append(abs(y - x) / x)
    cyc[f] = short_cycles(G)
    rep[f] = dict(
        nodes=len(n), junctions=int((n.node_type == "junction").sum()), edges=len(e),
        route_km=round(float(e.length_km.sum()), 1), vs_official=round(float(e.length_km.sum()) / OFFICIAL_KM - 1, 4),
        components=comps, cycles=G.number_of_edges() - G.number_of_nodes() + comps,
        bridges=sum(1 for _ in nx.bridges(G)), cut_points=sum(1 for _ in nx.articulation_points(G)),
        degree1_stations=sum(1 for x in st if G.degree(x) == 1), max_degree=max(d for _, d in G.degree()),
        stations_in_giant=round(len(max(nx.connected_components(G), key=len) & st) / len(st), 4),
        places_max_error=round(max(errs), 4), places_pairs=len(errs),
        short_cycles_lt_0_5km=len(cyc[f]),
        paths_km={f"{a}-{b}": sp(G, a, b) for a, b in PAIRS},
        degree={s: G.degree(s) if s in G else None for s in WATCH},
        through_stations_fixed=f"{sum(1 for s in THROUGH if G.degree(s) >= 2)}/{len(THROUGH)}",
        through_stations_still_leaf=[s for s in THROUGH if G.degree(s) < 2])
for f in FLAGS[1:]:
    new = {k: v for k, v in cyc[f].items() if k not in cyc["off"]}
    n = pd.read_csv(HERE / "out" / f / "open" / "nodes.csv", dtype=str)
    st = set(n.node_id[n.node_type == "station"])
    rep[f]["new_short_cycles"] = dict(n=len(new), touching_station=sum(1 for k in new if k & st), km=round(sum(new.values()), 2),
                                      list=sorted([sorted(k), v] for k, v in new.items()))
json.dump(rep, open(HERE / "out" / "eval_o3m.json", "w"), indent=1)
keys = ["nodes", "junctions", "edges", "route_km", "vs_official", "components", "cycles", "bridges", "cut_points",
        "degree1_stations", "max_degree", "stations_in_giant", "places_max_error", "short_cycles_lt_0_5km", "through_stations_fixed"]
print(pd.DataFrame({f: {k: rep[f][k] for k in keys} for f in FLAGS}).to_string())
print(pd.DataFrame({f: rep[f]["paths_km"] for f in FLAGS}).to_string())
print(pd.DataFrame({f: rep[f]["degree"] for f in FLAGS}).T.to_string())
for f in FLAGS[1:]: print(f, "new short cycles:", {k: v for k, v in rep[f]["new_short_cycles"].items() if k != "list"}, "| still leaf:", rep[f]["through_stations_still_leaf"])
