"""G5 - repair trunk wiring, using the official timetable as ground truth.

Where two stations are consecutive stops on a train, the timetable states both that
they are adjacent on the track and how far apart they are. Summed along a stopping
train those distances reconcile exactly with the end-to-end figure (checked on the
Aligarh-Tundla stretch: 78.0 km either way, 2017 and 2024), so they are a sound
reference for the graph's own topology and lengths.

Three repairs, each carrying its evidence:

  remove_edge  a phantom shortcut - no train runs it, and without it the same two
               stations are still joined by a chain of stations that trains do run,
               lying along the same alignment. SOMNA-DAUD KHAN (28.8 km, no geometry,
               no trains) is the case that put ALIGARH JN off the Delhi-Kanpur trunk.
  set_length   the graph holds the edge, but its length disagrees with the official
               distance for that adjacency. BARHAN-MITAWAL is 4.12 km in the graph
               (a straight-line lower bound) against 8 km official.
  add_edge     the timetable runs the two as consecutive stops, but the graph has no
               direct link and routes the long way round. MITAWAL-TUNDLA JN is 7 km
               official; the graph went 12.6 km via Shivarampur and Etmadpur.

Guards: an adjacency must be attested by at least `min_trains` trains; an added edge
must be physically possible (straight-line distance no greater than the official
figure, measured on the better of the graph's or OSM's coordinates); and nothing is
kept unless the national verification run shows route error improving.

Run:  python repair.py <Rail-Intell root> <detector dir> <output dir>
"""
import json, math, sys
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT, DET, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "04_analysis_modules/E-702_station_code_crosswalk"))
from resolve import load_resolver                                    # noqa: E402

TH = dict(min_trains=3, len_tol_km=1.0, len_tol_frac=0.10, add_ratio=1.25,
          add_min_excess_km=2.0, coord_disagree_km=1.5,
          # a length must be physically possible and not absurd for an adjacency:
          # no shorter than the straight line, no more than a curving line could be
          # official distances are whole kilometres and chargeable rather than
          # geodesic, so the floor carries a small proportional tolerance
          plaus_floor_km=0.3, plaus_floor_frac=0.08,
          plaus_ceiling_frac=1.40, plaus_ceiling_km=2.0)

nodes = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/nodes.csv")
edges = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/edges.csv")
res = load_resolver(ROOT)
nm = dict(zip(nodes.node_id, nodes.node_name))
gpos = {r.node_id: (r.longitude, r.latitude) for r in nodes.itertuples()}

# better-of coordinates: OSM where it knows the code, else the graph's own
osm = pd.concat([pd.read_parquet(p) for p in
                 sorted((ROOT / "external_data/osm_india_rail").glob("rail_stations_*.parquet"))],
                ignore_index=True)
osm["code"] = osm.ref.fillna(osm.railway_ref).astype(str).str.strip().str.upper()
opos = {r.code: (r.lon, r.lat) for r in osm.itertuples() if r.code in gpos}

def hav(a, b):
    (lo1, la1), (lo2, la2) = a, b
    p = math.pi / 180
    h = (math.sin((la2 - la1) * p / 2) ** 2 + math.cos(la1 * p) * math.cos(la2 * p) *
         math.sin((lo2 - lo1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(min(1, h)))

def straight(a, b):
    """Shortest plausible separation, taking the smaller of graph and OSM positions."""
    cand = []
    for pa in (gpos.get(a), opos.get(a)):
        for pb in (gpos.get(b), opos.get(b)):
            if pa and pb: cand.append(hav(pa, pb))
    return min(cand) if cand else None

coord_moves = [dict(node=k, name=nm[k], graph_lon=gpos[k][0], graph_lat=gpos[k][1],
                    osm_lon=opos[k][0], osm_lat=opos[k][1], km_apart=round(hav(gpos[k], opos[k]), 2))
               for k in opos if hav(gpos[k], opos[k]) > TH["coord_disagree_km"]]

G = nx.Graph()
for r in edges.itertuples():
    if G.has_edge(r.from_node, r.to_node) and G[r.from_node][r.to_node]["km"] <= r.length_km:
        continue
    G.add_edge(r.from_node, r.to_node, km=float(r.length_km), eid=r.edge_id,
               direct=int(r.service_direct), src=r.length_source)

# ---------------------------------------------------------------- official adjacency
def adjacency(df, code, train, seq, dist):
    df = df.sort_values([train, seq])
    out = defaultdict(list)
    for t, g in df.groupby(train, sort=False):
        prev = None
        for r in g.itertuples():
            nd = res.node(getattr(r, code)); d = getattr(r, dist)
            if nd is None or pd.isna(d): continue
            if prev and nd != prev[0]:
                k = (prev[0], nd) if prev[0] < nd else (nd, prev[0])
                out[k].append(abs(d - prev[1]))
            prev = (nd, d)
    return out

t17 = pd.read_csv(ROOT / "external_data/timetable_2017_datagovin/Train_details_22122017.csv",
                  dtype=str)
t17["seq"] = pd.to_numeric(t17.SEQ, errors="coerce")
t17["km"] = pd.to_numeric(t17.Distance, errors="coerce")
t17["code"] = t17["Station Code"].str.strip()
a17 = adjacency(t17, "code", "Train No", "seq", "km")

r24 = pd.read_csv(ROOT / "external_data/iitkgp_rstgcn_network_2024/"
                  "Indian-Railway-Network-and-Delays/train_routes_Sep2024.csv", dtype=str)
r24["seq"] = r24.stnSerialNumber.astype(int)
r24["km"] = pd.to_numeric(r24.distance, errors="coerce")
r24["tno"] = r24.trainNumber.str.zfill(5)
a24 = adjacency(r24, "station_code", "tno", "seq", "km")

adj = {}
for k in set(a17) | set(a24):
    v = a17.get(k, []) + a24.get(k, [])
    v = [x for x in v if x > 0]
    if len(v) >= TH["min_trains"]:
        adj[k] = dict(trains=len(v), km=float(np.median(v)),
                      years=("2017+2024" if k in a17 and k in a24 else
                             ("2017" if k in a17 else "2024")))

def graph_chord(a, b):
    pa, pb = gpos.get(a), gpos.get(b)
    return hav(pa, pb) if pa and pb else None

def plausible(a, b, km):
    """Could two stations this far apart really be km apart along the track?
    Below the straight line is impossible; far above it means the pair is not a
    track adjacency at all (a reversal, or a train looping round)."""
    s = straight(a, b)
    if s is None: return True, "no coordinates"
    slack = max(TH["plaus_floor_km"], s * TH["plaus_floor_frac"])
    if km < s - slack:
        return False, f"shorter than the straight line ({km:.1f} < {s:.2f} km)"
    ceil = s * TH["plaus_ceiling_frac"] + TH["plaus_ceiling_km"]
    if km > ceil:
        return False, f"far longer than the straight line ({km:.1f} vs {s:.2f} km)"
    return True, ""

# ---------------------------------------------------------------- build the repairs
rep, rejected = [], []

sc = pd.read_csv(DET / "shortcut_edges.csv")
for r in sc.itertuples():
    rep.append(dict(action="remove_edge", item=r.edge_id, a=r.u, b=r.v, name=r.name,
                    current=r.km, new=None,
                    evidence=(f"no train runs it; without it {r.u}-{r.v} is still joined in "
                              f"{r.bypass_km} km via {r.via} ({r.min_leg_trains}+ trains on "
                              f"every leg), max offset {r.max_offset_km} km from the alignment"),
                    trains=int(r.min_leg_trains), restores=r.via))

for (a, b), o in adj.items():
    if a not in G or b not in G: continue
    if G.has_edge(a, b):
        cur = G[a][b]["km"]
        tol = max(TH["len_tol_km"], o["km"] * TH["len_tol_frac"])
        if abs(cur - o["km"]) > tol:
            ok, why = plausible(a, b, o["km"])
            if not ok:
                rejected.append(dict(action="set_length", name=f"{nm[a]} - {nm[b]}",
                                     current=round(cur, 2), official=o["km"],
                                     trains=o["trains"], reason=why)); continue
            rep.append(dict(action="set_length", item=G[a][b]["eid"], a=a, b=b,
                            name=f"{nm[a]} - {nm[b]}", current=round(cur, 2),
                            new=round(o["km"], 2),
                            evidence=(f"official consecutive-stop distance {o['km']:.0f} km "
                                      f"from {o['trains']} trains ({o['years']}); graph has "
                                      f"{cur:.2f} km from {G[a][b]['src']}"),
                            trains=o["trains"], restores="",
                            src=G[a][b]["src"],
                            raises_lower_bound=(G[a][b]["src"] == "lower_bound_straight_line"
                                                and o["km"] > cur),
                            invariant_safe=((gc := graph_chord(a, b)) is None
                                            or o["km"] >= gc - TH["plaus_floor_km"])))
    else:
        try:
            path_km = nx.shortest_path_length(G, a, b, weight="km")
            path = nx.shortest_path(G, a, b, weight="km")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            path_km, path = None, None
        s = straight(a, b)
        if path_km is None: continue
        if path_km <= o["km"] * TH["add_ratio"]: continue
        if path_km - o["km"] < TH["add_min_excess_km"]: continue
        ok, why = plausible(a, b, o["km"])   # subsumes the straight-line test
        if not ok:
            rejected.append(dict(action="add_edge", name=f"{nm[a]} - {nm[b]}",
                                 current=round(path_km, 2), official=o["km"],
                                 trains=o["trains"], reason=why)); continue
        rep.append(dict(action="add_edge", item=f"{a}|{b}", a=a, b=b,
                        name=f"{nm[a]} - {nm[b]}", current=round(path_km, 2),
                        new=round(o["km"], 2),
                        evidence=(f"consecutive stops on {o['trains']} trains ({o['years']}) at "
                                  f"{o['km']:.0f} km, but the graph has no direct link and goes "
                                  f"{path_km:.2f} km via "
                                  f"{' > '.join(nm[x] for x in path[1:-1][:6])}"
                                  f"; straight-line separation {s:.2f} km"),
                        trains=o["trains"], restores="", src="",
                        raises_lower_bound=False,
                        invariant_safe=((gc := graph_chord(a, b)) is None
                                        or o["km"] >= gc - TH["plaus_floor_km"])))

# Where a repair is impossible against the graph's own coordinates but fine against
# OSM's, the coordinate is the outlier, not the distance: two independent sources
# (the official timetable and OSM) agree against the graph. Move the node.
osm_km = {d["node"]: d for d in coord_moves}
need_move = defaultdict(list)
for r in rep:
    if r["action"] not in ("set_length", "add_edge") or r.get("invariant_safe", True):
        continue
    for end in (r["a"], r["b"]):
        if end in osm_km: need_move[end].append(r["name"])
for node, because in need_move.items():
    d = osm_km[node]
    rep.append(dict(action="move_node", item=node, a=node, b=None, name=nm[node],
                    current=f"{d['graph_lon']:.5f},{d['graph_lat']:.5f}",
                    new=f"{d['osm_lon']:.5f},{d['osm_lat']:.5f}",
                    evidence=(f"graph position is {d['km_apart']} km from OSM's; the official "
                              f"distance for {because[0]} is impossible at the graph position "
                              f"but consistent at OSM's, so two sources agree against the graph"),
                    trains=0, restores="", src="", raises_lower_bound=False,
                    invariant_safe=True))

rp = pd.DataFrame(rep).sort_values(["action", "trains"], ascending=[True, False])
rp.to_csv(OUT / "repairs_proposed.csv", index=False)
rj = pd.DataFrame(rejected)
rj.to_csv(OUT / "repairs_rejected_implausible.csv", index=False)
json.dump(dict(experiment="E-703 / gap G5", thresholds=TH,
               official_adjacencies=len(adj),
               proposed={k: int(v) for k, v in rp.action.value_counts().items()},
               rejected_as_implausible=len(rj),
               rejected_breakdown=({k: int(v) for k, v in rj.reason.str.split(" (", regex=False)
                                    .str[0].value_counts().items()} if len(rj) else {}),
               coordinate_disagreements_over_1_5km=len(coord_moves),
               worst_coordinate_disagreements=sorted(
                   coord_moves, key=lambda d: -d["km_apart"])[:15]),
          open(OUT / "repair_report.json", "w"), indent=2, default=str)
pd.DataFrame(coord_moves).sort_values("km_apart", ascending=False).to_csv(
    OUT / "coordinate_disagreements.csv", index=False)
print(json.dumps(dict(official_adjacencies=len(adj),
                      proposed={k: int(v) for k, v in rp.action.value_counts().items()},
                      coord_disagreements=len(coord_moves)), indent=1))
