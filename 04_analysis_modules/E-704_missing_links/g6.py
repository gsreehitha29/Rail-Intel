"""G6 - add the links trains attest but the graph still routes around, after G5.

G5 added 150 links on official adjacency, but refused 69 more because the official
distance was shorter than the straight line between the two stations. That test
conflated two questions. Whether a link EXISTS is settled by the trains: 249 trains
call at Diva and Kopar Road one after the other, and no train lists two stations
consecutively unless its route runs from one to the other. How LONG it is, is a
separate matter, and the official figure is a chargeable distance, rounded to whole
kilometres, that can fall below the geodesic.

So G6 splits them: take the trains' word on existence, and floor the length at the
straight line so the graph stays physically coherent. Garifa - Hooghly Ghat, 1 km
official against a 1.43 km separation, is a real adjacency over the Jubilee Bridge;
it was rejected by G5 for being 0.43 km too short on paper.

The correction that shapes this module. Consecutive stops do NOT prove a direct
link: a fast train skipping Dombivli still runs over the track through it. They
prove only that track of about that length joins the two. So an excess is a missing
link only when the graph's own path goes somewhere else entirely:

  alignment  take the graph's current path and measure how far its intermediate
             stations sit from the straight line between the two. Diva - Kopar Road
             runs through Dativli and Dombivli, both on the line, so the chain is
             real and the 2 km "excess" is only chargeable distance against summed
             segments - adding a direct edge there would bypass Dombivli, which is
             the very defect G5 removed. Bahadurgarh - Ghevra detours 33 km by way
             of Shakurbasti, nowhere near the line, so the track really is absent.

Two further guards:
  cap     an added edge longer than `max_add_km` would be a new suspect-long edge,
          standing in for a whole missing line and its stations. Those are recorded
          as missing line segments for G3 instead of papered over with one edge.
  excess  the graph's path must be meaningfully longer than the official figure.

Run:  python g6.py <Rail-Intell root> <G5 dir> <output dir>
"""
import json, math, sys
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT, G5DIR, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "04_analysis_modules/E-702_station_code_crosswalk"))
from resolve import load_resolver                                    # noqa: E402

TH = dict(min_trains=2, add_ratio=1.25, add_min_excess_km=2.0, max_add_km=60.0,
          chord_margin=1.02,
          # the graph's path counts as "following the alignment" - and so as a real
          # chain rather than a detour - while its stations stay this close to it
          align_offset_km=2.0, align_offset_frac=0.25,
          # a straight line far longer than the official distance means the two
          # disagree about what they are: wrong coordinates, or the wrong station
          max_chord_over_official=2.0)

nodes = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/nodes.csv")
edges = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/edges.csv")
g5 = pd.read_csv(G5DIR / "repairs_proposed.csv")
res = load_resolver(ROOT)
nm = dict(zip(nodes.node_id, nodes.node_name))
gpos = {r.node_id: (r.longitude, r.latitude) for r in nodes.itertuples()}

osm = pd.concat([pd.read_parquet(p) for p in
                 sorted((ROOT / "external_data/osm_india_rail").glob("rail_stations_*.parquet"))],
                ignore_index=True)
osm["code"] = osm.ref.fillna(osm.railway_ref).astype(str).str.strip().str.upper()
opos = {r.code: (r.lon, r.lat) for r in osm.itertuples() if r.code in gpos}

def hav(pa, pb):
    if pa is None or pb is None: return None
    (lo1, la1), (lo2, la2) = pa, pb
    p = math.pi / 180
    h = (math.sin((la2 - la1) * p / 2) ** 2 + math.cos(la1 * p) * math.cos(la2 * p) *
         math.sin((lo2 - lo1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(min(1, h)))

def offset_km(p, a, b):
    """Perpendicular distance of point p from the segment a-b, in km."""
    k = math.cos(math.radians(a[1])) * 111.32
    ax, ay, bx, by, px, py = (a[0] * k, a[1] * 111.32, b[0] * k, b[1] * 111.32,
                              p[0] * k, p[1] * 111.32)
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0: return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

def follows_alignment(path, a, b, c):
    """Does the graph's current path stay along the a-b line? Then it is the real
    chain of intermediate stations, not a detour, and nothing is missing."""
    pa, pb = gpos.get(a), gpos.get(b)
    mid = [gpos[x] for x in path[1:-1] if x in gpos]
    if pa is None or pb is None or not mid: return False, None
    lim = max(TH["align_offset_km"], (c or 0) * TH["align_offset_frac"])
    worst = max(offset_km(p, pa, pb) for p in mid)
    return worst <= lim, worst

def chord(a, b):
    """Smallest defensible separation: the graph's own, or OSM's where it has both."""
    cand = [d for d in (hav(gpos.get(a), gpos.get(b)), hav(opos.get(a), opos.get(b)))
            if d is not None]
    return min(cand) if cand else None

def base_graph(with_g5=True):
    G = nx.Graph()
    for r in edges.itertuples():
        if G.has_edge(r.from_node, r.to_node) and G[r.from_node][r.to_node]["km"] <= r.length_km:
            continue
        G.add_edge(r.from_node, r.to_node, km=float(r.length_km), eid=r.edge_id)
    if with_g5:
        for r in g5.itertuples():
            if r.action == "remove_edge" and G.has_edge(r.a, r.b): G.remove_edge(r.a, r.b)
            elif r.action == "add_edge" and not G.has_edge(r.a, r.b):
                G.add_edge(r.a, r.b, km=float(r.new), eid=f"G5:{r.a}|{r.b}")
    return G

# ---------------------------------------------------------------- adjacency evidence
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

G = base_graph()
adds, segments, already = [], [], []
for k in set(a17) | set(a24):
    a, b = k
    if a not in G or b not in G or G.has_edge(a, b): continue
    v = [x for x in a17.get(k, []) + a24.get(k, []) if x > 0]
    if len(v) < TH["min_trains"]: continue
    off = float(np.median(v))
    try:
        pkm, path = nx.single_source_dijkstra(G, a, b, weight="km")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        pkm, path = float("inf"), None
    if pkm <= off * TH["add_ratio"] or pkm - off < TH["add_min_excess_km"]: continue
    c = chord(a, b)
    if path is not None:
        ok, worst = follows_alignment(path, a, b, c)
        if ok:
            already.append(dict(a=a, b=b, name=f"{nm[a]} - {nm[b]}", trains=len(v),
                                official_km=round(off, 1), graph_km=round(pkm, 2),
                                max_offset_km=round(worst, 2),
                                via=" > ".join(nm[x] for x in path[1:-1][:6]),
                                reason=("the graph already runs this through intermediate "
                                        "stations along the same line; the difference is "
                                        "chargeable distance against summed segments")))
            continue
    years = "2017+2024" if k in a17 and k in a24 else ("2017" if k in a17 else "2024")
    if c is not None and c > off * TH["max_chord_over_official"]:
        already.append(dict(a=a, b=b, name=f"{nm[a]} - {nm[b]}", trains=len(v),
                            official_km=round(off, 1), graph_km=round(pkm, 2),
                            max_offset_km=None,
                            via=" > ".join(nm[x] for x in (path or [])[1:-1][:6]),
                            reason=(f"the {c:.2f} km straight line is {c / off:.1f} times the "
                                    f"{off:.0f} km official distance: the coordinates or the "
                                    "station identity disagree, so this needs a human look")))
        continue
    km = off if c is None else max(off, c * TH["chord_margin"])
    row = dict(a=a, b=b, name=f"{nm[a]} - {nm[b]}", trains=len(v), official_km=round(off, 1),
               chord_km=None if c is None else round(c, 2), length_km=round(km, 2),
               graph_km_before=None if pkm == float("inf") else round(pkm, 2), years=years,
               floored=bool(c is not None and km > off + 1e-9))
    if off > TH["max_add_km"]:
        row["reason"] = (f"gap of {off:.0f} km is too long for one edge: a whole line "
                         "with its stations is missing here")
        segments.append(row)
    else:
        row["evidence"] = (f"consecutive stops on {len(row and v)} trains ({years}) at "
                           f"{off:.0f} km official; the graph had no direct link and went "
                           f"{row['graph_km_before']} km"
                           + (f"; length floored to the {c:.2f} km straight line"
                              if row["floored"] else ""))
        adds.append(row)

ad = pd.DataFrame(adds).sort_values("trains", ascending=False)
sg = pd.DataFrame(segments).sort_values("trains", ascending=False)
al = pd.DataFrame(already).sort_values("trains", ascending=False)
ad.to_csv(OUT / "links_added.csv", index=False)
sg.to_csv(OUT / "missing_line_segments.csv", index=False)
al.to_csv(OUT / "not_missing_already_routed.csv", index=False)

ov = pd.DataFrame(dict(audit_file="G6_missing_links", item_id=ad.a + "|" + ad.b, field="edge",
                       current_value=ad.graph_km_before, new_value=ad.length_km,
                       action="add_edge", evidence=ad.evidence, source_url="", reviewer="",
                       review_date="", notes="attested by " + ad.trains.astype(str) + " trains"))
ov.to_csv(OUT / "OVERRIDES_G6.csv", index=False)

json.dump(dict(experiment="E-704 / gap G6", thresholds=TH,
               not_missing_already_routed=len(al),
               links_added=len(ad), lengths_floored_to_chord=int(ad.floored.sum()),
               added_km=round(float(ad.length_km.sum()), 1),
               missing_line_segments=len(sg),
               by_train_support={str(k): int(v) for k, v in
                                 ad.groupby(pd.cut(ad.trains, [1, 2, 4, 10, 10**6],
                                                   labels=["2", "3-4", "5-10", ">10"]),
                                            observed=True).size().items()},
               top=ad.head(15)[["name", "trains", "official_km", "chord_km", "length_km",
                                "graph_km_before"]].to_dict("records"),
               segments=sg.head(10)[["name", "trains", "official_km",
                                     "graph_km_before"]].to_dict("records")),
          open(OUT / "report.json", "w"), indent=2, default=str)
print(json.dumps(dict(links_added=len(ad), floored=int(ad.floored.sum()),
                      added_km=round(float(ad.length_km.sum()), 1),
                      missing_line_segments=len(sg)), indent=1))
