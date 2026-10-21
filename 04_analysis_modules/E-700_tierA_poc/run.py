"""E-700 - Tier A proof of concept on one regional subgraph of graph v1.3 (open).

Question: do the Tier A applications (routing, load, criticality, accessibility,
circuity, empirical running times) actually work on the data we have, or only on paper?

Region: Delhi - Agra - Kanpur - Lucknow - Moradabad - Bareilly (bbox lon 77.0-81.2,
lat 26.3-29.0). Chosen because it has dense junctions, genuine alternative routes and
some of the heaviest passenger traffic in the 2017 timetable.

Inputs (read-only):
  03_graph_construction/graph_v1_3/open/{nodes,edges}.csv
  03_graph_construction/service_layer_v1_3/open/service_edges_directed.csv
  external_data/timetable_2017_datagovin/Train_details_22122017.csv

Run:  python run.py <Rail-Intell root> <output dir>
"""
import json, math, sys
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("out")
OUT.mkdir(parents=True, exist_ok=True)
BBOX = dict(lon=(77.0, 81.2), lat=(26.3, 29.0))
KEY = ["NDLS", "DLI", "NZM", "ANVT", "GZB", "ALJN", "HRS", "TDL", "AGC", "AF", "MTJ",
       "ETW", "CNB", "LKO", "LJN", "MB", "BE", "KSJ", "FZD", "SRE"]

nodes = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/nodes.csv")
edges = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/edges.csv")
svc = pd.read_csv(ROOT / "03_graph_construction/service_layer_v1_3/open/service_edges_directed.csv")
tt = pd.read_csv(ROOT / "external_data/timetable_2017_datagovin/Train_details_22122017.csv", dtype=str)

def hav(lon1, lat1, lon2, lat2):
    p = math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2 +
         math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(a))

# ---------------------------------------------------------------- 1. subgraph
allids = set(nodes.node_id)
inreg = nodes[nodes.longitude.between(*BBOX["lon"]) & nodes.latitude.between(*BBOX["lat"])]
reg = set(inreg.node_id)
pos = dict(zip(nodes.node_id, zip(nodes.longitude, nodes.latitude)))
name = dict(zip(nodes.node_id, nodes.node_name))
state = dict(zip(nodes.node_id, nodes.state))

def build(ids=None):
    G = nx.Graph()
    for r in edges.itertuples():
        if ids is not None and not (r.from_node in ids and r.to_node in ids):
            continue
        a, b = r.from_node, r.to_node
        if G.has_edge(a, b) and G[a][b]["km"] <= r.length_km:
            continue  # keep shortest parallel
        G.add_edge(a, b, km=float(r.length_km), eid=r.edge_id, src=r.length_source,
                   lb=bool(r.length_is_lower_bound), tmod=float(r.travel_time_min)
                   if pd.notna(r.travel_time_min) else float(r.length_km) / 60 * 60,
                   load_build=int(r.service_load), tracks=r.n_tracks)
    return G

G = build(reg)
GN = build()  # national graph, used only to test boundary effects
comps = sorted(nx.connected_components(G), key=len, reverse=True)
sub = dict(nodes=G.number_of_nodes(), edges=G.number_of_edges(),
           km=round(sum(d["km"] for *_, d in G.edges(data=True)), 1),
           components=len(comps), giant_share=round(len(comps[0]) / G.number_of_nodes(), 4),
           key_present={k: (k in G) for k in KEY},
           length_source_share={k: round(v, 4) for k, v in pd.Series(
               [d["src"] for *_, d in G.edges(data=True)]).value_counts(normalize=True).items()},
           bridges=len(list(nx.bridges(G))), articulation_points=len(list(nx.articulation_points(G))))
ekey = lambda a, b: (a, b) if a < b else (b, a)

# ---------------------------------------------------------------- 2. route trains
tt["code"] = tt["Station Code"].str.strip()
tt["seq"] = pd.to_numeric(tt["SEQ"], errors="coerce")
tt["dist"] = pd.to_numeric(tt["Distance"], errors="coerce")
tt["tno"] = tt["Train No"].str.strip()
tt = tt.sort_values(["tno", "seq"])

segments = []  # contiguous in-region runs of a train's stops
unknown_codes = set()
for tno, g in tt.groupby("tno", sort=False):
    run = []
    for r in g.itertuples():
        c = r.code
        if c not in allids:
            unknown_codes.add(c)
            continue  # not in graph at all: skip, don't break the run
        if c in reg:
            if not run or run[-1][0] != c:
                run.append((c, r.dist))
        else:
            if len(run) >= 2:
                segments.append((tno, run))
            run = []
    if len(run) >= 2:
        segments.append((tno, run))

path_cache = {}
def sp(a, b):
    k = (a, b)
    if k not in path_cache:
        try:
            p = nx.shortest_path(G, a, b, weight="km")
            path_cache[k] = (p, sum(G[u][v]["km"] for u, v in zip(p, p[1:])))
        except nx.NetworkXNoPath:
            path_cache[k] = (None, None)
    return path_cache[k]

seg_rows, pair_trains, pair_rows = [], defaultdict(set), []
seg_runs = {}
edge_trains = defaultdict(set)
for tno, run in segments:
    route_km, ok, used = 0.0, True, set()
    for (a, da), (b, db) in zip(run, run[1:]):
        p, km = sp(a, b)
        if p is None:
            ok = False; break
        route_km += km
        pair_trains[(a, b)].add(tno)
        if da is not None and db is not None and not (pd.isna(da) or pd.isna(db)):
            pair_rows.append(dict(a=a, b=b, train=tno, tt_km=abs(db - da), route_km=km))
        used.update(ekey(u, v) for u, v in zip(p, p[1:]))
    seg_runs[len(seg_rows)] = run
    off = sum(G[u][v]["km"] for u, v in used if G[u][v]["src"].startswith("official"))
    tot = sum(G[u][v]["km"] for u, v in used) or 1
    tt_km = (run[-1][1] - run[0][1]) if run[-1][1] is not None and run[0][1] is not None else np.nan
    seg_rows.append(dict(train=tno, first=run[0][0], last=run[-1][0], stops=len(run),
                         routed=ok, route_km=round(route_km, 2) if ok else None, timetable_km=tt_km,
                         official_len_share=round(off / tot, 3)))
    if ok:
        for k in used:
            edge_trains[k].add(tno)
seg = pd.DataFrame(seg_rows)
seg["err"] = (seg.route_km - seg.timetable_km) / seg.timetable_km
ev = seg[seg.routed & (seg.timetable_km >= 20)]
routing = dict(trains_touching_region=int(seg.train.nunique()), segments=len(seg),
               routed_share=round(seg.routed.mean(), 4),
               unknown_codes_skipped=len(unknown_codes),
               evaluated_segments=len(ev),
               median_abs_err=round(ev.err.abs().median(), 4),
               within_2pct=round((ev.err.abs() <= .02).mean(), 4),
               within_5pct=round((ev.err.abs() <= .05).mean(), 4),
               signed_median=round(ev.err.median(), 4),
               err_by_official_length_share={b: dict(n=int(len(g)), median_abs_err=round(g.err.abs().median(), 4))
                   for b, g in ev.groupby(pd.cut(ev.official_len_share, [-.01, .25, .5, .75, 1.0],
                                                 labels=["0-25%", "25-50%", "50-75%", "75-100%"]), observed=True)})
pr = pd.DataFrame(pair_rows)
pr = pr[(pr.tt_km > 0)].groupby(["a", "b"]).agg(trains=("train", "nunique"), tt_km=("tt_km", "median"),
                                                route_km=("route_km", "first")).reset_index()
pr["ratio"] = pr.route_km / pr.tt_km
ml = pr[(pr.ratio > 1.25) & (pr.route_km - pr.tt_km > 5)].copy()
ml["key"] = [tuple(sorted(x)) for x in zip(ml.a, ml.b)]
ml = ml.sort_values("trains", ascending=False).drop_duplicates("key")
ml["pair"] = ml.a.map(name) + " - " + ml.b.map(name)
short = pr[(pr.ratio < 0.8) & (pr.tt_km - pr.route_km > 5)].copy()
short["key"] = [tuple(sorted(x)) for x in zip(short.a, short.b)]
short = short.drop_duplicates("key")
routing["missing_link_candidates"] = len(ml)
routing["missing_link_top"] = ml.head(12)[["pair", "trains", "tt_km", "route_km"]].round(1).to_dict("records")
routing["graph_shorter_than_timetable_pairs"] = len(short)
ml.drop(columns="key").to_csv(OUT / "missing_link_candidates.csv", index=False)
seg.to_csv(OUT / "routing_segments.csv", index=False)

# ---------------------------------------------------------------- 3. load
load = pd.DataFrame([dict(a=a, b=b, eid=G[a][b]["eid"], km=G[a][b]["km"],
                          trains=len(edge_trains.get(ekey(a, b), ())),
                          load_build=G[a][b]["load_build"], tracks=G[a][b]["tracks"])
                     for a, b in G.edges()])
load["name"] = load.a.map(name) + " - " + load.b.map(name)
loadres = dict(edges_with_trains=int((load.trains > 0).sum()),
               edges_with_trains_share=round((load.trains > 0).mean(), 4),
               spearman_vs_build_service_load=round(load[["trains", "load_build"]].corr("spearman").iloc[0, 1], 3),
               top10=load.sort_values("trains", ascending=False).head(10)[["name", "trains", "tracks"]].to_dict("records"))
load.to_csv(OUT / "edge_load.csv", index=False)

# ---------------------------------------------------------------- 4. criticality (edge removal)
pair_paths = {k: path_cache[k] for k in pair_trains if path_cache.get(k, (None,))[0]}
edge_pairs = defaultdict(list)
for k, (p, km) in pair_paths.items():
    for u, v in zip(p, p[1:]):
        edge_pairs[ekey(u, v)].append(k)

crit = []
for e_, pairs in edge_pairs.items():
    a, b = e_
    d = G[a][b]
    G.remove_edge(a, b)
    stranded_tr, affected_tr, extra = set(), set(), 0.0
    strand_pairs = []
    for (s, t) in pairs:
        trs = pair_trains[(s, t)]
        affected_tr |= trs
        try:
            km2 = nx.shortest_path_length(G, s, t, weight="km")
            extra += (km2 - pair_paths[(s, t)][1]) * len(trs)
        except nx.NetworkXNoPath:
            stranded_tr |= trs
            strand_pairs.append((s, t))
    G.add_edge(a, b, **d)
    crit.append(dict(a=a, b=b, eid=d["eid"], name=f"{name[a]} - {name[b]}", trains=len(affected_tr),
                     stranded_trains=len(stranded_tr), extra_train_km=round(extra, 1),
                     strand_pairs=strand_pairs, km=d["km"]))
crit = pd.DataFrame(crit)

# boundary check: are 'stranded' pairs really stranded, or only inside the box?
GN_rm_cache = {}
def nat_alt(a, b, s, t):
    d = GN[a][b]; GN.remove_edge(a, b)
    try:
        ok = nx.has_path(GN, s, t)
    finally:
        GN.add_edge(a, b, **d)
    return ok
crit["stranded_nationally"] = 0
for i, r in crit[crit.stranded_trains > 0].iterrows():
    nat = set()
    for (s, t) in r.strand_pairs:
        if not nat_alt(r.a, r.b, s, t):
            nat |= pair_trains[(s, t)]
    crit.at[i, "stranded_nationally"] = len(nat)

# topology-only comparison: plain edge betweenness
eb = nx.edge_betweenness_centrality(G, weight="km", normalized=True)
crit["topo_betweenness"] = [eb.get((r.a, r.b), eb.get((r.b, r.a), 0)) for r in crit.itertuples()]
crit["score"] = crit.stranded_nationally * 1000 + crit.extra_train_km  # strand first, then detour
crit = crit.sort_values(["stranded_nationally", "extra_train_km"], ascending=False)
top_s = set(crit.head(20).eid)
top_t = set(crit.sort_values("topo_betweenness", ascending=False).head(20).eid)
trunk = crit[(crit.stranded_nationally == 0)].sort_values("extra_train_km", ascending=False)
critres = dict(edges_tested=len(crit),
               edges_whose_loss_strands_trains_in_box=int((crit.stranded_trains > 0).sum()),
               edges_whose_loss_strands_trains_nationally=int((crit.stranded_nationally > 0).sum()),
               boundary_overstatement=int((crit.stranded_trains > 0).sum() - (crit.stranded_nationally > 0).sum()),
               top20_overlap_with_plain_betweenness=len(top_s & top_t),
               spearman_extra_km_vs_betweenness=round(crit[["extra_train_km", "topo_betweenness"]].corr("spearman").iloc[0, 1], 3),
               top_detour=trunk.head(15)[["name", "trains", "extra_train_km", "km"]].to_dict("records"),
               top15=crit.head(15)[["name", "trains", "stranded_nationally", "extra_train_km", "km"]].to_dict("records"))
crit.drop(columns=["strand_pairs"]).to_csv(OUT / "criticality_edges.csv", index=False)

# node removal for named junctions: every train that stops at or passes the junction
# is re-routed over its remaining stops with the junction removed from the graph
seg_index = seg.reset_index(drop=True)
node_rows = []
for k in ["GZB", "ALJN", "HRS", "TDL", "CNB", "LKO", "MB", "MTJ", "BE", "ETW"]:
    if k not in G: continue
    nb = list(G.edges(k, data=True)); G.remove_node(k)
    aff, st, ex, lost_term = set(), set(), 0.0, set()
    for i, run in seg_runs.items():
        r0 = seg_index.loc[i]
        if not r0.routed: continue
        stops_ = [c for c, _ in run]
        passes = any(k in path_cache[(x, y)][0] for x, y in zip(stops_, stops_[1:]))
        if not passes: continue
        aff.add(r0.train)
        rem = [c for c in stops_ if c != k]
        if stops_[0] == k or stops_[-1] == k:
            lost_term.add(r0.train)
            continue  # the train's run in the box starts/ends here: no like-for-like detour
        try:
            new = sum(nx.shortest_path_length(G, x, y, weight="km") for x, y in zip(rem, rem[1:]))
            ex += new - r0.route_km
        except nx.NetworkXNoPath:
            st.add(r0.train)
    G.add_node(k); G.add_edges_from((u, v, d) for u, v, d in nb)
    node_rows.append(dict(station=k, name=name[k], trains_affected=len(aff), lose_terminal=len(lost_term),
                          stranded_in_box=len(st), extra_train_km=round(ex, 1),
                          extra_km_per_rerouted_train=round(ex / max(1, len(aff) - len(st) - len(lost_term)), 1)))
nodecrit = pd.DataFrame(node_rows).sort_values("trains_affected", ascending=False)
nodecrit.to_csv(OUT / "criticality_junctions.csv", index=False)

# ---------------------------------------------------------------- 5. empirical running times
s = svc[svc.is_direct_physical_edge == True].copy()
s["k"] = [ekey(a, b) for a, b in zip(s.from_station, s.to_station)]
emp = s.groupby("k").apply(lambda g: pd.Series(dict(
    runtime=np.average(g.runtime_min_median, weights=g.n_runtime_obs.clip(lower=1)),
    obs=int(g.n_runtime_obs.sum())))).to_dict("index")
rt_rows = []
for a, b, d in G.edges(data=True):
    k = ekey(a, b); m = emp.get(k)
    rt_rows.append(dict(eid=d["eid"], km=d["km"], model_min=d["tmod"],
                        observed_min=m["runtime"] if m else np.nan, obs=m["obs"] if m else 0))
rt = pd.DataFrame(rt_rows)
rt["obs_speed"] = rt.km / (rt.observed_min / 60)
o = rt[rt.observed_min > 0]
runtime = dict(edges=len(rt), edges_with_observed_runtime=len(o), coverage=round(len(o) / len(rt), 4),
               km_coverage=round(o.km.sum() / rt.km.sum(), 4),
               observed_speed_median=round(o.obs_speed.median(), 1),
               speed_p10_p90=[round(o.obs_speed.quantile(.1), 1), round(o.obs_speed.quantile(.9), 1)],
               implausible_over_130=int((o.obs_speed > 130).sum()),
               implausible_under_10=int((o.obs_speed < 10).sum()),
               model_vs_observed_median_ratio=round((o.model_min / o.observed_min).median(), 3))
rt.to_csv(OUT / "edge_runtime.csv", index=False)

# time weight: observed where available and plausible, else modelled
for a, b, d in G.edges(data=True):
    m = emp.get(ekey(a, b))
    spd = d["km"] / (m["runtime"] / 60) if m and m["runtime"] > 0 else None
    d["tmin"] = m["runtime"] if spd and 10 <= spd <= 130 else d["tmod"]

# ---------------------------------------------------------------- 6. accessibility
stops = tt[tt.code.isin(reg)].groupby("code").tno.nunique()
hubs = list(stops.sort_values(ascending=False).head(8).index)
dist_t = nx.multi_source_dijkstra_path_length(G, hubs, weight="tmin")
dist_k = nx.multi_source_dijkstra_path_length(G, hubs, weight="km")
acc = pd.DataFrame(dict(node=list(G.nodes())))
acc["name"] = acc.node.map(name); acc["state"] = acc.node.map(state)
acc["min_to_hub"] = acc.node.map(dist_t); acc["km_to_hub"] = acc.node.map(dist_k)
acc["trains_stopping"] = acc.node.map(stops).fillna(0).astype(int)
acc["lon"] = acc.node.map(lambda x: pos[x][0]); acc["lat"] = acc.node.map(lambda x: pos[x][1])
bystate = acc.groupby("state").agg(stations=("node", "size"), median_min=("min_to_hub", "median"),
                                   share_within_60=("min_to_hub", lambda x: (x <= 60).mean()),
                                   median_trains=("trains_stopping", "median")).round(3)
bystate = bystate[bystate.stations >= 10].sort_values("median_min")
accres = dict(hubs=[f"{h} {name[h]} ({stops[h]} trains)" for h in hubs],
              median_min=round(acc.min_to_hub.median(), 1),
              within_60=round((acc.min_to_hub <= 60).mean(), 4),
              within_120=round((acc.min_to_hub <= 120).mean(), 4),
              stations_with_no_stopping_train=int((acc.trains_stopping == 0).sum()),
              worst10=acc.sort_values("min_to_hub", ascending=False).head(10)[["name", "state", "min_to_hub", "trains_stopping"]].round(1).to_dict("records"),
              by_state=bystate.reset_index().to_dict("records"))
acc.to_csv(OUT / "accessibility_stations.csv", index=False)

# ---------------------------------------------------------------- 7. circuity
served = list(stops[stops >= 20].index)
served = [x for x in served if x in G]
ck = {x: nx.single_source_dijkstra_path_length(G, x, weight="km") for x in served}
cr = []
for i, a in enumerate(served):
    for b in served[i + 1:]:
        h = hav(*pos[a], *pos[b])
        if h < 30: continue
        cr.append(dict(a=a, b=b, crow_km=h, net_km=ck[a][b], circuity=ck[a][b] / h))
cr = pd.DataFrame(cr)
# explain outliers: do their paths lean on lower-bound (straight-line) lengths?
def lb_share(a, b):
    p = nx.shortest_path(G, a, b, weight="km"); tot = sum(G[u][v]["km"] for u, v in zip(p, p[1:]))
    return sum(G[u][v]["km"] for u, v in zip(p, p[1:]) if G[u][v]["lb"]) / tot
out_ = cr.sort_values("circuity", ascending=False).head(15).copy()
out_["lower_bound_km_share"] = [round(lb_share(r.a, r.b), 3) for r in out_.itertuples()]
out_["pair"] = out_.a.map(name) + " - " + out_.b.map(name)
circ = dict(stations=len(served), pairs=len(cr), median=round(cr.circuity.median(), 3),
            p90=round(cr.circuity.quantile(.9), 3), share_over_1_5=round((cr.circuity > 1.5).mean(), 4),
            share_below_1=int((cr.circuity < 0.999).sum()),
            top=out_[["pair", "crow_km", "net_km", "circuity", "lower_bound_km_share"]].round(2).to_dict("records"))
cr.to_csv(OUT / "circuity_pairs.csv", index=False)

# ---------------------------------------------------------------- trunk sanity: do shortest paths pass the junctions they should?
trunk_checks = {}
for a, b, must in [("GZB", "CNB", ["ALJN", "HRS", "TDL", "ETW"]), ("NDLS", "AGC", ["MTJ"]),
                   ("GZB", "MB", []), ("MB", "LKO", ["BE"]), ("CNB", "LKO", [])]:
    p = nx.shortest_path(G, a, b, weight="km")
    ta, tb = tt[tt.code == a][["tno", "dist"]], tt[tt.code == b][["tno", "dist"]]
    both = ta.merge(tb, on="tno")
    tkm = float((both.dist_x - both.dist_y).abs().median()) if len(both) else None
    trunk_checks[f"{a}-{b}"] = dict(km=round(nx.path_weight(G, p, "km"), 1), timetable_km_median=tkm,
                                    trains_with_both=int(both.tno.nunique()),
                                    missing_expected_junctions=[m for m in must if m not in p])
for k in ["ALJN"]:
    trunk_checks[f"{k}_neighbours"] = {name[x]: [round(G[k][x]["km"], 1), G[k][x]["src"]] for x in G[k]}

# ---------------------------------------------------------------- map data + report
mapdata = dict(nodes=[[x, name[x], round(pos[x][0], 4), round(pos[x][1], 4),
                       None if pd.isna(dist_t.get(x)) else round(dist_t[x]), int(stops.get(x, 0))] for x in G.nodes()],
               edges=[[a, b, len(edge_trains.get(ekey(a, b), ())),
                       int(crit.set_index("eid").stranded_nationally.get(G[a][b]["eid"], 0)),
                       float(crit.set_index("eid").extra_train_km.get(G[a][b]["eid"], 0))] for a, b in G.edges()],
               hubs=hubs, key=[k for k in KEY if k in G])
json.dump(mapdata, open(OUT / "map_data.json", "w"))
report = dict(experiment="E-700", graph="graph_v1_3/open", bbox=BBOX, subgraph=sub, routing=routing,
              load=loadres, criticality=critres, junction_removal=nodecrit.to_dict("records"), trunk_checks=trunk_checks,
              running_times=runtime, accessibility=accres, circuity=circ)
json.dump(report, open(OUT / "report.json", "w"), indent=2, default=str)
print(json.dumps(report, indent=1, default=str))
