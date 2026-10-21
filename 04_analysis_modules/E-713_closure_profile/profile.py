"""E-713 - full profile of graph v1.4 for the dataset-closure audit, plus a manual audit pack.

Every number in the closure audit document comes from here. Re-runnable:
    python profile.py <root> <out dir>
Outputs:
    out/profile.json            every measured figure
    out/audit_pack/*.csv        stratified samples with blank verdict/note columns to fill by hand
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

SEED = 20261015
INDIA = dict(lon=(68.0, 97.5), lat=(6.5, 37.5))


def q(s, ps=(0, 1, 5, 25, 50, 75, 95, 99, 100)):
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return {"empty": True}
    return {f"p{p}": round(float(np.percentile(s, p)), 3) for p in ps}


def vc(s, n=40):
    return {str(k): int(v) for k, v in s.value_counts(dropna=False).head(n).items()}


def km_by(e, col):
    g = e.groupby(e[col].astype(str), dropna=False).agg(edges=("edge_id", "size"),
                                                       km=("length_km", "sum"))
    g["km"] = g.km.round(1)
    g["km_share"] = (g.km / e.length_km.sum()).round(4)
    return g.sort_values("km", ascending=False).reset_index().to_dict("records")


def maps(lat, lon):
    return f"https://www.google.com/maps?q={lat:.6f},{lon:.6f}" if pd.notna(lat) else ""


def maps2(a, b):
    if any(pd.isna(x) for x in (*a, *b)):
        return ""
    return f"https://www.google.com/maps/dir/{a[0]:.6f},{a[1]:.6f}/{b[0]:.6f},{b[1]:.6f}"


def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    pack = out / "audit_pack"
    pack.mkdir(parents=True, exist_ok=True)
    g3 = root / "03_graph_construction"
    gd = g3 / "graph_v1_4"
    sd = g3 / "service_layer_v1_4" / "open"

    n = pd.read_csv(gd / "open" / "nodes.csv")
    e = pd.read_csv(gd / "open" / "edges.csv")
    ov = pd.read_csv(gd / "OVERRIDES.csv")
    cw = pd.read_csv(gd / "station_code_crosswalk.csv")
    gates = json.loads((gd / "gates.json").read_text())
    man = json.loads((gd / "graph_v1_4.manifest.json").read_text())
    svc = pd.read_csv(sd / "service_edges_directed.csv")
    es = pd.read_csv(sd / "edge_service.csv")
    fq = pd.read_csv(sd / "train_frequency.csv")
    hr = pd.read_csv(sd / "service_hourly.csv")

    pos = {r.node_id: (r.latitude, r.longitude) for r in n.itertuples()}
    name = dict(zip(n.node_id, n.node_name))
    state = dict(zip(n.node_id, n.state))

    G = nx.Graph()
    G.add_nodes_from(n.node_id)
    for r in e.itertuples():
        G.add_edge(r.from_node, r.to_node)

    P = {}

    # ------------------------------------------------------------------ nodes
    dupname = n[n.node_name.duplicated(keep=False)].sort_values("node_name")
    coords = n.dropna(subset=["latitude", "longitude"])
    dupc = coords[coords.duplicated(["latitude", "longitude"], keep=False)]
    outside = coords[~coords.longitude.between(*INDIA["lon"]) | ~coords.latitude.between(*INDIA["lat"])]
    P["nodes"] = dict(
        total=len(n), by_type=vc(n.node_type),
        with_station_code=int(n.station_code.notna().sum()),
        without_station_code=int(n.station_code.isna().sum()),
        missing_coordinates=int(n[["latitude", "longitude"]].isna().any(axis=1).sum()),
        missing_coordinate_ids=n[n[["latitude", "longitude"]].isna().any(axis=1)].node_id.tolist(),
        identical_coordinate_nodes=len(dupc),
        identical_coordinate_groups=int(dupc.groupby(["latitude", "longitude"]).ngroups),
        outside_india_bbox=len(outside),
        bbox=dict(lon=[round(coords.longitude.min(), 4), round(coords.longitude.max(), 4)],
                  lat=[round(coords.latitude.min(), 4), round(coords.latitude.max(), 4)]),
        coordinate_source=vc(n.coordinate_source),
        coord_fixed=vc(n.coord_fixed),
        missing_state=int(n.state.isna().sum()),
        missing_state_ids=n[n.state.isna()].node_id.tolist(),
        states=int(n.state.nunique()), by_state=vc(n.state),
        state_source=vc(n.state_source),
        state_changed_from_v12=int(n.state_v12_disagrees.fillna(False).astype(bool).sum()),
        missing_zone=int(n.zone_code.isna().sum()), zones=int(n.zone_code.nunique()),
        by_zone=vc(n.zone_code), zone_source=vc(n.zone_source),
        code_identity_suspect=int(n.code_identity_suspect.fillna(False).astype(bool).sum()),
        node_origin=vc(n.node_origin),
        merged_nodes=int(n.merged_from.notna().sum()),
        match_method=vc(n.match_method),
        match_confidence=q(pd.to_numeric(n.match_confidence, errors="coerce")),
        touched_by_overrides=int((pd.to_numeric(n.overrides_applied, errors="coerce").fillna(0) > 0).sum()),
        not_in_giant=int((~n.in_giant.astype(bool)).sum()),
        isolated=int(sum(1 for _, d in G.degree() if d == 0)),
        names_shared_by_more_than_one_node=int(dupname.node_name.nunique()),
        nodes_with_shared_name=len(dupname),
        degree_column_matches_graph=bool((n.set_index("node_id").degree
                                          == pd.Series(dict(G.degree()))).all()),
    )

    # ------------------------------------------------------------------ edges
    e["ratio_to_chord"] = e.length_km / e.length_chord_km
    e["ratio_to_official"] = e.length_km / e.official_km
    key = e.apply(lambda r: tuple(sorted((r.from_node, r.to_node))), axis=1)
    lb = e.length_is_lower_bound.astype(bool)
    off = e.official_km.notna()
    agree = (e.loc[off, "ratio_to_official"] - 1).abs()
    P["edges"] = dict(
        total=len(e), route_km=round(float(e.length_km.sum()), 1),
        length_quantiles_km=q(e.length_km),
        under_0_2km=int((e.length_km < 0.2).sum()), under_0_5km=int((e.length_km < 0.5).sum()),
        under_1km=int((e.length_km < 1).sum()),
        over_30km=int((e.length_km > 30).sum()), over_50km=int((e.length_km > 50).sum()),
        over_100km=int((e.length_km > 100).sum()),
        missing_length=int(e.length_km.isna().sum()),
        non_positive_length=int((e.length_km <= 0).sum()),
        self_loops=int((e.from_node == e.to_node).sum()),
        parallel_pairs=int(key.duplicated().sum()),
        edge_id_unique=bool(e.edge_id.is_unique),
        dangling_endpoints=int((~e.from_node.isin(n.node_id) | ~e.to_node.isin(n.node_id)).sum()),
        length_source=km_by(e, "length_source"),
        lower_bound_edges=int(lb.sum()),
        lower_bound_km=round(float(e.loc[lb, "length_km"].sum()), 1),
        lower_bound_km_share=round(float(e.loc[lb, "length_km"].sum() / e.length_km.sum()), 4),
        below_chord_edges=int((e.ratio_to_chord < 0.999).sum()),
        below_chord_by_more_than_5pct=int((e.ratio_to_chord < 0.95).sum()),
        ratio_to_chord=q(e.ratio_to_chord),
        circuity_over_2x=int((e.ratio_to_chord > 2).sum()),
        official_coverage_edges=int(off.sum()),
        official_coverage_share=round(float(off.mean()), 4),
        official_coverage_km_share=round(float(e.loc[off, "length_km"].sum() / e.length_km.sum()), 4),
        agree_with_official_within_2pct=round(float((agree <= 0.02).mean()), 4),
        agree_with_official_within_5pct=round(float((agree <= 0.05).mean()), 4),
        agree_with_official_within_10pct=round(float((agree <= 0.10).mean()), 4),
        disagree_with_official_over_25pct=int((agree > 0.25).sum()),
        official_source=vc(e.official_source),
        flags={c: int(e[c].fillna(False).astype(bool).sum()) for c in
               ["official_conflict", "official_detour", "official_sources_disagree",
                "spine_disagrees_official", "raised_to_chord", "suspect_long_edge",
                "geometry_unsupported", "bridge_present_edge", "tunnel_present_edge"]},
        gauge=km_by(e, "gauge_code"), zone=km_by(e, "zone_code"),
        n_tracks=vc(e.n_tracks), n_tracks_missing=int(e.n_tracks.isna().sum()),
        origin=vc(e.origin), edge_origin=vc(e.edge_origin),
        geometry_source=vc(e.geometry_source),
        corridors=int(e.corridor_id.nunique()),
        edges_without_corridor=int(e.corridor_id.isna().sum()),
        speed_missing=int(e.speed_used_kmph.isna().sum()),
        speed_quantiles=q(e.speed_used_kmph), speed_source=vc(e.speed_source),
        service_load_zero=int((e.service_load.fillna(0) == 0).sum()),
        service_direct_zero=int((e.service_direct.fillna(0) == 0).sum()),
        changed_length_since_v12=int((e.length_km - e.length_km_v12).abs().gt(0.01).sum()),
    )

    # ------------------------------------------------------------------ topology
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    frag = []
    for i, c in enumerate(comps[1:], 1):
        sts = sorted({state.get(x) for x in c if pd.notna(state.get(x))})
        frag.append(dict(fragment=i, nodes=len(c), states=", ".join(sts),
                         stations=", ".join(sorted(name.get(x, x) for x in c)[:6])))
    deg = pd.Series(dict(G.degree()))
    H = G.subgraph(comps[0])
    P["topology"] = dict(
        components=len(comps), giant_nodes=len(comps[0]),
        giant_share=round(len(comps[0]) / len(n), 4),
        fragment_sizes=[len(c) for c in comps[1:]],
        nodes_outside_giant=int(sum(len(c) for c in comps[1:])),
        cycle_rank_giant=int(H.number_of_edges() - H.number_of_nodes() + 1),
        degree_counts={int(k): int(v) for k, v in deg.value_counts().sort_index().items()},
        mean_degree=round(float(deg.mean()), 3), max_degree=int(deg.max()),
        max_degree_nodes=[f"{name.get(x, x)} ({x})" for x in deg[deg == deg.max()].index],
        termini=int((deg == 1).sum()), chain_nodes=int((deg == 2).sum()),
        junctions=int((deg >= 3).sum()),
        density=round(nx.density(G), 6),
    )
    pd.DataFrame(frag).to_csv(pack / "A_fragments_all.csv", index=False)

    # ------------------------------------------------------------------ service
    rt = svc.runtime_min_median.notna()
    P["service"] = dict(
        directed_pairs=len(svc),
        stations=int(pd.unique(pd.concat([svc.from_station, svc.to_station])).size),
        direct_physical_edge_pairs=int(svc.is_direct_physical_edge.astype(bool).sum()),
        trains_per_day=q(svc.trains_per_day),
        pairs_with_runtime=int(rt.sum()), pairs_with_runtime_share=round(float(rt.mean()), 4),
        observed_speed_kmph=q(svc.observed_speed_kmph),
        speed_over_160=int((svc.observed_speed_kmph > 160).sum()),
        speed_under_10=int((svc.observed_speed_kmph < 10).sum()),
        unroutable_pairs=int(svc.physical_path_km.isna().sum()),
        edges_with_service=int((es.trains_per_day > 0).sum()),
        edges_without_service=int(len(e) - (es.trains_per_day > 0).sum()),
        edge_trains_per_day=q(es.trains_per_day),
        frequency_trains=len(fq), frequency_columns=list(fq.columns),
        frequency_pattern=vc(fq["pattern"]) if "pattern" in fq.columns else None,
        hourly_rows=len(hr), hourly_columns=list(hr.columns),
    )

    # ------------------------------------------------------------------ provenance
    P["provenance"] = dict(
        overrides_rows=len(ov),
        overrides_by_module_action={f"{a} / {b}": int(c) for (a, b), c in
                                    ov.groupby(["audit_file", "action"]).size().items()},
        overrides_without_evidence=int(ov.evidence.isna().sum()),
        overrides_without_reviewer=int(ov.reviewer.isna().sum()),
        crosswalk=vc(cw.resolution), crosswalk_columns=list(cw.columns),
        manifest_files=len(man["files"]),
        manifest_byte_reproducible=int(sum(1 for v in man["files"].values() if v.get("byte_reproducible"))),
        manifest_inputs=len(man.get("inputs", {})),
    )
    P["gates"] = gates

    (out / "profile.json").write_text(json.dumps(P, indent=1, default=str))

    # ------------------------------------------------------------------ audit pack
    blank = dict(verdict="", note="")
    rng = np.random.default_rng(SEED)

    def samp(df, k):
        return df.sample(min(k, len(df)), random_state=int(rng.integers(1e9)))

    # B. nodes, stratified by role in the network
    n["role"] = np.select([n.degree <= 1, n.degree == 2, n.degree >= 3],
                          ["terminus", "intermediate", "junction"], "other")
    bn = pd.concat([samp(n[n.role == "terminus"], 10), samp(n[n.role == "intermediate"], 20),
                    samp(n[n.role == "junction"], 20)])
    bn = bn[["node_id", "node_name", "node_type", "station_code", "role", "degree", "state",
             "zone_code", "latitude", "longitude", "coordinate_source"]].copy()
    bn["map"] = [maps(a, b) for a, b in zip(bn.latitude, bn.longitude)]
    bn["check"] = "Is the station really here? Name, state and zone right? Degree plausible?"
    bn.assign(**blank).to_csv(pack / "B_nodes_sample_50.csv", index=False)

    def edge_view(df, check):
        d = df.copy()
        d["from_name"] = d.from_node.map(name)
        d["to_name"] = d.to_node.map(name)
        d["route"] = [maps2(pos.get(a, (np.nan, np.nan)), pos.get(b, (np.nan, np.nan)))
                      for a, b in zip(d.from_node, d.to_node)]
        d["check"] = check
        cols = ["edge_id", "from_node", "from_name", "to_node", "to_name", "length_km",
                "length_source", "length_is_lower_bound", "length_chord_km", "official_km",
                "gauge_code", "zone_code", "n_tracks", "route", "check"]
        return d[[c for c in cols if c in d.columns]].assign(**blank)

    # C. edges, stratified by how the length was obtained
    ce = pd.concat([samp(e[e.length_source == s], 8) for s in e.length_source.unique()])
    edge_view(ce, "Are these consecutive stations on one line? Is the length right within ~5%?"
              ).to_csv(pack / "C_edges_sample_by_length_source.csv", index=False)
    # D. the longest sections - most likely to hide a missing intermediate station
    edge_view(e.nlargest(30, "length_km"),
              "A long section: is there really no station between these two?"
              ).to_csv(pack / "D_edges_longest_30.csv", index=False)
    # E. the shortest - most likely to be one station held as two nodes
    edge_view(e.nsmallest(30, "length_km"),
              "A very short section: two real stations, or one station held twice?"
              ).to_csv(pack / "E_edges_shortest_30.csv", index=False)
    # F. biggest disagreement with official timetable distance
    f = e[off].assign(gap=(e.ratio_to_official - 1).abs()).nlargest(30, "gap")
    edge_view(f, "Our length vs the timetable's: which is right?"
              ).to_csv(pack / "F_edges_disagree_with_official_30.csv", index=False)
    # G. edges shorter than their straight line (physically impossible)
    edge_view(e[e.ratio_to_chord < 0.999].sort_values("ratio_to_chord"),
              "Shorter than the straight line: wrong length, or wrong coordinates?"
              ).to_csv(pack / "G_edges_below_straight_line.csv", index=False)
    # H. nodes with a missing attribute
    miss = n[n[["latitude", "longitude", "state", "zone_code"]].isna().any(axis=1)]
    miss[["node_id", "node_name", "node_type", "station_code", "latitude", "longitude",
          "state", "zone_code", "degree"]].assign(
        check="Find the missing value, or confirm it cannot be found", **blank
    ).to_csv(pack / "H_nodes_missing_attributes.csv", index=False)
    # I. names shared by more than one node
    di = dupname[["node_id", "node_name", "station_code", "state", "latitude", "longitude",
                  "degree"]].copy()
    di["map"] = [maps(a, b) for a, b in zip(di.latitude, di.longitude)]
    di.assign(check="Same station twice, or genuinely different places with one name?",
              **blank).to_csv(pack / "I_nodes_shared_names.csv", index=False)
    # J. implausible observed speeds
    sp = svc[(svc.observed_speed_kmph > 160) | (svc.observed_speed_kmph < 10)]
    sp.assign(check="Implausible speed: bad runtime, or bad path length?", **blank
              ).to_csv(pack / "J_service_implausible_speeds.csv", index=False)
    # K. overrides sample
    samp(ov, 25).assign(check="Does the evidence actually support the action?", **blank
                        ).to_csv(pack / "K_overrides_sample_25.csv", index=False)

    counts = {p.name: sum(1 for _ in open(p)) - 1 for p in sorted(pack.glob("*.csv"))}
    (out / "audit_pack_index.json").write_text(json.dumps(counts, indent=1))
    print(json.dumps(P, indent=1, default=str)[:200])
    print("audit pack:", json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
