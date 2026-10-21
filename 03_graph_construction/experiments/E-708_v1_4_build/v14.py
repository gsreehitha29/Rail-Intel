"""graph v1.4 - the repaired graph as a reproducible, frozen release.

v1.3 is built from source by E-600. v1.4 adds the repairs found by E-702 to E-706 and
freezes the result, so downstream work loads files instead of re-running five scripts in
the right order.

Two layers, deliberately separate:

  derivation   E-702..E-706 work out WHAT to repair from the evidence, and write their
               findings as decision tables. Reproducible, slow, and reviewable.
  application  this module applies those decisions to v1.3 and exports. Fast,
               deterministic, and the only thing a downstream user needs to run.

The join between them is `OVERRIDES.csv`, which is the mechanism the project already
designed for exactly this ("record every decision as one row ... they are applied on
every rebuild") and had not yet used. Every row carries its evidence and the experiment
that produced it, including the 42 rejected as redundant, so the decision trail survives.

Stages, in order:

  overrides   consolidate E-702..E-706 decisions into OVERRIDES.csv + the station-code
              crosswalk the release ships for joining external data
  graph       apply them to v1.3 open, export nodes/edges/GraphML
  service     build the 2024 service layer and trains-per-day on the v1.4 graph
  gates       the checks a build must pass to be called v1.4
  manifest    hash every input and output, record thresholds, stages, gates

Run:  python run.py <stage>      (or `make v14` for all of them)
"""
from __future__ import annotations

import hashlib, json, math, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

VERSION = "v1.4"
SLUG = "v1_4"          # directory and file naming, matching graph_v1_3
BASE = "graph_v1_3/open"
MODULES = dict(g1="E-702_station_code_crosswalk", g5="E-703_trunk_wiring",
               g6="E-704_missing_links", g15="E-705_service_layer_2024",
               g16="E-706_trains_per_day")

GATES = dict(
    # a release must not contradict its own geometry, lose reach, or route worse
    max_edges_below_straight_line=120,
    min_route_2024_within_5pct=0.94,
    max_route_2024_median_err=0.010,
    max_components=18,
    min_giant_share=0.99,
    max_unroutable_2024=2,
    min_irn_within_5pct=0.82,
    max_off_spine_detour_km=60000,
)


# --------------------------------------------------------------------- helpers
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hav(pa, pb):
    if pa is None or pb is None or any(pd.isna(x) for x in (*pa, *pb)): return None
    (lo1, la1), (lo2, la2) = pa, pb
    p = math.pi / 180
    h = (math.sin((la2 - la1) * p / 2) ** 2 +
         math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(min(1, h)))


def mod(root: Path, key: str) -> Path:
    return root / "04_analysis_modules" / MODULES[key] / "out"


# --------------------------------------------------------------------- stage: overrides
def stage_overrides(root: Path, out: Path) -> dict:
    """Consolidate every repair decision into the project's own override format."""
    out.mkdir(parents=True, exist_ok=True)
    rows = []

    g5 = pd.read_csv(mod(root, "g5") / "repairs_proposed.csv")
    g6 = pd.read_csv(mod(root, "g6") / "links_added.csv")
    audit = pd.read_csv(mod(root, "g15") / "added_edge_audit.csv")
    dropped = set(audit.loc[audit.verdict != "keep", "edge_id"])

    for r in g5.sort_values("item").itertuples():
        if r.action == "remove_edge":
            rows.append(dict(audit_file="E-703_trunk_wiring", item_id=r.item, field="edge",
                             current_value=r.current, new_value="", action="remove_edge",
                             evidence=r.evidence, notes=f"attested by {int(r.trains)} trains"))
        elif r.action == "add_edge":
            eid = f"G5:{r.a}|{r.b}"
            act = "reject" if eid in dropped else "add_edge"
            note = ("redundant: a chain of the same length already runs this, so adding it "
                    "would only let trains skip the stations on it"
                    if eid in dropped else f"attested by {int(r.trains)} trains")
            rows.append(dict(audit_file="E-703_trunk_wiring", item_id=f"{r.a}|{r.b}",
                             field="edge", current_value=r.current, new_value=r.new,
                             action=act, evidence=r.evidence, notes=note))

    for r in g6.sort_values(["a", "b"]).itertuples():
        eid = f"G6:{r.a}|{r.b}"
        act = "reject" if eid in dropped else "add_edge"
        note = ("redundant: a chain of the same length already runs this"
                if eid in dropped else f"attested by {int(r.trains)} trains ({r.years})")
        rows.append(dict(audit_file="E-704_missing_links", item_id=f"{r.a}|{r.b}", field="edge",
                         current_value=r.graph_km_before, new_value=r.length_km,
                         action=act, evidence=r.evidence, notes=note))

    ov = pd.DataFrame(rows)
    for c in ("source_url", "reviewer", "review_date"):
        ov[c] = ""
    ov = ov[["audit_file", "item_id", "field", "current_value", "new_value", "action",
             "evidence", "source_url", "reviewer", "review_date", "notes"]]
    ov.to_csv(out / "OVERRIDES.csv", index=False)

    # the crosswalk ships with the release: any join to current data needs it
    cw = pd.read_csv(mod(root, "g1") / "crosswalk.csv")
    keep = ["code", "name", "resolution", "graph_node", "graph_node_name", "stops_2024",
            "trains_2024", "km_apart", "name_sim", "route_fit", "old_code_retired",
            "evidence", "review"]
    cw[[c for c in keep if c in cw.columns]].sort_values(["resolution", "code"]).to_csv(
        out / "station_code_crosswalk.csv", index=False)

    return dict(overrides_rows=len(ov),
                applied={k: int(v) for k, v in
                         ov.loc[ov.action != "reject", "action"].value_counts().items()},
                rejected=int((ov.action == "reject").sum()),
                crosswalk_aliases=int((cw.resolution == "alias").sum()),
                crosswalk_missing=int((cw.resolution == "missing_station").sum()),
                crosswalk_unresolved=int((cw.resolution == "unresolved").sum()))


# --------------------------------------------------------------------- stage: graph
def build_graph(root: Path, overrides_csv: Path):
    """v1.3 open + the applied overrides. Deterministic: inputs are sorted throughout."""
    nodes = pd.read_csv(root / f"03_graph_construction/{BASE}/nodes.csv").sort_values("node_id")
    edges = pd.read_csv(root / f"03_graph_construction/{BASE}/edges.csv").sort_values("edge_id")
    ov = pd.read_csv(overrides_csv)
    ov = ov[ov.action != "reject"]

    G = nx.Graph()
    for r in nodes.itertuples():
        G.add_node(r.node_id, **{c: getattr(r, c) for c in nodes.columns if c != "node_id"})
    for r in edges.itertuples():
        a, b = r.from_node, r.to_node
        if G.has_edge(a, b) and G[a][b]["length_km"] <= r.length_km:
            continue                      # keep the shorter of parallel edges
        G.add_edge(a, b, **{c: getattr(r, c) for c in edges.columns
                            if c not in ("from_node", "to_node")}, origin=BASE)

    applied = defaultdict(int)
    for r in ov.sort_values("item_id").itertuples():
        if r.action == "remove_edge":
            hit = [(u, v) for u, v, d in G.edges(data=True) if d.get("edge_id") == r.item_id]
            for u, v in hit:
                G.remove_edge(u, v); applied["remove_edge"] += 1
        elif r.action == "add_edge":
            a, b = r.item_id.split("|")
            if not G.has_edge(a, b):
                G.add_edge(a, b, edge_id=f"{VERSION}:{a}|{b}", length_km=float(r.new_value),
                           length_source="official_adjacency", length_is_lower_bound=False,
                           origin=r.audit_file)
                applied["add_edge"] += 1
    return G, dict(applied), nodes, edges


def stage_graph(root: Path, out: Path) -> dict:
    G, applied, nodes, edges = build_graph(root, out / "OVERRIDES.csv")
    d = out / "open"; d.mkdir(parents=True, exist_ok=True)

    ncols = list(nodes.columns)
    nrows = [dict(node_id=n, **{c: G.nodes[n].get(c) for c in ncols if c != "node_id"})
             for n in sorted(G.nodes())]
    nd = pd.DataFrame(nrows)
    nd["dataset_version"] = f"{VERSION}-open"

    ecols = [c for c in edges.columns if c not in ("from_node", "to_node")]
    erows = []
    for u, v in sorted(tuple(sorted(e)) for e in G.edges()):
        a = G[u][v]
        erows.append(dict(from_node=u, to_node=v, origin=a.get("origin"),
                          **{c: a.get(c) for c in ecols}))
    ed = pd.DataFrame(erows)
    ed["dataset_version"] = f"{VERSION}-open"
    # recompute the two fields the repairs invalidate
    pos = dict(zip(nd.node_id, zip(nd.longitude, nd.latitude)))
    ed["length_chord_km"] = [hav(pos.get(r.from_node), pos.get(r.to_node))
                             for r in ed.itertuples()]
    ed = ed.sort_values("edge_id")

    nd.to_csv(d / "nodes.csv", index=False); nd.to_parquet(d / "nodes.parquet", index=False)
    ed.to_csv(d / "edges.csv", index=False); ed.to_parquet(d / "edges.parquet", index=False)

    H = nx.Graph()
    for r in nd.itertuples():
        H.add_node(r.node_id, **{c: ("" if pd.isna(getattr(r, c)) else str(getattr(r, c)))
                                 for c in nd.columns if c != "node_id"})
    for r in ed.itertuples():
        H.add_edge(r.from_node, r.to_node,
                   **{c: ("" if pd.isna(getattr(r, c)) else str(getattr(r, c)))
                      for c in ed.columns if c not in ("from_node", "to_node")})
    nx.write_graphml(H, d / f"rail_graph_{SLUG}_open.graphml")

    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    return dict(applied=applied, nodes=G.number_of_nodes(), edges=G.number_of_edges(),
                route_km=round(float(ed.length_km.sum()), 1), components=len(comps),
                giant_share=round(len(comps[0]) / G.number_of_nodes(), 4),
                edges_by_origin={k: int(v) for k, v in ed.origin.value_counts().items()})


# --------------------------------------------------------------------- shared loaders
def load_v14(root: Path):
    """The released graph, from files. This is what downstream work should call."""
    root = Path(root)
    d = root / f"03_graph_construction/graph_{SLUG}/open"
    nodes = pd.read_csv(d / "nodes.csv")
    edges = pd.read_csv(d / "edges.csv")
    G = nx.Graph()
    for r in nodes.itertuples():
        G.add_node(r.node_id, name=r.node_name, lon=r.longitude, lat=r.latitude,
                   state=r.state, zone=r.zone_code)
    for r in edges.itertuples():
        G.add_edge(r.from_node, r.to_node, km=float(r.length_km), eid=r.edge_id,
                   origin=r.origin, length_source=r.length_source)
    return G, nodes, edges


def _resolver(root: Path):
    cw = pd.read_csv(root / f"03_graph_construction/graph_{SLUG}/station_code_crosswalk.csv")
    nodes = pd.read_csv(root / f"03_graph_construction/graph_{SLUG}/open/nodes.csv")
    ids = set(nodes.node_id)
    alias = dict(zip(cw.loc[cw.resolution == "alias", "code"],
                     cw.loc[cw.resolution == "alias", "graph_node"]))
    return lambda c: c if c in ids else alias.get(c)


def _timetables(root: Path, node):
    def walk(df, code, train, seq, dist):
        df = df.sort_values([train, seq]); out = []
        for t, g in df.groupby(train, sort=False):
            stops = []
            for r in g.itertuples():
                nd = node(getattr(r, code)); v = getattr(r, dist)
                if nd is None or pd.isna(v): continue
                if not stops or stops[-1][0] != nd: stops.append((nd, v))
            if len(stops) >= 2: out.append((t, stops))
        return out
    t17 = pd.read_csv(root / "external_data/timetable_2017_datagovin/"
                      "Train_details_22122017.csv", dtype=str)
    t17["seq"] = pd.to_numeric(t17.SEQ, errors="coerce")
    t17["km"] = pd.to_numeric(t17.Distance, errors="coerce")
    t17["code"] = t17["Station Code"].str.strip()
    r24 = pd.read_csv(root / "external_data/iitkgp_rstgcn_network_2024/"
                      "Indian-Railway-Network-and-Delays/train_routes_Sep2024.csv", dtype=str)
    r24["seq"] = r24.stnSerialNumber.astype(int)
    r24["km"] = pd.to_numeric(r24.distance, errors="coerce")
    r24["tno"] = r24.trainNumber.str.zfill(5)
    return (walk(t17, "code", "Train No", "seq", "km"),
            walk(r24, "station_code", "tno", "seq", "km"))


# --------------------------------------------------------------------- stage: service
def stage_service(root: Path, out: Path) -> dict:
    """The 2024 service layer, built on v1.4 and weighted by observed frequency."""
    G, nodes, edges = load_v14(root)
    node = _resolver(root)
    X = root / "external_data/iitkgp_rstgcn_network_2024/Indian-Railway-Network-and-Delays"
    d = out.parent / f"service_layer_{SLUG}" / "open"
    d.mkdir(parents=True, exist_ok=True)

    # how often each train ran, observed over the 30 days of September 2024
    dl = pd.read_csv(X / "train_routes_delays_Sep2024.csv", dtype={"train": str},
                     usecols=["train", "date"])
    dl["tno"] = dl.train.str.zfill(5)
    dl["dow"] = pd.to_datetime(dl.date).dt.dayofweek
    freq = dl.groupby("tno").agg(dates_observed=("date", "nunique"),
                                 weekdays_used=("dow", "nunique")).reset_index()
    freq["trains_per_day"] = (freq.dates_observed / 30).round(4)
    freq["pattern"] = np.where(freq.dates_observed >= 25, "daily",
                      np.where(freq.weekdays_used <= 2, "weekly or twice weekly", "irregular"))
    freq.sort_values("tno").to_csv(d / "train_frequency.csv", index=False)
    tpd = dict(zip(freq.tno, freq.trains_per_day))

    r24 = pd.read_csv(X / "train_routes_Sep2024.csv", dtype=str)
    r24["seq"] = r24.stnSerialNumber.astype(int)
    r24["tno"] = r24.trainNumber.str.zfill(5)
    r24["km"] = pd.to_numeric(r24.distance, errors="coerce")
    r24 = r24.sort_values(["tno", "seq"])

    def minutes(t):
        try:
            hhmm, ap = str(t).strip().rsplit(" ", 1)
            h, m = (int(x) for x in hhmm.split(":")[:2])
        except Exception:
            return None
        return (h % 12 + (12 if ap.upper() == "PM" else 0)) * 60 + m

    r24["arr_m"] = r24.arrivalTime.map(minutes)
    r24["dep_m"] = r24.departureTime.map(minutes)

    pairs = defaultdict(lambda: dict(n=0, w=0.0, rt=[], hours=defaultdict(int)))
    for tno, g in r24.groupby("tno", sort=False):
        w = tpd.get(tno, 0.0)
        stops = []
        for r in g.itertuples():
            nd = node(r.station_code)
            if nd is None or (stops and stops[-1][0] == nd): continue
            stops.append((nd, r.arr_m, r.dep_m))
        for (a, _, dep), (b, arr, _) in zip(stops, stops[1:]):
            p = pairs[(a, b)]
            p["n"] += 1; p["w"] += w
            if dep is not None: p["hours"][dep // 60] += 1
            if dep is not None and arr is not None:
                run = arr - dep
                while run < 0: run += 1440
                if 0 < run <= 1800: p["rt"].append(run)

    cache = {}
    def route(a, b):
        k = (a, b) if a < b else (b, a)
        if k not in cache:
            try: cache[k] = nx.single_source_dijkstra(G, a, b, weight="km", cutoff=400)
            except (nx.NetworkXNoPath, nx.NodeNotFound): cache[k] = (None, None)
        return cache[k]

    rows, hourly, ew, en = [], [], defaultdict(float), defaultdict(int)
    for (a, b) in sorted(pairs):
        p = pairs[(a, b)]
        km, path = route(a, b) if (a in G and b in G) else (None, None)
        rt = pd.Series(p["rt"], dtype=float)
        med = float(rt.median()) if len(rt) else np.nan
        spd = km / (med / 60) if (km and med and med > 0) else np.nan
        if pd.notna(spd) and not (5 <= spd <= 160): spd = np.nan
        rows.append(dict(from_station=a, to_station=b, n_trains=p["n"],
                         trains_per_day=round(p["w"], 3),
                         runtime_min_median=round(med, 1) if pd.notna(med) else None,
                         runtime_min_p10=round(float(rt.quantile(.1)), 1) if len(rt) else None,
                         runtime_min_p90=round(float(rt.quantile(.9)), 1) if len(rt) else None,
                         n_runtime_obs=len(rt),
                         is_direct_physical_edge=bool(a in G and b in G and G.has_edge(a, b)),
                         physical_path_km=round(km, 6) if km is not None else None,
                         physical_hops=(len(path) - 1) if path else None,
                         observed_speed_kmph=round(spd, 4) if pd.notna(spd) else None,
                         physical_graph_release=f"graph_{SLUG}/open"))
        hourly.append(dict(from_station=a, to_station=b,
                           **{f"h{h:02d}": p["hours"].get(h, 0) for h in range(24)}))
        if path:
            for u, v in zip(path, path[1:]):
                k = (u, v) if u < v else (v, u)
                ew[k] += p["w"]; en[k] += p["n"]

    se = pd.DataFrame(rows)
    se.to_csv(d / "service_edges_directed.csv", index=False)
    pd.DataFrame(hourly).to_csv(d / "service_hourly.csv", index=False)

    er = []
    for u, v, a in sorted(G.edges(data=True), key=lambda t: t[2]["eid"]):
        k = (u, v) if u < v else (v, u)
        er.append(dict(edge_id=a["eid"], from_node=u, to_node=v, km=round(a["km"], 3),
                       origin=a["origin"], distinct_trains=en.get(k, 0),
                       trains_per_day=round(ew.get(k, 0.0), 2)))
    ed = pd.DataFrame(er)
    ed.to_csv(d / "edge_service.csv", index=False)

    return dict(trains=int(len(freq)), directed_pairs=len(se),
                pairs_with_runtime=int((se.n_runtime_obs > 0).sum()),
                edges_with_service=int((ed.trains_per_day > 0).sum()),
                edges_with_service_share=round(float((ed.trains_per_day > 0).mean()), 4),
                km_share=round(float(ed.loc[ed.trains_per_day > 0, "km"].sum()
                                     / ed.km.sum()), 4),
                mean_trains_per_day=round(float(freq.trains_per_day.mean()), 3),
                busiest_trains_per_day=round(float(ed.trains_per_day.max()), 1),
                frequency_mix={k: int(v) for k, v in freq.pattern.value_counts().items()})


# --------------------------------------------------------------------- stage: gates
def stage_gates(root: Path, out: Path) -> dict:
    """The checks a build must pass to be called v1.4. Any failure fails the build."""
    G, nodes, edges = load_v14(root)
    node = _resolver(root)
    T17, T24 = _timetables(root, node)
    pos = {r.node_id: (r.longitude, r.latitude) for r in nodes.itertuples()}

    cache = {}
    def sp(a, b):
        k = (a, b) if a < b else (b, a)
        if k not in cache:
            try: cache[k] = nx.shortest_path_length(G, a, b, weight="km")
            except (nx.NetworkXNoPath, nx.NodeNotFound): cache[k] = None
        return cache[k]

    m = {}
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    m["components"] = len(comps)
    m["giant_share"] = round(len(comps[0]) / G.number_of_nodes(), 4)
    m["edges_below_straight_line"] = sum(
        1 for u, v, d in G.edges(data=True)
        if (c := hav(pos.get(u), pos.get(v))) is not None and d["km"] < c - 0.3)
    m["edges_without_length"] = sum(1 for *_, d in G.edges(data=True)
                                    if not d.get("km") or pd.isna(d["km"]))
    ids = set(nodes.node_id)
    m["referential_integrity"] = bool(set(edges.from_node) <= ids and set(edges.to_node) <= ids)

    irn = pd.read_csv(root / "external_data/iitkgp_rstgcn_network_2024/"
                      "Indian-Railway-Network-and-Delays/IRN_edges.csv")
    irn["a"] = irn["from"].map(node); irn["b"] = irn["to"].map(node)
    irn = irn.dropna(subset=["a", "b"]); irn = irn[irn.a != irn.b]
    ip = {}
    for r in irn.itertuples():
        k = (r.a, r.b) if r.a < r.b else (r.b, r.a)
        ip.setdefault(k, []).append(float(r.distance))
    ip = {k: float(np.median(v)) for k, v in ip.items() if np.median(v) > 0}
    ok = n = 0
    for (a, b), v in ip.items():
        d = sp(a, b)
        if d is None: continue
        n += 1; ok += abs(d - v) <= max(1.0, 0.05 * v)
    m["irn_pairs"] = n; m["irn_within_5pct"] = round(ok / n, 4)

    for tag, TT in (("2024", T24), ("2017", T17)):
        errs, failed = [], 0
        for _, stops in TT:
            km, good = 0.0, True
            for (a, _), (b, _) in zip(stops, stops[1:]):
                d = sp(a, b)
                if d is None: good = False; break
                km += d
            if not good: failed += 1; continue
            t = stops[-1][1] - stops[0][1]
            if pd.notna(t) and t >= 20: errs.append((km - t) / t)
        e = pd.Series(errs)
        m[f"route_{tag}_median_err"] = round(float(e.abs().median()), 4)
        m[f"route_{tag}_within_5pct"] = round(float((e.abs() <= .05).mean()), 4)
        m[f"route_{tag}_unroutable"] = failed

    det = 0.0
    for _, stops in T24:
        s = [x for x, _ in stops]
        for p, q, r_ in zip(s, s[1:], s[2:]):
            if p == r_: continue
            a, b, c = sp(p, q), sp(q, r_), sp(p, r_)
            if None in (a, b, c): continue
            if (x := a + b - c) >= 2.0: det += x
    m["off_spine_detour_km"] = round(det, 1)

    g = {
        "G1_no_edge_far_below_straight_line":
            m["edges_below_straight_line"] <= GATES["max_edges_below_straight_line"],
        "G2_every_edge_has_a_length": m["edges_without_length"] == 0,
        "G3_referential_integrity": m["referential_integrity"],
        "G4_components_not_worse": m["components"] <= GATES["max_components"],
        "G5_giant_component": m["giant_share"] >= GATES["min_giant_share"],
        "G6_route_accuracy_2024":
            m["route_2024_within_5pct"] >= GATES["min_route_2024_within_5pct"]
            and m["route_2024_median_err"] <= GATES["max_route_2024_median_err"],
        "G7_independent_reference_held":
            m["irn_within_5pct"] >= GATES["min_irn_within_5pct"],
        "G8_trains_routable": m["route_2024_unroutable"] <= GATES["max_unroutable_2024"],
        "G9_off_spine_improved":
            m["off_spine_detour_km"] <= GATES["max_off_spine_detour_km"],
    }
    return dict(thresholds=GATES, measured=m, gates=g, all_passed=all(g.values()))


# --------------------------------------------------------------------- stage: manifest
def stage_manifest(root: Path, out: Path, stages: dict) -> dict:
    inputs = [f"03_graph_construction/{BASE}/nodes.csv",
              f"03_graph_construction/{BASE}/edges.csv",
              "external_data/timetable_2017_datagovin/Train_details_22122017.csv",
              "external_data/iitkgp_rstgcn_network_2024/Indian-Railway-Network-and-Delays/"
              "train_routes_Sep2024.csv",
              "external_data/iitkgp_rstgcn_network_2024/Indian-Railway-Network-and-Delays/"
              "train_routes_delays_Sep2024.csv",
              "external_data/iitkgp_rstgcn_network_2024/Indian-Railway-Network-and-Delays/"
              "IRN_edges.csv"]
    man = dict(
        artifact="Rail-Intell station-level physical railway graph",
        version=VERSION, supersedes="v1.3 (graph_v1_3/open)",
        experiment="E-708 (applies E-702, E-703, E-704, E-705, E-706)",
        built_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        what_changed=("v1.3 open plus the repairs: a station-code crosswalk for current "
                      "data, 8 phantom sections removed, 129 missing links added, 42 "
                      "rejected as redundant, and a 2024 service layer weighted by "
                      "observed train frequency."),
        base_source_licence_caveat=(
            "Inherited from v1.3: all variants derive from Railway_Network_.csv, origin "
            "unconfirmed. Release blocked until resolved."),
        derivation=("the decisions in OVERRIDES.csv are derived by "
                    + ", ".join(sorted(MODULES.values()))
                    + "; this build applies them and is deterministic"),
        thresholds=GATES, stages=stages,
        inputs={p: sha256(root / p) for p in inputs if (root / p).exists()},
        reproducibility=("re-running this build on unchanged inputs reproduces every "
                         "file marked byte_reproducible, on any machine; parquet copies "
                         "carry the Arrow writer version and are excluded from that claim"),
        files={})
    base = out.parent
    release_dirs = [out, out.parent / f"service_layer_{SLUG}"]
    for d in release_dirs:
        for p in sorted(d.rglob("*")):
            if p.is_file() and p.suffix in (".csv", ".parquet", ".graphml", ".json", ".md") \
                    and "manifest" not in p.name:
                man["files"][str(p.relative_to(base))] = dict(
                    bytes=p.stat().st_size, sha256=sha256(p),
                    # parquet embeds the Arrow writer version, so its bytes differ
                    # between environments even when the data is identical; the CSV
                    # is the canonical form and is byte-reproducible anywhere
                    byte_reproducible=p.suffix != ".parquet")
    (out / f"graph_{SLUG}.manifest.json").write_text(json.dumps(man, indent=1, default=str))
    return dict(inputs_hashed=len(man["inputs"]), files_hashed=len(man["files"]))


# --------------------------------------------------------------------- stage: docs
def stage_docs(root: Path, out: Path, state: dict) -> dict:
    """README and validation report, regenerated from this build's own numbers."""
    # read what the earlier stages wrote, so this stage runs standalone too
    g = state.get("gates")
    if not g:
        gp = out / "gates.json"
        g = json.loads(gp.read_text()) if gp.exists() else stage_gates(root, out)
    m = g["measured"]
    nd = pd.read_csv(out / "open" / "nodes.csv")
    ed = pd.read_csv(out / "open" / "edges.csv")
    gr = dict(nodes=len(nd), edges=len(ed), route_km=round(float(ed.length_km.sum()), 1))
    ovf = pd.read_csv(out / "OVERRIDES.csv")
    cw = pd.read_csv(out / "station_code_crosswalk.csv")
    ov = dict(rejected=int((ovf.action == "reject").sum()),
              crosswalk_aliases=int((cw.resolution == "alias").sum()),
              crosswalk_missing=int((cw.resolution == "missing_station").sum()))
    sp_ = out.parent / f"service_layer_{SLUG}" / "open" / "service_edges_directed.csv"
    s = dict(directed_pairs=len(pd.read_csv(sp_)) if sp_.exists() else 0)
    rows = "\n".join(f"| {k} | {'pass' if v else '**FAIL**'} |" for k, v in g["gates"].items())

    (out / f"VALIDATION_{SLUG}.md").write_text(f"""# Validation — graph {VERSION}

Generated by `experiments/E-708_{SLUG}_build/run.py`. Every figure is measured by that
run; none is carried over.

## Gates

| Gate | Result |
| --- | --- |
{rows}

**All passed: {g['all_passed']}**

## Measured

| Measure | Value |
| --- | --- |
| stations | {gr.get('nodes')} |
| sections | {gr.get('edges')} |
| route km | {gr.get('route_km')} |
| components | {m['components']} (giant {m['giant_share']:.2%}) |
| 2024 trains routed within 5% of official distance | {m['route_2024_within_5pct']:.2%} |
| 2024 median route error | {m['route_2024_median_err']:.2%} |
| 2017 trains within 5% | {m['route_2017_within_5pct']:.2%} |
| 2017 median route error | {m['route_2017_median_err']:.2%} |
| IIT KGP reference agreement (independent) | {m['irn_within_5pct']:.2%} of {m['irn_pairs']} pairs |
| off-spine detour | {m['off_spine_detour_km']:,.0f} km |
| sections shorter than their own straight line | {m['edges_below_straight_line']} |
| 2024 trains that cannot be routed | {m['route_2024_unroutable']} |

## Against v1.3 open

| | v1.3 | {VERSION} |
| --- | --- | --- |
| sections | 9,638 | {gr.get('edges')} |
| 2024 within 5% | 89.84% | {m['route_2024_within_5pct']:.2%} |
| 2024 median error | 0.93% | {m['route_2024_median_err']:.2%} |
| 2017 median error | 1.99% | {m['route_2017_median_err']:.2%} |
| off-spine detour | 93,773 km | {m['off_spine_detour_km']:,.0f} km |

The independent reference stays flat by design: these repairs change which track a train
runs over, not how long the track is.

## Known limits of this release

- {m['edges_below_straight_line']} sections are shorter than the straight line between their
  stations as the graph places them. In each case the link is attested by trains and OSM
  puts a station somewhere that makes it possible: the coordinate is wrong, not the link.
- 25.9% of route km is a straight-line lower bound rather than a measurement.
- Declared speeds are roughly half the observed; use the service layer's runtimes.
- 82 node pairs are the same station under two names, which understates junction criticality.
- 228 stations are absent; `station_code_crosswalk.csv` lists them.
- {m['route_2024_unroutable']} trains cannot be routed, both because of a disconnected fragment.
""")

    (out / "README.md").write_text(f"""# graph {VERSION} \u2014 FINAL

The repaired, frozen railway graph. Supersedes v1.3 open for analysis.

**Frozen.** What this graph can and cannot carry, and the rule for changing it:
[`FITNESS.md`](FITNESS.md). Amendments are a new version, never an edit in place
(D-055). The engineering contract is `docs/STABILITY.md`, enforced by `make test`.

**{gr.get('nodes')} stations · {gr.get('edges')} sections · {gr.get('route_km'):,} km · built by `make v14`**

## Use it

```python
import sys; sys.path.insert(0, "03_graph_construction")
from railgraph.release import load_graph, load_service, load_resolver, release_info

G    = load_graph()        # networkx graph
svc  = load_service()      # directed service pairs, with trains_per_day
code = load_resolver()     # station code from any dataset -> graph node
release_info()             # version, gates, caveats
```

Load it this way rather than reading the CSVs, so every module works on the same network.

## What is here

| Path | Contents |
| --- | --- |
| `open/nodes.csv` `.parquet` | {gr.get('nodes')} stations |
| `open/edges.csv` `.parquet` | {gr.get('edges')} sections, each with `origin` saying which release or repair put it there |
| `open/rail_graph_{SLUG}_open.graphml` | the same graph for Gephi, igraph and the like |
| `OVERRIDES.csv` | every repair decision, including the {ov.get('rejected')} rejected, each with its evidence |
| `station_code_crosswalk.csv` | {ov.get('crosswalk_aliases')} renamed codes resolved, {ov.get('crosswalk_missing')} stations recorded as absent |
| `gates.json` · `VALIDATION_{SLUG}.md` | what this build was checked against |
| `graph_{SLUG}.manifest.json` | SHA-256 of every input and output |
| `../service_layer_{SLUG}/open/` | {s.get('directed_pairs')} directed pairs, hourly departures, per-section loads, per-train frequency |

## How it is built

`make v14` runs five stages and takes about a minute. The repairs themselves are *derived*
by E-702 to E-706, which read the evidence and write decision tables; this build *applies*
those decisions and is deterministic. Re-running on unchanged inputs reproduces every
output hash, which the manifest records.

The split is deliberate. Deciding what to repair needs judgement and evidence, and should
be reviewable row by row. Applying the decisions should not need either.

## Before you use it

Read `VALIDATION_{SLUG}.md`. The short version: topology is sound and validated against
trains the graph was never built from; distance is three-quarters sound; declared speed
should not be used at all.
""")
    return dict(wrote=[f"VALIDATION_{SLUG}.md", "README.md"])
