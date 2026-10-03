"""E-200 -- the construction-choice sensitivity sweep (g05).

One-at-a-time around the shipped default, plus the tolerance x stitching
interaction grid. Each cell gets the full battery; the output is a per-conclusion
robust / conditional / artifact verdict.

    python experiments/E-200/run.py
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
import pandas as pd  # noqa: E402
from railgraph import sensitivity as S  # noqa: E402

OUT = Path(__file__).parent

def main() -> None:
    print("=" * 78, flush=True)
    print("E-200  construction-choice sensitivity sweep", flush=True)
    print("=" * 78, flush=True)

    # reference ranking from the default cell
    print("\n[ref] measuring the default cell", flush=True)
    ref = S.measure_cell("default", {})
    ref_nodes, ref_corr = ref["top_nodes"], ref["top_corridors"]
    ref[f"top{S.TOPK}_node_overlap"] = 1.0
    ref[f"top{S.TOPK}_corridor_overlap"] = 1.0
    rows = [ref]
    print(f"      done in {ref['secs']}s", flush=True)

    cells = [c for c in S.one_at_a_time_cells() if c[0] != "default"]
    cells += [c for c in S.interaction_cells()
              if c[0] not in {x[0] for x in cells}]
    print(f"\n[sweep] {len(cells)} further cells", flush=True)
    for i, (label, kw) in enumerate(cells, 1):
        try:
            r = S.measure_cell(label, kw, ref_nodes=ref_nodes, ref_corridors=ref_corr)
            rows.append(r)
            print(f"  {i:2}/{len(cells)} {label:26} n={r['n_edges']:6,} "
                  f"giant={r['giant_share']*100:5.1f}% br={r['bridge_share']*100:5.1f}% "
                  f"path={r['mean_path']:8.1f} corrOv={r[f'top{S.TOPK}_corridor_overlap']:.2f} "
                  f"R_rand={r['R_random']:.4f} [{r['secs']}s]", flush=True)
        except Exception as ex:                      # a failed cell is data too
            print(f"  {i:2}/{len(cells)} {label:26} FAILED: {type(ex).__name__}: {ex}",
                  flush=True)
            rows.append({"cell": label, "error": f"{type(ex).__name__}: {ex}"})

    df = pd.DataFrame(rows)
    df.drop(columns=["top_nodes", "top_corridors"]).to_csv(OUT / "cells.csv", index=False)
    json.dump({r["cell"]: {"top_nodes": r.get("top_nodes"),
                           "top_corridors": r.get("top_corridors")}
               for r in rows if "top_nodes" in r},
              open(OUT / "rankings.json", "w"), indent=2, default=str)

    ok = df[df.get("error").isna()] if "error" in df.columns else df
    print("\n[verdicts] per-conclusion robustness over the whole sweep", flush=True)
    v = S.verdicts(ok)
    print(v.to_string(index=False), flush=True)
    v.to_csv(OUT / "verdicts.csv", index=False)

    print("\n[F-007] tolerance sensitivity, stitched vs unstitched", flush=True)
    damp = S.sensitivity_damping(
        ok, "stitchON", "stitchOFF",
        ["giant_share", "bridge_share", "meshedness", "mean_path",
         "independent_cycles", "R_random", f"top{S.TOPK}_corridor_overlap"])
    print(damp.to_string(index=False), flush=True)
    damp.to_csv(OUT / "damping.csv", index=False)

    print("\n[F-011] is the inverted attack ordering robust?", flush=True)
    inv = ok[["cell", "R_random", "R_degree", "R_betweenness",
              "worst_strategy", "random_worse_than_betweenness"]]
    print(inv.to_string(index=False), flush=True)
    n = int(inv.random_worse_than_betweenness.sum())
    print(f"\n  random worse than betweenness in {n}/{len(inv)} cells", flush=True)
    print(f"  worst strategy is 'degree' in "
          f"{int((inv.worst_strategy == 'degree').sum())}/{len(inv)} cells", flush=True)
    inv.to_csv(OUT / "attack_ordering.csv", index=False)
    print(f"\nwrote cells.csv, verdicts.csv, damping.csv, attack_ordering.csv, "
          f"rankings.json", flush=True)

if __name__ == "__main__":
    main()
