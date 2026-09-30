"""
Stage 08 — Assemble the graph-input package and run the QA suite.

Produces the two tables the graph-engineering workstream actually consumes
(a junction node candidate table and an enriched corridor table), then runs
every integrity check and writes the machine-generated section of the
validation report.

Outputs
-------
graph_inputs/nodes_junctions.csv
graph_inputs/corridors_enriched.csv
graph_inputs/QA_SUMMARY.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import GRAPH_INPUT_VERSION, OUT_DIR, banner  # noqa: E402

LINES: list[str] = []


def say(msg: str = "") -> None:
    print(msg)
    LINES.append(msg)


def main() -> None:
    banner("STAGE 08 — ASSEMBLE GRAPH-INPUT PACKAGE + QA")

    junc = pd.read_csv(OUT_DIR / "junctions_canonical.csv")
    jcoord = pd.read_csv(OUT_DIR / "junction_coordinates.csv")
    matches = pd.read_csv(OUT_DIR / "junction_station_matches.csv")
    corridors = pd.read_csv(OUT_DIR / "corridors.csv")
    paths = pd.read_csv(OUT_DIR / "corridor_paths.csv")
    summ = pd.read_csv(OUT_DIR / "corridor_sequence_summary.csv")
    seq = pd.read_csv(OUT_DIR / "corridor_station_sequence.csv")

    # ------------------------------------------------------------------
    # Node candidate table
    # ------------------------------------------------------------------
    deg = pd.concat([corridors["corridor_a"], corridors["corridor_b"]]).value_counts()
    nodes = (
        junc[["junction_id", "canonical_junction_name", "junction_class",
              "n_raw_variants", "raw_variants", "merged_from_variants"]]
        .merge(jcoord[["canonical_junction_name", "longitude", "latitude",
                       "coord_method", "n_incident_corridors", "n_corridors_agreeing",
                       "agreement_ratio", "cluster_spread_km"]],
               on="canonical_junction_name", how="left")
        .merge(matches[["canonical_junction_name", "match_method", "station_code",
                        "station_name", "name_score", "spatial_gap_km",
                        "match_confidence", "nearest_station_code", "nearest_station_km"]],
               on="canonical_junction_name", how="left")
    )
    nodes["corridor_degree"] = nodes["canonical_junction_name"].map(deg).fillna(0).astype(int)
    nodes["source_file"] = "Railway_Network_.csv + Railway_Network_.geojson"
    nodes["graph_input_version"] = GRAPH_INPUT_VERSION
    nodes.to_csv(OUT_DIR / "nodes_junctions.csv", index=False)

    # ------------------------------------------------------------------
    # Enriched corridor table
    # ------------------------------------------------------------------
    enr = corridors.merge(
        paths[["corridor_id", "status", "n_segments", "n_components", "total_length_km",
               "spine_length_km", "spine_coverage", "spur_length_km"]],
        on="corridor_id", how="left",
    ).merge(
        summ[["corridor_id", "n_stations_found", "station_count_delta",
              "median_offset_km", "orientation"]],
        on="corridor_id", how="left",
    )
    enr = enr.rename(columns={
        "status": "reconstruction_status",
        "total_length_km": "geodesic_length_km",
        "geometry_length_km": "declared_shape_length_km",
    })
    enr["length_inflation_ratio"] = (
        enr["declared_shape_length_km"] / enr["geodesic_length_km"]
    )
    enr["graph_input_version"] = GRAPH_INPUT_VERSION
    enr.to_csv(OUT_DIR / "corridors_enriched.csv", index=False)

    # ------------------------------------------------------------------
    # QA suite
    # ------------------------------------------------------------------
    say("GRAPH-INPUT QA SUMMARY  (%s)" % GRAPH_INPUT_VERSION)
    say("=" * 70)
    say()
    say("-- KEY INTEGRITY --")
    say(f"junction_id unique                     : {nodes['junction_id'].is_unique}")
    say(f"canonical_junction_name unique         : {nodes['canonical_junction_name'].is_unique}")
    say(f"corridor_id unique                     : {enr['corridor_id'].is_unique}")
    say(f"corridor (a,b) pair unique             : "
        f"{not enr.duplicated(['corridor_a','corridor_b']).any()}")
    say(f"(corridor_id, sequence_index) unique   : "
        f"{not seq.duplicated(['corridor_id','sequence_index']).any()}")

    say()
    say("-- REFERENTIAL INTEGRITY --")
    jnames = set(nodes["canonical_junction_name"])
    bad_a = (~enr["corridor_a"].isin(jnames)).sum()
    bad_b = (~enr["corridor_b"].isin(jnames)).sum()
    say(f"corridor endpoints missing from nodes  : {int(bad_a + bad_b)}")
    say(f"sequence rows with unknown corridor_id : "
        f"{int((~seq['corridor_id'].isin(set(enr['corridor_id']))).sum())}")
    orphan_nodes = int((nodes['corridor_degree'] == 0).sum())
    say(f"junctions on zero corridors            : {orphan_nodes}")

    say()
    say("-- COVERAGE --")
    say(f"canonical junctions                    : {len(nodes):,}")
    say(f"  with a coordinate                    : {int(nodes['longitude'].notna().sum()):,} "
        f"({nodes['longitude'].notna().mean()*100:.1f}%)")
    say(f"  with high/medium station match       : "
        f"{int(nodes['match_confidence'].isin(['high','medium']).sum()):,}")
    say(f"corridors                              : {len(enr):,}")
    say(f"  with reconstructed spine             : {int(enr['spine_length_km'].notna().sum()):,}")
    say(f"  clean_path                           : "
        f"{int((enr['reconstruction_status']=='clean_path').sum()):,}")
    say(f"  with >=2 stations placed             : {int((enr['n_stations_found']>=2).sum()):,}")
    say(f"station placements                     : {len(seq):,}")
    say(f"  distinct stations placed             : {seq['station_code'].nunique():,}")

    say()
    say("-- GEOMETRY / WEIGHT SANITY --")
    say(f"total geodesic corridor length         : {enr['geodesic_length_km'].sum():,.0f} km")
    say(f"total declared (st_lengthshape) length : {enr['declared_shape_length_km'].sum():,.0f} km")
    say(f"median inflation ratio declared/geodesic: {enr['length_inflation_ratio'].median():.4f}")
    say("   (Year Book 2024-25 reports 69,439 route km; the geodesic total is the")
    say("    closer of the two, so geodesic lengths should be used as edge weights)")
    neg = int((enr["geodesic_length_km"] <= 0).sum())
    say(f"corridors with non-positive length     : {neg}")
    say(f"station perpendicular offset median    : {seq['offset_km'].median()*1000:.0f} m")
    say(f"station offsets > 1.5 km (weak placement): {int((seq['offset_km']>1.5).sum()):,}")

    say()
    say("-- MONOTONIC ORDERING CHECK --")
    bad_order = 0
    for cid, g in seq.groupby("corridor_id"):
        m = g.sort_values("sequence_index")["measure_km"].values
        if len(m) > 1 and not np.all(np.diff(m) >= -1e-9):
            bad_order += 1
    say(f"corridors whose measure_km is not monotonic: {bad_order}")

    say()
    say("-- SPINE SHORTCUT CHECK --")
    say("   Along-line distance between consecutive stations should never be shorter")
    say("   than their crow-flies distance once each station's lateral offset is")
    say("   accounted for. Where it is, the spine has cut a corner the real track does")
    say("   not (a chord or parallel line inside the corridor became the shortest path).")
    s = seq.sort_values(["corridor_id", "sequence_index"])
    nx_ = s.groupby("corridor_id").shift(-1)
    pair = s.assign(m2=nx_["measure_km"], lon2=nx_["station_longitude"],
                    lat2=nx_["station_latitude"], off2=nx_["offset_km"]).dropna(subset=["m2"])
    from config import haversine_km as _hv
    dd = _hv(pair["station_longitude"].values, pair["station_latitude"].values,
             pair["lon2"].values, pair["lat2"].values)
    dm = (pair["m2"] - pair["measure_km"]).values
    lat = pair["offset_km"].values + pair["off2"].values
    excess = dd - np.sqrt(dm ** 2 + lat ** 2)
    rel = np.where(dd > 0.05, excess / np.maximum(dd, 1e-9), 0.0)
    aff = excess > 0.001
    say(f"consecutive station pairs              : {len(dd):,}")
    say(f"  affected at all                      : {int(aff.sum()):,} ({aff.mean()*100:.1f}%)")
    say(f"  shortfall > 10% of pair distance      : {int((aff & (rel > 0.10)).sum()):,}")
    say(f"  shortfall > 25% of pair distance      : {int((aff & (rel > 0.25)).sum()):,}")
    say(f"  median shortfall among affected       : {np.median(rel[aff])*100:.2f}%")

    say()
    say("-- CONNECTIVITY OF THE CANONICAL JUNCTION NETWORK --")
    G = nx.Graph()
    G.add_nodes_from(nodes["canonical_junction_name"])
    for _, r in enr.iterrows():
        if r["corridor_a"] != r["corridor_b"]:
            G.add_edge(r["corridor_a"], r["corridor_b"])
    ccs = sorted(nx.connected_components(G), key=len, reverse=True)
    say(f"nodes                                  : {G.number_of_nodes():,}")
    say(f"edges                                  : {G.number_of_edges():,}")
    say(f"connected components                   : {len(ccs):,}   (was 113 before canonicalisation)")
    say(f"largest component                      : {len(ccs[0]):,} nodes "
        f"({len(ccs[0])/G.number_of_nodes()*100:.1f}%)")
    say(f"isolated 2-node components             : {sum(1 for c in ccs if len(c)==2):,}")

    say()
    say("-- WHAT REMAINS OPEN FOR GRAPH ENGINEERING --")
    amb = int((nodes["coord_method"] == "spine_end_ambiguous").sum())
    rej = int((nodes["match_confidence"] == "rejected_name_spatial_conflict").sum())
    multi = seq.groupby("station_code")["corridor_id"].nunique()
    say(f"junctions with ambiguous coordinate    : {amb}")
    say(f"name matches rejected on spatial conflict: {rej}")
    say(f"stations sitting on >2 corridors        : {int((multi>2).sum()):,}")
    say(f"corridors still fragmented (>1 component): {int((enr['n_components']>1).sum()):,}")
    say(f"corridors with 0 stations placed        : {int((enr['n_stations_found']==0).sum()):,}")

    (OUT_DIR / "QA_SUMMARY.txt").write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print()
    print(f"WROTE {OUT_DIR / 'nodes_junctions.csv'}")
    print(f"WROTE {OUT_DIR / 'corridors_enriched.csv'}")
    print(f"WROTE {OUT_DIR / 'QA_SUMMARY.txt'}")


if __name__ == "__main__":
    main()
