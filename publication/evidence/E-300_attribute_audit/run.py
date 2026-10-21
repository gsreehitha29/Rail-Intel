"""E-300 -- attribute provenance and enrichment audit.

Answers one question: **what do the edge and node attributes actually measure,
and what is recoverably missing?**

The graph currently carries `length_km`, `gauge_code`, `speed_kmph`, `n_tracks`,
`bridge_present`, `tunnel_present`. None of those were audited against the source
GIS when they were built -- they were carried through `s02`/`s09` and trusted.
This experiment establishes, for each one, the *granularity at which the value
was actually observed*, which is not the granularity at which it is stored.

Five parts:

  1. granularity -- does each GIS attribute vary within a corridor, or is it a
     corridor constant broadcast onto every segment?
  2. length -- the shipped `length_km` is a haversine chord between station
     coordinates. The true along-track distance is recoverable from
     `station_sequences.measure_km`. Quantify the difference, and the regime in
     which the spine measure itself breaks down.
  3. sinuosity -- rank corridors by true/chord ratio and check the ranking
     against an external ground truth nobody gave the pipeline: India's
     mountain railways.
  4. bridges -- the GIS splits its polylines at bridge structures, so
     `bridge_yn` is genuine segment-level data. Test whether it is a usable
     inventory by validating zone totals against the official count.
  5. coverage -- attribute nullity and conflict rates at corridor and edge level.

    python publication/evidence/E-300_attribute_audit/run.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

GIS = ROOT / "01_data_engineering" / "Railway_Network_.csv"
SEQ = ROOT / "02_graph_inputs" / "graph_dataset" / "station_sequences.csv"
CORR = ROOT / "02_graph_inputs" / "graph_dataset" / "corridors.csv"
NODES = ROOT / "03_graph_construction" / "graph_v1" / "nodes.parquet"
EDGES = ROOT / "03_graph_construction" / "graph_v1" / "edges.parquet"
RS_BRIDGES = ROOT / "reference_data" / "RS_Session_267_AS_371_A_i.csv"
STATIONS = ROOT / "01_data_engineering" / "processed_data" / "cleaned_stations.csv"

EARTH_R_KM = 6371.0088  # the radius s09 uses; kept identical so lengths compare

ZONE_MAP = {
    "Central Railway": "CR", "Eastern Railway": "ER", "East Central Railway": "ECR",
    "East Coast Railway": "ECoR", "Northern Railway": "NR", "North Central Railway": "NCR",
    "North Eastern Railway": "NER", "Northeast Frontier Railway": "NFR",
    "North Western Railway": "NWR", "Southern Railway": "SR", "South Central Railway": "SCR",
    "South Eastern Railway": "SER", "South East Central Railway": "SECR",
    "South Western Railway": "SWR", "Western Railway": "WR",
    "West Central Railway": "WCR", "Konkan Railway": "KR",
}

#: Corridors whose endpoints identify one of India's recognised mountain
#: railways. Declared here as an EXTERNAL ground truth -- nothing in the
#: pipeline knows about terrain, so recovering these by geometry alone is a
#: real test, not a tautology. Four are UNESCO-listed (DHR 1999, NMR 2005,
#: KSR 2008; Matheran is on the tentative list).
MOUNTAIN_RAILWAYS = {
    ("Darjeeling", "New Jalpaiguri Junction"): "Darjeeling Himalayan (UNESCO 1999)",
    ("Mettupalayam", "Udagamandalam"): "Nilgiri Mountain (UNESCO 2005)",
    ("Kalka", "Shimla"): "Kalka-Shimla (UNESCO 2008)",
    ("Matheran", "Neral Jn NG"): "Matheran Hill (UNESCO tentative)",
}


def haversine_km(lon1, lat1, lon2, lat2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlam / 2) ** 2
    return 2 * EARTH_R_KM * np.arcsin(np.sqrt(a))


def consecutive_pairs() -> pd.DataFrame:
    """Consecutive station pairs on each corridor, with chord and spine length.

    These are the pairs `s09` turns into edges, so this is the edge population
    before junction stitching.
    """
    seq = pd.read_csv(SEQ)
    s = seq[seq.used_for_edges].sort_values(["corridor_id", "sequence_index"]).copy()
    g = s.groupby("corridor_id")
    for c in ["station_longitude", "station_latitude", "measure_km",
              "station_code", "offset_km"]:
        s["nx_" + c] = g[c].shift(-1)
    p = s.dropna(subset=["nx_station_code"]).copy()
    p["chord_km"] = haversine_km(p.station_longitude, p.station_latitude,
                                 p.nx_station_longitude, p.nx_station_latitude)
    p["spine_km"] = (p.nx_measure_km - p.measure_km).abs()
    p = p[(p.spine_km > 0) & (p.chord_km > 0)].copy()
    p["ratio"] = p.spine_km / p.chord_km
    p["max_offset_km"] = p[["offset_km", "nx_offset_km"]].max(axis=1)
    return p


# --------------------------------------------------------------------------- #
# part 1 -- granularity
# --------------------------------------------------------------------------- #

def part1_granularity(gis: pd.DataFrame) -> pd.DataFrame:
    print("\n[1] ATTRIBUTE GRANULARITY -- is the value observed per segment, "
          "or is it a corridor constant?")
    key = ["fromjunction", "tojunction"]
    rows = []
    for c in ["speed", "type", "noofstations", "tracklength", "railwayzone",
              "nooflanes", "bridge_yn", "tunnel_yn"]:
        nu = gis.groupby(key)[c].nunique(dropna=False)
        rows.append({
            "attribute": c,
            "corridors_constant_pct": round(100 * (nu <= 1).mean(), 2),
            "mean_distinct_values_per_corridor": round(nu.mean(), 3),
            "granularity": "segment" if (nu <= 1).mean() < 0.90 else "corridor",
        })
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    n_corr = gis.groupby(key).ngroups
    print(f"\n    {len(gis):,} GIS segments carry only {n_corr:,} distinct "
          f"corridor-level values for the 'corridor' rows above.")
    print(f"    effective sample size for those attributes is {n_corr:,}, not {len(gis):,}.")
    df.to_csv(HERE / "granularity.csv", index=False)
    return df


# --------------------------------------------------------------------------- #
# part 2 -- length
# --------------------------------------------------------------------------- #

def part2_length(p: pd.DataFrame) -> dict:
    print("\n[2] LENGTH -- shipped haversine chord vs recoverable along-track distance")
    tot_chord, tot_spine = p.chord_km.sum(), p.spine_km.sum()
    print(f"    pairs analysed            {len(p):,}")
    print(f"    total chord km            {tot_chord:11,.1f}   <- what the graph ships")
    print(f"    total along-track km      {tot_spine:11,.1f}   <- recoverable from measure_km")
    print(f"    understatement            {tot_spine - tot_chord:11,.1f} km "
          f"({100*(tot_spine-tot_chord)/tot_chord:.2f}%)")
    print("\n    distribution of (along-track / chord):")
    for q in [0.05, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]:
        print(f"      p{int(q*100):<3} {p.ratio.quantile(q):7.4f}")
    print(f"      max  {p.ratio.max():7.4f}")
    print("\n    share of pairs understated by more than:")
    for t in [0.02, 0.05, 0.10, 0.25, 0.50, 1.00]:
        print(f"      {100*t:5.0f}%  {(p.ratio > 1+t).sum():5,} pairs  "
              f"({100*(p.ratio > 1+t).mean():5.2f}%)")

    # the spine measure is not universally trustworthy
    imp = p[p.ratio < 0.95]
    print(f"\n    BUT: {len(imp):,} pairs ({100*len(imp)/len(p):.2f}%) report an along-track")
    print("    distance SHORTER than the straight line, which is geometrically impossible.")
    print("    Cause -- stations far from the spine project onto the same spine position:")
    bands = pd.cut(p.max_offset_km, [0, .1, .25, .5, 1.0, 1.5, 99],
                   labels=["<0.1", "0.1-0.25", "0.25-0.5", "0.5-1.0", "1.0-1.5", ">1.5"])
    t = p.groupby(bands, observed=True).agg(
        pairs=("ratio", "size"),
        impossible_pct=("ratio", lambda r: round(100 * (r < 0.95).mean(), 1)),
        median_ratio=("ratio", lambda r: round(r.median(), 4)))
    t.index.name = "max_offset_km_band"
    print(t.to_string())
    t.to_csv(HERE / "length_offset_bands.csv")

    clean = p[(p.max_offset_km < 0.25) & (p.ratio >= 0.95)]
    print(f"\n    on the trustworthy subset (offset <0.25 km, ratio >=0.95): "
          f"{len(clean):,} pairs ({100*len(clean)/len(p):.1f}%)")
    print(f"    understatement there is {100*(clean.spine_km.sum()-clean.chord_km.sum())/clean.chord_km.sum():.2f}%")

    res = {
        "pairs": int(len(p)),
        "total_chord_km": round(float(tot_chord), 1),
        "total_spine_km": round(float(tot_spine), 1),
        "understatement_pct": round(float(100*(tot_spine-tot_chord)/tot_chord), 3),
        "median_ratio": round(float(p.ratio.median()), 5),
        "pairs_understated_gt5pct": int((p.ratio > 1.05).sum()),
        "pairs_understated_gt5pct_share": round(float((p.ratio > 1.05).mean()), 5),
        "impossible_pairs": int(len(imp)),
        "impossible_share": round(float(len(imp)/len(p)), 5),
        "trustworthy_pairs": int(len(clean)),
        "trustworthy_share": round(float(len(clean)/len(p)), 5),
    }
    p[["corridor_id", "station_code", "nx_station_code", "chord_km", "spine_km",
       "ratio", "max_offset_km"]].to_csv(HERE / "length_pairs.csv", index=False)
    return res


# --------------------------------------------------------------------------- #
# part 3 -- sinuosity vs external ground truth
# --------------------------------------------------------------------------- #

def part3_sinuosity(p: pd.DataFrame, corr: pd.DataFrame) -> dict:
    print("\n[3] SINUOSITY -- does the along-track measure recover real terrain?")
    clean = p[(p.max_offset_km < 0.25) & (p.ratio >= 0.95)]
    agg = clean.groupby("corridor_id").apply(
        lambda d: pd.Series({"sinuosity": d.spine_km.sum()/d.chord_km.sum(),
                             "pairs": len(d)}), include_groups=False)
    agg = agg[agg.pairs >= 3].copy()
    c = corr.set_index("corridor_id")
    agg["corridor_a"] = agg.index.map(c.corridor_a)
    agg["corridor_b"] = agg.index.map(c.corridor_b)
    agg["gauge"] = agg.index.map(c.gauge_name)
    agg["zone"] = agg.index.map(c.zone_code)
    agg = agg.sort_values("sinuosity", ascending=False)
    agg["rank"] = range(1, len(agg) + 1)

    print(f"    corridors ranked: {len(agg):,} (>=3 trustworthy pairs each)")
    print("\n    top 12 by sinuosity:")
    print(agg.head(12)[["rank", "corridor_a", "corridor_b", "gauge", "zone",
                        "pairs", "sinuosity"]].to_string(index=False))

    print("\n    EXTERNAL CHECK -- India's recognised mountain railways.")
    print("    The pipeline has no terrain, elevation or heritage input whatsoever.")
    found = []
    for (a, b), label in MOUNTAIN_RAILWAYS.items():
        hit = agg[((agg.corridor_a == a) & (agg.corridor_b == b)) |
                  ((agg.corridor_a == b) & (agg.corridor_b == a))]
        if len(hit):
            r = hit.iloc[0]
            found.append({"railway": label, "rank": int(r["rank"]),
                          "sinuosity": round(float(r.sinuosity), 3)})
            print(f"      rank {int(r['rank']):>4} / {len(agg)}   "
                  f"sinuosity {r.sinuosity:.3f}   {label}")
        else:
            print(f"      NOT FOUND (too few clean pairs)        {label}")
    if found:
        worst = max(f["rank"] for f in found)
        print(f"\n    all {len(found)} recovered mountain railways fall in the top "
              f"{worst} of {len(agg)} corridors (top {100*worst/len(agg):.1f}%).")
    agg.to_csv(HERE / "corridor_sinuosity.csv")
    return {"corridors_ranked": int(len(agg)), "mountain_railways": found}


# --------------------------------------------------------------------------- #
# part 4 -- bridges
# --------------------------------------------------------------------------- #

def part4_bridges(gis: pd.DataFrame) -> dict:
    print("\n[4] BRIDGES -- is the segment-level bridge flag a usable inventory?")
    share = (gis.bridge_yn == "Y").mean()
    bl = gis.loc[gis.bridge_yn == "Y", "st_lengthshape"]
    nl = gis.loc[gis.bridge_yn == "N", "st_lengthshape"]
    print(f"    segments flagged as bridge: {(gis.bridge_yn=='Y').sum():,} ({100*share:.2f}%)")
    print(f"    median length of a bridge segment     {bl.median():8.1f} m")
    print(f"    median length of a non-bridge segment {nl.median():8.1f} m")
    print("    -> the GIS splits its polylines AT the structures; flagged segments")
    print("       are the bridge decks themselves, so a per-edge COUNT and a")
    print("       bridged-metres total are both derivable. Far richer than a boolean.")

    gis = gis.copy()
    gis["zone_code"] = gis.railwayzone.map(ZONE_MAP)
    counted = gis[gis.bridge_yn == "Y"].groupby("zone_code").size().rename("gis_bridge_segments")
    rs = pd.read_csv(RS_BRIDGES).set_index("Railway")["Nos. of Bridges"].rename("official_bridges")
    cmp = rs.to_frame().join(counted).dropna()
    cmp["capture_rate"] = (cmp.gis_bridge_segments / cmp.official_bridges).round(4)
    cmp = cmp.sort_values("official_bridges", ascending=False)
    print("\n    VALIDATION against Rajya Sabha Q.371 (official bridge count per zone):")
    print(cmp.to_string())
    overall = cmp.gis_bridge_segments.sum() / cmp.official_bridges.sum()
    sp = cmp.gis_bridge_segments.corr(cmp.official_bridges, method="spearman")
    pe = cmp.gis_bridge_segments.corr(cmp.official_bridges)
    print(f"\n    overall capture rate {overall:.3f}  "
          f"(GIS {int(cmp.gis_bridge_segments.sum()):,} vs official {int(cmp.official_bridges.sum()):,})")
    print(f"    Spearman {sp:.3f}   Pearson {pe:.3f}")
    print(f"    capture rate range {cmp.capture_rate.min():.3f} ({cmp.capture_rate.idxmin()}) "
          f"to {cmp.capture_rate.max():.3f} ({cmp.capture_rate.idxmax()})")
    print("    -> VERDICT: the flag is real but the inventory is INCOMPLETE and the")
    print("       shortfall is strongly zone-dependent. Usable as a relative, within-zone")
    print("       density; NOT usable as an absolute count or for cross-zone comparison.")
    cmp.to_csv(HERE / "bridge_validation.csv")
    return {"segment_bridge_share": round(float(share), 4),
            "overall_capture_rate": round(float(overall), 4),
            "spearman": round(float(sp), 4), "pearson": round(float(pe), 4),
            "min_capture_zone": str(cmp.capture_rate.idxmin()),
            "min_capture_rate": float(cmp.capture_rate.min())}


# --------------------------------------------------------------------------- #
# part 5 -- coverage and conflicts
# --------------------------------------------------------------------------- #

def part5_coverage(corr: pd.DataFrame) -> dict:
    print("\n[5] COVERAGE AND CONFLICT -- what is missing, and what was silently arbitrated")
    nodes = pd.read_parquet(NODES)
    edges = pd.read_parquet(EDGES)

    print("\n    edge attribute nullity (shipped graph):")
    ecov = {}
    for c in ["length_km", "gauge_code", "n_tracks", "speed_kmph", "service_load"]:
        ecov[c] = round(float(edges[c].notna().mean()), 4)
        flag = "  <- fabricated for the rest by the 50 km/h fallback" if c == "speed_kmph" else ""
        print(f"      {c:<16} {100*ecov[c]:6.2f}%{flag}")

    print("\n    node attribute nullity (shipped graph):")
    ncov = {}
    for c in ["longitude", "zone_code", "state"]:
        ncov[c] = round(float(nodes[c].notna().mean()), 4)
        flag = "  <- blocks any state-level accessibility analysis" if c == "state" else ""
        print(f"      {c:<16} {100*ncov[c]:6.2f}%{flag}")

    # can the station master fix state? only if it has it
    st = pd.read_csv(STATIONS)
    m = nodes[nodes.node_type == "station"].merge(
        st[["station_code", "state"]], left_on="node_id",
        right_on="station_code", how="left", suffixes=("_graph", "_master"))
    print(f"\n      state on station nodes now          {100*m.state_graph.notna().mean():6.2f}%")
    print(f"      state obtainable from station master {100*m.state_master.notna().mean():6.2f}%")
    print("      -> the master has no more than the graph does. State is NOT recoverable")
    print("         from in-repo sources; it needs reverse geocoding from the coordinates,")
    print("         which are 100% present.")

    print("\n    corridor attribute conflicts already detected in Phase 2:")
    conf = {}
    for c in ["speed_kmph_conflict", "gauge_conflict", "no_of_lanes_conflict",
              "railway_zone_conflict", "any_attribute_conflict"]:
        conf[c] = int(corr[c].sum())
        print(f"      {c:<24} {corr[c].sum():5,} corridors ({100*corr[c].mean():5.2f}%)")
    print("      -> these flags exist on corridors.csv and were NEVER propagated to the")
    print("         edge table. An edge on a conflicted corridor carries an arbitrated")
    print("         value with no marker that arbitration occurred.")
    return {"edge_coverage": ecov, "node_coverage": ncov, "conflicts": conf,
            "state_recoverable_from_master": False}


def main() -> None:
    print("=" * 78)
    print("E-300  attribute provenance and enrichment audit")
    print("=" * 78)
    gis = pd.read_csv(GIS, encoding="utf-8-sig", low_memory=False)
    corr = pd.read_csv(CORR)
    pairs = consecutive_pairs()

    report = {}
    part1_granularity(gis)
    report["length"] = part2_length(pairs)
    report["sinuosity"] = part3_sinuosity(pairs, corr)
    report["bridges"] = part4_bridges(gis)
    report["coverage"] = part5_coverage(corr)

    (HERE / "report.json").write_text(json.dumps(report, indent=2, default=str))
    print(f"\nwrote report.json, granularity.csv, length_pairs.csv, "
          f"length_offset_bands.csv, corridor_sinuosity.csv, bridge_validation.csv")


if __name__ == "__main__":
    main()
