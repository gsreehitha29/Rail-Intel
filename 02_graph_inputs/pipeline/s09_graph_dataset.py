"""
Stage 09 — assemble the cleaned, normalised, graph-ready dataset.

Everything produced by s01-s08 is *intermediate*: it still carries the source
vocabularies, the sentinel values and the unresolved node identities. This
stage applies the controlled vocabularies from config.py, resolves node
identity, constructs the physical edge list using the agreed approach, derives
the service layer, and writes one self-describing folder that Phase 3 builds
from.

Output: 02_graph_inputs/graph_dataset/
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
from config import (  # noqa: E402
    CLEANED_SCHEDULES, CLEANED_STATIONS, CLEANED_TRAINS, GRAPH_INPUT_VERSION,
    OUT_DIR, PHASE_DIR, banner, haversine_km,
)

DATASET_DIR = PHASE_DIR / "graph_dataset"
DATASET_DIR.mkdir(exist_ok=True)

# ---- decisions fixed by the finalised approach (see docs/GRAPH_HANDOFF_V2.md §4)
OFFSET_MAX_KM = 1.5          # placement tolerance for edge construction
MATCH_CONF = ("high", "medium")
MIN_EDGE_KM = 0.05           # floor for co-located stations
SERVICE_PATH_CUTOFF_KM = 300.0


def _load():
    return (
        pd.read_csv(OUT_DIR / "corridor_station_sequence.csv"),
        pd.read_csv(OUT_DIR / "nodes_junctions.csv"),
        pd.read_csv(OUT_DIR / "corridors_enriched.csv"),
        pd.read_csv(CLEANED_STATIONS),
        pd.read_csv(CLEANED_TRAINS),
    )


def build_stations(st: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({
        "station_code": st.station_code.astype(str).str.strip(),
        "station_name": st.station_name.map(config.clean_token),
        "zone_code": st.zone.map(config.zone_code),
        "zone_name": st.zone.map(config.zone_name),
        "state": st.state.map(config.normalize_state),
        "longitude": pd.to_numeric(st.longitude, errors="coerce"),
        "latitude": pd.to_numeric(st.latitude, errors="coerce"),
    })
    out["has_coordinates"] = out.longitude.notna() & out.latitude.notna()
    out["in_scope"] = ~out.state.isin(config.OUT_OF_SCOPE_STATES)
    # distinct codes sharing one coordinate -> at least one is mislocated
    k = (out.longitude.round(5).astype(str) + "," + out.latitude.round(5).astype(str))
    dup = k[out.has_coordinates].duplicated(keep=False)
    out["coordinate_shared"] = False
    out.loc[dup[dup].index, "coordinate_shared"] = True
    out["source"] = "railways-master/stations.json via cleaned_stations.csv"
    out["dataset_version"] = GRAPH_INPUT_VERSION
    return out.sort_values("station_code").reset_index(drop=True)


def build_corridors(corr: pd.DataFrame) -> pd.DataFrame:
    out = corr.copy()
    out["zone_code"] = out.railway_zone.map(config.zone_code)
    out["zone_name"] = out.railway_zone.map(config.zone_name)
    out["gauge_code"] = out.gauge.map(config.gauge_code)
    out["gauge_name"] = out.gauge.map(config.clean_token)
    out = out.drop(columns=["railway_zone", "gauge"])
    keep = [
        "corridor_id", "corridor_a", "corridor_b", "segment_count",
        "geodesic_length_km", "spine_length_km", "spine_coverage",
        "declared_track_length_km", "length_inflation_ratio",
        "gauge_code", "gauge_name", "zone_code", "zone_name",
        "speed_kmph", "no_of_lanes", "bridge_present", "tunnel_present",
        "declared_no_of_stations", "n_stations_found", "station_count_delta",
        "median_offset_km", "reconstruction_status", "n_components",
        "is_self_loop", "any_attribute_conflict", "zone_count",
        "speed_kmph_conflict", "gauge_conflict", "no_of_lanes_conflict",
        "railway_zone_conflict", "orientation", "source_file",
    ]
    out = out[[c for c in keep if c in out.columns]].copy()
    out["attr_complete"] = (
        out.gauge_code.notna() & out.zone_code.notna()
        & out.no_of_lanes.notna() & (out.no_of_lanes > 0)
        & ~out.gauge_conflict.fillna(False).astype(bool)
        & ~out.railway_zone_conflict.fillna(False).astype(bool)
        & ~out.no_of_lanes_conflict.fillna(False).astype(bool)
    )
    out["recon_clean"] = out.reconstruction_status.eq("clean_path")
    out["core_v2"] = out.attr_complete & out.gauge_code.eq("BG")
    out["core_v4"] = out.core_v2 & (out.recon_clean | (out.n_stations_found.fillna(0) < 2))
    out["dataset_version"] = GRAPH_INPUT_VERSION
    return out


def build_nodes(seq, nodes, stations, corr_clean):
    """Resolve node identity: station where confident, operational junction otherwise."""
    conf = nodes.match_confidence.isin(MATCH_CONF) & nodes.station_code.notna()
    jmap, jrows = {}, []
    for r in nodes.itertuples():
        if r.canonical_junction_name in jmap:
            continue
        if conf.loc[r.Index]:
            jmap[r.canonical_junction_name] = str(r.station_code).strip()
        else:
            jmap[r.canonical_junction_name] = "JN::" + str(r.canonical_junction_name)
            jrows.append(r)

    smeta = stations.set_index("station_code")
    placed = seq[seq.offset_km <= OFFSET_MAX_KM]
    ncorr = placed.groupby("station_code").corridor_id.nunique()

    rows = []
    for code in sorted(set(placed.station_code) | {v for v in jmap.values() if not v.startswith("JN::")}):
        m = smeta.loc[code] if code in smeta.index else None
        rows.append({
            "node_id": code, "node_type": "station", "station_code": code,
            "node_name": (m.station_name if m is not None else None),
            "longitude": (m.longitude if m is not None else None),
            "latitude": (m.latitude if m is not None else None),
            "zone_code": (m.zone_code if m is not None else None),
            "zone_name": (m.zone_name if m is not None else None),
            "state": (m.state if m is not None else None),
            "in_scope": bool(m.in_scope) if m is not None else True,
            "junction_class": None, "match_confidence": None,
            "match_method": None, "spatial_gap_km": np.nan,
            "n_corridors": int(ncorr.get(code, 0)),
            "coordinate_shared": bool(m.coordinate_shared) if m is not None else False,
        })
    for r in jrows:
        rows.append({
            "node_id": "JN::" + str(r.canonical_junction_name),
            "node_type": "operational_junction", "station_code": None,
            "node_name": r.canonical_junction_name,
            "longitude": r.longitude, "latitude": r.latitude,
            "zone_code": None, "zone_name": None, "state": None, "in_scope": True,
            "junction_class": r.junction_class,
            "match_confidence": r.match_confidence,
            "match_method": r.match_method,
            "spatial_gap_km": r.spatial_gap_km,
            "n_corridors": int(r.corridor_degree) if pd.notna(r.corridor_degree) else 0,
            "coordinate_shared": False,
        })
    out = pd.DataFrame(rows).drop_duplicates("node_id").reset_index(drop=True)

    # The station master records a zone for only about half its rows. A node
    # sitting on a corridor can inherit that corridor's zone; this is recorded
    # as inferred rather than stated, so it never masquerades as source data.
    out["zone_source"] = np.where(out.zone_code.notna(), "station_master", None)
    czone = corr_clean.set_index("corridor_id")[["zone_code", "zone_name"]]
    link = placed[["station_code", "corridor_id"]].merge(
        czone, left_on="corridor_id", right_index=True, how="left").dropna(subset=["zone_code"])
    by_station = link.groupby("station_code").zone_code.agg(
        lambda s: s.mode().iloc[0] if not s.mode().empty else None)
    jl = []
    for r in jrows:
        inc = corr_clean[(corr_clean.corridor_a == r.canonical_junction_name)
                         | (corr_clean.corridor_b == r.canonical_junction_name)]
        z = inc.zone_code.dropna()
        if len(z):
            jl.append(("JN::" + str(r.canonical_junction_name), z.mode().iloc[0]))
    infer = dict(by_station.dropna())
    infer.update(dict(jl))
    need = out.zone_code.isna()
    out.loc[need, "zone_code"] = out.loc[need, "node_id"].map(infer)
    filled = need & out.zone_code.notna()
    out.loc[filled, "zone_source"] = "corridor_inferred"
    out["zone_name"] = out.zone_code.map(config.ZONE_NAME)

    out["dataset_version"] = GRAPH_INPUT_VERSION
    return out, jmap


def build_edges(seq, corr_clean, jmap):
    """Physical station-to-station edges: corridor chains stitched at junctions."""
    placed = seq[seq.offset_km <= OFFSET_MAX_KM].sort_values(["corridor_id", "measure_km"])
    recs = []
    for cid, g in placed.groupby("corridor_id"):
        a, b = jmap.get(g.corridor_a.iloc[0]), jmap.get(g.corridor_b.iloc[0])
        codes = [a] + list(g.station_code) + [b]
        meas = [np.nan] + list(g.measure_km) + [np.nan]
        offs = [np.nan] + list(g.offset_km) + [np.nan]
        keep = [i for i, c in enumerate(codes) if c and (i == 0 or c != codes[i - 1])]
        codes = [codes[i] for i in keep]; meas = [meas[i] for i in keep]; offs = [offs[i] for i in keep]
        span = float(g.measure_km.iloc[-1] - g.measure_km.iloc[0])
        for i in range(len(codes) - 1):
            u, v = codes[i], codes[i + 1]
            if u == v:
                continue
            d = meas[i + 1] - meas[i]
            if np.isnan(d):   # a stitch edge: distance not directly measured
                d = np.nan
            recs.append({"corridor_id": cid, "u": u, "v": v, "length_km": d,
                         "is_stitch": bool(np.isnan(d)),
                         "offset_u": offs[i], "offset_v": offs[i + 1]})
    # corridors with no placed stations still connect their two junctions
    have = set(placed.corridor_id)
    cmap = corr_clean.set_index("corridor_id")
    for r in corr_clean.itertuples():
        if r.corridor_id in have:
            continue
        a, b = jmap.get(r.corridor_a), jmap.get(r.corridor_b)
        if a and b and a != b:
            recs.append({"corridor_id": r.corridor_id, "u": a, "v": b,
                         "length_km": r.geodesic_length_km, "is_stitch": True,
                         "offset_u": np.nan, "offset_v": np.nan})
    e = pd.DataFrame(recs)
    e = e[e.u != e.v].copy()
    e["key"] = [tuple(sorted(p)) for p in zip(e.u, e.v)]
    return e, cmap


def finalise_edges(e, cmap, nodes_df):
    """Collapse to a simple undirected graph, attach attributes and flags."""
    pos = nodes_df.set_index("node_id")[["longitude", "latitude"]]
    # fill stitch lengths with the great-circle distance between the two nodes
    need = e.length_km.isna()
    if need.any():
        lu = pos.reindex(e.loc[need, "u"]).to_numpy()
        lv = pos.reindex(e.loc[need, "v"]).to_numpy()
        e.loc[need, "length_km"] = haversine_km(lu[:, 0], lu[:, 1], lv[:, 0], lv[:, 1])
    e["length_km"] = e.length_km.astype(float)

    agg = e.groupby("key").agg(
        length_km=("length_km", "min"),
        length_km_max=("length_km", "max"),
        n_parallel_corridors=("corridor_id", "nunique"),
        corridor_id=("corridor_id", "first"),
        any_stitch=("is_stitch", "any"),
        offset_max=("offset_u", "max"),
    ).reset_index()
    agg["from_node"] = [k[0] for k in agg.key]
    agg["to_node"] = [k[1] for k in agg.key]
    agg = agg.drop(columns=["key"])

    a = cmap.reindex(agg.corridor_id)
    for col, name in [("gauge_code", "gauge_code"), ("gauge_name", "gauge_name"),
                      ("zone_code", "zone_code"), ("zone_name", "zone_name"),
                      ("speed_kmph", "speed_kmph"), ("no_of_lanes", "n_tracks"),
                      ("bridge_present", "bridge_present"), ("tunnel_present", "tunnel_present"),
                      ("reconstruction_status", "reconstruction_status"),
                      ("attr_complete", "attr_complete"), ("recon_clean", "recon_clean"),
                      ("core_v2", "core_v2"), ("core_v4", "core_v4")]:
        agg[name] = a[col].to_numpy()

    agg["is_colocated"] = agg.length_km < MIN_EDGE_KM
    agg["length_km"] = agg.length_km.clip(lower=MIN_EDGE_KM)
    agg["parallel_differs"] = (agg.length_km_max - agg.length_km).abs() > 1.0
    agg["edge_id"] = ["E" + str(i).zfill(6) for i in range(1, len(agg) + 1)]
    agg["dataset_version"] = GRAPH_INPUT_VERSION
    cols = ["edge_id", "from_node", "to_node", "length_km", "corridor_id",
            "gauge_code", "gauge_name", "zone_code", "zone_name", "speed_kmph",
            "n_tracks", "bridge_present", "tunnel_present",
            "n_parallel_corridors", "parallel_differs", "is_colocated",
            "any_stitch", "reconstruction_status", "attr_complete",
            "recon_clean", "core_v2", "core_v4", "dataset_version"]
    return agg[cols]


def build_service(edges_df, nodes_df):
    """Service layer: adjacency, frequency, run-time, and load projected onto L1."""
    sch = pd.read_csv(CLEANED_SCHEDULES, low_memory=False,
                      usecols=["train_number", "station_code", "stop_sequence",
                               "arrival", "departure", "day"])
    sch = sch.dropna(subset=["station_code", "stop_sequence"]).sort_values(
        ["train_number", "stop_sequence"])
    nxt = sch.groupby("train_number").shift(-1)

    # Run-time: (next arrival - this departure) wrapped into 24h. The `day`
    # column is unreliable (it runs to 12 on trains that finish in a day), so
    # it is deliberately not used.
    dep = pd.to_timedelta(sch.departure, errors="coerce").dt.total_seconds() / 60
    arr = pd.to_timedelta(nxt.arrival, errors="coerce").dt.total_seconds() / 60
    mins = (arr - dep) % 1440

    S = pd.DataFrame({"u": sch.station_code, "v": nxt.station_code,
                      "t": sch.train_number, "mins": mins}).dropna(subset=["v"])
    S = S[S.u != S.v].copy()
    S["key"] = [tuple(sorted(p)) for p in zip(S.u, S.v)]
    svc = S.groupby("key").agg(
        n_trains=("t", "nunique"),
        runtime_min_median=("mins", "median"),
        runtime_min_p10=("mins", lambda s: s.quantile(.10)),
        runtime_min_p90=("mins", lambda s: s.quantile(.90)),
    ).reset_index()
    svc["from_station"] = [k[0] for k in svc.key]
    svc["to_station"] = [k[1] for k in svc.key]

    G = nx.Graph()
    for r in edges_df.itertuples():
        G.add_edge(r.from_node, r.to_node, w=float(r.length_km), eid=r.edge_id)
    GN = set(G.nodes())
    svc["both_in_graph"] = [a in GN and b in GN for a, b in zip(svc.from_station, svc.to_station)]
    svc["is_direct_edge"] = [G.has_edge(a, b) for a, b in zip(svc.from_station, svc.to_station)]

    # project each service pair onto its physical path; credit every edge
    load = {}
    hops = {}
    todo = svc[svc.both_in_graph]
    for src, grp in todo.groupby("from_station"):
        try:
            dist, paths = nx.single_source_dijkstra(G, src, weight="w",
                                                    cutoff=SERVICE_PATH_CUTOFF_KM)
        except Exception:
            continue
        for r in grp.itertuples():
            p = paths.get(r.to_station)
            if not p:
                continue
            hops[r.key] = len(p) - 1
            for a, b in zip(p, p[1:]):
                eid = G[a][b]["eid"]
                load[eid] = load.get(eid, 0) + int(r.n_trains)
    svc["physical_hops"] = [hops.get(k, np.nan) for k in svc.key]
    svc = svc.drop(columns=["key"])
    svc["dataset_version"] = GRAPH_INPUT_VERSION
    svc = svc[["from_station", "to_station", "n_trains", "runtime_min_median",
               "runtime_min_p10", "runtime_min_p90", "both_in_graph",
               "is_direct_edge", "physical_hops", "dataset_version"]]

    direct = {}
    for r in svc.itertuples():
        if r.is_direct_edge and G.has_edge(r.from_station, r.to_station):
            direct[G[r.from_station][r.to_station]["eid"]] = int(r.n_trains)
    return svc, load, direct


def main():
    banner("STAGE 09 — CLEAN, NORMALISED GRAPH DATASET")
    seq, nodes, corr, st, tr = _load()

    stations = build_stations(st)
    corr_clean = build_corridors(corr)
    nodes_df, jmap = build_nodes(seq, nodes, stations, corr_clean)
    e_raw, cmap = build_edges(seq, corr_clean, jmap)
    edges = finalise_edges(e_raw, cmap, nodes_df)

    # keep only nodes that actually appear on an edge
    used = set(edges.from_node) | set(edges.to_node)
    nodes_df = nodes_df[nodes_df.node_id.isin(used)].reset_index(drop=True)

    svc, load, direct = build_service(edges, nodes_df)
    edges["service_direct"] = edges.edge_id.map(direct).fillna(0).astype(int)
    edges["service_load"] = edges.edge_id.map(load).fillna(0).astype(int)

    G = nx.Graph()
    G.add_nodes_from(nodes_df.node_id)
    for r in edges.itertuples():
        G.add_edge(r.from_node, r.to_node, w=float(r.length_km))
    deg = dict(G.degree())
    nodes_df["degree"] = nodes_df.node_id.map(deg).fillna(0).astype(int)
    nodes_df["is_dissolvable"] = (nodes_df.node_type.eq("operational_junction")
                                  & nodes_df.degree.eq(2))
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    cid = {n: i for i, c in enumerate(comps) for n in c}
    nodes_df["component_id"] = nodes_df.node_id.map(cid)
    nodes_df["in_giant_component"] = nodes_df.component_id.eq(0)

    seq_clean = seq.copy()
    seq_clean["used_for_edges"] = seq_clean.offset_km <= OFFSET_MAX_KM
    seq_clean["dataset_version"] = GRAPH_INPUT_VERSION

    stations.to_csv(DATASET_DIR / "stations.csv", index=False)
    corr_clean.to_csv(DATASET_DIR / "corridors.csv", index=False)
    seq_clean.to_csv(DATASET_DIR / "station_sequences.csv", index=False)
    nodes_df.to_csv(DATASET_DIR / "nodes.csv", index=False)
    edges.to_csv(DATASET_DIR / "edges.csv", index=False)
    svc.to_csv(DATASET_DIR / "service_edges.csv", index=False)

    lines = []
    def w(s=""):
        print(s); lines.append(s)
    w(f"GRAPH DATASET QA  ({GRAPH_INPUT_VERSION})")
    w("=" * 70)
    w("")
    w("-- NORMALISATION APPLIED --")
    w(f"zone vocabulary unified to (zone_code, zone_name)  : {stations.zone_code.nunique()} codes on nodes, "
      f"{corr_clean.zone_code.nunique()} on corridors")
    w("zone spellings corrected upstream in s02           : 4 "
      "(East Coast Railwa, Southen Railway, Westem Railway, and "
      "North Frontier Railway -> Northeast Frontier Railway)")
    w(f"gauge vocabulary unified to (gauge_code, gauge_name): {corr_clean.gauge_code.nunique()} codes")
    w(f"station '?' zone sentinels mapped to null          : {int(st.zone.astype(str).eq('?').sum())}")
    w(f"'Orissa' renamed to 'Odisha'                       : {int(st.state.astype(str).eq('Orissa').sum())}")
    w(f"stations flagged out of scope (Bangladesh)         : {int((~stations.in_scope).sum())}")
    w(f"stations with a shared coordinate (mislocated)     : {int(stations.coordinate_shared.sum())}")
    w(f"stations without coordinates                       : {int((~stations.has_coordinates).sum())}")
    w("")
    w("-- NODES --")
    w(f"total nodes                        : {len(nodes_df):,}")
    for k, v in nodes_df.node_type.value_counts().items():
        w(f"   {k:<32}: {v:,}")
    w(f"   of which dissolvable (deg 2)    : {int(nodes_df.is_dissolvable.sum()):,}")
    w(f"nodes with coordinates             : {int(nodes_df.longitude.notna().sum()):,}")
    # Both counts are reported for the WHOLE graph and for operational
    # junctions alone. They were previously printed junction-only under a
    # label that read as whole-graph ("of which" under "nodes with
    # coordinates"): 313 / 46 read as 435 / 1,128 (found 2026-10-04).
    _jn = nodes_df.node_type.eq('operational_junction')
    w(f"   degree 1 (line ends), all nodes        : {int(nodes_df.degree.eq(1).sum()):,}")
    w(f"      of which operational junctions      : {int((_jn & nodes_df.degree.eq(1)).sum()):,}")
    w(f"   degree >=3 (branching), all nodes      : {int(nodes_df.degree.ge(3).sum()):,}")
    w(f"      of which operational junctions      : {int((_jn & nodes_df.degree.ge(3)).sum()):,}")
    w(f"nodes with a zone                  : {int(nodes_df.zone_code.notna().sum()):,} "
      f"({int(nodes_df.zone_source.eq('station_master').sum()):,} stated, "
      f"{int(nodes_df.zone_source.eq('corridor_inferred').sum()):,} inferred from corridor)")
    w(f"nodes with a state                 : {int(nodes_df.state.notna().sum()):,}")
    w("")
    w("-- EDGES --")
    w(f"total edges                        : {len(edges):,}")
    w(f"   attr_complete                   : {int(edges.attr_complete.sum()):,}")
    w(f"   core_v2 / core_v4               : {int(edges.core_v2.sum()):,} / {int(edges.core_v4.sum()):,}")
    w(f"   parallel corridors > 1          : {int((edges.n_parallel_corridors>1).sum()):,} "
      f"({int(edges.parallel_differs.sum()):,} genuinely different routes)")
    w(f"   co-located (floored to {MIN_EDGE_KM} km)  : {int(edges.is_colocated.sum()):,}")
    w(f"   carrying >=1 direct service     : {int((edges.service_direct>0).sum()):,} "
      f"({(edges.service_direct>0).mean():.1%})")
    w(f"   carrying projected service load : {int((edges.service_load>0).sum()):,} "
      f"({(edges.service_load>0).mean():.1%})")
    w(f"total route km                     : {edges.length_km.sum():,.0f}")
    w("")
    w("-- STRUCTURE --")
    w(f"components                         : {nx.number_connected_components(G):,}")
    w(f"giant component                    : {len(comps[0]):,} nodes "
      f"({len(comps[0])/G.number_of_nodes():.1%})")
    L = G.subgraph(comps[0])
    w(f"independent cycles in giant        : {L.number_of_edges()-L.number_of_nodes()+1:,}")
    w(f"bridges in giant                   : {len(list(nx.bridges(L))):,} "
      f"({len(list(nx.bridges(L)))/L.number_of_edges():.1%})")
    w(f"articulation points in giant       : {len(list(nx.articulation_points(L))):,}")
    d = np.array([v for _, v in G.degree()])
    w(f"degree mean/max                    : {d.mean():.2f} / {d.max()}")
    w("")
    w("-- SERVICE LAYER --")
    w(f"service adjacencies                : {len(svc):,}")
    w(f"   both endpoints in graph         : {int(svc.both_in_graph.sum()):,} ({svc.both_in_graph.mean():.1%})")
    ok = svc[svc.both_in_graph]
    w(f"   already a direct physical edge  : {int(ok.is_direct_edge.sum()):,} ({ok.is_direct_edge.mean():.1%})")
    h = ok.physical_hops.dropna()
    w(f"   resolved within 3 physical hops : {(h<=3).mean():.1%}")
    w(f"   unresolved (no path <= {SERVICE_PATH_CUTOFF_KM:.0f} km)  : {int(ok.physical_hops.isna().sum()):,}")
    w(f"run-times derived                  : {int(svc.runtime_min_median.notna().sum()):,} pairs, "
      f"median {svc.runtime_min_median.median():.0f} min")
    w("")
    w("-- REFERENTIAL INTEGRITY OF THIS PACKAGE --")
    N = set(nodes_df.node_id)
    w(f"edge endpoints missing from nodes.csv : {len(((set(edges.from_node)|set(edges.to_node))-N)):,}")
    w(f"duplicate node_id                     : {int(nodes_df.node_id.duplicated().sum())}")
    w(f"duplicate edge (from,to)              : {int(edges.duplicated(subset=['from_node','to_node']).sum())}")
    w(f"self-loops                            : {int((edges.from_node==edges.to_node).sum())}")
    w(f"edges with null length                : {int(edges.length_km.isna().sum())}")
    (DATASET_DIR / "QA_REPORT.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWROTE {DATASET_DIR}")


if __name__ == "__main__":
    main()
