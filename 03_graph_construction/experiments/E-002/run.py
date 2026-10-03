"""E-002 -- g01 acceptance test and early construction-sensitivity preview.

Three things in one run:
  1. the shipped default builds and passes SHIPPED_INVARIANTS
  2. the parameterised rebuild path reproduces edges.csv exactly (D-023)
  3. a first pass over the construction and representation parameters, which is
     a preview of the E-200 sweep and the evidence for F-007..F-010

    python experiments/E-002/run.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from railgraph import (  # noqa: E402
    BuildSpec, load_graph, measure, verify_rebuild_equivalence,
)

OUT = Path(__file__).parent

CELLS = [
    ("shipped default", {}),
    # F-007: tolerance x stitching
    *[(f"tol={t} stitch=ON", {"offset_max_km": t, "stitch_junctions": True})
      for t in (1.0, 1.5, 2.0, 3.0)],
    *[(f"tol={t} stitch=OFF", {"offset_max_km": t, "stitch_junctions": False})
      for t in (1.0, 1.5, 2.0, 3.0)],
    # D-001 node model
    ("node_model=station_only", {"node_model": "station_only"}),
    ("node_model=junction_only", {"node_model": "junction_only"}),
    # representation
    ("dissolve_degree2", {"dissolve_degree2": True}),
    ("prune_degree1", {"prune_degree1": True}),
    ("merge_colocated", {"merge_colocated": True}),
    ("gauge_constrained", {"gauge_constrained": True}),
    ("view=core_v2", {"view": "core_v2"}),
    ("view=core_v4", {"view": "core_v4"}),
    # D-003 matching
    ("match_conf=high only", {"match_conf": ("high",)}),
    # D-006 parallel policy
    ("parallel=mean", {"parallel_policy": "mean"}),
]


def main() -> None:
    print("=" * 78)
    print("E-002  g01 acceptance + construction-sensitivity preview")
    print("=" * 78)

    print("\n[1] shipped default vs SHIPPED_INVARIANTS")
    t = time.time()
    load_graph()                        # raises InvariantError on any mismatch
    print(f"    PASS  ({time.time() - t:.1f}s)")

    print("\n[2] rebuild equivalence vs edges.csv  (D-023)")
    eq = verify_rebuild_equivalence()
    print(f"    shipped {eq['shipped_edges']:,} / rebuilt {eq['rebuilt_edges']:,} edges")
    print(f"    identical pair set: {eq['identical_pair_set']}   "
          f"length mismatches: {eq['length_mismatches']}")
    assert eq["equivalent"], f"REBUILD DIVERGED: {eq}"
    print("    PASS")

    print("\n[3] parameter cells")
    rows = []
    for label, kw in CELLS:
        t = time.time()
        G = load_graph(BuildSpec(label=label, **kw), strict=False)
        m = measure(G)
        m["label"] = label
        m["spec_hash"] = G.graph["spec_hash"]
        m["bridge_share"] = m["bridges"] / m["giant_edges"] if m["giant_edges"] else 0.0
        m["secs"] = round(time.time() - t, 2)
        rows.append(m)
        print(f"    {label:26} n={m['n_nodes']:6,} e={m['n_edges']:6,} "
              f"comp={m['n_components']:4,} giant={m['giant_share'] * 100:5.1f}% "
              f"cyc={m['independent_cycles']:4,} br={m['bridge_share'] * 100:5.1f}% "
              f"km={m['route_km']:8,.0f}")

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "cells.csv", index=False)

    # F-007: the headline -- how much does stitching damp the tolerance swing?
    on = df[df.label.str.contains("stitch=ON")]
    off = df[df.label.str.contains("stitch=OFF")]
    summary = {
        "giant_share_range_stitched": float(on.giant_share.max() - on.giant_share.min()),
        "giant_share_range_unstitched": float(off.giant_share.max() - off.giant_share.min()),
        "bridge_share_range_stitched": float(on.bridge_share.max() - on.bridge_share.min()),
        "bridge_share_range_unstitched": float(off.bridge_share.max() - off.bridge_share.min()),
        "cycles_range_stitched": int(on.independent_cycles.max() - on.independent_cycles.min()),
        "cycles_range_unstitched": int(off.independent_cycles.max() - off.independent_cycles.min()),
    }
    summary["giant_sensitivity_damping_factor"] = (
        summary["giant_share_range_unstitched"] / summary["giant_share_range_stitched"]
        if summary["giant_share_range_stitched"] else None)
    summary["rebuild_equivalence"] = eq

    print("\n[4] F-007 -- tolerance sensitivity, stitched vs unstitched")
    print(f"    giant-component share range  stitched {summary['giant_share_range_stitched'] * 100:5.2f} pp"
          f"   unstitched {summary['giant_share_range_unstitched'] * 100:5.2f} pp")
    print(f"    bridge share range           stitched {summary['bridge_share_range_stitched'] * 100:5.2f} pp"
          f"   unstitched {summary['bridge_share_range_unstitched'] * 100:5.2f} pp")
    print(f"    independent cycles range     stitched {summary['cycles_range_stitched']:5,}"
          f"      unstitched {summary['cycles_range_unstitched']:5,}")
    print(f"    => stitching damps the tolerance sensitivity by "
          f"{summary['giant_sensitivity_damping_factor']:.0f}x")

    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nwrote {OUT / 'cells.csv'} and {OUT / 'summary.json'}")


if __name__ == "__main__":
    main()
