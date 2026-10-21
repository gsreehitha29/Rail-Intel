"""E-701 - Downstream feasibility: what each dataset adds to graph v1.3, measured.

For every external dataset, measure how much of it joins to the graph and what
analysis it enables, with a pilot of the most promising new analysis
(does infrastructure explain where trains lose time? - Sept 2024 delays).

Run:  python feas.py <Rail-Intell root> <output dir>
"""
import json, sys
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
X = ROOT / "external_data/iitkgp_rstgcn_network_2024/Indian-Railway-Network-and-Delays"
rep = {}

nodes = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/nodes.csv")
edges = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/edges.csv")
full = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/full/edges.csv")
ids = set(nodes.node_id)
G = nx.Graph()
for r in edges.itertuples():
    if G.has_edge(r.from_node, r.to_node) and G[r.from_node][r.to_node]["km"] <= r.length_km:
        continue
    G.add_edge(r.from_node, r.to_node, km=float(r.length_km), eid=r.edge_id, tracks=r.n_tracks,
               load=int(r.service_load), gauge=r.gauge_code, lb=bool(r.length_is_lower_bound))
ek = lambda a, b: (a, b) if a < b else (b, a)

cache = {}
def sp(a, b, cutoff_factor=None):
    k = ek(a, b)
    if k not in cache:
        try:
            p = nx.bidirectional_dijkstra(G, a, b, weight="km")
            cache[k] = p
        except nx.NetworkXNoPath:
            cache[k] = (None, None)
    km, p = cache[k]
    if p is not None and p[0] != a:
        p = p[::-1]
    return km, p

# ------------------------------------------------------------ 2017 timetable (baseline)
tt = pd.read_csv(ROOT / "external_data/timetable_2017_datagovin/Train_details_22122017.csv", dtype=str)
tt["tno"] = tt["Train No"].str.strip().str.zfill(5)
t17 = set(tt.tno)

# ------------------------------------------------------------ A. running days
rd = json.load(open(ROOT / "external_data/running_days_prasenjit27/trains.json"))
days = {t["trainNumber"].zfill(5): sum(bool(v) for v in t["runningDays"].values()) for t in rd}
dser = pd.Series(days)
rep["running_days"] = dict(
    trains=len(days), daily=int((dser == 7).sum()), daily_share=round((dser == 7).mean(), 3),
    days_distribution={int(k): int(v) for k, v in dser.value_counts().sort_index().items()},
    match_2017_timetable=round(len(set(days) & t17) / len(days), 3),
    trains_per_week_vs_distinct_trains=round(dser.sum() / 7 / len(dser), 3),
    use="turns 'distinct trains' into trains per day: weight = days/7")

# ------------------------------------------------------------ B. 2024 routes on the graph
r24 = pd.read_csv(X / "train_routes_Sep2024.csv", dtype=str)
r24["seq"] = r24.stnSerialNumber.astype(int); r24["dist"] = pd.to_numeric(r24.distance, errors="coerce")
r24["tno"] = r24.trainNumber.str.zfill(5)
r24 = r24.sort_values(["tno", "seq"])
codes24 = set(r24.station_code)
seg_err, pair_edges, edge_tr24 = [], {}, defaultdict(set)
unroutable_pairs, routed_trains, skipped_stops = 0, 0, 0
for tno, g in r24.groupby("tno", sort=False):
    st = [(c, d) for c, d in zip(g.station_code, g.dist) if c in ids]
    skipped_stops += len(g) - len(st)
    if len(st) < 2: continue
    ok, km_sum, used = True, 0.0, set()
    for (a, da), (b, db) in zip(st, st[1:]):
        if a == b: continue
        km, p = sp(a, b)
        if p is None: ok = False; unroutable_pairs += 1; break
        km_sum += km
        used.update(ek(u, v) for u, v in zip(p, p[1:]))
        pair_edges[(a, b)] = p
    if not ok: continue
    routed_trains += 1
    for k in used: edge_tr24[k].add(tno)
    tkm = st[-1][1] - st[0][1]
    if tkm and tkm >= 20: seg_err.append((km_sum - tkm) / tkm)
se = pd.Series(seg_err)
load24 = pd.Series({G[a][b]["eid"]: len(edge_tr24.get(ek(a, b), ())) for a, b in G.edges()})
load17 = pd.Series({G[a][b]["eid"]: G[a][b]["load"] for a, b in G.edges()})
rep["routes_2024"] = dict(
    trains=int(r24.tno.nunique()), stations=len(codes24),
    station_codes_in_graph=round(len(codes24 & ids) / len(codes24), 3),
    stop_rows_skipped_not_in_graph=int(skipped_stops), stop_rows=int(len(r24)),
    trains_routed=routed_trains, routed_share=round(routed_trains / r24.tno.nunique(), 3),
    median_abs_route_err=round(se.abs().median(), 4), within_5pct=round((se.abs() <= .05).mean(), 3),
    trains_also_in_2017=round(len(set(r24.tno) & t17) / r24.tno.nunique(), 3),
    edges_used_2024=int((load24 > 0).sum()), edges_used_2017_service_load=int((load17 > 0).sum()),
    edges_used_2024_not_2017=int(((load24 > 0) & (load17 == 0)).sum()),
    km_used_2024_not_2017=round(sum(G[a][b]["km"] for a, b in G.edges()
                                    if load24[G[a][b]["eid"]] > 0 and load17[G[a][b]["eid"]] == 0), 1),
    spearman_load_2024_vs_2017=round(pd.concat([load24, load17], axis=1).corr("spearman").iloc[0, 1], 3))

# ------------------------------------------------------------ C. delays, Sept 2024
d = pd.read_csv(X / "train_routes_delays_Sep2024.csv", dtype={"train": str})
d["tno"] = d.train.str.zfill(5)
same = (d.arr_delay == d.dep_delay).mean()
seqmap = {(t, c): s for t, c, s in zip(r24.tno, r24.station_code, r24.seq)}
d["seq"] = [seqmap.get((t, c)) for t, c in zip(d.tno, d.station)]
d = d.dropna(subset=["seq"]).sort_values(["tno", "date", "seq"])
d["prev_station"] = d.groupby(["tno", "date"]).station.shift()
d["prev_delay"] = d.groupby(["tno", "date"]).dep_delay.shift()
d["gain"] = d.arr_delay - d.prev_delay  # minutes lost (+) or recovered (-) on the run between stops
hops = d.dropna(subset=["prev_station"])
hops = hops[hops.station.isin(ids) & hops.prev_station.isin(ids)]
# attribute each stop-to-stop hop to the physical edges on its route, by km share
edge_gain, edge_runs = defaultdict(float), defaultdict(int)
hop_rows = []
grp = hops.groupby(["prev_station", "station"]).agg(runs=("gain", "size"), gain_mean=("gain", "mean"),
                                                     gain_med=("gain", "median")).reset_index()
for r in grp.itertuples():
    p = pair_edges.get((r.prev_station, r.station))
    if p is None:
        km, p = sp(r.prev_station, r.station)
        if p is None: continue
    kms = [G[u][v]["km"] for u, v in zip(p, p[1:])]; tot = sum(kms) or 1
    single = sum(k for (u, v), k in zip(zip(p, p[1:]), kms) if G[u][v]["tracks"] == 1) / tot
    load = np.average([G[u][v]["load"] for u, v in zip(p, p[1:])], weights=kms)
    hop_rows.append(dict(a=r.prev_station, b=r.station, runs=r.runs, km=tot, gain_mean=r.gain_mean,
                         gain_per_100km=r.gain_mean / tot * 100, single_track_share=single, load=load))
hp = pd.DataFrame(hop_rows)
hp = hp[(hp.km >= 5) & (hp.runs >= 20)]
hp["track_class"] = np.where(hp.single_track_share >= .5, "mostly single", "mostly double+")
hp["load_band"] = pd.qcut(hp.load, 4, labels=["Q1 low", "Q2", "Q3", "Q4 high"])
w = lambda g: np.average(g.gain_per_100km, weights=g.runs)
by_track = {k: dict(hops=int(len(g)), runs=int(g.runs.sum()), min_lost_per_100km=round(w(g), 2))
            for k, g in hp.groupby("track_class")}
by_load = {str(k): dict(hops=int(len(g)), min_lost_per_100km=round(w(g), 2))
           for k, g in hp.groupby("load_band", observed=True)}
cross = {f"{a} / {b}": round(w(g), 2) for (a, b), g in hp.groupby(["track_class", "load_band"], observed=True) if len(g) >= 30}
st_delay = d[d.station.isin(ids)].groupby("station").arr_delay.median()
rep["delays_2024"] = dict(
    rows=int(len(d)), trains=int(d.tno.nunique()), days=int(d.date.nunique()),
    arr_equals_dep_share=round(same, 3),
    station_coverage_of_graph_nodes=round(len(set(d.station) & ids) / len(ids), 3),
    hops_mapped_to_track=int(len(hp)), hop_runs=int(hp.runs.sum()),
    loss_by_track=by_track, loss_by_load_quartile=by_load, loss_track_x_load=cross,
    spearman_loss_vs_single_share=round(hp[["gain_per_100km", "single_track_share"]].corr("spearman").iloc[0, 1], 3),
    spearman_loss_vs_load=round(hp[["gain_per_100km", "load"]].corr("spearman").iloc[0, 1], 3),
    median_station_delay_min=round(float(st_delay.median()), 1))
hp.sort_values("gain_per_100km", ascending=False).to_csv(OUT / "delay_hops.csv", index=False)

# ------------------------------------------------------------ D. 2015 timetable
t15 = pd.read_csv(ROOT / "external_data/timetable_2015_datagovin/isl_wise_train_detail_03082015_v1.csv", dtype=str)
t15["tno"] = t15["Train No."].str.strip("' ").str.zfill(5)
c15 = set(t15["station Code"].str.strip())
rep["timetable_2015"] = dict(trains=int(t15.tno.nunique()), stop_rows=int(len(t15)),
                             trains_also_in_2017=round(len(set(t15.tno) & t17) / t15.tno.nunique(), 3),
                             trains_also_in_2024=round(len(set(t15.tno) & set(r24.tno)) / t15.tno.nunique(), 3),
                             station_codes_in_graph=round(len(c15 & ids) / len(c15), 3))
rep["three_snapshots"] = dict(trains_in_2015_2017_2024=len(set(t15.tno) & t17 & set(r24.tno)),
                              trains_in_2017_and_2024=len(t17 & set(r24.tno)))

# ------------------------------------------------------------ E. OSM attributes (full variant only)
rep["osm_full_variant"] = dict(
    edges=len(full), electrification_coverage=round(full.electrified_share_osm.notna().mean(), 3),
    fully_electrified_share_of_tagged=round((full.electrified_share_osm.dropna() >= .99).mean(), 3),
    not_electrified_km=round(full.loc[full.electrified_share_osm < .5, "length_km"].sum(), 1),
    gauge_coverage=round(full.gauge_osm_mm.notna().mean(), 3),
    licence="ODbL 1.0: results derived from these carry share-alike")

# ------------------------------------------------------------ F. structure available without new data
rep["structure"] = dict(nodes=G.number_of_nodes(), edges=G.number_of_edges(),
                        components=nx.number_connected_components(G),
                        bridges=sum(1 for _ in nx.bridges(G)),
                        articulation_points=sum(1 for _ in nx.articulation_points(G)),
                        single_track_km_share=round(edges.loc[edges.n_tracks == 1, "length_km"].sum() / edges.length_km.sum(), 3),
                        lower_bound_length_km_share=round(edges.loc[edges.length_is_lower_bound, "length_km"].sum() / edges.length_km.sum(), 3))
json.dump(rep, open(OUT / "report.json", "w"), indent=2, default=str)
print(json.dumps(rep, indent=1, default=str))
