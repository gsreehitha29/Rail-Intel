"""E-500 -- graph v1.2: the five known weaknesses, each fixed as far as evidence allows.

  W-1  spurious stitch edges removed (topology change, proven)        repair.py
  W-2  edge-level attributes from GIS segments                         enrich12.segment_overlay
  W-3  speed: constant 50 km/h replaced by validated imputation        enrich12.impute_speed
  W-4  state: coverage raised by validated inference; AP/TG flagged    enrich12.infer_state
  W-5  (service layer -- separate artifact, E-502)

Every fix is followed by a gate that could fail. Reads the released v1.1
(`make v11` first); writes graph_v1_2/ and never touches v1.0 or v1.1.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PHASE3 = HERE.parents[1]
REPO = PHASE3.parent
sys.path.insert(0, str(PHASE3))

from railgraph import io as IO, metrics as M, repair, enrich12, geometry as GEO  # noqa: E402
from railgraph.config import BuildSpec  # noqa: E402

V11 = PHASE3 / "graph_v1_1"
OUT = PHASE3 / "graph_v1_2"
DS = REPO / "02_graph_inputs" / "graph_dataset"
DERIVED_NODE = ["degree", "component_id", "in_giant_component", "in_giant",
                "strength_service_load", "strength_km", "clustering", "spec_hash",
                "dataset_version"]


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    e = pd.read_parquet(V11 / "edges.parquet")
    nodes = pd.read_csv(DS / "nodes.csv").drop(columns=DERIVED_NODE, errors="ignore")
    corridors = pd.read_csv(DS / "corridors.csv")
    spines = GEO.load_spines()
    gates = []

    def gate(name, ok, **detail):
        gates.append({"gate": name, "pass": bool(ok), **detail})

    # ---------------- W-2 edge-level attributes ----------------
    ov = enrich12.segment_overlay(e, nodes, spines)
    e = e.merge(ov, on="edge_id", how="left")
    sp = e[e.length_source.astype(str).eq("spine") & e.overlay_km.notna()]
    r = sp.overlay_km / sp.length_km
    gate("W2_overlay_length_matches_edge_length",
         r.between(0.9, 1.1).mean() >= 0.99,
         spine_edges=int(len(sp)), within_10pct=float(r.between(0.9, 1.1).mean()),
         median=float(r.median()))
    bp = e.bridge_present_edge.eq(True)
    gate("W2_edge_bridge_subset_of_corridor_bridge",
         int((bp & ~e.bridge_present.astype(bool)).sum()) == 0,
         violations=int((bp & ~e.bridge_present.astype(bool)).sum()))
    tp = e.tunnel_present_edge.eq(True)
    gate("W2_edge_tunnel_subset_of_corridor_tunnel",
         int((tp & ~e.tunnel_present.astype(bool)).sum()) == 0,
         violations=int((tp & ~e.tunnel_present.astype(bool)).sum()))
    good = e.edge_attr_source.eq("segment_overlay")
    w2 = {
        "edges_segment_overlay": int(good.sum()), "edges_corridor_fallback": int((~good).sum()),
        "bridge_edges_corridor_level": int(e.bridge_present.astype(bool).sum()),
        "bridge_edges_edge_level": int(bp.sum()),
        "bridge_km_total": float(e.bridge_km.sum()),
        "tunnel_edges_corridor_level": int(e.tunnel_present.astype(bool).sum()),
        "tunnel_edges_edge_level": int(tp.sum()),
        "zone_differs_from_corridor": int((good & e.zone_code_seg.notna() & (e.zone_code_seg != e.zone_code)).sum()),
        "tracks_differs_from_corridor": int((good & e.n_tracks_seg.notna() & e.n_tracks.notna() & (e.n_tracks_seg != e.n_tracks)).sum()),
        "speed_differs_from_corridor": int((good & e.speed_kmph_seg.notna() & e.speed_kmph.notna() & (e.speed_kmph_seg != e.speed_kmph)).sum()),
        "gauge_differs_from_corridor": int((good & e.gauge_code_seg.notna() & (e.gauge_code_seg != e.gauge_code.astype(str))).sum()),
    }

    # ---------------- W-3 speed ----------------
    e, cv = enrich12.impute_speed(e)
    gate("W3_imputation_beats_old_constant", cv["mae_kmph"] < cv["old_constant_50_mae_kmph"],
         cv_mae=cv["mae_kmph"], old_constant_mae=cv["old_constant_50_mae_kmph"])
    allowed = {"declared_segment", "declared_corridor", "imputed_gauge_zone_median",
               "imputed_gauge_median", "none"}
    gate("W3_every_speed_is_declared_or_validated_imputation",
         set(e.speed_source.dropna()) <= allowed and e.speed_source.notna().all(),
         sources=e.speed_source.value_counts().to_dict())

    # An edge gets no speed only when its gauge has NO declared speed anywhere --
    # there is nothing to impute from, and inventing one is the silent
    # substitution this fix exists to end. Those edges are listed, not hidden.
    declared_gauges = set(e.loc[e.speed_declared_kmph.notna(), "gauge_code"].fillna("unknown"))
    none = e[e.speed_source == "none"]
    gate("W3_unimputed_only_where_gauge_has_no_declared_speed",
         e.speed_source.notna().all() and not set(none.gauge_code.fillna("unknown")) & declared_gauges,
         unimputed_edges=none.edge_id.tolist(), unimputed_gauges=sorted(set(none.gauge_code.fillna("unknown"))),
         unimputed_km=float(none.length_km.sum()))

    # ---------------- W-4 state ----------------
    nodes, sv = enrich12.infer_state(nodes)
    gate("W4_inference_rule_loo_accuracy_ge_99pct", sv["loo_rule_accuracy"] >= 0.99, **sv)

    # ---------------- W-1 topology repair ----------------
    rem = repair.find_removals(e, corridors)
    rem.to_csv(OUT / "removed_edges.csv", index=False)
    e = repair.flag_columns(e, corridors)
    e2 = e[~e.edge_id.isin(rem.edge_id)].copy()

    def build(ed):
        G = nx.Graph()
        for rr in nodes.to_dict("records"):
            nid = rr.pop("node_id")
            G.add_node(nid, **{k: v for k, v in rr.items()
                               if not (isinstance(v, float) and np.isnan(v)) and v is not None})
        for rr in ed.to_dict("records"):
            u, v = rr.pop("from_node"), rr.pop("to_node")
            G.add_edge(u, v, **{k: v2 for k, v2 in rr.items()
                                if not (isinstance(v2, float) and np.isnan(v2)) and v2 is not None})
        return G

    G11, G = build(e), build(e2)
    s11, s12 = M.cut_structure(G11), M.cut_structure(G)
    conn = []
    for x in rem.itertuples():
        try:
            L = nx.dijkstra_path_length(G, x.from_node, x.to_node, weight="length_km")
        except nx.NetworkXNoPath:
            L = np.inf
        conn.append(L / x.length_km)
    conn = np.array(conn)
    band_ok = np.isfinite(conn).all() and (conn <= 1.30 + 1e-9).all() and (conn >= 0.85 - 1e-9).all()
    gate("W1_connectivity_unchanged",
         s11["n_components"] == s12["n_components"] and s11["giant_nodes"] == s12["giant_nodes"]
         and G.number_of_nodes() == G11.number_of_nodes(),
         components=(s11["n_components"], s12["n_components"]),
         giant=(s11["giant_nodes"], s12["giant_nodes"]))
    gate("W1_every_removed_edge_has_equivalent_route", band_ok,
         alt_ratio_min=float(conn.min()) if len(conn) else None,
         alt_ratio_max=float(conn.max()) if len(conn) else None)
    gate("W1_cycle_rank_drops_by_exactly_removed",
         s11["independent_cycles"] - s12["independent_cycles"] == len(rem),
         cycles=(s11["independent_cycles"], s12["independent_cycles"]), removed=int(len(rem)))
    w1 = {"removed": int(len(rem)), "by_kind": rem.kind.value_counts().to_dict(),
          "removed_km": float(rem.length_km.sum()),
          "removed_service_direct_zero": int((rem.service_direct == 0).sum()),
          "structure_v11": {k: s11[k] for k in ("n_edges", "independent_cycles", "bridges", "articulation_points", "meshedness")},
          "structure_v12": {k: s12[k] for k in ("n_edges", "independent_cycles", "bridges", "articulation_points", "meshedness")},
          "route_km_v11": float(e.length_km.sum()), "route_km_v12": float(e2.length_km.sum()),
          "sensitivity_removal_count": "see E-501 part A"}

    # ---------------- export ----------------
    gran = json.loads(json.dumps({"gauge_code": "corridor", "speed_kmph": "corridor", "n_tracks": "corridor",
            "zone_code": "corridor", "bridge_present": "corridor_or", "tunnel_present": "corridor_or",
            "bridge_present_edge": "segment_overlay", "bridge_km": "segment_overlay",
            "tunnel_present_edge": "segment_overlay", "tunnel_km": "segment_overlay",
            "zone_code_seg": "segment_overlay", "n_tracks_seg": "segment_overlay",
            "speed_kmph_seg": "segment_overlay", "gauge_code_seg": "segment_overlay",
            "speed_used_kmph": "declared_or_imputed (see speed_source)",
            "length_km": "edge", "service_load": "edge", "service_direct": "edge"}))
    G.graph.update({"dataset_version": "v1.0", "version": "v1.2",
                    "spec_hash": BuildSpec(label="graph v1.2").hash,
                    "attribute_granularity": json.dumps(gran),
                    "export_revision": IO.EXPORT_REVISION})
    geo = pd.read_parquet(V11 / "edge_geometry.parquet")
    geo = geo[~geo.edge_id.isin(rem.edge_id)].copy()
    geo["coords"] = [GEO.read_wkb_linestring(b) if b is not None else None for b in geo.wkb]
    al = geo.drop(columns=["wkb"])
    outputs = {"graphml": IO.export_graphml(G, OUT / "rail_graph_v1_2.graphml")}
    outputs.update({f"geojson_{k}": v for k, v in IO.export_geojson(G, OUT, al).items()})
    outputs["parquet_edge_geometry"] = IO.export_geometry_table(al, OUT)
    tabs = IO.export_tables(G, OUT)
    outputs["parquet_nodes"], outputs["parquet_edges"] = tabs["nodes"], tabs["edges"]
    e2.to_csv(OUT / "edges.csv", index=False)
    rt = IO.verify_roundtrip(G, OUT, graphml="rail_graph_v1_2.graphml")
    gate("export_roundtrip_attribute_exact", rt["all_roundtrip_ok"],
         **{k: {kk: rt[k][kk] for kk in ("exact", "attribute_value_mismatches")} for k in ("graphml", "parquet", "geojson")})
    sh = IO.verify_against_shipped(OUT, graphml="rail_graph_v1_2.graphml", length_col="length_km_v10")
    touched = set(rem.from_node) | set(rem.to_node)
    gate("carries_every_phase2_column_and_value_except_removal_effects",
         all(not sh[f][k] for f in ("graphml", "parquet", "geojson")
             for k in ("node_columns_missing", "edge_columns_missing"))
         and not sh["edge_value_diffs_vs_csv"]
         and set(sh["node_value_diffs_vs_csv"]) <= {"degree"},
         edge_value_diffs=sh["edge_value_diffs_vs_csv"], node_value_diffs=sh["node_value_diffs_vs_csv"],
         nodes_touched_by_removal=len(touched))
    manifest = IO.write_manifest(
        G, BuildSpec(label="graph v1.2"), OUT, outputs, version="v1.2",
        filename="graph_v1_2.manifest.json",
        extra={"supersedes": "v1.1 (graph_v1_1/) -- topology changed: 51 spurious stitch edges removed",
               "implements": ["D-043", "D-044", "D-045", "D-046"],
               "w1": w1, "w2": w2, "w3_speed_cv": cv, "w4_state": sv},
        caveats={"topology": "v1.2 is NOT topology-identical to v1.0/v1.1: see removed_edges.csv",
                 "speed_used_kmph": "declared where the source has it, else gauge x zone median "
                                    "(grouped CV MAE %.1f km/h). An estimate, flagged by speed_source." % cv["mae_kmph"],
                 "state_best": "station master, else 7-NN inference (LOO %.1f%%); every Andhra Pradesh "
                               "label is ambiguous (pre-Telangana source)" % (100 * sv["loo_rule_accuracy"])})
    rep = {"experiment": "E-500", "title": "graph v1.2", "gates": gates, "w1": w1, "w2": w2,
           "w3_speed_cv": cv, "w4_state": sv, "secs": round(time.time() - t0, 1),
           "outputs": {k: str(v.name) for k, v in outputs.items()}}
    (OUT / "E-500_report.json").write_text(json.dumps(rep, indent=2, default=str))
    for g in gates:
        print(f"  {'PASS' if g['pass'] else 'FAIL'}  {g['gate']}")
    print(json.dumps({"w1": w1, "w2": w2}, indent=1, default=str))
    print("speed CV:", {k: v for k, v in cv.items() if k != "by_gauge"})
    print("state:", sv)
    ok = all(g["pass"] for g in gates)
    print("RESULT:", "PASS" if ok else "FAIL", f"({time.time()-t0:.0f}s)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
