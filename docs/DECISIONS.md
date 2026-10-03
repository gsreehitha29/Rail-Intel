# Decision register (ADRs)

> Every modelling and construction decision, numbered, with the measurement that
> justified it. Two hard rules:
>
> 1. **No decision is accepted without an experiment ID** (`docs/EXPERIMENTS.md`).
> 2. **Every ADR states its reversibility.**
>
> `D-001`–`D-015` are migrated from `docs/GRAPH_HANDOFF_V2.md` §4.8, where they
> were agreed on 2026-09-30 and implemented in `s09_graph_dataset.py`. Their
> evidence is the Phase 2 pipeline measurement set, registered as `E-000`.
>
> Status vocabulary: `accepted` · `open` · `superseded` · `rejected`
> Last updated: 2026-10-03

---

## Index

| ID | Decision | Status | Reversible |
|---|---|---|---|
| D-001 | Node granularity: hybrid typed model | accepted | yes, re-run |
| D-002 | Degree-2 junctions retained and flagged | accepted | yes, one line |
| D-003 | Match confidence: high + medium | accepted | yes, filter |
| D-004 | Placement tolerance: offset_km ≤ 1.5 | accepted | yes, re-run |
| D-005 | Corridor-to-corridor connection: stitch at junctions | accepted | yes, re-run |
| D-006 | Parallel corridors: simple graph, shortest edge | accepted | yes, re-run |
| D-007 | Co-located stations: retain, floor length | accepted | yes, re-run |
| D-008 | Self-loops dropped from edge list | accepted | yes, in corridors.csv |
| D-009 | Physical layer undirected, service layer directed | accepted | yes |
| D-010 | Edge weight: geodesic length_km | accepted | yes |
| D-011 | Gauge: attribute and constraint, not filter | accepted | yes |
| D-012 | Speed: nullable attribute, never a filter | accepted | yes |
| D-013 | Data subset: two views via flags, not a smaller export | accepted | yes |
| D-014 | Service layer: L1 + L2 + coupling; space-P on demand | accepted | yes |
| D-015 | Service weighting: path-projected service_load | accepted | yes, both shipped |
| D-016 | Graph storage format | **open** | — |
| D-017 | Dissolve the 115 degree-2 junctions? | **open** | yes, one line |
| D-018 | core_v2 vs core_v4 as default attributed view | **open** | yes, flag |
| D-019 | Recompute spine-shortcut-affected edge lengths? | **open** | — |
| D-020 | The 18 residual components: keep, drop or investigate | **open** | yes |
| D-021 | `is_colocated` semantics: "was floored" vs "is short" | **open** | yes, one line |
| D-022 | Graph library: NetworkX as primary | accepted | yes, API-isolated |
| D-023 | Reimplement s09's edge construction rather than modify it | accepted | n/a |

---

# Accepted — migrated from Phase 2

## D-001 — Node granularity: hybrid typed model
**Date:** 2026-09-30 · **Status:** accepted · **Owner:** Bhuvanesh/Sandeep
**Evidence:** `E-000` · **Reversible:** yes, pipeline re-run

**Question.** Are nodes stations, junctions, or both?

**Options measured.**

| Model | Nodes | Giant component | Problem |
|---|---|---|---|
| junction-only | 2,029 | 88.2% | abandons the station-level thesis |
| station-only | 8,598 | 59.4% | silently drops 474 junctions, 101 at corridor_degree ≥ 3 |
| **hybrid** | **9,095** | **99.6%** | requires an explicit `node_type` |

**Decision.** Hybrid: a node is a `station` where a confident station identity
exists, and a typed `operational_junction` where it does not. The graph therefore
*states* where it asserts a passenger station versus merely a topology point.

**Why not the others.** Station-only fragments the network; junction-only
abandons the project's central claim. Of the 474 unmatched junctions, 46 are
degree ≥ 3 and structurally load-bearing — dropping them is not cosmetic.

**Precedent.** `[UIC16]` already distinguishes operation points from topology
points at meso level, so the typed model aligns with the standard rather than
inventing a category.

---

## D-002 — Degree-2 operational junctions retained and flagged
**Date:** 2026-09-30 · **Status:** accepted · **Evidence:** `E-000`
**Reversible:** yes — dissolution is one line downstream

**Question.** Dissolve degree-2 operational junctions by path contraction?

**Measurement.** Of the 474 junction nodes carrying no station identity:
**115 are degree 2** (dissolvable by path contraction — merge the two incident
edges, sum the lengths), **313 are degree 1** (line ends; prunable, not
dissolvable), **46 are degree ≥ 3** (load-bearing). Independently reconfirmed
from the shipped edge list in `E-001`. *An earlier handoff draft said 428 were
dissolvable; that was wrong and is corrected in `CHANGELOG.md`.*

**Decision.** Retain all 474; mark exactly the 115 with `is_dissolvable`.

**Why.** Dissolving is a one-line operation downstream; un-dissolving is not.
The flag costs nothing and preserves provenance.

**Precedent.** `[BOE25]` edge simplification; `[KAR16]` node merging. Both treat
degree-2 smoothing as a *downstream* choice, not a property of the stored graph.

**Open follow-up:** `D-017` decides whether graph v1 ships dissolved.

---

## D-003 — Match confidence: accept high + medium
**Date:** 2026-09-30 · **Status:** accepted · **Evidence:** `E-000`
**Reversible:** yes — filter on `match_confidence`

**Decision.** Accept `high` and `medium` station matches for junction identity
(1,555 of 2,029 junctions).

**Why.** Medium matches each carry a recorded spatial gap, so the risk is
*filterable* rather than hidden. 40 exact-name matches were deliberately
**rejected** on spatial conflict (worst: 1,620 km apart) rather than accepted —
see `LIMITATIONS.md` and `D-020`'s sibling follow-up.

---

## D-004 — Placement tolerance: `offset_km ≤ 1.5`
**Date:** 2026-09-30 · **Status:** accepted · **Evidence:** `E-000`
**Reversible:** yes, pipeline re-run

**Decision.** Use `offset_km ≤ 1.5` when chaining stations into edges; ship all
12,305 placements with a `used_for_edges` flag (11,662 used).

**Why.** `D-005` makes the graph insensitive to this threshold (99.6% vs 99.7%
giant component at 1.5 vs 2.0), so the tighter value is free. **This insensitivity
is itself a finding — `F-001` — and is the primary subject of `g05`.**

---

## D-005 — Corridor-to-corridor connection: stitch at shared junctions
**Date:** 2026-09-30 · **Status:** accepted · **Evidence:** `E-000`
**Reversible:** yes, pipeline re-run · **This is the load-bearing decision.**

**Question.** Corridors meet at *junctions*, not at stations. Where a junction
carries no confident station identity, or its station was not placed on both
corridors meeting there, the two station chains never touch and the network
shatters. How do we connect them?

**Measurement.**

| Build | Nodes | Edges | Components | Giant | Cycles |
|---|---|---|---|---|---|
| chains only, ≤ 1.5 km | 8,598 | 8,816 | 50 | **59.4%** | 268 |
| chains only, ≤ 2.0 km | 8,610 | 8,989 | 24 | 92.2% | 403 |
| **chains + stitched, ≤ 1.5** | **9,095** | **9,689** | **18** | **99.6%** | **612** |
| chains + stitched, ≤ 2.0 | 9,102 | 9,810 | 14 | 99.7% | 722 |

**Decision.** Attach every corridor chain to both of its junction endpoints;
corridors with zero placed stations still connect their two endpoints.

**Why.** Worth ~40 points of connectivity, and it removes the tolerance
sensitivity (`F-001`). Worked example: `Villupuram Junction` (station `VM`,
confidence high, gap 0.42 km) has five incident corridors; four contain VM and
connect naturally, the fifth (C02267) has its first placed station 18.7 km along
its spine, so that branch and 355 stations beyond it float away as a separate
component. Stitching adds one edge, `VM — KDMD`, and reattaches all of it.

**Precedent.** None found. `[KUR06]` removes shortcuts from timetable graphs;
`[KAR16, BOE25]` merge over-segmented street nodes. Chain *non-meeting* at
attribute-poor junctions appears to be rail-specific and unnamed. **This is
claim C2.** 2,252 of 9,689 edges carry `any_stitch = True`, so the operator's
footprint is large enough that `g04`/V3 must validate it separately.

---

## D-006 — Parallel corridors: simple graph, shortest edge retained
**Date:** 2026-09-30 · **Status:** accepted · **Evidence:** `E-000`, `E-001`
**Reversible:** yes, pipeline re-run

**Measurement.** **581** station pairs are produced by more than one corridor;
only **124** differ in length by more than 1 km (`E-001` reconfirms both).

**Decision.** Simple `Graph`, keeping the shortest edge, with
`n_parallel_corridors` and `parallel_differs` retained as attributes.

**Why.** A `MultiGraph` taxes every downstream algorithm across all 9,689 edges
for 124 genuinely distinct cases. The 124 are flagged, so Module 3 can recover
them for redundancy analysis.

---

## D-007 — Co-located stations: retain as separate nodes, floor the length
**Date:** 2026-09-30 · **Status:** accepted · **Evidence:** `E-000`, `E-001`
**Reversible:** yes, pipeline re-run

**Decision.** Keep co-located stations as separate nodes; floor edge length at
0.05 km; flag with `is_colocated` (249 edges).

**Why.** Merging destroys station identity, which Module 2 accessibility needs.

**Caveat found in `E-001`:** the flag means "*was floored*", not "*is short*" —
see `F-002` and `D-021`. `[BOE25]` recommends **topological** rather than
geometric consolidation if merging is ever revisited.

---

## D-008 — Self-loops dropped from the edge list
**Status:** accepted · **Evidence:** `E-000` · **Reversible:** yes

5 yard and balloon loops. No analytical value as graph edges; retained in
`corridors.csv` so nothing is lost.

---

## D-009 — Physical layer undirected; service layer keeps direction
**Status:** accepted · **Evidence:** `E-000` · **Reversible:** yes

GIS geometry direction is digitisation order, not operational direction, so
asserting it would be fabrication. Timetables do carry real direction, so the
service layer keeps it. Matches the `[KUR06]` G^φ / G^λ split.

---

## D-010 — Edge weight: geodesic `length_km`
**Status:** accepted · **Evidence:** `E-000` · **Reversible:** yes

The source `st_lengthshape` field is **~9% inflated** (median ratio 1.0902) —
computed in a projected CRS, not on the ground.

| Measure | Total |
|---|---|
| sum of `st_lengthshape` | 78,126 km |
| true geodesic length of the same geometry | **71,759 km** |
| IR Year Book 2024–25 route km | 69,439 km |

**Decision.** Geodesic everywhere. Never use the legacy
`rail_edges_initial.geometry_length_km`, which carries the inflation.

**Note.** 71,759 vs 69,439 is **+3.3%**, which `g04`/V2 must *decompose and
explain* (expected: parallel chords and loops counted as separate corridors), not
merely report as "close".

---

## D-011 — Gauge: edge attribute and traversability constraint, not a filter
**Status:** accepted · **Evidence:** `E-000` · **Reversible:** yes

2,217 of 2,279 corridors are Broad Gauge; 31 Metre, 29 Narrow, 1 Standard. Those
60 are genuinely not interoperable, so a shortest path crossing them is a
modelling error — but removing them from the graph is also wrong. Carried as an
attribute with an opt-in `gauge_constrained` routing mode.

---

## D-012 — Speed: nullable attribute, never a filter
**Status:** accepted · **Evidence:** `E-000` · **Reversible:** yes

Present on only 1,135 of 2,279 corridors (49.8%), and the corridors that have it
are **scattered, not clustered** — so requiring it collapses the giant component
to **771 nodes (14.6%)**. Any `travel_time_proxy` weight must state its treatment
of the nulls explicitly rather than impute silently.

---

## D-013 — Data subset: two views via flags, not a smaller export
**Status:** accepted · **Evidence:** `E-000` · **Reversible:** yes

| Subset | Corridors | Nodes | Edges | Cycles | Bridges |
|---|---|---|---|---|---|
| full, no filter | 2,279 | 9,058 | 9,669 | 612 | **14.6%** |
| V1 gauge+zone+lanes present | 2,042 | 7,983 | 8,454 | 472 | 25.1% |
| V2 V1 + Broad Gauge only | 1,988 | 7,780 | 8,241 | 462 | 25.3% |
| V4 V2 + clean reconstruction | 1,921 | 7,386 | 7,796 | 411 | 30.4% |
| V5 V4 + ≥2 stations placed | 1,525 | 6,890 | 7,217 | 328 | **35.8%** |

**Decision.** One graph; `attr_complete` / `recon_clean` / `core_v2` / `core_v4`
as **edge flags**. Never a separate filtered export.

**Why.** Every filter deletes real track, and deleted track was carrying
alternative routes. Independent cycles fall 612 → 328 while bridge share climbs
14.6% → 35.8%: **a resilience analysis on the filtered core would overstate
fragility by ~2.5×**, not because the network is fragile but because the filter
removed the redundancy. Independently corroborated in spirit by `[PAL26]`.

---

## D-014 — Service layer: L1 + L2 + coupling shipped; space-P derived on demand
**Status:** accepted · **Evidence:** `E-000` · **Reversible:** yes

Space-P (the transfer graph) would be roughly 16 million rows. The derivation is
three lines from the schedules, so it is computed on demand, not materialised.

---

## D-015 — Service weighting: path-projected `service_load`
**Status:** accepted · **Evidence:** `E-000` · **Reversible:** yes, both shipped

**Problem.** Counting only *direct* consecutive-stop pairs under-credits every
edge adjacent to a station that expresses skip. On corridor C00786 the counts
alternate 30/67 — not a traffic pattern but an artifact: 67 trains run the
corridor and 37 of them skip TRX, PQM, PCLM and NMO. This is exactly the
**shortcut** problem of `[KUR06]`.

**Decision.** Project every service pair onto its physical path and credit
**every** edge on that path (`service_load`). Edge coverage rises 80.0% → 89.9%.
The naive `service_direct` is retained for comparison.

**Bonus.** The same projection converts a topological cut into a service-impact
statement ("this edge strands N trains"), which is what makes Module 3 more than
a textbook percolation exercise.

---

## D-022 — Graph library: NetworkX as primary, behind an isolating API
**Date:** 2026-10-03 · **Status:** accepted · **Evidence:** none required
**Reversible:** yes — `railgraph.metrics` is the only caller

9,095 nodes is small; correctness and readability beat speed, and the Phase 4
modules will be written against it. All library calls are confined to
`railgraph/`, so `igraph` or `graph-tool` can be substituted behind the same API
if exact weighted betweenness across the `g05` sweep proves too slow (`g05` risk).

---

# Open — to be decided in g02

## D-016 — Graph storage format
**Status:** open · **Decides in:** `g02` · **Blueprint:** §13 asks for
interoperable tabular **plus** graph-native.

**Options.** GraphML · parquet node/edge tables · pickle · a graph database.

**Proposed (to confirm with evidence).** Ship all three non-exclusive formats —
GraphML as the citable graph-native primary, parquet for analysis speed, GeoJSON
for maps — and reject pickle (version-fragile, not interoperable, fails `[WIL16]`
Interoperable) and a graph database (operational burden with no analytical gain at
this scale). Decide by measuring round-trip fidelity and load time.

## D-017 — Dissolve the 115 degree-2 junctions in graph v1?
**Status:** proposed — **do not dissolve** · **Evidence:** `E-002` / `F-009`
**Confirm in:** `g02` after the centrality half of the measurement
**Reversible:** yes, one line

**Measured (`E-002`).** Dissolution is *not* topology-preserving on this graph:

```
nodes 9,095 -> 8,980  (-115, expected)   edges 9,689 -> 9,552  (-137, expected -115)
independent cycles 612 -> 590  (-22)
```

**22 of the 115 contractions land on an already-adjacent pair** — the junction
sits on a route parallel to a direct edge between its neighbours, so contracting
merges two distinct physical routes and destroys a cycle. 20 are visible in the
original graph; 2 more emerge during sequential contraction, making the operation
**order-dependent**.

**Proposed decision.** Do not dissolve in graph v1. Retain all 474 junctions with
`is_dissolvable` as today.

**Why.** Dissolving costs 3.6% of the network's independent cycles — precisely
the redundancy Module 3 measures — and the loss is silent unless cycles are
counted before and after. `[BOE25]` recommends degree-2 simplification for street
networks, where the neutrality assumption holds; `F-009` shows it does not hold
here. Keeping the flag preserves the option; dissolving destroys information.

**Still to measure before `accepted`:** betweenness top-50 overlap and Kendall τ
across dissolution, in `g03`/`E-003`. If rankings are also disturbed, the case
closes; if they are stable, the cycle loss alone still decides it.

## D-018 — `core_v2` vs `core_v4` as the default attributed view
**Status:** open · **Decides in:** `g02`

V4 additionally requires a clean spine reconstruction, so station ordering is more
trustworthy, at the cost of 394 nodes / 364 edges. Both flags ship either way;
this decides only the documented default. Measure: whether any attribute-weighted
conclusion differs between them.

## D-019 — Recompute the spine-shortcut-affected edge lengths?
**Status:** open · **Decides in:** `g02`, informed by `g05`

Affects **1,741 of 10,167** consecutive station pairs (17.1%), median shortfall
5.0%, 542 pairs > 10%, 54 > 25%. Topology is unaffected; **distance-weighted
results carry a systematic downward bias.**

**Options.** (a) recompute affected lengths from raw corridor geometry;
(b) accept and quantify, reporting every distance-weighted result with a
sensitivity band. Decide empirically: if `g05` shows no conclusion moves, (b)
is honest and cheap.

## D-020 — The 18 residual components
**Status:** open · **Decides in:** `g02`

9,058 of 9,095 nodes are in the giant component; the remaining 37 nodes form 17
small components. Investigate whether they are real isolated branch lines or
residual data gaps **before** dropping. Dropping without investigating would be
exactly the silent-deletion failure the project's engineering principles forbid.

## D-021 — `is_colocated` semantics
**Status:** open · **Decides in:** `g02` · **Evidence:** `F-002` (`E-001`)
**Reversible:** yes, one line

`is_colocated` currently means "*this edge's length was floored to 0.05 km*", not
"*these stations are co-located*". One edge, `E000454` (AMPR–PGK, 0.050404 km),
is 50 m long but unflagged because it sits just above the floor. Anyone filtering
on the flag to find co-located pairs will miss it.

**Options.** (a) redefine the flag by a distance threshold (e.g. < 0.1 km);
(b) keep the flooring semantics and rename to `length_floored`; (c) ship both
columns. Low impact (n=1 today) but it is a semantic trap for Phase 4, and
renaming is cheaper now than after freeze.


---

## D-023 — Reimplement `s09`'s edge construction in `railgraph`, rather than modifying `s09`
**Date:** 2026-10-03 · **Status:** accepted · **Evidence:** `E-002`
**Reversible:** n/a (no Phase 2 code was changed)

**Question.** `g05` needs `offset_km` and `stitch_junctions` as live parameters,
but in `s09_graph_dataset.py` they are module constants. Three ways to get there:

| Option | Cost |
|---|---|
| (a) refactor `s09` to take parameters | touches shipped Phase 2 code that currently produces a byte-identical rebuild; the project's own rules say change the pipeline only to change the dataset |
| (b) import `s09` and monkeypatch its constants | fragile, invisible at the call site, breaks on any `s09` refactor |
| (c) reimplement the construction in `railgraph`, parameterised, and **assert equivalence** | duplicate logic, with drift risk |

**Decision.** (c). `railgraph.build` reimplements `build_nodes` / `build_edges` /
`finalise_edges` with every constant promoted to a `BuildSpec` field, including
the pipeline's exact earth radius (6371.0088 km).

**Why the drift risk is controlled.** `verify_rebuild_equivalence()` rebuilds at
the shipped default and compares against `edges.csv` on canonical
`(from, to, rounded length)` form. `E-002` result:

```
shipped 9,689 edges / rebuilt 9,689 edges
identical pair set: True · length mismatches: 0 · worst length delta: 0.0
```

The test runs as step 2 of `experiments/E-002/run.py` and **fails the run loudly**
if the reimplementation ever diverges. That is a stronger guarantee than a
refactor would have given, because it is checked on every run rather than
reviewed once.

**Consequence.** Phase 2 is untouched, so `s10_verify_dataset.py` still passes
and the shipped dataset remains the authority. Phase 3 owns its own
construction code.

---

## D-024 — Add a `length_source` column to the Phase 2 pipeline
**Status:** proposed · **Decides in:** Phase 2 (`s09_graph_dataset.py`,
`s10_verify_dataset.py`) · **Evidence:** `F-021` (`E-007`, g02 round-trip test)

Exporting the graph to GeoJSON (g02) surfaced a defect no internal check had
caught: `JN::Khandala` is the one node of 9,095 with no coordinate. Its single
edge is a stitch, so its `length_km` is a haversine between endpoints — which
is **undefined**, not merely missing. That undefined value passes through the
`clip(lower=0.05)` floor in `s09` and comes out as `length_km = 0.05` with
`is_colocated = True`, indistinguishable from a real 50 m measurement.
`VERIFICATION.txt`'s "no null edge lengths" check passes — satisfied by an
undefined quantity having been turned into a number, which is exactly the
silent-substitution failure the project's engineering principles forbid.

**Options.** (a) leave it — the magnitude is one edge out of 9,689; (b) special-case
`JN::Khandala` with a hand-picked coordinate; (c) add a `length_source` column
(`measured` / `floored` / `undefined`) in `s09`, and change `s10`'s verification
to assert *measurement* rather than non-nullity.

**Decision.** (c), proposed. One edge changes nothing in the shipped numbers,
but the mechanism would hide the same failure on any future edge whose
endpoints both lack coordinates — and `s10`'s current check would still pass.
(b) only patches the instance, not the mechanism. This is a Phase 2 pipeline
change, outside `railgraph`'s read-only reimplementation (`D-023`), so it
belongs to the dataset owner rather than to Phase 3's graph build.

**Why not now.** Phase 2's dataset is frozen and `s10_verify_dataset.py`
currently passes against it; reopening the pipeline mid-Phase-3 risks exactly
the kind of silent dataset drift `D-023` was written to avoid. Tracked here so
it isn't lost, to be applied as a Phase 2 patch release rather than inside the
Phase 3 graph build.

**Reversible:** yes — additive column, no existing consumer depends on its
absence.
