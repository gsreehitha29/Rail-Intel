"""E-102 -- per-zone route km against an independent official total.

The national route-km check (`F-019`) compares one number to one number: ours is
+3.98% against the Year Book, and excluding zero-station corridors reconciles it
to -0.06% without establishing why. One comparison cannot distinguish a correct
total from two errors cancelling.

This runs the same check **seventeen times**, once per railway zone, against
per-zone broad-gauge route km published for 2021. Seventeen independent
comparisons discriminate where one does not: a uniform offset means a systematic
construction effect, scatter means zone-specific data problems, and the pattern
of the residual tells us which.

Scope. The reference is **broad gauge only**, so the graph is filtered to
`gauge_code == "BG"`. The reference is dated 2021 and the graph is undated, so
exact agreement is not expected and is not the test; the test is the structure of
the disagreement.

    python publication/evidence/E-102_zone_route_km/run.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EDGES = ROOT / "03_graph_construction" / "graph_v1" / "edges.parquet"
REF = ROOT / "reference_data" / "zone_electrification_2021.csv"
CORR = ROOT / "02_graph_inputs" / "graph_dataset" / "corridors.csv"

NAME_TO_CODE = {
    "Central": "CR", "Eastern": "ER", "East Central": "ECR", "East Coast": "ECoR",
    "Northern": "NR", "North Central": "NCR", "North Eastern": "NER",
    "Northeast Frontier": "NFR", "North Western": "NWR", "Southern": "SR",
    "South Central": "SCR", "South Eastern": "SER", "South East Central": "SECR",
    "South Western": "SWR", "Western": "WR", "West Central": "WCR", "Konkan": "KR",
}


def main() -> None:
    print("=" * 74)
    print("E-102  per-zone broad-gauge route km vs the 2021 official figure")
    print("=" * 74)

    edges = pd.read_parquet(EDGES)
    corr = pd.read_csv(CORR).set_index("corridor_id")
    edges = edges.copy()
    edges["declared"] = edges.corridor_id.map(corr.declared_no_of_stations)
    edges["found"] = edges.corridor_id.map(corr.n_stations_found)
    edges["suspect"] = ((edges.declared - edges.found) >= 3) & (edges.length_km > 10)

    ref = pd.read_csv(REF, encoding="utf-8-sig")
    ref = ref[ref.railway.isin(NAME_TO_CODE)].copy()
    ref["zone_code"] = ref.railway.map(NAME_TO_CODE)
    ref = ref.set_index("zone_code")

    bg = edges[edges.gauge_code == "BG"]
    ours = bg.groupby("zone_code").length_km.sum().rename("ours_km")
    ours_clean = bg[~bg.suspect].groupby("zone_code").length_km.sum().rename("ours_excl_suspect_km")

    t = ref[["railway", "total_bg_route_km"]].join([ours, ours_clean]).dropna(subset=["ours_km"])
    t["delta_pct"] = 100 * (t.ours_km - t.total_bg_route_km) / t.total_bg_route_km
    t["delta_pct_excl"] = 100 * (t.ours_excl_suspect_km - t.total_bg_route_km) / t.total_bg_route_km
    t = t.sort_values("delta_pct")

    print("\nper zone (BG route km):\n")
    print(t[["railway", "total_bg_route_km", "ours_km", "delta_pct", "delta_pct_excl"]]
          .round(1).to_string())

    tot_ref, tot_ours = t.total_bg_route_km.sum(), t.ours_km.sum()
    tot_clean = t.ours_excl_suspect_km.sum()
    print(f"\nnational BG total   reference {tot_ref:,.0f} km   ours {tot_ours:,.0f} km   "
          f"delta {100*(tot_ours-tot_ref)/tot_ref:+.2f}%")
    print(f"excluding suspect edges        ours {tot_clean:,.0f} km   "
          f"delta {100*(tot_clean-tot_ref)/tot_ref:+.2f}%")

    d = t.delta_pct
    print(f"\nper-zone deviation: median {d.median():+.1f}%  mean {d.mean():+.1f}%  "
          f"sd {d.std():.1f}pp")
    print(f"  range {d.min():+.1f}% ({t.railway[d.idxmin()]}) to "
          f"{d.max():+.1f}% ({t.railway[d.idxmax()]})")
    print(f"  zones within +/-10%: {int((d.abs() <= 10).sum())} of {len(d)}")
    print(f"  zones within +/-20%: {int((d.abs() <= 20).sum())} of {len(d)}")

    r = np.corrcoef(t.total_bg_route_km, t.ours_km)[0, 1]
    print(f"\ncorrelation of per-zone totals: Pearson {r:.4f}  "
          f"Spearman {t.total_bg_route_km.corr(t.ours_km, method='spearman'):.4f}")

    print("\nINTERPRETATION")
    if d.std() < 8:
        print("  Deviation is tight across zones -> a systematic, uniform offset.")
    else:
        print(f"  Deviation scatters widely (sd {d.std():.1f}pp) -> the national agreement in")
        print("  F-019 is NOT a uniform construction offset. Zone-level errors of opposite")
        print("  sign are partially cancelling in the national total, which is exactly what a")
        print("  single-number check cannot detect.")
    imp = (t.delta_pct_excl.abs().median() < t.delta_pct.abs().median())
    print(f"  Excluding suspect edges {'improves' if imp else 'does NOT improve'} the median "
          f"absolute deviation "
          f"({t.delta_pct.abs().median():.1f}% -> {t.delta_pct_excl.abs().median():.1f}%).")

    t.round(3).to_csv(HERE / "zone_route_km.csv")
    (HERE / "report.json").write_text(json.dumps({
        "reference": "zone_electrification_2021.csv (BG route km, 2021)",
        "zones_compared": int(len(t)),
        "national_ref_km": float(tot_ref), "national_ours_km": float(tot_ours),
        "national_delta_pct": round(float(100*(tot_ours-tot_ref)/tot_ref), 3),
        "national_delta_pct_excl_suspect": round(float(100*(tot_clean-tot_ref)/tot_ref), 3),
        "zone_delta_median_pct": round(float(d.median()), 3),
        "zone_delta_sd_pp": round(float(d.std()), 3),
        "zone_delta_min_pct": round(float(d.min()), 3),
        "zone_delta_max_pct": round(float(d.max()), 3),
        "zones_within_10pct": int((d.abs() <= 10).sum()),
        "pearson": round(float(r), 4),
    }, indent=2))
    print(f"\nwrote zone_route_km.csv, report.json")


if __name__ == "__main__":
    main()
