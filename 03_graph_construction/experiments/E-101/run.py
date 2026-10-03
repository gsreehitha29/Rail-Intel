"""E-101 -- the g04 validation battery (V1, V2, V3, V3b, V6).

V4 (prior-art reproduction) needs cleaned_schedules.csv and is E-104.
V5 labelling is manual; this run emits its sampling frame.

    python experiments/E-101/run.py
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
import pandas as pd  # noqa: E402
from railgraph import load_graph  # noqa: E402
from railgraph import validate as V  # noqa: E402

OUT = Path(__file__).parent

def main() -> None:
    print("=" * 78); print("E-101  validation battery"); print("=" * 78)
    G = load_graph()
    t = time.time()
    rep = V.run_all(G)
    print(f"\nbattery completed in {time.time() - t:.0f}s")

    print("\n[V1] invariants:", "ALL PASS" if rep["V1"]["all_invariants_pass"] else "FAIL")
    d = rep["V2_degree"]
    print(f"[V2] degree: favoured={d['favoured']} (LLR {d['loglik_ratio_exp_over_pl']:,.0f}), "
          f"max degree {d['degree_max']}, [KUR06] met={d['kurant_thiran_prediction_met']}")
    rk = rep["V2_route_km_reconciliation"]
    print(f"[V2] route km: {rk['graph_km']:,.0f} vs YB {rk['yearbook_route_km']:,.0f} "
          f"({rk['gap_pct']:+.2f}%); excl. zero-station {rk['gap_pct_excluding_zero_station']:+.2f}% "
          f"-- mechanism established: {rk['mechanism_established']}")
    c = rep["V3"]["completeness_service_to_physical"]
    print(f"[V3] completeness: {c['both_endpoints_share']:.1%} resolvable, "
          f"{c['direct_share_of_resolvable']:.1%} direct, "
          f"{c['within_3_hops_share']:.1%} within 3 hops, "
          f"{c['cross_component_contradictions']} cross-component contradictions")
    f = rep["V3b"]
    print(f"[V3b] stitching: raw gap {f['raw_gap_pp']:.1f} pp -> fair gap "
          f"{f['fair_gap_pp_direct']:.1f} pp ({f['artifact_share_of_raw_gap']:.0%} was "
          f"definitional); Fisher OR {f['fisher_odds_ratio']:.3f}, p={f['fisher_p']:.1e}")
    v6 = rep["V6"]
    print(f"[V6] bridge share obs {v6['observed']['bridge_share']:.4f} vs null "
          f"{v6['null_mean']['bridge_share']:.4f}, z={v6['z_bridge_share']:+.1f}")

    (OUT / "report.json").write_text(json.dumps(rep, indent=2, default=str))
    pd.DataFrame(rep["V3"]["soundness_physical_to_service_by_stratum"]).to_csv(
        OUT / "v3_strata.csv", index=False)
    frame = V.v5_audit_frame(G, per_stratum=25)
    frame.to_csv(OUT / "v5_audit_frame.csv", index=False)
    print(f"\nwrote report.json, v3_strata.csv, and a {len(frame)}-edge V5 audit frame")

if __name__ == "__main__":
    main()
