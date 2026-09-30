"""
Stage 06 — Tiered junction <-> station-master matching with confidence.

Addresses validation gaps #5 and #6, and satisfies the blueprint requirement
that "station matching must have a documented rule, confidence score/status".

Method
------
Name matching is SPATIALLY CONSTRAINED. For each junction we first take the set
of stations within CANDIDATE_RADIUS_KM of its geometry-derived coordinate
(stage 05), and only then apply name tiers inside that set:

  1 exact_name     canonical match_key == station match_key      (in radius)
  2 relaxed_name   match after stripping railway suffixes        (in radius)
  3 fuzzy_name     rapidfuzz WRatio >= FUZZY_MIN on relaxed key  (in radius)
  4 spatial_only   nearest station, no name evidence

If a name matches only OUTSIDE the radius, that is recorded explicitly as
`*_spatial_conflict` rather than accepted - this is what catches same-name-
different-place errors (the ~1,000-2,000 km mismatches found in validation).

Constraining fuzzy matching by geography is what makes it safe: an unconstrained
fuzzy pass over all 8,697 stations produced matches like
"Thiruvananthapuram Central" -> "PURA HALT" 2,017 km away.

Nothing is dropped and nothing is auto-accepted; the graph designer filters on
`match_confidence`. The spatial alternative is always reported alongside, in
`nearest_station_code` / `nearest_station_km`.

Outputs
-------
graph_inputs/junction_station_matches.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from rapidfuzz import process as rf_process, fuzz as rf_fuzz
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (  # noqa: E402
    CLEANED_STATIONS, GRAPH_INPUT_VERSION, OUT_DIR, banner, haversine_km,
    match_key, relaxed_key, to_local_xy,
)

CANDIDATE_RADIUS_KM = 15.0   # name matching is only trusted inside this radius
FUZZY_MIN = 88.0
HIGH_MAX_KM = 2.0
MEDIUM_MAX_KM = 8.0
SPATIAL_HIGH_KM = 0.5
SPATIAL_LOW_KM = 3.0


def main() -> None:
    banner("STAGE 06 — TIERED JUNCTION <-> STATION MATCHING")

    jc = pd.read_csv(OUT_DIR / "junction_coordinates.csv")
    st = pd.read_csv(CLEANED_STATIONS)
    st = st[st["spatially_usable"] == True].copy().reset_index(drop=True)  # noqa: E712
    st["match_key"] = st["station_name"].apply(match_key)
    st["relaxed_key"] = st["station_name"].apply(relaxed_key)
    print(f"Junctions            : {len(jc):,}")
    print(f"Stations with coords : {len(st):,}")
    print(f"Name-match radius    : {CANDIDATE_RADIUS_KM:.0f} km")

    sx, sy = to_local_xy(st["longitude"].values, st["latitude"].values)
    tree = cKDTree(np.column_stack([sx, sy]))

    st_mk = st["match_key"].values
    st_rk = st["relaxed_key"].values
    st_lon = st["longitude"].values
    st_lat = st["latitude"].values
    st_code = st["station_code"].values
    st_name = st["station_name"].values

    global_exact: dict[str, list] = {}
    for i, mk in enumerate(st_mk):
        global_exact.setdefault(mk, []).append(i)

    rows = []
    for _, j in jc.iterrows():
        jlon, jlat = j["longitude"], j["latitude"]
        has_coord = bool(pd.notna(jlon) and pd.notna(jlat))
        jkey = j["match_key"] if pd.notna(j["match_key"]) else ""
        jrel = relaxed_key(j["canonical_junction_name"])

        local: np.ndarray = np.array([], dtype=int)
        nearest_i, nearest_km = None, np.nan
        if has_coord:
            jx, jy = to_local_xy([jlon], [jlat])
            pt = np.column_stack([jx, jy])
            local = np.array(tree.query_ball_point(pt, CANDIDATE_RADIUS_KM)[0], dtype=int)
            _, ni = tree.query(pt, k=1)
            nearest_i = int(np.atleast_1d(ni)[0])
            nearest_km = float(haversine_km(jlon, jlat, st_lon[nearest_i], st_lat[nearest_i]))

        method, pick, score = "none", None, np.nan
        n_cand = 0

        def choose(idxs):
            """Pick the spatially nearest among equally-named candidates."""
            if len(idxs) == 1:
                return int(idxs[0])
            d = haversine_km(jlon, jlat, st_lon[idxs], st_lat[idxs])
            return int(idxs[int(np.argmin(d))])

        if len(local) and jkey:
            hit = local[st_mk[local] == jkey]
            if len(hit):
                method, pick, score, n_cand = "exact_name", choose(hit), 100.0, len(hit)

        if pick is None and len(local) and jrel:
            hit = local[st_rk[local] == jrel]
            if len(hit):
                method, pick, score, n_cand = "relaxed_name", choose(hit), 100.0, len(hit)

        if pick is None and len(local) and jrel:
            choices = {int(i): st_rk[i] for i in local}
            hit = rf_process.extractOne(jrel, choices, scorer=rf_fuzz.WRatio,
                                        score_cutoff=FUZZY_MIN)
            if hit is not None:
                method, pick, score, n_cand = "fuzzy_name", int(hit[2]), float(hit[1]), 1

        # name match exists, but only far away -> explicit conflict, not accepted
        conflict_km = np.nan
        if pick is None and jkey and jkey in global_exact:
            far = global_exact[jkey]
            if has_coord:
                d = haversine_km(jlon, jlat, st_lon[far], st_lat[far])
                k = int(np.argmin(d))
                conflict_km = float(d[k])
                method, pick, score, n_cand = "exact_name_out_of_radius", int(far[k]), 100.0, len(far)
            else:
                method, pick, score, n_cand = "exact_name_no_coord", int(far[0]), 100.0, len(far)

        if pick is None and nearest_i is not None:
            method, pick, score = "spatial_only", nearest_i, np.nan

        gap = (float(haversine_km(jlon, jlat, st_lon[pick], st_lat[pick]))
               if (pick is not None and has_coord) else np.nan)

        # ---- documented confidence rule ---------------------------------
        if pick is None:
            conf = "none"
        elif method in ("exact_name", "relaxed_name"):
            conf = "high" if gap <= HIGH_MAX_KM else ("medium" if gap <= MEDIUM_MAX_KM else "low")
        elif method == "fuzzy_name":
            if gap <= HIGH_MAX_KM and score >= 95:
                conf = "high"
            elif gap <= HIGH_MAX_KM:
                conf = "medium"
            elif gap <= MEDIUM_MAX_KM:
                conf = "low"
            else:
                conf = "low"
        elif method in ("exact_name_out_of_radius", "exact_name_no_coord"):
            conf = "rejected_name_spatial_conflict"
        else:  # spatial_only
            conf = ("medium" if gap <= SPATIAL_HIGH_KM
                    else "low" if gap <= SPATIAL_LOW_KM else "none")

        rows.append(dict(
            junction_id=j["junction_id"],
            canonical_junction_name=j["canonical_junction_name"],
            junction_class=j["junction_class"],
            junction_longitude=jlon, junction_latitude=jlat,
            coord_method=j["coord_method"],
            match_method=method,
            station_code=(st_code[pick] if pick is not None else None),
            station_name=(st_name[pick] if pick is not None else None),
            station_longitude=(float(st_lon[pick]) if pick is not None else np.nan),
            station_latitude=(float(st_lat[pick]) if pick is not None else np.nan),
            name_score=score,
            spatial_gap_km=gap,
            n_name_candidates=n_cand,
            n_stations_within_radius=int(len(local)),
            nearest_station_code=(st_code[nearest_i] if nearest_i is not None else None),
            nearest_station_km=nearest_km,
            match_confidence=conf,
        ))

    out = pd.DataFrame(rows)
    out["graph_input_version"] = GRAPH_INPUT_VERSION

    print()
    print("MATCH METHOD:")
    print(out["match_method"].value_counts().to_string())
    print()
    print("MATCH CONFIDENCE:")
    print(out["match_confidence"].value_counts().to_string())

    usable = out["match_confidence"].isin(["high", "medium"])
    print()
    print(f"USABLE (high+medium): {int(usable.sum()):,} / {len(out):,} "
          f"({usable.mean()*100:.1f}%)   [previous pipeline: 727 name matches]")
    nm = out[out["match_method"].isin(["exact_name", "relaxed_name", "fuzzy_name"])]
    print(f"Name-evidenced matches inside radius: {len(nm):,}")
    print(f"  median spatial gap : {nm['spatial_gap_km'].median()*1000:.0f} m")
    print(f"  gap <= 2 km        : {int((nm['spatial_gap_km']<=2).sum()):,}")
    print()
    print("By junction class (usable = high or medium):")
    for cls, grp in out.groupby("junction_class"):
        u = int(out.loc[grp.index, "match_confidence"].isin(["high", "medium"]).sum())
        print(f"  {cls:<14} {u:>5,} usable / {len(grp):>5,}")
    print()
    print("Same-name-different-place conflicts caught and NOT accepted:")
    bad = out[out["match_confidence"] == "rejected_name_spatial_conflict"]
    print(f"  count: {len(bad):,}")
    if len(bad):
        print(bad[["canonical_junction_name", "station_code", "station_name", "spatial_gap_km"]]
              .sort_values("spatial_gap_km", ascending=False).head(8).to_string(index=False))

    out.to_csv(OUT_DIR / "junction_station_matches.csv", index=False)
    print()
    print(f"WROTE {OUT_DIR / 'junction_station_matches.csv'}")


if __name__ == "__main__":
    main()
