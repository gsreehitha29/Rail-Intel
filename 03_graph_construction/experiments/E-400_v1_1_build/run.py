"""E-400 -- build, validate and export graph v1.1 (the provenance layer).

v1.1 adds no data source and no capability. It implements D-025, D-026, D-027,
D-029 and D-030: every value that was previously indistinguishable from a
measurement now says how it was obtained.

Run:  python 03_graph_construction/experiments/E-400_v1_1_build/run.py

Writes graph_v1_1/ beside the frozen graph_v1/ and never modifies it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PHASE3 = HERE.parents[1]
REPO = PHASE3.parent
sys.path.insert(0, str(PHASE3))

from railgraph import BuildSpec, ProvenanceSpec, shipped_tables, to_graph  # noqa: E402
from railgraph.provenance import enrich, summarise  # noqa: E402
from railgraph import metrics as M  # noqa: E402

DATASET = REPO / "02_graph_inputs" / "graph_dataset"
OUT = PHASE3 / "graph_v1_1"
REF = REPO / "reference_data"

#: F-029's external ground truth. Zero terrain input reaches the pipeline, so
#: recovering these from geometry alone is a check that could fail.
MOUNTAIN = {
    frozenset(("MATHERAN", "NERAL")), frozenset(("DJ", "NJP")),
    frozenset(("KLK", "SML")), frozenset(("MTP", "UAM")),
}
#: Matched on name *prefixes*, because corridors.csv spells endpoints with
#: suffixes the UNESCO citation does not ("Neral Jn NG", "New Jalpaiguri
#: Junction"). An exact-string gate silently found only 2 of 4 and passed
#: vacuously on the rest -- the gate now fails unless all four are located.
MOUNTAIN_NAMES = (
    ("matheran", "neral"),
    ("darjeeling", "new jalpaiguri"),
    ("kalka", "shimla"),
    ("mettupalayam", "udagamandalam"),
)

ZONE_NAME_TO_CODE = {
    "Central": "CR", "Eastern": "ER", "East Central": "ECR", "East Coast": "ECoR",
    "Northern": "NR", "North Central": "NCR", "North Eastern": "NER",
    "Northeast Frontier": "NFR", "North Western": "NWR", "Southern": "SR",
    "South Central": "SCR", "South Eastern": "SER", "South East Central": "SECR",
    "South Western": "SWR", "Western": "WR", "West Central": "WCR", "Konkan": "KR",
}


def gate_a(e: pd.DataFrame) -> dict:
    """No spine-sourced edge may be shorter than its own chord (D-026 gate a)."""
    bad = e[(e.length_source == "spine") & (e.length_km < e.length_chord_km - 1e-9)]
    return {"gate": "a_no_edge_below_its_chord", "violations": int(len(bad)),
            "pass": bool(len(bad) == 0)}


def gate_b(e: pd.DataFrame, corridors: pd.DataFrame) -> dict:
    """Corridor sinuosity must still rank all four mountain railways in the top 1%.

    Computed on the v1.1 edge sinuosity aggregated per corridor, so it tests the
    shipped column rather than re-deriving E-300's version.
    """
    s = (e[e.sinuosity.notna()].groupby("corridor_id")
         .agg(sinuosity=("sinuosity", "median"), n=("sinuosity", "size")))
    s = s[s.n >= 2].sort_values("sinuosity", ascending=False)
    c = corridors.set_index("corridor_id")
    s["a"] = c.corridor_a.reindex(s.index).str.strip().str.lower()
    s["b"] = c.corridor_b.reindex(s.index).str.strip().str.lower()
    s["rank"] = range(1, len(s) + 1)
    s["a"] = s.a.fillna("")
    s["b"] = s.b.fillna("")
    hits, missing = [], []
    for p, q in MOUNTAIN_NAMES:
        sel = (((s.a.str.startswith(p)) & (s.b.str.startswith(q)))
               | ((s.a.str.startswith(q)) & (s.b.str.startswith(p))))
        m = s[sel]
        if len(m):
            r = int(m["rank"].iloc[0])
            hits.append({"corridor": f"{m.a.iloc[0]} <-> {m.b.iloc[0]}", "rank": r,
                         "sinuosity": round(float(m.sinuosity.iloc[0]), 4),
                         "percentile": round(r / len(s) * 100, 3)})
        else:
            missing.append(f"{p} <-> {q}")
    top1pct = max(1, int(len(s) * 0.01))
    return {"gate": "b_mountain_railways_in_top_1pct", "n_corridors_ranked": int(len(s)),
            "top_1pct_cutoff_rank": top1pct, "found": len(hits),
            "missing": missing, "detail": sorted(hits, key=lambda h: h["rank"]),
            "pass": bool(not missing and len(hits) == len(MOUNTAIN_NAMES)
                         and all(h["rank"] <= top1pct for h in hits))}


def gate_c(e: pd.DataFrame) -> dict:
    """Per-zone route km re-reconciled against the official BG figures (E-102)."""
    path = REF / "zone_electrification_2021.csv"
    if not path.exists():
        return {"gate": "c_per_zone_route_km", "pass": None, "note": "reference missing"}
    ref = pd.read_csv(path)
    ref["code"] = ref.iloc[:, 0].astype(str).str.strip().map(ZONE_NAME_TO_CODE)
    ref = ref.dropna(subset=["code"])
    kmcol = [c for c in ref.columns if "bg_route_km" in c.lower()]
    if not kmcol:
        return {"gate": "c_per_zone_route_km", "pass": None, "note": "no route-km column"}
    ref = ref.set_index("code")[kmcol[0]].astype(float)
    bg = e[e.gauge_code.astype(str).str.upper().str.startswith("BG")]
    rows = []
    for ver, col in (("v1.0", "length_km_v10"), ("v1.1", "length_km")):
        ours = bg.groupby(bg.zone_code.astype(str))[col].sum()
        j = pd.concat([ours.rename("ours"), ref.rename("ref")], axis=1).dropna()
        dev = (j.ours / j.ref - 1.0) * 100
        rows.append({"version": ver, "zones": int(len(j)),
                     "national_dev_pct": round(float((j.ours.sum() / j.ref.sum() - 1) * 100), 3),
                     "zone_dev_median_pct": round(float(dev.median()), 3),
                     "zone_dev_min_pct": round(float(dev.min()), 3),
                     "zone_dev_max_pct": round(float(dev.max()), 3),
                     "zone_dev_sd_pp": round(float(dev.std()), 3),
                     "pearson_r": round(float(j.ours.corr(j.ref)), 4)})
    return {"gate": "c_per_zone_route_km", "pass": True, "note":
            "reported, not thresholded -- F-041 established the national figure "
            "is not evidence of correctness", "comparison": rows}


def main() -> int:
    bspec = BuildSpec(label="graph v1.1 release")
    pspec = ProvenanceSpec(label="v1.1 default")
    nodes, edges = shipped_tables()
    corridors = pd.read_csv(DATASET / "corridors.csv")

    print(f"shipped v1.0: {len(nodes):,} nodes  {len(edges):,} edges  "
          f"{edges.length_km.sum():,.1f} route km")

    e = enrich(edges, nodes, corridors, spec=pspec)
    summary = summarise(e)

    # topology must be untouched: v1.1 is additive
    G10 = to_graph(nodes, edges, bspec)
    G11 = to_graph(nodes, e, bspec)
    topo = {
        "nodes_equal": G10.number_of_nodes() == G11.number_of_nodes(),
        "edges_equal": G10.number_of_edges() == G11.number_of_edges(),
        "edge_set_identical": set(map(frozenset, G10.edges())) == set(map(frozenset, G11.edges())),
        "components_equal": nx.number_connected_components(G10) == nx.number_connected_components(G11),
        "bridges_equal": len(list(nx.bridges(G10))) == len(list(nx.bridges(G11))),
        "articulation_equal": len(list(nx.articulation_points(G10))) == len(list(nx.articulation_points(G11))),
    }
    topo["pass"] = all(topo.values())

    gates = [gate_a(e), gate_b(e, corridors), gate_c(e)]

    OUT.mkdir(parents=True, exist_ok=True)
    # length_source is a Categorical; GraphML and GeoJSON want a plain string
    e["length_source"] = e.length_source.astype(str)
    (OUT / "length_source_breakdown.csv").write_text(
        e.groupby([e.length_source.astype(str), e.any_stitch]).agg(
            n=("length_km", "size"),
            km_v10=("length_km_v10", "sum"),
            km_v11=("length_km", "sum")).to_csv())

    # full interoperable export, written beside the frozen v1.0 artifact
    from railgraph import io as IO
    from railgraph.provenance import GRANULARITY
    G = to_graph(nodes, e, bspec)
    # D-027: granularity is constant per attribute, so it belongs once on the
    # graph rather than 9,689 times on its edges.
    G.graph.update({"version": "v1.1", "provenance_spec_hash": pspec.hash,
                    "attribute_granularity": json.dumps(GRANULARITY)})
    # W1: true alignment where the spine is trusted (length_source == "spine"),
    # an explicit chord elsewhere, and "none" where an endpoint has no
    # coordinate. Geometry trust is defined by D-026, not re-decided here.
    from railgraph import geometry as GEO
    seq = pd.read_csv(DATASET / "station_sequences.csv")
    al = GEO.build_alignments(e, nodes, seq, GEO.load_spines(), bspec.offset_max_km,
                              corridors)
    gcols = ["geometry_source", "geometry_corridor", "geometry_offset_km",
             "geometry_length_km"]
    for r in al.itertuples(index=False):
        u, v = e.loc[e.edge_id == r.edge_id, ["from_node", "to_node"]].iloc[0]
        for c in gcols:
            val = getattr(r, c)
            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                G.edges[u, v][c] = val
    e = e.merge(al[["edge_id"] + gcols], on="edge_id", how="left")
    G.graph["export_revision"] = IO.EXPORT_REVISION
    geo_summary = al.geometry_source.value_counts().to_dict()
    geo_summary["spine_share_edges_pct"] = round(
        100 * (al.geometry_source == "spine").mean(), 2)

    outputs = {"graphml": IO.export_graphml(G, OUT / "rail_graph_v1_1.graphml")}
    outputs.update({f"geojson_{k}": v
                    for k, v in IO.export_geojson(G, OUT, al).items()})
    outputs["parquet_edge_geometry"] = IO.export_geometry_table(al, OUT)
    # export_tables writes the complete node table (stored + derived); the edge
    # table is then rewritten from the enriched frame so the per-edge
    # granularity markers ship too.
    tabs = IO.export_tables(G, OUT)
    e.to_parquet(OUT / "edges.parquet", index=False)
    e.to_csv(OUT / "edges.csv", index=False)
    outputs["parquet_edges"] = tabs["edges"]
    outputs["parquet_nodes"] = tabs["nodes"]
    manifest = IO.write_manifest(
        G, bspec, OUT, outputs, version="v1.1",
        filename="graph_v1_1.manifest.json",
        extra={"provenance_spec": pspec.to_dict(),
               "provenance_spec_hash": pspec.hash,
               "supersedes": "v1.0 (graph_v1/, spec f9adf8ca9042) -- topology identical",
               "implements": ["D-025", "D-026", "D-027", "D-029", "D-030"],
               "v1_1_summary": summary,
               "geometry_summary": geo_summary},
        caveats={
            "length_km_bias": (
                "superseded in v1.1: length_km is now the D-026 hybrid and every "
                "edge carries length_source. v1.0's value is retained as "
                "length_km_v10. F-042: the v1.0 length was already the along-spine "
                "measure on non-stitch edges, not the chord E-300 assumed."),
            "attribute_granularity": (
                "gauge_code, speed_kmph, n_tracks, zone_code are CORRIDOR "
                "constants displayed per edge (D-027). Treat 9,689 edges as "
                "~2,279 observations for these, not 9,689."),
            "suspect_long_edge": (
                "764 edges / 24.4% of route km. A PATH-analysis caveat, not a "
                "length filter -- F-041 showed excluding them makes route-km "
                "agreement worse because their length is real."),
            "speed_is_fallback": (
                "35.6% of edges carry a substituted 50 km/h, not a measurement "
                "(D-029). Observed run-times imply the declared value is ~2x too "
                "high anyway (F-036) -- prefer service_edges.runtime_min_median."),
            "stitch_length_unchanged": (
                "2,252 stitch edges keep their as-built length (length_source="
                "stitch_as_built); D-026 specified the hybrid for consecutive "
                "station placements only (F-043)."),
        })
    outputs["manifest"] = manifest

    # D-039: attribute-level round trip + completeness against the Phase 2 CSVs
    rt = IO.verify_roundtrip(G, OUT, graphml="rail_graph_v1_1.graphml")
    sh = IO.verify_against_shipped(OUT, graphml="rail_graph_v1_1.graphml",
                                   length_col="length_km_v10")
    gates += [
        {"gate": "d_export_roundtrip_attribute_exact", "pass": bool(rt["all_roundtrip_ok"]),
         "detail": {k: rt[k] for k in ("graphml", "parquet", "geojson")}},
        {"gate": "e_carries_every_phase2_column_and_value", "pass": bool(sh["complete"]),
         "detail": sh},
        {"gate": "f_every_edge_has_geometry_or_a_reason",
         "pass": bool(len(al) == G.number_of_edges()
                      and set(al.geometry_source) <= {"spine", "chord", "none"}
                      and int((al.geometry_source == "none").sum())
                      == rt["geojson"]["edge_features_null_geometry"]),
         "detail": geo_summary},
    ]

    report = {"experiment": "E-400", "title": "graph v1.1 provenance layer",
              "build_spec": bspec.to_dict(), "build_spec_hash": bspec.hash,
              "provenance_spec": pspec.to_dict(), "provenance_spec_hash": pspec.hash,
              "summary": summary, "topology_unchanged": topo, "gates": gates,
              "implements": ["D-025", "D-026", "D-027", "D-029", "D-030"],
              "findings": ["F-042", "F-043", "F-046"],
              "geometry_summary": geo_summary,
              "outputs": {k: str(v.name) for k, v in outputs.items()}}
    (OUT / "E-400_report.json").write_text(json.dumps(report, indent=2, default=str))

    print("\n--- v1.1 layer ---")
    for k, v in summary.items():
        print(f"  {k:28s} {v}")
    print("\n--- topology unchanged (v1.1 is additive) ---")
    for k, v in topo.items():
        print(f"  {k:28s} {v}")
    print("\n--- D-026 validation gates ---")
    for g in gates:
        print(f"  {g['gate']:34s} pass={g['pass']}")
        if g["gate"].startswith("b") and g.get("detail"):
            for h in g["detail"]:
                print(f"      rank {h['rank']:>4}  ({h['percentile']:.2f}%)  "
                      f"sinuosity {h['sinuosity']:.3f}  {h['corridor']}")
        if g["gate"].startswith("c") and g.get("comparison"):
            for r in g["comparison"]:
                print(f"      {r['version']}  national {r['national_dev_pct']:+.2f}%  "
                      f"zone median {r['zone_dev_median_pct']:+.2f}%  "
                      f"range [{r['zone_dev_min_pct']:+.1f}, {r['zone_dev_max_pct']:+.1f}]  "
                      f"r={r['pearson_r']}")

    ok = topo["pass"] and all(g["pass"] is not False for g in gates)
    print(f"\nwrote {OUT}")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
