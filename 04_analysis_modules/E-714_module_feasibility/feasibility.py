"""E-714 - measured feasibility of the downstream modules, and the contribution against IRN."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
from scipy.stats import spearmanr

root = Path(sys.argv[1]); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
g = root / "03_graph_construction"
n = pd.read_csv(g / "graph_v1_4/open/nodes.csv"); e = pd.read_csv(g / "graph_v1_4/open/edges.csv")
cw = pd.read_csv(g / "graph_v1_4/station_code_crosswalk.csv")
es = pd.read_csv(g / "service_layer_v1_4/open/edge_service.csv")
irn = pd.read_csv(root / "external_data/iitkgp_rstgcn_network_2024/Indian-Railway-Network-and-Delays/IRN_edges.csv")
ids = set(n.node_id); alias = dict(zip(cw.loc[cw.resolution == "alias", "code"], cw.loc[cw.resolution == "alias", "graph_node"]))
res = lambda c: c if c in ids else alias.get(c)
R = {}

def graph(scale=None):
    G = nx.Graph(); G.add_nodes_from(n.node_id)
    for r in e.itertuples():
        km = r.length_km * (scale if (scale and r.length_is_lower_bound) else 1.0)
        G.add_edge(r.from_node, r.to_node, km=km, eid=r.edge_id)
    return G
G = graph()

# ---------------- T1: the timetable-built IRN against physical track
irn["a"] = irn["from"].map(res); irn["b"] = irn["to"].map(res)
both = irn.dropna(subset=["a", "b"]); both = both[both.a != both.b]
stations_irn = pd.unique(pd.concat([irn["from"], irn["to"]]))
rows = []
for r in both.itertuples():
    if G.has_edge(r.a, r.b):
        rows.append(dict(direct=True, hops=1, skipped=0, ratio=G[r.a][r.b]["km"] / r.distance if r.distance else np.nan)); continue
    try:
        p = nx.shortest_path(G, r.a, r.b, weight="km")
        km = nx.path_weight(G, p, "km")
        rows.append(dict(direct=False, hops=len(p) - 1, skipped=len(p) - 2, ratio=km / r.distance if r.distance else np.nan))
    except nx.NetworkXNoPath:
        rows.append(dict(direct=False, hops=None, skipped=None, ratio=np.nan))
t = pd.DataFrame(rows)
R["irn"] = dict(irn_stations=int(len(stations_irn)), irn_edges=int(len(irn)),
    irn_stations_in_graph=int(sum(1 for c in stations_irn if res(c))),
    edges_both_ends_in_graph=int(len(both)),
    single_physical_section=round(float(t.direct.mean()), 4),
    skip_one_or_more_stations=round(float((t.skipped.fillna(-1) >= 1).mean()), 4),
    skip_three_or_more=round(float((t.skipped.fillna(-1) >= 3).mean()), 4),
    median_stations_skipped_when_skipping=float(t.loc[t.skipped >= 1, "skipped"].median()),
    max_skipped=int(t.skipped.max()),
    no_physical_path=int(t.hops.isna().sum()),
    graph_nodes_not_in_irn=int(len(ids - {res(c) for c in stations_irn if res(c)})),
    path_km_within_5pct_of_irn_distance=round(float(((t.ratio - 1).abs() <= 0.05).mean()), 4))

# ---------------- T2: sensitivity to the 25% of km that is a straight-line floor
o = e[e.length_is_lower_bound.astype(bool) & e.official_km.notna()]
f = float((o.official_km / o.length_km).median())
R["floor_factor"] = dict(floor_edges_with_official=int(len(o)), median_official_over_floor=round(f, 3),
                         p75=round(float((o.official_km / o.length_km).quantile(.75)), 3))
Ga = graph(scale=f)
rng = np.random.default_rng(20261019)
H = G.subgraph(max(nx.connected_components(G), key=len)).copy(); Ha = Ga.subgraph(H.nodes).copy()
sample = list(rng.choice(sorted(H.nodes), 400, replace=False))

# M2: stations reachable within 100 km of network distance
def reach(Gx, km=100):
    return [len(nx.single_source_dijkstra_path_length(Gx, s, cutoff=km, weight="km")) for s in sample]
r0, r1 = reach(H), reach(Ha)
rel = (np.array(r1) - np.array(r0)) / np.maximum(np.array(r0), 1)
R["m2_reach_100km"] = dict(spearman=round(spearmanr(r0, r1).statistic, 4), median_rel_change=round(float(np.median(rel)), 4),
                          share_changed_over_10pct=round(float((np.abs(rel) > .10).mean()), 4))
# M2 topological: stations within 10 hops (km-free)
def hops(Gx, k=10): return [len(nx.single_source_shortest_path_length(Gx, s, cutoff=k)) for s in sample]
R["m2_reach_10hops"] = dict(note="topological; identical under any length change by construction", sample=len(sample))

# M3: detour km if each of the 100 busiest sections is lost
tpd = dict(zip(es.edge_id, es.trains_per_day))
top = e.assign(t=e.edge_id.map(tpd).fillna(0)).nlargest(100, "t")
def detours(Gx):
    out = []
    for r in top.itertuples():
        if not Gx.has_edge(r.from_node, r.to_node): out.append(np.nan); continue
        d = dict(Gx[r.from_node][r.to_node]); Gx.remove_edge(r.from_node, r.to_node)
        try: out.append(nx.dijkstra_path_length(Gx, r.from_node, r.to_node, weight="km") - d["km"])
        except nx.NetworkXNoPath: out.append(np.nan)
        Gx.add_edge(r.from_node, r.to_node, **d)
    return np.array(out)
d0, d1 = detours(H.copy()), detours(Ha.copy())
m = ~np.isnan(d0) & ~np.isnan(d1)
R["m3_detour_top100"] = dict(spearman=round(spearmanr(d0[m], d1[m]).statistic, 4),
    median_rel_change=round(float(np.median((d1[m] - d0[m]) / np.maximum(d0[m], .1))), 4),
    severing_unchanged=bool((np.isnan(d0) == np.isnan(d1)).all()))

# M1: km-weighted betweenness ranking - treatment vs sampling noise floor
def btw(Gx, seed): return nx.betweenness_centrality(Gx, k=300, weight="km", seed=seed)
b1, b2, b3 = btw(H, 1), btw(H, 2), btw(Ha, 1)
top50 = lambda b: set(sorted(b, key=b.get, reverse=True)[:50])
R["m1_betweenness_top50"] = dict(noise_floor_overlap=len(top50(b1) & top50(b2)),
                                 floor_change_overlap=len(top50(b1) & top50(b3)),
                                 repair_overlap_E707=35)
# M1/M3: articulation points and bridges are length-free
R["m1_cut_structure"] = dict(note="cut points, bridges, components: length-free, identical under any length change; nested under repair (D-055)")

# M3: random vs targeted failure, giant-component decay (topological)
def decay(order, Gx, steps=(0.01, 0.02, 0.05)):
    res_ = {}; N = Gx.number_of_nodes()
    for s in steps:
        Hx = Gx.copy(); Hx.remove_nodes_from(order[: int(s * N)])
        res_[f"{int(s*100)}pct"] = round(len(max(nx.connected_components(Hx), key=len)) / N, 4)
    return res_
deg_order = sorted(H.nodes, key=lambda x: H.degree(x), reverse=True)
rand_order = list(rng.permutation(sorted(H.nodes)))
btw_order = sorted(b1, key=b1.get, reverse=True)
R["m3_failure_decay_giant_share"] = dict(random=decay(rand_order, H), targeted_degree=decay(deg_order, H),
                                          targeted_betweenness=decay(btw_order, H))
(out / "E-714_feasibility.json").write_text(json.dumps(R, indent=1, default=str))
print(json.dumps(R, indent=1, default=str))
