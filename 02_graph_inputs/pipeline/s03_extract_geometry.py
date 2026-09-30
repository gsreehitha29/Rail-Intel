"""
Stage 03 — Extract per-segment geometry from Railway_Network_.geojson.

Streams the 88 MB GeoJSON line-by-line (one Feature per line) so that the whole
file is never held in memory, and caches a compact parquet with each segment's
WKB geometry, endpoints and true geodesic length.

Output (cache, not a deliverable):
pipeline/cache/segments_geometry.parquet
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import LineString
from shapely import wkb as shapely_wkb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (  # noqa: E402
    CACHE_DIR, RAW_NETWORK_GEOJSON, banner, haversine_km, normalize_junction_name,
)


def chain_length_km(coords) -> float:
    a = np.asarray(coords, dtype=float)
    if len(a) < 2:
        return 0.0
    return float(haversine_km(a[:-1, 0], a[:-1, 1], a[1:, 0], a[1:, 1]).sum())


def main() -> None:
    banner("STAGE 03 — SEGMENT GEOMETRY EXTRACTION")
    print(f"Streaming {RAW_NETWORK_GEOJSON.name} ...")

    rows = []
    n_lines = 0
    n_features = 0
    n_multi = 0
    n_skipped = 0

    with open(RAW_NETWORK_GEOJSON, "r", encoding="utf-8") as fh:
        for line in fh:
            n_lines += 1
            line = line.strip()
            if not line.startswith('{ "type": "Feature"') and not line.startswith('{"type": "Feature"'):
                continue
            if line.endswith(","):
                line = line[:-1]
            try:
                feat = json.loads(line)
            except json.JSONDecodeError:
                n_skipped += 1
                continue

            n_features += 1
            props = feat.get("properties", {}) or {}
            geom = feat.get("geometry") or {}
            gtype = geom.get("type")
            coords = geom.get("coordinates")
            if not coords:
                n_skipped += 1
                continue

            if gtype == "MultiLineString":
                n_multi += 1
                # keep the longest part; the remainder is recorded in part_count
                parts = [c for c in coords if c and len(c) >= 2]
                if not parts:
                    n_skipped += 1
                    continue
                part_count = len(parts)
                coords = max(parts, key=chain_length_km)
            elif gtype == "LineString":
                part_count = 1
                if len(coords) < 2:
                    n_skipped += 1
                    continue
            else:
                n_skipped += 1
                continue

            f_can = normalize_junction_name(props.get("fromjunction"))
            t_can = normalize_junction_name(props.get("tojunction"))
            a, b = (f_can, t_can) if f_can <= t_can else (t_can, f_can)

            ls = LineString(coords)
            rows.append({
                "objectid": props.get("objectid"),
                "seg_id": props.get("id"),
                "from_canonical": f_can,
                "to_canonical": t_can,
                "corridor_a": a,
                "corridor_b": b,
                "geom_type": gtype,
                "part_count": part_count,
                "n_coords": len(coords),
                "start_lon": float(coords[0][0]), "start_lat": float(coords[0][1]),
                "end_lon": float(coords[-1][0]), "end_lat": float(coords[-1][1]),
                "length_km": chain_length_km(coords),
                "declared_length_m": props.get("st_lengthshape"),
                "wkb": shapely_wkb.dumps(ls),
            })

            if n_features % 20000 == 0:
                print(f"  ... {n_features:,} features parsed")

    df = pd.DataFrame(rows)
    print()
    print(f"Lines read              : {n_lines:,}")
    print(f"Features parsed         : {n_features:,}")
    print(f"MultiLineString features: {n_multi}")
    print(f"Skipped (no usable geom): {n_skipped}")
    print(f"Segments cached         : {len(df):,}")
    print()
    print("Segments with an empty canonical endpoint name (excluded from corridors):",
          int(((df['from_canonical'] == '') | (df['to_canonical'] == '')).sum()))

    gl = df["length_km"].sum()
    dl = pd.to_numeric(df["declared_length_m"], errors="coerce").sum() / 1000.0
    print(f"Total geodesic length of all segments : {gl:,.1f} km")
    print(f"Total st_lengthshape of all segments  : {dl:,.1f} km")
    print(f"Ratio (geodesic / declared)           : {gl/dl:.4f}")

    out = CACHE_DIR / "segments_geometry.parquet"
    df.to_parquet(out, index=False)
    print()
    print(f"WROTE {out}  ({out.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
