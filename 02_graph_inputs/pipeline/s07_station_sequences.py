"""
Stage 07 — Ordered station sequences along corridor spines.

This is the hand-off artifact for graph engineering. For every corridor it
answers: "which stations lie on this corridor, in what physical order, and how
far along the line is each one?"

Method
------
1. Each corridor spine (stage 04) is oriented so that measure 0 = corridor_a and
   measure = length is corridor_b, using the geometry-derived junction
   coordinates from stage 05.
2. Candidate stations are prefiltered with a KD-tree in a planar frame, then
   confirmed with exact geodesic distances.
3. Each station is linearly referenced onto the spine. The projection (which
   vertex pair it falls on, and how far along that pair) is computed in the
   planar frame - accurate to well under a metre across one ~100 m vertex pair -
   and is then converted to a TRUE GEODESIC distance using the spine's
   cumulative haversine profile. `measure_km` and `offset_km` are therefore real
   great-circle kilometres, not planar approximations.

   This matters: a fixed-latitude planar frame misstates east-west distance by
   up to ~7% across India's latitude range, which would have been baked into
   every edge weight derived from these measures.
4. Stations are ordered by measure_km.

Deliberately NOT done here: converting consecutive stations into graph edges.
Edge semantics are the graph-engineering workstream's decision. `measure_km`
makes inter-station distance a subtraction whenever those edges are built.

Independent validation
----------------------
The GIS source carries a `noofstations` attribute per corridor that was never
used. Comparing it against the number of stations this stage finds is an
evidence check that neither side could provide alone.

Outputs
-------
graph_inputs/corridor_station_sequence.csv
graph_inputs/corridor_sequence_summary.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely import wkb as shapely_wkb
from shapely.geometry import LineString, Point

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (  # noqa: E402
    CACHE_DIR, CLEANED_STATIONS, GRAPH_INPUT_VERSION, OUT_DIR, banner,
    haversine_km, to_local_xy,
)

BUFFER_KM = 2.0
PREFILTER_SLACK = 1.15  # absorbs planar-frame scale error during prefiltering


def main() -> None:
    banner("STAGE 07 — ORDERED STATION SEQUENCES ALONG CORRIDORS")

    spines = pd.read_parquet(CACHE_DIR / "corridor_spines.parquet")
    corridors = pd.read_csv(OUT_DIR / "corridors.csv").set_index("corridor_id")
    paths = pd.read_csv(OUT_DIR / "corridor_paths.csv").set_index("corridor_id")
    jcoord = pd.read_csv(OUT_DIR / "junction_coordinates.csv").set_index(
        "canonical_junction_name")[["longitude", "latitude"]]

    st = pd.read_csv(CLEANED_STATIONS)
    st = st[st["spatially_usable"] == True].copy().reset_index(drop=True)  # noqa: E712
    st_lon = st["longitude"].values
    st_lat = st["latitude"].values
    sx, sy = to_local_xy(st_lon, st_lat)
    st_xy = np.column_stack([sx, sy])
    tree = cKDTree(st_xy)
    print(f"Spines: {len(spines):,} | Stations with coords: {len(st):,} | buffer {BUFFER_KM} km")
    print("Measures and offsets are true geodesic km (planar frame used only for prefilter/projection)")

    seq_rows, summary_rows = [], []

    for _, sp in spines.iterrows():
        cid = sp["corridor_id"]
        if cid not in corridors.index:
            continue
        cinfo = corridors.loc[cid]
        ll = np.asarray(shapely_wkb.loads(sp["wkb"]).coords, dtype=float)

        # ---- orient so measure 0 == corridor_a ---------------------------
        a_name, b_name = cinfo["corridor_a"], cinfo["corridor_b"]
        oriented = "unknown"
        if a_name in jcoord.index and b_name in jcoord.index and a_name != b_name:
            a = jcoord.loc[a_name]; b = jcoord.loc[b_name]
            d_a = float(haversine_km(ll[0, 0], ll[0, 1], a["longitude"], a["latitude"]))
            d_b = float(haversine_km(ll[0, 0], ll[0, 1], b["longitude"], b["latitude"]))
            if d_b < d_a:
                ll = ll[::-1]
                oriented = "reversed_to_a"
            else:
                oriented = "as_built"

        if len(ll) < 2:
            continue

        # ---- geodesic and planar cumulative profiles ---------------------
        seg_geo = haversine_km(ll[:-1, 0], ll[:-1, 1], ll[1:, 0], ll[1:, 1])
        cum_geo = np.concatenate([[0.0], np.cumsum(seg_geo)])
        spine_geodesic_km = float(cum_geo[-1])

        lx, ly = to_local_xy(ll[:, 0], ll[:, 1])
        xy = np.column_stack([lx, ly])
        seg_pl = np.linalg.norm(np.diff(xy, axis=0), axis=1)
        cum_pl = np.concatenate([[0.0], np.cumsum(seg_pl)])
        line = LineString(xy)
        if spine_geodesic_km <= 0 or cum_pl[-1] <= 0:
            continue

        # ---- candidate stations -----------------------------------------
        step = float(seg_pl.max()) if len(seg_pl) else 0.0
        radius = (BUFFER_KM + step) * PREFILTER_SLACK
        cand = set()
        for idx in tree.query_ball_point(xy, radius):
            cand.update(idx)
        cand = np.array(sorted(cand), dtype=int)

        hits = []
        for i in cand:
            s_pl = float(line.project(Point(st_xy[i])))
            k = int(np.clip(np.searchsorted(cum_pl, s_pl, side="right") - 1, 0, len(seg_pl) - 1))
            frac = ((s_pl - cum_pl[k]) / seg_pl[k]) if seg_pl[k] > 0 else 0.0
            frac = float(np.clip(frac, 0.0, 1.0))
            # geodesic measure along the spine
            measure = float(cum_geo[k] + frac * seg_geo[k])
            # exact geodesic offset to the interpolated point on the line
            plon = ll[k, 0] + frac * (ll[k + 1, 0] - ll[k, 0])
            plat = ll[k, 1] + frac * (ll[k + 1, 1] - ll[k, 1])
            off = float(haversine_km(st_lon[i], st_lat[i], plon, plat))
            if off <= BUFFER_KM:
                hits.append((measure, off, int(i)))
        hits.sort()

        for k, (measure, off, i) in enumerate(hits, start=1):
            seq_rows.append(dict(
                corridor_id=cid, corridor_a=a_name, corridor_b=b_name,
                sequence_index=k,
                station_code=st.at[i, "station_code"],
                station_name=st.at[i, "station_name"],
                station_longitude=float(st_lon[i]),
                station_latitude=float(st_lat[i]),
                measure_km=round(measure, 6),
                offset_km=round(off, 6),
                is_corridor_endpoint=(k == 1 or k == len(hits)),
            ))

        declared = cinfo["declared_no_of_stations"]
        summary_rows.append(dict(
            corridor_id=cid, corridor_a=a_name, corridor_b=b_name,
            spine_geodesic_km=spine_geodesic_km,
            reconstruction_status=paths.at[cid, "status"] if cid in paths.index else None,
            orientation=oriented,
            n_stations_found=len(hits),
            declared_no_of_stations=declared,
            station_count_delta=(len(hits) - declared) if pd.notna(declared) else np.nan,
            median_offset_km=float(np.median([h[1] for h in hits])) if hits else np.nan,
            max_gap_between_stations_km=(
                float(np.max(np.diff([h[0] for h in hits]))) if len(hits) > 1 else np.nan),
        ))

    seq = pd.DataFrame(seq_rows)
    summ = pd.DataFrame(summary_rows)
    seq["graph_input_version"] = GRAPH_INPUT_VERSION
    summ["graph_input_version"] = GRAPH_INPUT_VERSION

    per_station = seq.groupby("station_code")["corridor_id"].nunique()
    seq["station_n_corridors"] = seq["station_code"].map(per_station)

    print()
    print(f"Corridors with >=1 station : {int((summ['n_stations_found']>0).sum()):,} / {len(summ):,}")
    print(f"Corridors with >=2 stations: {int((summ['n_stations_found']>=2).sum()):,}")
    print(f"Total station placements   : {len(seq):,}")
    print(f"Distinct stations placed   : {seq['station_code'].nunique():,} / {len(st):,}")
    print(f"Median perpendicular offset: {seq['offset_km'].median()*1000:.0f} m")

    # measure must never exceed the spine's own geodesic length
    last = seq.sort_values("sequence_index").groupby("corridor_id")["measure_km"].last()
    chk = summ.set_index("corridor_id")["spine_geodesic_km"].reindex(last.index)
    over = int((last > chk + 1e-6).sum())
    print(f"Corridors where last measure > spine length: {over}  (must be 0)")

    print()
    print("INDEPENDENT CHECK vs the GIS 'noofstations' attribute (never used before):")
    ok = summ.dropna(subset=["station_count_delta"])
    for lo, hi, lbl in [(-1, 1, "within +/-1"), (-3, 3, "within +/-3"), (-5, 5, "within +/-5")]:
        n = int(ok["station_count_delta"].between(lo, hi).sum())
        print(f"  {lbl:<14}: {n:>6,} / {len(ok):,}  ({n/len(ok)*100:5.1f}%)")
    print(f"  median delta  : {ok['station_count_delta'].median():+.1f}")
    print(f"  correlation   : {ok['n_stations_found'].corr(ok['declared_no_of_stations']):.3f}")
    print()
    print("Stations lying on multiple corridors (ambiguity to resolve downstream):")
    print(f"  on 1 corridor : {int((per_station==1).sum()):,}")
    print(f"  on 2 corridors: {int((per_station==2).sum()):,}")
    print(f"  on >2         : {int((per_station>2).sum()):,}")

    seq.to_csv(OUT_DIR / "corridor_station_sequence.csv", index=False)
    summ.to_csv(OUT_DIR / "corridor_sequence_summary.csv", index=False)
    print()
    print(f"WROTE {OUT_DIR / 'corridor_station_sequence.csv'}  ({len(seq):,} rows)")
    print(f"WROTE {OUT_DIR / 'corridor_sequence_summary.csv'}  ({len(summ):,} rows)")


if __name__ == "__main__":
    main()
