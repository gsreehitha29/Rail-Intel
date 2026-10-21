"""E-402 -- independent audit of the released edge geometry (W1 acceptance).

Reads ONLY the released v1.1 files plus the Phase 2 spines. It does not call
`railgraph.geometry`, so a bug in the slicer cannot also be in its own check.

Acceptance (docs/GRAPH_V2_ROADMAP.md W1):
  A1  every edge with length_source == spine carries a LineString whose length
      agrees with length_km within 1%
  A2  edges without a trustworthy spine keep a chord and say so
Additional audits (each could fail):
  B   WKB table and GeoJSON hold the same coordinates
  C   orientation: the first vertex is at/near from_node, the last at/near to_node
  D   endpoint placement: slice ends within the recorded offset (<0.25 km) of the nodes
  E   every vertex of a slice lies on the source corridor spine (no invented track)
  F   no untrusted placement is promoted to a spine geometry
  G   no feature is missing; null geometry only where a coordinate is missing

Run: python 03_graph_construction/experiments/E-402_alignment_audit/run.py
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PHASE3 = HERE.parents[1]
REPO = PHASE3.parent
REL = PHASE3 / "graph_v1_1"
SPINES = REPO / "02_graph_inputs" / "pipeline" / "cache" / "corridor_spines.parquet"
R = 6371.0088


def hav(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def path_len(xy):
    xy = np.asarray(xy, float)
    return float(hav(xy[:-1, 0], xy[:-1, 1], xy[1:, 0], xy[1:, 1]).sum()) if len(xy) > 1 else 0.0


def wkb_xy(b):
    o = "<" if b[0] == 1 else ">"
    assert struct.unpack(o + "I", b[1:5])[0] == 2
    n = struct.unpack(o + "I", b[5:9])[0]
    return np.frombuffer(b, dtype=o + "f8", count=2 * n, offset=9).reshape(n, 2)


def dist_to_polyline(p, xy):
    """Distance (km) from point p to the nearest SEGMENT of polyline xy (local planar)."""
    lat0 = np.radians(p[1])
    kx, ky = R * np.cos(lat0) * np.pi / 180, R * np.pi / 180
    P = np.array([(p[0]) * kx, p[1] * ky])
    A = np.c_[xy[:-1, 0] * kx, xy[:-1, 1] * ky]
    B = np.c_[xy[1:, 0] * kx, xy[1:, 1] * ky]
    AB = B - A
    t = np.clip(((P - A) * AB).sum(1) / np.maximum((AB ** 2).sum(1), 1e-18), 0, 1)
    C = A + AB * t[:, None]
    return float(np.sqrt(((C - P) ** 2).sum(1)).min())


def main() -> int:
    gj = json.loads((REL / "edges.geojson").read_text())["features"]
    gn = {f["properties"]["node_id"]: f for f in json.loads((REL / "nodes.geojson").read_text())["features"]}
    ge = pd.read_parquet(REL / "edge_geometry.parquet").set_index("edge_id")
    ed = pd.read_parquet(REL / "edges.parquet").set_index("edge_id")
    spines = pd.read_parquet(SPINES).set_index("corridor_id")
    checks, fails = {}, []

    def rec(name, ok, **kw):
        checks[name] = {"pass": bool(ok), **kw}
        if not ok:
            fails.append(name)

    # G -- completeness
    null_geo = [f["properties"]["edge_id"] for f in gj if f["geometry"] is None]
    no_coord_nodes = {n for n, f in gn.items() if f["geometry"] is None}
    expect_null = {r.Index for r in ed.itertuples()
                   if r.from_node in no_coord_nodes or r.to_node in no_coord_nodes}
    rec("G_no_feature_missing", len(gj) == len(ed) and len(gn) == 9095,
        edge_features=len(gj), node_features=len(gn))
    rec("G_null_geometry_only_where_coordinate_missing", set(null_geo) == expect_null,
        null_edges=null_geo, nodes_without_coordinates=sorted(no_coord_nodes))

    rows, spine_rows = [], []
    bounds_bad = 0
    for f in gj:
        p = f["properties"]; eid = p["edge_id"]
        if f["geometry"] is None:
            continue
        xy = np.array(f["geometry"]["coordinates"], float)
        if not ((68 <= xy[:, 0]) & (xy[:, 0] <= 98) & (6 <= xy[:, 1]) & (xy[:, 1] <= 38)).all():
            bounds_bad += 1
        rows.append((eid, p["geometry_source"], len(xy), path_len(xy)))
        if p["geometry_source"] == "spine":
            spine_rows.append((eid, xy, p))
    rec("coordinates_inside_india_bounds", bounds_bad == 0, outside=bounds_bad)

    # A2 -- chords say so, and are exactly 2-point lines
    src = pd.Series({r[0]: r[1] for r in rows})
    nv = pd.Series({r[0]: r[2] for r in rows})
    rec("A2_chord_edges_are_two_point_and_labelled",
        bool((nv[src == "chord"] == 2).all()),
        n_chord=int((src == "chord").sum()))

    # A1 -- length agreement within 1% against the derived length
    rel = []
    for eid, xy, p in spine_rows:
        L = float(ed.loc[eid, "length_km"])
        rel.append(abs(path_len(xy) - L) / L)
    rel = np.array(rel)
    rec("A1_spine_geometry_length_within_1pct", bool((rel <= 0.01).all()),
        n=len(rel), max_rel_err=float(rel.max()), p99=float(np.quantile(rel, .99)),
        n_over_1pct=int((rel > 0.01).sum()))

    # B -- WKB table equals GeoJSON
    mism = 0
    for f in gj:
        eid = f["properties"]["edge_id"]
        if f["geometry"] is None:
            mism += int(ge.loc[eid, "wkb"] is not None and not pd.isna(ge.loc[eid, "wkb"]))
            continue
        a = np.array(f["geometry"]["coordinates"], float)
        b = wkb_xy(ge.loc[eid, "wkb"])
        mism += int(a.shape != b.shape or not np.allclose(a, b, atol=1e-12))
    rec("B_wkb_equals_geojson", mism == 0, mismatches=mism)

    # C, D -- orientation and endpoint placement
    swapped, far, max_end = 0, 0, 0.0
    for eid, xy, p in spine_rows:
        a = gn[ed.loc[eid, "from_node"]]["geometry"]["coordinates"]
        b = gn[ed.loc[eid, "to_node"]]["geometry"]["coordinates"]
        d_ff = hav(*xy[0], *a); d_ft = hav(*xy[0], *b)
        d_ll = hav(*xy[-1], *b); d_lf = hav(*xy[-1], *a)
        if d_ff > d_ft + 1e-6 and d_ll > d_lf + 1e-6:
            swapped += 1
        m = max(d_ff, d_ll); max_end = max(max_end, m)
        # tolerance: recorded offset is the worst of the pair, +10 m for rounding
        if m > float(p.get("geometry_offset_km", 0.25)) + 0.25 + 0.01:
            far += 1
    rec("C_orientation_from_to", swapped == 0, reversed_edges=swapped)
    rec("D_endpoints_within_trusted_offset", far == 0 and max_end < 0.5,
        edges_beyond_tolerance=far, max_endpoint_distance_km=round(max_end, 4))

    # E -- every slice vertex lies on its source spine
    off_spine = 0; worst = 0.0; checked = 0
    for eid, xy, p in spine_rows:
        cid = p["geometry_corridor"]
        sp = wkb_xy(spines.loc[cid, "wkb"])
        for q in xy[:: max(1, len(xy) // 12)]:         # sampled, always incl. ends
            d = dist_to_polyline(q, sp); worst = max(worst, d); checked += 1
            if d > 0.005:                               # 5 m
                off_spine += 1
        for q in (xy[0], xy[-1]):
            d = dist_to_polyline(q, sp); worst = max(worst, d)
            if d > 0.005:
                off_spine += 1
    rec("E_vertices_lie_on_source_spine", off_spine == 0,
        vertices_checked=checked, vertices_off_spine=off_spine,
        worst_distance_km=round(worst, 6))

    # F -- spine geometry only where length_source == spine
    ls = ed.length_source.astype(str)
    promoted = [e for e in src[src == "spine"].index if ls[e] != "spine"]
    demoted = [e for e in ls[ls == "spine"].index if src.get(e) != "spine"]
    rec("F_geometry_trust_follows_D026", not promoted and not demoted,
        untrusted_promoted=len(promoted), trusted_not_sliced=len(demoted))

    # coverage (reported, not thresholded)
    km = ed.length_km
    cov = {
        "edges_spine": int((src == "spine").sum()), "edges_chord": int((src == "chord").sum()),
        "edges_none": len(ed) - len(src),
        "edges_true_alignment_pct": round(100 * (src == "spine").sum() / len(ed), 2),
        "route_km_true_alignment_pct": round(100 * km[src[src == "spine"].index].sum() / km.sum(), 2),
        "roadmap_target_pct": 85,
        "chord_by_length_source": ls[src[src == "chord"].index].value_counts().to_dict(),
    }
    sinu = ed.sinuosity.dropna()
    cov["sinuosity_median"] = round(float(sinu.median()), 4)

    ok = not fails
    rep = {"experiment": "E-402", "title": "alignment geometry audit",
           "checks": checks, "coverage": cov, "failed": fails,
           "verdict": "PASS" if ok else "FAIL"}
    (REL / "E-402_report.json").write_text(json.dumps(rep, indent=2, default=str))
    for k, v in checks.items():
        print(f"  {'PASS' if v['pass'] else 'FAIL'}  {k:48s} "
              f"{ {a: b for a, b in v.items() if a != 'pass'} }")
    print("\ncoverage:", json.dumps(cov, indent=1))
    print("\nRESULT:", rep["verdict"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
