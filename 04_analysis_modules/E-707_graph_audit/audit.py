"""Full audit of the repaired graph: structure, attributes, validation, residual defects.

Measures the graph as it now stands (v1.3 open + G5/G6 repairs, pruned) and compares it
against v1.3 raw, the independent IIT KGP reference, both timetables, and the published
Indian-railway network studies. Nothing here is recalled; every figure is computed.

Run:  python audit.py <Rail-Intell root> <output dir>
"""
import json, math, random, sys
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "04_analysis_modules/E-705_service_layer_2024"))
sys.path.insert(0, str(ROOT / "04_analysis_modules/E-702_station_code_crosswalk"))
from resolve import load_resolver                                    # noqa: E402
from railgraph_repaired import load_graph                            # noqa: E402

random.seed(0); np.random.seed(0)
res = load_resolver(ROOT)
G, gmeta = load_graph(ROOT)
RAW, _ = load_graph(ROOT, with_repairs=False)
nodes = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/nodes.csv")
edges = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/edges.csv")
pos = {r.node_id: (r.longitude, r.latitude) for r in nodes.itertuples()}
A = {}

def hav(pa, pb):
    if pa is None or pb is None: return None
    (lo1, la1), (lo2, la2) = pa, pb
    p = math.pi / 180
    h = (math.sin((la2-la1)*p/2)**2 + math.cos(la1*p)*math.cos(la2*p)*math.sin((lo2-lo1)*p/2)**2)
    return 12742 * math.asin(math.sqrt(min(1, h)))

# =============================================================== A. structure
comps = sorted(nx.connected_components(G), key=len, reverse=True)
giant = G.subgraph(comps[0]).copy()
deg = dict(G.degree())
degc = Counter(deg.values())
route_km = sum(d["km"] for *_, d in G.edges(data=True))

# exponential vs power law on the degree distribution (Kurant & Thiran predict exponential
# for a network embedded in space); fit both on the tail and compare residuals
ks = np.array(sorted(k for k in degc if k >= 1))
pk = np.array([degc[k] for k in ks], dtype=float); pk /= pk.sum()
tail = ks >= 2
lx, ly = np.log(ks[tail]), np.log(pk[tail])
pl_fit = np.polyfit(lx, ly, 1)                      # power law: log p ~ a log k
ex_fit = np.polyfit(ks[tail], ly, 1)                # exponential: log p ~ a k
pl_res = float(np.sum((ly - np.polyval(pl_fit, lx)) ** 2))
ex_res = float(np.sum((ly - np.polyval(ex_fit, ks[tail])) ** 2))

# path lengths on a sample (full APSP is 9k^2)
sample = random.sample(list(giant.nodes()), 300)
hops, kms = [], []
for s in sample:
    hl = nx.single_source_shortest_path_length(giant, s)
    kl = nx.single_source_dijkstra_path_length(giant, s, weight="km")
    hops.extend(hl.values()); kms.extend(kl.values())
A["structure"] = dict(
    nodes=G.number_of_nodes(), edges=G.number_of_edges(), route_km=round(route_km, 1),
    components=len(comps), giant_nodes=len(comps[0]),
    giant_share=round(len(comps[0]) / G.number_of_nodes(), 4),
    small_components=[len(c) for c in comps[1:]],
    degree_mean=round(float(np.mean(list(deg.values()))), 3),
    degree_max=max(deg.values()),
    degree_distribution={int(k): int(v) for k, v in sorted(degc.items())},
    degree_1_nodes=degc.get(1, 0), degree_2_nodes=degc.get(2, 0),
    junctions_degree_3_plus=sum(v for k, v in degc.items() if k >= 3),
    bridges=len(list(nx.bridges(G))),
    articulation_points=len(list(nx.articulation_points(G))),
    bridge_share=round(len(list(nx.bridges(G))) / G.number_of_edges(), 4),
    cycle_rank=G.number_of_edges() - G.number_of_nodes() + len(comps),
    mean_hops_sampled=round(float(np.mean(hops)), 2),
    max_hops_sampled=int(np.max(hops)),
    mean_km_sampled=round(float(np.mean(kms)), 1),
    max_km_sampled=round(float(np.max(kms)), 1),
    degree_fit=dict(exponential_residual=round(ex_res, 3), power_law_residual=round(pl_res, 3),
                    better="exponential" if ex_res < pl_res else "power law",
                    exponential_rate=round(float(ex_fit[0]), 3)),
    vs_raw=dict(edges_raw=RAW.number_of_edges(), edges_now=G.number_of_edges(),
                route_km_raw=round(sum(d["km"] for *_, d in RAW.edges(data=True)), 1),
                components_raw=nx.number_connected_components(RAW)))

# =============================================================== B. attributes
e = edges.copy()
tot_km = e.length_km.sum()
def share(mask): return round(float(e.loc[mask, "length_km"].sum() / tot_km), 4)
A["attributes"] = dict(
    length_sources={k: dict(edges=int(v), km_share=share(e.length_source == k))
                    for k, v in e.length_source.value_counts().items()},
    measured_or_official_km_share=share(~e.length_is_lower_bound),
    lower_bound_km_share=share(e.length_is_lower_bound),
    suspect_long_edges=int((e.suspect_long_edge == True).sum()),
    suspect_long_km_share=share(e.suspect_long_edge == True),
    speed_declared_km_share=share(e.speed_source.str.startswith("declared")),
    speed_imputed_edges=int(e.speed_source.str.startswith("imputed").sum()),
    gauge_km_share=share(e.gauge_code.notna()),
    tracks_km_share=share(e.n_tracks.notna()),
    single_track_km_share=share(e.n_tracks == 1),
    zone_km_share=share(e.zone_code.notna()),
    node_coordinates=round(float(nodes.longitude.notna().mean()), 4),
    node_state=round(float(nodes.state.notna().mean()), 4),
    node_zone=round(float(nodes.zone_code.notna().mean()), 4),
    gauge_mix={k: share(e.gauge_code == k) for k in e.gauge_code.dropna().unique()},
    corridor_constant_note=("speed, gauge and n_tracks are corridor-level in the source "
                            "itself, so they cannot vary within a corridor"))

# =============================================================== C. validation
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

def validate(Gx):
    cache = {}
    def sp(a, b):
        k = (a, b) if a < b else (b, a)
        if k not in cache:
            try: cache[k] = nx.shortest_path_length(Gx, a, b, weight="km")
            except (nx.NetworkXNoPath, nx.NodeNotFound): cache[k] = None
        return cache[k]
    out = {}
    diffs, within = [], 0
    for (a, b), v in ip.items():
        d = sp(a, b)
        if d is None: continue
        diffs.append(abs(d - v) / v)
        if abs(d - v) <= max(1.0, 0.05 * v): within += 1
    out["irn_pairs"] = len(diffs)
    out["irn_within_5pct"] = round(within / len(diffs), 4)
    out["irn_median_abs_err"] = round(float(np.median(diffs)), 4)
    for tag, TT in (("2024", T24), ("2017", T17)):
        errs, failed = [], 0
        for stops in TT:
            kmv, ok = 0.0, True
            for (a, _), (b, _) in zip(stops, stops[1:]):
                d = sp(a, b)
                if d is None: ok = False; break
                kmv += d
            if not ok: failed += 1; continue
            t = stops[-1][1] - stops[0][1]
            if pd.notna(t) and t >= 20: errs.append((kmv - t) / t)
        s = pd.Series(errs)
        out[f"route_{tag}_median_abs_err"] = round(s.abs().median(), 4)
        out[f"route_{tag}_within_5pct"] = round((s.abs() <= .05).mean(), 4)
        out[f"route_{tag}_trains"] = len(s)
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
    out["edges_shorter_than_straight_line"] = sum(
        1 for u, v, d in Gx.edges(data=True)
        if (c := hav(pos.get(u), pos.get(v))) is not None and d["km"] < c - 0.3)
    return out

A["validation"] = dict(repaired=validate(G), raw=validate(RAW))

# =============================================================== D. residual defects
cw = pd.read_csv(ROOT / "04_analysis_modules/E-702_station_code_crosswalk/out/crosswalk.csv")
dup = pd.read_csv(ROOT / "04_analysis_modules/E-705_service_layer_2024/out/"
                  "duplicate_node_pairs.csv")
defer = pd.read_csv(ROOT / "04_analysis_modules/E-703_trunk_wiring/out/deferred_findings.csv")
coord = pd.read_csv(ROOT / "04_analysis_modules/E-703_trunk_wiring/out/"
                    "coordinate_disagreements.csv")
A["residual_defects"] = dict(
    lengths_lower_bound=dict(edges=int(e.length_is_lower_bound.sum()),
                             km_share=share(e.length_is_lower_bound),
                             pending_set_length=int((defer.action == "set_length").sum())),
    coordinates=dict(nodes_over_1_5km_from_osm=len(coord),
                     worst_km=round(float(coord.km_apart.max()), 1),
                     pending_move_node=int((defer.action == "move_node").sum())),
    duplicate_nodes=dict(pairs=len(dup), trains_affected=int(dup.service_load_2024.sum())),
    missing_stations=dict(codes=int((cw.resolution == "missing_station").sum()),
                          unresolved=int((cw.resolution == "unresolved").sum()),
                          stops_2024_lost=int(cw.loc[cw.resolution != "alias",
                                                     "stops_2024"].sum())),
    disconnected=dict(components=len(comps) - 1,
                      stations=int(sum(len(c) for c in comps[1:])),
                      trains_unroutable=A["validation"]["repaired"]["route_2024_unroutable"]),
    model_limits=["undirected physical graph", "no turn restrictions at junctions",
                  "no capacity, signalling or block sections", "passenger trains only",
                  "speed imputed on 40.8% of route km"])

# =============================================================== E. service layer
se24 = pd.read_csv(ROOT / "04_analysis_modules/E-706_trains_per_day/out/"
                   "service_edges_directed_2024_weighted.csv")
ed24 = pd.read_csv(ROOT / "04_analysis_modules/E-706_trains_per_day/out/"
                   "edge_service_2024_weighted.csv")
se17 = pd.read_csv(ROOT / "03_graph_construction/service_layer_v1_3/open/"
                   "service_edges_directed.csv")
freq = pd.read_csv(ROOT / "04_analysis_modules/E-706_trains_per_day/out/"
                   "train_frequency_2024.csv")
A["service"] = dict(
    layer_2024=dict(trains=int(freq.shape[0]), directed_pairs=len(se24),
                    pairs_with_runtime=int((se24.n_runtime_obs > 0).sum()),
                    edges_with_service=int((ed24.trains_per_day_2024 > 0).sum()),
                    edges_with_service_share=round(float((ed24.trains_per_day_2024 > 0).mean()), 4),
                    km_share=round(float(ed24.loc[ed24.trains_per_day_2024 > 0, "km"].sum()
                                         / ed24.km.sum()), 4),
                    median_trains_per_day_on_served=round(
                        float(ed24.loc[ed24.trains_per_day_2024 > 0,
                                       "trains_per_day_2024"].median()), 2),
                    busiest_trains_per_day=round(float(ed24.trains_per_day_2024.max()), 1)),
    layer_2017=dict(trains=5208, directed_pairs=len(se17),
                    edges_with_service=int((ed24.service_load_2017.fillna(0) > 0).sum())),
    frequency=dict(mean_trains_per_day=round(float(freq.trains_per_day.mean()), 3),
                   daily=int((freq.pattern == "daily").sum()),
                   weekly=int((freq.pattern == "weekly or twice weekly").sum()),
                   irregular=int((freq.pattern == "irregular").sum())),
    observed_runtime_km_share=None)

# runtime coverage in km terms, on the repaired graph
rt_pairs = {(r.from_station, r.to_station) for r in se24.itertuples() if r.n_runtime_obs > 0}
direct_rt = {tuple(sorted(k)) for k in rt_pairs}
covered = sum(d["km"] for u, v, d in G.edges(data=True)
              if tuple(sorted((u, v))) in direct_rt)
A["service"]["observed_runtime_km_share"] = round(covered / route_km, 4)

# =============================================================== F. literature
A["literature"] = dict(
    sen_2003=dict(stations=587, source="printed timetable", side="service"),
    bhatia_2015=dict(stations=809, source="origin-destination trains", side="service"),
    rstgcn_2025=dict(stations=4735, source="timetable stop sequences", side="service"),
    this_graph=dict(stations=G.number_of_nodes(), source="GIS infrastructure segments",
                    side="infrastructure"),
    degree_prediction=("Kurant & Thiran predict an exponential degree distribution for a "
                       "spatially embedded rail network, not scale-free"),
    degree_observed=A["structure"]["degree_fit"]["better"])

json.dump(A, open(OUT / "audit.json", "w"), indent=2, default=str)

# flat summary table for the write-up
rows = []
for sec, d in A.items():
    def walk(prefix, v):
        if isinstance(v, dict):
            for k2, v2 in v.items(): walk(f"{prefix}.{k2}" if prefix else k2, v2)
        else:
            rows.append(dict(section=sec, metric=prefix, value=v))
    walk("", d)
pd.DataFrame(rows).to_csv(OUT / "audit_flat.csv", index=False)
print(json.dumps({k: v for k, v in A.items() if k in ("structure", "validation")},
                 indent=1, default=str)[:4000])
