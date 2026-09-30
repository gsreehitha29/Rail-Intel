"""
Stage 02 — Single authoritative corridor table.

Fixes validation gap #1 (three code paths produced three different corridor
counts: 2,305 / 2,290 / 2,257) by defining ONE corridor rule and emitting it
once, and gap #2 (corridors are keyed on canonical junction names).

Corridor definition
-------------------
A corridor is the set of raw GIS segments sharing the same *unordered* pair of
canonical junction names. Unordered, because a physical railway line A-B is the
same infrastructure as B-A. The direction(s) actually observed in the source
are preserved in `observed_directions` so that a directed view remains
available downstream without re-deriving it from raw.

Attribute rules
---------------
- geometry_length_km : SUM of st_lengthshape over segments (metres -> km)
- categorical/numeric attributes : MODE across segments, with an explicit
  `<attr>_conflict` flag and `<attr>_n_distinct` count
- zeros in speed/tracklength/noofstations/nooflanes are treated as UNKNOWN
  (set to NaN) and counted in `<attr>_zero_segments`, never silently imputed
- bridge_present / tunnel_present : True if ANY segment flags it

Outputs
-------
graph_inputs/corridors.csv
graph_inputs/segments_quarantined.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
from config import GRAPH_INPUT_VERSION, OUT_DIR, RAW_NETWORK_CSV, banner, normalize_junction_name  # noqa: E402

ZERO_AS_UNKNOWN = ["speed", "tracklength", "noofstations", "nooflanes"]


def mode_or_nan(s: pd.Series):
    s = s.dropna()
    if s.empty:
        return np.nan
    m = s.mode()
    return m.iloc[0] if len(m) else np.nan


def main() -> None:
    banner("STAGE 02 — AUTHORITATIVE CORRIDOR TABLE")

    df = pd.read_csv(RAW_NETWORK_CSV, low_memory=False)
    print(f"Raw GIS segment rows: {len(df):,}")

    df["from_canonical"] = df["fromjunction"].apply(normalize_junction_name)
    df["to_canonical"] = df["tojunction"].apply(normalize_junction_name)

    # ---- quarantine rows that cannot define a corridor -------------------
    bad = (df["from_canonical"] == "") | (df["to_canonical"] == "")
    quarantine = df[bad].copy()
    quarantine["quarantine_reason"] = np.where(
        (quarantine["from_canonical"] == "") & (quarantine["to_canonical"] == ""),
        "both_endpoints_missing",
        np.where(quarantine["from_canonical"] == "",
                 "from_endpoint_missing", "to_endpoint_missing"),
    )
    print(f"Quarantined segments (missing endpoint name): {len(quarantine):,}")
    print(quarantine["quarantine_reason"].value_counts().to_string())

    valid = df[~bad].copy()
    print(f"Valid segments used for corridors: {len(valid):,}")

    # ---- zero -> unknown, with counters ---------------------------------
    for col in ZERO_AS_UNKNOWN:
        valid[f"{col}_is_zero"] = (valid[col] == 0)
        valid.loc[valid[col] == 0, col] = np.nan
    neg_lanes = int((valid["nooflanes"] < 0).sum())
    valid["nooflanes_is_negative"] = valid["nooflanes"] < 0
    valid.loc[valid["nooflanes"] < 0, "nooflanes"] = np.nan
    print(f"Negative nooflanes values set to unknown: {neg_lanes}")

    # Canonicalise the zone BEFORE grouping. Four spellings in the raw GIS
    # layer are typos of real zones; left uncorrected they both mislabel the
    # corridor and inflate the zone-conflict count.
    valid["railwayzone"] = (
        valid["railwayzone"].map(config.zone_name).astype("string")
    )
    valid["type"] = valid["type"].astype("string").str.strip().replace("", pd.NA)

    # ---- unordered corridor key -----------------------------------------
    pair = np.sort(valid[["from_canonical", "to_canonical"]].to_numpy(), axis=1)
    valid["corridor_a"] = pair[:, 0]
    valid["corridor_b"] = pair[:, 1]
    valid["direction_observed"] = np.where(
        valid["from_canonical"] == valid["corridor_a"], "a_to_b", "b_to_a"
    )

    g = valid.groupby(["corridor_a", "corridor_b"], sort=True)

    corridors = pd.DataFrame({
        "segment_count": g.size(),
        "geometry_length_m": g["st_lengthshape"].sum(),
        "speed_kmph": g["speed"].agg(mode_or_nan),
        "gauge": g["type"].agg(mode_or_nan),
        "declared_no_of_stations": g["noofstations"].agg(mode_or_nan),
        "declared_track_length_km": g["tracklength"].agg(mode_or_nan),
        "no_of_lanes": g["nooflanes"].agg(mode_or_nan),
        "railway_zone": g["railwayzone"].agg(mode_or_nan),
        "bridge_present": g["bridge_yn"].agg(lambda x: (x == "Y").any()),
        "tunnel_present": g["tunnel_yn"].agg(lambda x: (x == "Y").any()),
        "zone_count": g["railwayzone"].nunique(dropna=True),
    }).reset_index()

    # conflict flags + distinct counts
    conflict_map = {
        "speed": "speed_kmph", "type": "gauge", "noofstations": "declared_no_of_stations",
        "tracklength": "declared_track_length_km", "nooflanes": "no_of_lanes",
        "railwayzone": "railway_zone",
    }
    for raw_col, out_col in conflict_map.items():
        nunique = g[raw_col].nunique(dropna=True).reset_index(drop=True)
        corridors[f"{out_col}_n_distinct"] = nunique.values
        corridors[f"{out_col}_conflict"] = nunique.values > 1

    for col in ZERO_AS_UNKNOWN:
        corridors[f"{col}_zero_segments"] = g[f"{col}_is_zero"].sum().values

    dir_sets = g["direction_observed"].agg(lambda s: set(s)).reset_index(drop=True)
    corridors["observed_directions"] = [
        "both" if len(s) > 1 else list(s)[0] for s in dir_sets
    ]

    corridors["geometry_length_km"] = corridors["geometry_length_m"] / 1000.0
    corridors["is_self_loop"] = corridors["corridor_a"] == corridors["corridor_b"]
    corridors["any_attribute_conflict"] = corridors[
        [c for c in corridors.columns if c.endswith("_conflict")]
    ].any(axis=1)

    corridors = corridors.sort_values(["corridor_a", "corridor_b"]).reset_index(drop=True)
    corridors.insert(0, "corridor_id", ["C%05d" % (i + 1) for i in range(len(corridors))])
    corridors["source_file"] = "Railway_Network_.csv"
    corridors["graph_input_version"] = GRAPH_INPUT_VERSION

    print()
    print(f"CORRIDORS (canonical, unordered): {len(corridors):,}")
    print(f"  self-loop corridors: {int(corridors['is_self_loop'].sum())}")
    print(f"  with >=1 attribute conflict: {int(corridors['any_attribute_conflict'].sum())}")
    print(f"  observed in both directions: {int((corridors['observed_directions']=='both').sum())}")
    print(f"  spanning >1 railway zone: {int((corridors['zone_count']>1).sum())}")
    print()
    print("Missing representative attribute values:")
    for col in ["speed_kmph", "gauge", "declared_no_of_stations",
                "declared_track_length_km", "no_of_lanes", "railway_zone"]:
        print(f"  {col}: {int(corridors[col].isna().sum())}")

    # segment -> corridor provenance map
    seg_map = valid[["objectid", "id", "corridor_a", "corridor_b",
                     "from_canonical", "to_canonical", "direction_observed"]].merge(
        corridors[["corridor_id", "corridor_a", "corridor_b"]],
        on=["corridor_a", "corridor_b"], how="left",
    )

    corridors.to_csv(OUT_DIR / "corridors.csv", index=False)
    quarantine.to_csv(OUT_DIR / "segments_quarantined.csv", index=False)
    seg_map.to_parquet(Path(__file__).resolve().parent / "cache" / "segment_corridor_map.parquet")
    print()
    print(f"WROTE {OUT_DIR / 'corridors.csv'}")
    print(f"WROTE {OUT_DIR / 'segments_quarantined.csv'}")


if __name__ == "__main__":
    main()
