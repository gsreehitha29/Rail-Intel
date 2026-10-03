# Experiment registry

> Every measurement that supports a decision, finding or paper claim. One row per
> run. Results are archived under `03_graph_construction/experiments/<id>/` with
> the script, the config, the environment and the output.
>
> ID blocks: `E-000` Phase 2 inheritance · `E-0xx` g00–g02 · `E-1xx` g03–g04
> validation · `E-2xx` g05 sensitivity · `E-3xx` figures and tables.
>
> Last updated: 2026-10-03

| ID | What it measures | Stage | Supports | Status |
|---|---|---|---|---|
| E-000 | Phase 2 pipeline measurement set (inherited) | s01–s10 | D-001…D-015, F-001, F-004, F-005 | complete |
| E-001 | Independent recomputation of the contested structural figures | g00 | D-002, D-006, D-007, F-002, F-003 | **complete** |
| E-002 | g01 acceptance + construction-sensitivity preview | g01 | **D-017, D-023, F-007…F-010** | **complete** |
| E-007 | Storage-format round-trip fidelity and load time | g02 | D-016 | planned |
| E-003 | Effect of degree-2 dissolution on structure and rankings | g02 | D-017 | planned |
| E-004 | core_v2 vs core_v4 on attribute-weighted conclusions | g02 | D-018 | planned |
| E-005 | Spine-shortcut bias: do affected edges change any conclusion? | g02 | D-019 | planned |
| E-006 | The 18 residual components: real branch lines or data gaps? | g02 | D-020 | planned |
| E-100 | Metric baselines on the frozen default graph | g03 | all downstream | planned |
| E-101 | V1 invariant re-derivation from the graph object | g04 | C1 | planned |
| E-102 | V2 structural plausibility vs theory (degree fit, route-km decomposition) | g04 | C1, F-004, `[KUR06]` prediction | planned |
| E-103 | V3 cross-source validation, **stratified** by stitch/confidence/offset | g04 | **C2, C3** | planned |
| E-104 | V4 prior-art reproduction: Sen and Bhatia from our data | g04 | C1, F-006 | planned |
| E-105 | V5 stratified ground-truth audit, two raters | g04 | C2 | planned |
| E-106 | V6 null models: degree-preserving and distance-constrained | g04 | C1 | planned |
| E-200 | One-at-a-time construction sensitivity sweep (~30 cells) | g05 | **C3** | planned |
| E-201 | tolerance × stitching interaction across the full battery | g05 | **C3, F-001** | planned |

---

## E-001 — Independent recomputation of the contested structural figures
**Date:** 2026-10-03 · **Stage:** g00 · **Script:** `experiments/E-001/g00_verify.py`
**Inputs:** `02_graph_inputs/graph_dataset/{nodes,edges,station_sequences}.csv`
**Environment:** Python 3.10.12, pandas 2.3.3, networkx 3.4.2, numpy 2.2.6

**Purpose.** Two of the project's own documents disagreed on articulation points,
bridges, parallel pairs and co-located edges. Rather than trust either, recompute
all of them from the shipped edge list.

**Result.** Every recomputed value matches `QA_REPORT.txt` / `VERIFICATION.txt`;
`GRAPH_HANDOFF_V2.md` §4.3 and §4.7 were the stale source (`F-003`).

```
nodes 9,095 · edges 9,689 · components 18 · giant 9,058 (99.6%) · giant edges 9,669
articulation points 1,338 · bridges 1,412 (14.6%) · independent cycles 612
degree mean 2.13 / max 7 · degree-2 share 82.8% · route km 72,201
n_parallel_corridors > 1: 581 · parallel_differs: 124 · is_colocated: 249
any_stitch: 2,252 · placements 12,305 (11,662 used) · offset > 1.5 km: 643
nodes: 8,621 station + 474 operational_junction, 115 dissolvable
```

**Incidental finding.** `is_colocated` counts 249 but 250 edges are ≤ 0.051 km —
the flag records flooring, not shortness (`F-002`, `D-021`).

**Supports.** `D-002` (115 dissolvable reconfirmed), `D-006` (581/124),
`D-007` (249), `F-002`, `F-003`.


---

## E-002 — g01 acceptance test and construction-sensitivity preview
**Date:** 2026-10-03 · **Stage:** g01 · **Script:** `experiments/E-002/run.py`
**Outputs:** `cells.csv` (20 cells × 18 measures), `summary.json`, `result.txt`
**Environment:** Python 3.10.12, pandas 2.3.3, networkx 3.4.2, numpy 2.2.6

**Three purposes in one run.**

1. **Invariant check.** The shipped default builds and matches all 14
   `SHIPPED_INVARIANTS`. Raises `InvariantError` otherwise.
2. **Rebuild equivalence (`D-023`).** The parameterised rebuild path reproduces
   `edges.csv` exactly — 9,689 edges both sides, identical pair set, 0 length
   mismatches, worst delta 0.0. This is the safety net for reimplementing `s09`
   rather than modifying it, and it fails the run loudly on any drift.
3. **Twenty parameter cells**, covering tolerance × stitching, the three node
   models, four representation transforms, two views, match confidence and
   parallel policy.

**Headline result (`F-007`).** Stitching damps the placement-tolerance
sensitivity of the giant-component share by **322×** — 0.23 pp stitched against
74.61 pp unstitched. Bridge-share sensitivity falls from 19.50 pp to 0.79 pp.

**Other findings generated.** `F-008` (tolerance saturates at 2.0 km; the sweep's
"∞" level is redundant), `F-009` (dissolution destroys 22 independent cycles and
is order-dependent → decides `D-017`), `F-010` (stricter matching *increases*
node count by splitting identities).

**Incidental fix.** `_merge_colocated` was reimplemented from iterated pairwise
contraction to single-pass component relabelling: 24.2 s → 0.7 s, and the result
*changed* (8,884 → 8,856 nodes), because pairwise contraction handled chains of
three or more co-located stations order-dependently. 183 groups absorbing 239
nodes, so ~56 groups have 3+ members. The faster implementation is also the
correct one.

**Supports.** `D-017` (proposed), `D-023` (accepted), `F-007`, `F-008`, `F-009`,
`F-010`; supersedes the provisional status of `F-001`.
