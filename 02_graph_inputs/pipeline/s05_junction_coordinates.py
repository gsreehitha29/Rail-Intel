"""
Stage 05 — Geometry-derived junction coordinates.

Addresses validation gap #6 (1,339 junctions with no coordinates, previously
approached by nearest-station guessing with poor results).

Key idea
--------
Every reconstructed corridor spine has exactly two ends, and those two ends ARE
the corridor's two named junctions - we just don't know which end is which. A
junction shared by k corridors therefore has k spine-ends that should converge
on one location. Choosing, for each junction, the cluster where the most
distinct corridors agree recovers the junction's true position from geometry
alone, with no dependence on the station master at all.

That means coordinates become available for junctions that will NEVER appear in
a passenger station master (cabins, yards, block huts) - exactly the 260-odd
nodes GRAPH_HANDOFF flagged as needing a geometric solution.

Outputs
-------
graph_inputs/junction_coordinates.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from shapely import wkb as shapely_wkb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CACHE_DIR, GRAPH_INPUT_VERSION, OUT_DIR, banner, haversine_km  # noqa: E402

CLUSTER_TOL_KM = 2.0


def main() -> None:
    banner("STAGE 05 — GEOMETRY-DERIVED JUNCTION COORDINATES")

    spines = pd.read_parquet(CACHE_DIR / "corridor_spines.parquet")
    corridors = pd.read_csv(OUT_DIR / "corridors.csv")
    junctions = pd.read_csv(OUT_DIR / "junctions_canonical.csv")

    spine_ends = {}
    for _, r in spines.iterrows():
        line = shapely_wkb.loads(r["wkb"])
        c = list(line.coords)
        spine_ends[r["corridor_id"]] = (c[0], c[-1])
    print(f"Corridor spines with ends: {len(spine_ends):,}")

    cor = corridors[corridors["corridor_id"].isin(spine_ends)].copy()

    # junction -> list of (corridor_id, end_index)
    incident: dict[str, list] = {}
    for _, r in cor.iterrows():
        for j in (r["corridor_a"], r["corridor_b"]):
            incident.setdefault(j, []).append(r["corridor_id"])
    print(f"Junctions appearing on >=1 corridor: {len(incident):,}")

    resolved = {}
    rows = []

    # ---- pass 1: junctions on >= 2 corridors, resolved by consensus -------
    for jname, cids in incident.items():
        cands = []  # (corridor_id, end_idx, lon, lat)
        for cid in cids:
            e0, e1 = spine_ends[cid]
            cands.append((cid, 0, e0[0], e0[1]))
            cands.append((cid, 1, e1[0], e1[1]))
        if len(cids) < 2:
            continue

        arr = np.array([[c[2], c[3]] for c in cands])
        best = None
        for i in range(len(cands)):
            d = haversine_km(arr[i, 0], arr[i, 1], arr[:, 0], arr[:, 1])
            near = d <= CLUSTER_TOL_KM
            distinct = {cands[k][0] for k in np.flatnonzero(near)}
            score = (len(distinct), -float(d[near].mean()))
            if best is None or score > best[0]:
                best = (score, near)
        near = best[1]
        members = [cands[k] for k in np.flatnonzero(near)]
        distinct_cor = {m[0] for m in members}
        lon = float(np.mean([m[2] for m in members]))
        lat = float(np.mean([m[3] for m in members]))
        spread = float(haversine_km(
            [m[2] for m in members], [m[3] for m in members], lon, lat
        ).max()) if len(members) > 1 else 0.0

        resolved[jname] = (lon, lat)
        rows.append(dict(
            canonical_junction_name=jname, longitude=lon, latitude=lat,
            coord_method="spine_end_consensus", n_incident_corridors=len(cids),
            n_corridors_agreeing=len(distinct_cor),
            agreement_ratio=len(distinct_cor) / len(cids),
            cluster_spread_km=spread,
        ))

    print(f"Pass 1 (consensus, >=2 corridors): {len(rows):,} junctions resolved")

    # ---- pass 2: degree-1 junctions, resolved by elimination -------------
    pass2 = 0
    for jname, cids in incident.items():
        if jname in resolved or len(cids) != 1:
            continue
        cid = cids[0]
        row = cor[cor["corridor_id"] == cid].iloc[0]
        other = row["corridor_b"] if row["corridor_a"] == jname else row["corridor_a"]
        e0, e1 = spine_ends[cid]
        if other in resolved:
            olon, olat = resolved[other]
            d0 = float(haversine_km(e0[0], e0[1], olon, olat))
            d1 = float(haversine_km(e1[0], e1[1], olon, olat))
            pick = e0 if d0 > d1 else e1  # this junction is the FAR end
            method, conf = "spine_end_by_elimination", 1.0
        else:
            pick = e0
            method, conf = "spine_end_ambiguous", 0.0
        resolved[jname] = (pick[0], pick[1])
        rows.append(dict(
            canonical_junction_name=jname, longitude=float(pick[0]), latitude=float(pick[1]),
            coord_method=method, n_incident_corridors=1, n_corridors_agreeing=1,
            agreement_ratio=conf, cluster_spread_km=0.0,
        ))
        pass2 += 1
    print(f"Pass 2 (degree-1 elimination)    : {pass2:,} junctions resolved")

    out = pd.DataFrame(rows)
    out = junctions[["junction_id", "canonical_junction_name", "junction_class",
                     "n_raw_variants", "match_key"]].merge(
        out, on="canonical_junction_name", how="left"
    )
    out["has_geometry_coordinate"] = out["longitude"].notna()
    out["graph_input_version"] = GRAPH_INPUT_VERSION

    print()
    print(f"Junctions total                     : {len(out):,}")
    print(f"With geometry-derived coordinate    : {int(out['has_geometry_coordinate'].sum()):,} "
          f"({out['has_geometry_coordinate'].mean()*100:.1f}%)")
    print(f"Without                             : {int((~out['has_geometry_coordinate']).sum()):,}")
    print()
    print("Coordinate method:")
    print(out["coord_method"].value_counts(dropna=False).to_string())
    print()
    good = out[out["coord_method"] == "spine_end_consensus"]
    print("Consensus quality (junctions on >=2 corridors):")
    print(f"  all incident corridors agree     : {int((good['agreement_ratio']>=0.999).sum()):,}")
    print(f"  >=75% agree                      : {int((good['agreement_ratio']>=0.75).sum()):,}")
    print(f"  <50% agree (suspect)             : {int((good['agreement_ratio']<0.5).sum()):,}")
    print(f"  median cluster spread            : {good['cluster_spread_km'].median()*1000:.0f} m")
    print(f"  cluster spread > 1 km            : {int((good['cluster_spread_km']>1).sum()):,}")

    # sanity: coordinates inside India-ish bounds
    inb = out["longitude"].between(67, 98) & out["latitude"].between(6, 38)
    print()
    print(f"Coordinates outside plausible bounds: {int((out['has_geometry_coordinate'] & ~inb).sum())}")

    out.to_csv(OUT_DIR / "junction_coordinates.csv", index=False)
    print()
    print(f"WROTE {OUT_DIR / 'junction_coordinates.csv'}")


if __name__ == "__main__":
    main()
