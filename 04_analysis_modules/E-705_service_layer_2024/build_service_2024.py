"""G15 - the 2024 service layer: which trains run over which track, directed and timed.

The shipped service layer is built from the 2017 timetable, so 267 track sections that
carry trains today show none, and every service-weighted result describes 2017 running
on current track. This rebuilds it from the September 2024 routes.

It only becomes possible after the earlier gaps: G1's crosswalk resolves the 335
renamed codes the 2024 data uses (Mughalsarai -> DDU, Allahabad -> Prayagraj), and the
G5/G6 repairs put the track under the trains where it belongs.

Schema follows the 2017 layer exactly, so the two are directly comparable:

  service_edges_directed_2024.csv   one row per ordered station pair that trains run
      between as consecutive stops, with train counts, observed runtimes, and how that
      pair sits on the physical graph (direct edge, path km, hops, implied speed)
  service_hourly_2024.csv           departures per hour of day, per ordered pair
  edge_service_2024.csv             per physical edge: trains, and the share arriving
      through G5/G6 repairs, so a later reader can see what the repairs carry

Times are "08:00 AM" strings with no day number, so a stop timed earlier than the one
before it is taken as the next day; runs implying more than `max_runtime_h` are
dropped rather than guessed at.

Run:  python build_service_2024.py <Rail-Intell root> <output dir>
"""
import json, sys
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "04_analysis_modules/E-702_station_code_crosswalk"))
from resolve import load_resolver                                    # noqa: E402
from railgraph_repaired import load_graph                            # noqa: E402

TH = dict(max_runtime_h=30, max_path_km=400, speed_min=5, speed_max=160)

res = load_resolver(ROOT)
G, gmeta = load_graph(ROOT)
nm = {n: d.get("name") for n, d in G.nodes(data=True)}

r24 = pd.read_csv(ROOT / "external_data/iitkgp_rstgcn_network_2024/"
                  "Indian-Railway-Network-and-Delays/train_routes_Sep2024.csv", dtype=str)
r24["seq"] = r24.stnSerialNumber.astype(int)
r24["km"] = pd.to_numeric(r24.distance, errors="coerce")
r24["tno"] = r24.trainNumber.str.zfill(5)
r24 = r24.sort_values(["tno", "seq"])

def minutes(t):
    """'08:00 AM' -> minutes past midnight."""
    try:
        hhmm, ap = str(t).strip().rsplit(" ", 1)
        h, m = (int(x) for x in hhmm.split(":")[:2])
    except Exception:
        return None
    h = h % 12 + (12 if ap.upper() == "PM" else 0)
    return h * 60 + m

r24["arr_m"] = r24.arrivalTime.map(minutes)
r24["dep_m"] = r24.departureTime.map(minutes)

# train type from the name, same spirit as the 2017 layer's train_types
def kind(name):
    s = str(name).lower()
    for key, lab in (("rajdhani", "Rajdhani"), ("shatabdi", "Shatabdi"),
                     ("vande", "VandeBharat"), ("duronto", "Duronto"),
                     ("garib", "GaribRath"), ("humsafar", "Humsafar"),
                     ("jan shatabdi", "JanShatabdi"), ("superfast", "SF"),
                     ("express", "Exp"), ("passenger", "Pass"), ("memu", "MEMU"),
                     ("demu", "DEMU"), ("emu", "EMU"), ("special", "Spl")):
        if key in s: return lab
    return "Other"

# ---------------------------------------------------------------- walk the trains
pairs = defaultdict(lambda: dict(n=0, rt=[], types=defaultdict(int), hours=defaultdict(int),
                                 tt_km=[]))
unmapped_rows = skipped_dupe = 0
trains_used = set()
for tno, g in r24.groupby("tno", sort=False):
    rows = []
    for r in g.itertuples():
        nd = res.node(r.station_code)
        if nd is None: unmapped_rows += 1; continue
        if rows and rows[-1][0] == nd: skipped_dupe += 1; continue
        rows.append((nd, r.arr_m, r.dep_m, r.km))
    if len(rows) < 2: continue
    trains_used.add(tno)
    k = kind(g.trainName.iloc[0])
    prev_abs = None
    for (a, _, dep_a, km_a), (b, arr_b, _, km_b) in zip(rows, rows[1:]):
        d = pairs[(a, b)]
        d["n"] += 1
        d["types"][k] += 1
        if dep_a is not None:
            d["hours"][dep_a // 60] += 1
        if dep_a is not None and arr_b is not None:
            run = arr_b - dep_a
            while run < 0: run += 1440          # crossed midnight
            if 0 < run <= TH["max_runtime_h"] * 60: d["rt"].append(run)
        if pd.notna(km_a) and pd.notna(km_b) and km_b > km_a:
            d["tt_km"].append(km_b - km_a)

# ---------------------------------------------------------------- map onto the track
_sp = {}
def path(a, b):
    k = (a, b) if a < b else (b, a)
    if k not in _sp:
        try:
            km, p = nx.single_source_dijkstra(G, a, b, weight="km",
                                              cutoff=TH["max_path_km"])
            _sp[k] = (km, p)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            _sp[k] = (None, None)
    return _sp[k]

rows, hourly, edge_trains = [], [], defaultdict(set)
for (a, b), d in pairs.items():
    both = a in G and b in G
    km, p = path(a, b) if both else (None, None)
    direct = bool(both and G.has_edge(a, b))
    rt = pd.Series(d["rt"], dtype=float)
    med = float(rt.median()) if len(rt) else np.nan
    spd = (km / (med / 60)) if (km and med and med > 0) else np.nan
    if pd.notna(spd) and not (TH["speed_min"] <= spd <= TH["speed_max"]): spd = np.nan
    rows.append(dict(
        from_station=a, to_station=b, n_trains=d["n"],
        runtime_min_median=round(med, 1) if pd.notna(med) else None,
        runtime_min_p10=round(float(rt.quantile(.1)), 1) if len(rt) else None,
        runtime_min_p90=round(float(rt.quantile(.9)), 1) if len(rt) else None,
        n_runtime_obs=len(rt),
        train_types=json.dumps(dict(sorted(d["types"].items(), key=lambda t: -t[1]))),
        both_in_physical_graph=both, is_direct_physical_edge=direct,
        physical_path_km=round(km, 6) if km is not None else None,
        physical_hops=(len(p) - 1) if p else None,
        observed_speed_kmph=round(spd, 6) if pd.notna(spd) else None,
        timetable_km=round(float(np.median(d["tt_km"])), 1) if d["tt_km"] else None,
        physical_graph_release="graph_v1_3/open + G5 + G6"))
    hourly.append(dict(from_station=a, to_station=b,
                       **{f"h{h:02d}": d["hours"].get(h, 0) for h in range(24)}))
    if p:
        for u, v in zip(p, p[1:]):
            edge_trains[(u, v) if u < v else (v, u)].add((a, b))

se = pd.DataFrame(rows).sort_values("n_trains", ascending=False)
se.to_csv(OUT / "service_edges_directed_2024.csv", index=False)
pd.DataFrame(hourly).to_csv(OUT / "service_hourly_2024.csv", index=False)

# per physical edge: how many trains run over it
pair_n = {(r.from_station, r.to_station): r.n_trains for r in se.itertuples()}
erows = []
for u, v, d in G.edges(data=True):
    k = (u, v) if u < v else (v, u)
    served = edge_trains.get(k, set())
    erows.append(dict(edge_id=d["eid"], a=u, b=v, name=f"{nm[u]} - {nm[v]}",
                      km=round(d["km"], 3), origin=d["origin"],
                      service_load_2024=sum(pair_n.get(x, 0) for x in served),
                      service_direct_2024=pair_n.get((u, v), 0) + pair_n.get((v, u), 0)))
ed = pd.DataFrame(erows).sort_values("service_load_2024", ascending=False)

# ---------------------------------------------------------------- compare with 2017
old = pd.read_csv(ROOT / "03_graph_construction/service_layer_v1_3/open/"
                  "service_edges_directed.csv")
old_pairs = set(zip(old.from_station, old.to_station))
new_pairs = set(zip(se.from_station, se.to_station))
old_edge = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/edges.csv")
old_load = dict(zip(old_edge.edge_id, old_edge.service_load))
ed["service_load_2017"] = ed.edge_id.map(old_load)
ed.to_csv(OUT / "edge_service_2024.csv", index=False)
cmp_ = ed.dropna(subset=["service_load_2017"])
newly = ed[(ed.service_load_2024 > 0) & (ed.service_load_2017.fillna(0) == 0)]
lost = ed[(ed.service_load_2024 == 0) & (ed.service_load_2017.fillna(0) > 0)]

rep = dict(
    experiment="E-705 / gap G15", physical_graph=gmeta, thresholds=TH,
    trains=len(trains_used), stop_rows=len(r24), stop_rows_unmapped=unmapped_rows,
    directed_pairs=len(se), undirected_pairs=len({tuple(sorted(x)) for x in new_pairs}),
    pairs_served_both_directions=sum(1 for a, b in new_pairs if (b, a) in new_pairs) // 2,
    both_in_physical_graph_share=round(se.both_in_physical_graph.mean(), 4),
    direct_physical_edge_share=round(se.is_direct_physical_edge.mean(), 4),
    resolved_share=round(se.physical_path_km.notna().mean(), 4),
    pairs_with_runtime=int((se.n_runtime_obs > 0).sum()),
    observed_speed_kmph_median=round(float(se.observed_speed_kmph.median()), 2),
    edges_with_service_2024=int((ed.service_load_2024 > 0).sum()),
    edges_with_service_2024_share=round((ed.service_load_2024 > 0).mean(), 4),
    km_with_service_2024_share=round(ed.loc[ed.service_load_2024 > 0, "km"].sum()
                                     / ed.km.sum(), 4),
    repaired_edges_carrying_trains=int((ed[ed.origin != "v1.3"].service_load_2024 > 0).sum()),
    repaired_edges=int((ed.origin != "v1.3").sum()),
    vs_2017=dict(
        pairs_2017=len(old_pairs), pairs_2024=len(new_pairs),
        pairs_only_2024=len(new_pairs - old_pairs), pairs_only_2017=len(old_pairs - new_pairs),
        pairs_in_both=len(new_pairs & old_pairs),
        spearman_edge_load=round(float(cmp_[["service_load_2024", "service_load_2017"]]
                                       .corr("spearman").iloc[0, 1]), 3),
        edges_newly_served=len(newly), edges_newly_served_km=round(float(newly.km.sum()), 1),
        edges_no_longer_served=len(lost), edges_no_longer_served_km=round(float(lost.km.sum()), 1)),
    busiest=ed.head(10)[["name", "service_load_2024", "origin"]].to_dict("records"),
    newly_served_top=newly.head(10)[["name", "km", "service_load_2024",
                                     "origin"]].to_dict("records"))
json.dump(rep, open(OUT / "E-705_report.json", "w"), indent=2, default=str)
newly.to_csv(OUT / "edges_newly_served_2024.csv", index=False)
lost.to_csv(OUT / "edges_no_longer_served_2024.csv", index=False)
print(json.dumps({k: v for k, v in rep.items()
                  if k not in ("busiest", "newly_served_top", "physical_graph")},
                 indent=1, default=str))
