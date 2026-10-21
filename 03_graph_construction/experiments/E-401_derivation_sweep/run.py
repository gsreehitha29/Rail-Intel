"""E-401 -- W7: length *derivation* as a sensitivity factor.

E-200 swept construction and representation parameters and returned "Tier A:
0 artifacts of 9 conclusions". E-200's own limitations section says why that is
narrower than it sounds: the sweep never varied **how length or travel time
were derived**, so it could not have detected G-01 or G-02. v1.1 (`E-400`) made
length derivation a real switchable parameter, so the gap is now closeable.

This runs only the new derivation cells and merges them with E-200's existing
grid rather than recomputing it -- E-200's cells are unchanged, so recomputing
them would burn 30 minutes to reproduce identical numbers.

    python 03_graph_construction/experiments/E-401_derivation_sweep/run.py            # resume, ~150s of work
    python 03_graph_construction/experiments/E-401_derivation_sweep/run.py --budget 0  # finalise only

**Resumable by design.** Each cell costs ~60-100s and completed cells are
appended to `cells_derivation.csv`, so a run does as much as its time budget
allows, skips what is already done, and only computes the verdicts once every
cell is present. That makes the experiment restartable after an interruption
instead of restarting a twenty-minute job from zero.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
PHASE3 = HERE.parents[1]
sys.path.insert(0, str(PHASE3))

from railgraph import sensitivity as S  # noqa: E402

E200 = PHASE3 / "experiments" / "E-200"
TOPK = S.TOPK


def _done_cells() -> tuple[pd.DataFrame, set]:
    f = HERE / "cells_derivation.csv"
    if not f.exists():
        return pd.DataFrame(), set()
    df = pd.read_csv(f)
    return df, set(df.cell.astype(str))


def main() -> int:
    budget = 150.0
    if "--budget" in sys.argv:
        budget = float(sys.argv[sys.argv.index("--budget") + 1])

    print("=" * 78, flush=True)
    print("E-401  length-derivation sensitivity (W7)", flush=True)
    print("=" * 78, flush=True)

    # E-200's default cell is the common reference, so overlap numbers from the
    # two experiments are measured against the same ranking.
    rk = json.loads((E200 / "rankings.json").read_text())
    ref_nodes = rk["default"]["top_nodes"]
    ref_corr = rk["default"]["top_corridors"]
    prior = pd.read_csv(E200 / "cells.csv")
    print(f"[ref] E-200 default cell, {len(prior)} prior cells loaded", flush=True)

    cells = S.derivation_cells() + S.derivation_interaction_cells()
    done_df, done = _done_cells()
    todo = [c for c in cells if c[0] not in done]
    print(f"[sweep] {len(cells)} derivation cells: {len(done)} done, "
          f"{len(todo)} to run, budget {budget:.0f}s\n", flush=True)

    rank_f = HERE / "rankings.json"
    rankings = json.loads(rank_f.read_text()) if rank_f.exists() else {}
    rows = []
    t_start = time.time()
    for i, (label, kw, pkw) in enumerate(todo, 1):
        if time.time() - t_start > budget:
            print(f"  budget spent; {len(todo) - i + 1} cells remain. "
                  f"Re-run to continue.", flush=True)
            break
        t0 = time.time()
        try:
            r = S.measure_cell(label, kw, prov_kw=pkw,
                               ref_nodes=ref_nodes, ref_corridors=ref_corr)
            rankings[label] = {"top_nodes": r.pop("top_nodes"),
                               "top_corridors": r.pop("top_corridors")}
            rows.append(r)
            print(f"  {i:2}/{len(todo)} {label:26} n={r['n_edges']:6,} "
                  f"km={r['route_km']:9,.0f} path={r['mean_path']:8.1f} "
                  f"circ={r['circuity_median']:.4f} "
                  f"ov={r.get(f'top{TOPK}_corridor_overlap', float('nan')):.2f} "
                  f"({time.time() - t0:.0f}s)", flush=True)
        except Exception as exc:  # a failed cell is data, not a crash
            rows.append({"cell": label, "error": repr(exc)})
            print(f"  {i:2}/{len(todo)} {label:26} ERROR {exc!r}", flush=True)

    df = pd.concat([done_df, pd.DataFrame(rows)], ignore_index=True) if rows else done_df
    if len(df):
        df.to_csv(HERE / "cells_derivation.csv", index=False)
    rank_f.write_text(json.dumps(rankings, indent=2, default=str))

    missing = [c[0] for c in cells if c[0] not in set(df.cell.astype(str))] if len(df) else [c[0] for c in cells]
    if missing:
        print(f"\n[incomplete] {len(missing)} cells still to run: "
              f"{', '.join(missing)}", flush=True)
        print("RESULT: PARTIAL -- re-run to continue", flush=True)
        return 0

    ok = df[df.get("error").isna()] if "error" in df.columns else df

    # 1. derivation factors alone
    print("\n[verdicts] derivation factors only", flush=True)
    v_der = S.verdicts(ok) if "default" in set(ok.cell) else None
    if v_der is None:
        # no 'default' row here; length=asis IS the default by construction
        tmp = ok.copy()
        tmp.loc[tmp.cell == "length=asis", "cell"] = "default"
        v_der = S.verdicts(tmp)
    print(v_der.to_string(index=False), flush=True)
    v_der.to_csv(HERE / "verdicts_derivation.csv", index=False)

    # 2. THE claim: Tier A plus derivation. A verdict over every cell is
    #    uninformative, because some E-200 cells deliberately negate a decided
    #    operator and of course break conclusions. The published headline is
    #    Tier A, so that is what the derivation factors must be added to.
    union = pd.concat([prior, ok], ignore_index=True)
    der_labels = tuple(str(c) for c in ok.cell)

    # first: assert the tier definitions reproduce E-200's published Tier A,
    # since that file shipped without a script that regenerates it (F-044)
    pub = pd.read_csv(E200 / "verdicts_tierA.csv").set_index("conclusion")
    repro = S.verdicts_for_tier(prior, "A").set_index("conclusion")
    tier_check = []
    for c in pub.index:
        tier_check.append({
            "conclusion": c, "published": pub.loc[c].verdict,
            "reproduced": repro.loc[c].verdict,
            "dev_published": round(float(pub.loc[c].max_deviation), 9),
            "dev_reproduced": round(float(repro.loc[c].max_deviation), 9),
            "exact": bool(pub.loc[c].verdict == repro.loc[c].verdict
                          and abs(float(pub.loc[c].max_deviation)
                                  - float(repro.loc[c].max_deviation)) < 1e-9)})
    tier_ok = all(t["exact"] for t in tier_check)
    print(f"\n[tier check] E-200 Tier A reproduced exactly from code: {tier_ok}",
          flush=True)

    print("\n[verdicts] TIER A + derivation -- the W7 answer", flush=True)
    v_tierA = S.verdicts_for_tier(prior, "A")
    v_tierA_der = S.verdicts_for_tier(union, "A", extra=der_labels)
    cmp_rows = []
    for c in v_tierA_der.conclusion:
        a = v_tierA.set_index("conclusion").loc[c]
        b = v_tierA_der.set_index("conclusion").loc[c]
        cmp_rows.append({
            "conclusion": c,
            "tierA_verdict": a.verdict, "tierA_plus_derivation": b.verdict,
            "changed": bool(a.verdict != b.verdict),
            "tierA_dev": round(float(a.max_deviation), 4),
            "with_derivation_dev": round(float(b.max_deviation), 4),
            "worst_cell": b.worst_cell,
            "worst_is_derivation": bool(str(b.worst_cell) in set(der_labels))})
    tcmp = pd.DataFrame(cmp_rows)
    print(tcmp.to_string(index=False), flush=True)
    tcmp.to_csv(HERE / "verdicts_tierA_with_derivation.csv", index=False)
    v_tierA_der.to_csv(HERE / "verdicts_tierA_plus_derivation.csv", index=False)
    n_tier_changed = int(tcmp.changed.sum())
    n_tier_der_worst = int(tcmp.worst_is_derivation.sum())
    n_artifacts = int((v_tierA_der.verdict == "artifact").sum())
    union.to_csv(HERE / "cells_union.csv", index=False)
    print(f"\n[verdicts] union of E-200 and E-401 -- {len(union)} cells", flush=True)
    v_all = S.verdicts(union)
    print(v_all.to_string(index=False), flush=True)
    v_all.to_csv(HERE / "verdicts_union.csv", index=False)

    # 3. what changed relative to E-200's published verdict
    prior_v = pd.read_csv(E200 / "verdicts.csv").set_index("conclusion")
    comp = []
    for c in v_all.conclusion:
        new = v_all.set_index("conclusion").loc[c]
        old = prior_v.loc[c] if c in prior_v.index else None
        comp.append({
            "conclusion": c,
            "E200_verdict": (old.verdict if old is not None else "-"),
            "E401_union_verdict": new.verdict,
            "changed": bool(old is not None and old.verdict != new.verdict),
            "E200_max_dev": (round(float(old.max_deviation), 4)
                             if old is not None else None),
            "union_max_dev": round(float(new.max_deviation), 4),
            "worst_cell_now": new.worst_cell,
            "worst_cell_is_derivation": bool(
                str(new.worst_cell).startswith("length=")
                or "_length" in str(new.worst_cell)),
        })
    cdf = pd.DataFrame(comp)
    cdf.to_csv(HERE / "verdict_change.csv", index=False)
    print("\n[change] E-200 verdict vs the union verdict", flush=True)
    print(cdf.to_string(index=False), flush=True)

    n_changed = int(cdf.changed.sum())
    n_der_worst = int(cdf.worst_cell_is_derivation.sum())
    report = {
        "experiment": "E-401", "title": "length-derivation sensitivity (W7)",
        "n_derivation_cells": int(len(ok)), "n_union_cells": int(len(union)),
        "tier_definitions_reproduce_E200_tierA_exactly": tier_ok,
        "tier_check": tier_check,
        "TIER_A_PLUS_DERIVATION": {
            "artifacts": n_artifacts,
            "verdicts_changed_vs_tierA": n_tier_changed,
            "conclusions_worst_at_a_derivation_cell": n_tier_der_worst,
            "verdicts": v_tierA_der.to_dict("records"),
            "comparison": cmp_rows,
        },
        "verdicts_changed_vs_E200_untiered": n_changed,
        "conclusions_whose_worst_cell_is_a_derivation_cell": n_der_worst,
        "route_km_by_mode": {
            str(r.cell): round(float(r.route_km), 1)
            for r in ok.itertuples() if hasattr(r, "route_km")},
        "verdicts_union": v_all.to_dict("records"),
        "verdicts_derivation": v_der.to_dict("records"),
        "verdict_change": comp,
        "closes": "W7 (length_source as a sweep factor), D-026 g05 consequence",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2, default=str))

    print(f"\n{'=' * 78}")
    print(f"W7 ANSWER -- Tier A + derivation: {n_artifacts} artifacts, "
          f"{n_tier_changed} verdicts changed, "
          f"{n_tier_der_worst} conclusions worst at a derivation cell")
    print(f"{'=' * 78}")
    print(f"\nverdicts changed vs E-200 (untiered): {n_changed}")
    print(f"conclusions now worst at a derivation cell: {n_der_worst}")
    print(f"wrote {HERE}")
    print("RESULT: COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
