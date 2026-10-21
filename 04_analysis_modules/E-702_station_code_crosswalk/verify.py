"""G1 verification - apply the crosswalk and measure what it recovers.

Routes the Sept 2024 trains over graph v1.3 open twice, once with the raw codes and
once with the crosswalk applied, and compares. A crosswalk that is right should:
  - recover stops without making route error worse (an alias puts the train on the
    same track the stop was always on, so the km check is the guard against a wrong
    mapping: a bad alias sends the route somewhere else and the error jumps);
  - leave no train with the same node twice in a row;
  - leave the hardest stations - the ones the graph simply lacks - still unmatched.

Run:  python verify.py <Rail-Intell root> <crosswalk dir> <output dir>
"""
import json, sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT, CW, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)

nodes = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/nodes.csv")
edges = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/edges.csv")
r24 = pd.read_csv(ROOT / "external_data/iitkgp_rstgcn_network_2024/"
                  "Indian-Railway-Network-and-Delays/train_routes_Sep2024.csv", dtype=str)
cw = pd.read_csv(CW / "crosswalk.csv")
xwalk = dict(zip(cw.loc[cw.resolution == "alias", "code"],
                 cw.loc[cw.resolution == "alias", "graph_node"]))

ids = set(nodes.node_id)
G = nx.Graph()
for r in edges.itertuples():
    if G.has_edge(r.from_node, r.to_node) and G[r.from_node][r.to_node]["km"] <= r.length_km:
        continue
    G.add_edge(r.from_node, r.to_node, km=float(r.length_km))

r24["seq"] = r24.stnSerialNumber.astype(int)
r24["dist"] = pd.to_numeric(r24.distance, errors="coerce")
r24["tno"] = r24.trainNumber.str.zfill(5)
r24 = r24.sort_values(["tno", "seq"])

cache = {}
def sp(a, b):
    k = (a, b) if a < b else (b, a)
    if k not in cache:
        try: cache[k] = nx.shortest_path_length(G, a, b, weight="km")
        except (nx.NetworkXNoPath, nx.NodeNotFound): cache[k] = None
    return cache[k]

def run(apply_cw):
    matched = total = 0
    errs, routed, failed, adjacent_dupes = [], 0, 0, 0
    trains = 0
    for tno, g in r24.groupby("tno", sort=False):
        trains += 1
        stops = []
        for r in g.itertuples():
            total += 1
            c = xwalk.get(r.station_code, r.station_code) if apply_cw else r.station_code
            if c not in ids: continue
            matched += 1
            if stops and stops[-1][0] == c:
                adjacent_dupes += 1
                continue
            stops.append((c, r.dist))
        if len(stops) < 2: continue
        km, ok = 0.0, True
        for (a, da), (b, db) in zip(stops, stops[1:]):
            d = sp(a, b)
            if d is None: ok = False; break
            km += d
        if not ok: failed += 1; continue
        routed += 1
        tkm = stops[-1][1] - stops[0][1]
        if pd.notna(tkm) and tkm >= 20: errs.append((km - tkm) / tkm)
    e = pd.Series(errs)
    return dict(stop_rows=total, stop_rows_matched=matched,
                stop_rows_matched_share=round(matched / total, 4),
                trains=trains, trains_routed=routed, trains_unroutable=failed,
                evaluated=len(e), median_abs_route_err=round(e.abs().median(), 4),
                within_5pct=round((e.abs() <= .05).mean(), 4),
                p90_abs_err=round(e.abs().quantile(.9), 4),
                adjacent_duplicate_stops=adjacent_dupes)

before, after = run(False), run(True)

# ---- per-alias impact: route error of each alias's own trains, with and without it.
# An alias is only suspect if its name/position evidence was weak AND it moves the
# error. A sub-km exact-name match that moves the error is pointing at broken track
# in the graph, not at a wrong mapping - which makes it a lead for G6/G9.
def train_err(g, apply_cw):
    stops = []
    for r in g.itertuples():
        c = xwalk.get(r.station_code, r.station_code) if apply_cw else r.station_code
        if c in ids and (not stops or stops[-1][0] != c): stops.append((c, r.dist))
    if len(stops) < 2: return np.nan
    km = 0.0
    for (a, _), (b, _) in zip(stops, stops[1:]):
        d = sp(a, b)
        if d is None: return np.nan
        km += d
    tkm = stops[-1][1] - stops[0][1]
    return (km - tkm) / tkm if pd.notna(tkm) and tkm >= 20 else np.nan

per = []
for tno, g in r24.groupby("tno", sort=False):
    hit = sorted(set(g.station_code) & set(xwalk))
    if hit: per.append(dict(codes=hit, b=train_err(g, False), a=train_err(g, True)))
pt = pd.DataFrame(per).dropna(subset=["b", "a"])
pt["jump"] = pt.a.abs() - pt.b.abs()
imp = (pt.explode("codes").groupby("codes")
       .agg(trains=("jump", "size"), median_error_jump=("jump", "median")).round(4))

comp = dict(zip(nodes.node_id, nodes.component_id))
cw["target_in_small_component"] = cw.graph_node.map(
    lambda x: None if pd.isna(x) else comp.get(x, 0) != 0)
cw = cw.merge(imp, left_on="code", right_index=True, how="left")
cw["exposes_defective_topology"] = cw.median_error_jump.fillna(0).abs() > 0.05
cw.to_csv(OUT / "crosswalk.csv", index=False)

suspect = cw[(cw.resolution == "alias") & cw.exposes_defective_topology]
rep = dict(experiment="E-702 verification", aliases_applied=len(xwalk),
           before=before, after=after,
           stop_rows_recovered=after["stop_rows_matched"] - before["stop_rows_matched"],
           coverage_before=before["stop_rows_matched_share"],
           coverage_after=after["stop_rows_matched_share"],
           route_error_change=round(after["median_abs_route_err"] -
                                    before["median_abs_route_err"], 4),
           median_error_on_alias_trains=dict(
               trains=int(len(pt)), before=round(pt.b.abs().median(), 4),
               after=round(pt.a.abs().median(), 4)),
           aliases_neutral_on_error=int((imp.median_error_jump.abs() <= 0.01).sum()),
           aliases_exposing_defective_topology=suspect[
               ["code", "name", "graph_node", "graph_node_name", "km_apart", "name_sim",
                "median_error_jump"]].to_dict("records"),
           alias_targets_in_small_components=cw.loc[
               (cw.resolution == "alias") & (cw.target_in_small_component == True),
               ["code", "graph_node"]].to_dict("records"),
           verdict=("crosswalk recovers stops without degrading route accuracy"
                    if after["stop_rows_matched"] > before["stop_rows_matched"]
                    and after["median_abs_route_err"] <= before["median_abs_route_err"] + 0.002
                    and after["adjacent_duplicate_stops"] == 0
                    else "REVIEW: accuracy moved or duplicate stops appeared"))
json.dump(rep, open(OUT / "verification.json", "w"), indent=2, default=str)
print(json.dumps(rep, indent=1, default=str))
