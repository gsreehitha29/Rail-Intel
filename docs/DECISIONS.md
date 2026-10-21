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
| D-016 | Graph storage format | accepted | — |
| D-017 | Dissolve the 115 degree-2 junctions? | accepted | yes, one line |
| D-018 | core_v2 vs core_v4 as default attributed view | accepted | yes, flag |
| D-019 | Recompute spine-shortcut-affected edge lengths? | superseded by `D-026` | — |
| D-020 | The 18 residual components: keep, drop or investigate | accepted | yes |
| D-021 | `is_colocated` semantics: "was floored" vs "is short" | accepted | yes, one line |
| D-022 | Graph library: NetworkX as primary | accepted | yes, API-isolated |
| D-023 | Reimplement s09's edge construction rather than modify it | accepted | n/a |
| D-024 | Add a `length_source` column to the Phase 2 pipeline | superseded by `D-026` (its Phase 2 verification change still stands) | yes |
| D-025 | Ship the station-matching defect flag in Phase 3; fix recall in Phase 2 separately | accepted | yes, additive columns |
| D-026 | Hybrid `length_km` with a `length_source` column | accepted | yes, but changes every distance-weighted |
| D-027 | Declare attribute granularity rather than implying edge-level measurement | accepted | yes, additive |
| D-028 | Ship bridge counts with a binding cross-zone restriction, or not at all | accepted | yes |
| D-029 | A fabricated speed must be visible in the output | accepted | yes, additive |
| D-030 | Propagate corridor conflict flags to the edge table | accepted | yes, pure join |
| D-031 | Derive `state` and `district` by reverse geocoding, not by join | accepted | yes |
| D-032 | An aggregate may validate a derived quantity; it may never populate a finer attribute | accepted | no |
| D-033 | The graph stays undirected in v1, stated rather than assumed | accepted | no, without a rebuild |
| D-034 | The product is infrastructure-side decision support; the time side is out of scope and said so | accepted | yes, with operational data |
| D-035 | Reconcile declared-but-unrun experiment IDs instead of deleting them | accepted | yes |
| D-036 | Split the licence by artifact class, and publish the method regardless of the dataset's terms | accepted | yes |
| D-037 | Verdict tiers live in code and are asserted against the published artifact | accepted | no, not sensibly |
| D-038 | The sensitivity claim now covers derivation; it still excludes travel time, and says so | accepted | no |
| D-039 | Exports carry every attribute, verified value-by-value; nothing is dropped from GeoJSON | accepted | yes |
| D-040 | Edge geometry: trusted spine slice, labelled chord, never snapped | accepted | yes |
| D-041 | The 17 small components are retained, reclassified, and listed for audit | accepted | — |
| D-042 | G-01 is a source-coverage gap, not a matching defect | accepted | n/a |
| D-043 | v1.2 removes 51 stitch edges that duplicate an existing route | accepted | yes |
| D-044 | Edge-level attributes from segment overlay | accepted | yes, additive |
| D-045 | Validated speed imputation replaces the 50 km/h constant | accepted | yes |
| D-046 | State inferred only above 99% LOO accuracy; AP/TG flagged | accepted | yes, additive |
| D-047 | Direction and time in the service layer; physical graph undirected | accepted | yes |
| D-048 | v1.3 ships as two variants: open (no OSM values) and full (ODbL) | accepted | yes |
| D-049 | Edge length by evidence hierarchy; official distance capped at 1.15x straight line + 1 km | accepted | yes |
| D-050 | OSM routed lengths are a check, never a length | accepted | yes |
| D-051 | A coordinate moves only if OSM, Wikidata and the node's own links all agree | accepted | yes |
| D-052 | State from boundary polygons replaces station-master and kNN states | accepted | yes |
| D-053 | Full-variant topology repairs need OSM routing evidence | accepted | yes, full only |
| D-054 | Manual corrections enter only through audit/OVERRIDES.csv, with evidence | accepted | yes |
| D-070 | Repo restructured; prior versions archived not deleted; one timeline document | accepted | yes |

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
**Status:** accepted · **Decided in:** `g02` · **Evidence:** `F-025`, `E-007`
**Resolution.** parquet as the working format (0.81 MB, 42x faster to load than
GraphML), GraphML as the citable primary, GeoJSON for GIS. Pickle rejected
(version-fragile, Python-only, fails FAIR interoperability); a graph database
rejected (operational burden, no analytical gain at 9,095 nodes).
interoperable tabular **plus** graph-native.

**Amended 2026-10-04 (`D-039`, `F-046`).** "GraphML as the citable primary" held
only if the GraphML carried the data; revision 1 did not (21 columns missing,
integers as strings). Revision 2 carries every attribute and is verified
value-by-value. The size figures quoted here are revision 1's (0.81 MB parquet;
GraphML 7.51 MB): revision 2 is 0.88 MB and 11.9 MB.

**Options.** GraphML · parquet node/edge tables · pickle · a graph database.

**Proposed (to confirm with evidence).** Ship all three non-exclusive formats —
GraphML as the citable graph-native primary, parquet for analysis speed, GeoJSON
for maps — and reject pickle (version-fragile, not interoperable, fails `[WIL16]`
Interoperable) and a graph database (operational burden with no analytical gain at
this scale). Decide by measuring round-trip fidelity and load time.

## D-017 — Dissolve the 115 degree-2 junctions in graph v1?
**Status:** accepted — **do not dissolve** · **Evidence:** `E-002` / `F-009`, confirmed by `E-100`
**Confirmation.** The centrality measurement ran in `E-100` and did not change the
conclusion: dissolving destroys 22 independent cycles and is order-dependent, so the
operation is not topology-preserving on this graph. The junctions are retained and
marked `is_dissolvable`, so a consumer can dissolve them deliberately and reversibly.
**Further evidence (`E-403`, `F-049`, 2026-10-04):** all 115 sit on a corridor
boundary (none has both edges on one corridor), 3 change gauge, and 20 land on an
already-adjacent pair — the reason, not only the count.
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
**Status:** accepted · **Decided in:** `g05` · **Evidence:** `F-022` (`E-200`)
**Resolution.** Neither. `view="topology"` -- the unfiltered graph -- stays the
default. Tier B of the sensitivity sweep shows `core_v4` filtering inflates mean
path length 47%, circuity 31% and bridge share 122%, and cuts top-50 corridor
criticality overlap to 0.34. The cores are attribute-completeness views, not
cleaner graphs, and ship as flags (`D-013`).

V4 additionally requires a clean spine reconstruction, so station ordering is more
trustworthy, at the cost of 394 nodes / 364 edges. Both flags ship either way;
this decides only the documented default. Measure: whether any attribute-weighted
conclusion differs between them.

## D-019 — Recompute the spine-shortcut-affected edge lengths?
**Status:** SUPERSEDED by `D-026` · **Decides in:** `g02`, informed by `g05`

Affects **1,741 of 10,167** consecutive station pairs (17.1%), median shortfall
5.0%, 542 pairs > 10%, 54 > 25%. Topology is unaffected; **distance-weighted
results carry a systematic downward bias.**

**Options.** (a) recompute affected lengths from raw corridor geometry;
(b) accept and quantify, reporting every distance-weighted result with a
sensitivity band. Decide empirically: if `g05` shows no conclusion moves, (b)
is honest and cheap.

## D-020 — The 18 residual components
**Status:** accepted · **Decided in:** `g02` · **Evidence:** `E-300`, `GAP_ANALYSIS.md`
**Resolution.** Retain all 18 components. The 37 non-giant nodes were enumerated
individually: every one is a junction-stitch pair or triple whose matched station
falls outside the giant component, not a data gap. They are flagged via
`component_id` and `in_giant` rather than dropped, and `giant_only` remains a
`BuildSpec` option for consumers who want the giant alone.

9,058 of 9,095 nodes are in the giant component; the remaining 37 nodes form 17
small components.

**Amended 2026-10-04 (`D-041`, `F-048`).** The resolution above said these are "not
a data gap"; that was asserted, not measured. `E-403` measured it and the evidence
points the other way: they sit closer to the giant than an ordinary node sits to
its neighbour, five share a coordinate with a giant node, and all 17 are on
corridors with the `G-01` station deficit. They are retained (dropping would be the
silent deletion the engineering principles forbid) but are now described as
*likely residual connection gaps, unverified*, with candidate links listed.

## D-021 — `is_colocated` semantics
**Status:** accepted · **Decided in:** `g02` · **Evidence:** `F-002`, `F-021`
**Resolution.** Keep the column and fix the semantics in the same change that
adds `length_source` (`D-026`): `is_colocated` currently means "this length was
floored", not "these stations are co-located". `length_source` makes the
distinction explicit, after which `is_colocated` is derived from a distance
threshold rather than from the flooring operation.
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
**Status:** SUPERSEDED by `D-026` (scope widened from the floored/undefined case to the full chord-vs-spine question); the Phase 2 verification change it proposed still stands · **Decides in:** Phase 2 (`s09_graph_dataset.py`,
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


---

## D-025 — Ship the station-matching defect flag in Phase 3; fix recall in Phase 2 separately
**Status:** accepted · **Evidence:** `F-026` (`E-300`) · **Reversible:** yes, additive columns

`F-026`: 42.9% of corridor–station incidences unmatched; 766 edges (24.5% of
route km) carry the defect signature.

**Options.** (a) do nothing until Phase 2 improves matching — leaves every
downstream module computing on a network where a fifth of the length is suspect,
with no way to know; (b) drop the suspect edges — disconnects the graph and
silently deletes real corridors, which the project's engineering principles
forbid; (c) flag them, ship, and let every module report with and without.

**Decision.** (c). Add to the edge table:

| column | definition |
|---|---|
| `station_match_deficit` | `declared_no_of_stations − n_stations_found` for the edge's corridor |
| `suspect_long_edge` | `deficit ≥ 3 AND length_km > 10` |

**Why not (b).** Dropping is irreversible and conflates "we failed to match" with
"no track here". Flagging is reversible and lets the sweep treat it as a factor.

**Why the threshold.** `deficit ≥ 3` and `>10 km` is where the `service_load = 0`
signature concentrates (40.9% of that subset). The thresholds are parameters in
`BuildSpec`, not constants, so `g05` can vary them.

**Phase 2 consequence (separate release).** `declared_no_of_stations` gives a
per-corridor target, so **station-matching recall becomes measurable for the first
time**. The project has never had this metric. That work belongs to the dataset
owner, not to the Phase 3 build (`D-023`).

**IMPLEMENTED 2026-10-03 (`E-400`).** 764 edges flagged, 17,670 km = **24.4% of
route km** — independently reproducing `E-300`'s 766 / 24.5% by a different
derivation. Usage guidance per `F-041`: a **path-analysis caveat, not a length
filter**.

**One deviation from the letter of this ADR.** The thresholds live in a separate
`ProvenanceSpec`, not in `BuildSpec`. Adding fields to `BuildSpec` changes
`spec.hash` and would have retired v1.0's frozen identity `f9adf8ca9042` for a
layer that is purely additive. The intent — thresholds as varyable parameters
available to the `g05` sweep, not constants — is preserved, and `ProvenanceSpec`
carries its own hash (`c9485b1d2e1e` at the default).

---

## D-026 — Hybrid `length_km` with a `length_source` column
**Status:** accepted · **Evidence:** `F-028`, `F-029` (`E-300`) · **Supersedes:** `D-024`
**Reversible:** yes, but changes every distance-weighted result

**Options.** (a) keep the chord — ignores real sinuosity, understates by 2.88%
aggregate and >5% on 17.7% of edges; (b) switch to the spine measure — adopts a
measure that is physically impossible on 12.9% of pairs and collapses to 64% of
the chord in the 1.0–1.5 km offset band; (c) hybrid, gated on offset and on
`spine ≥ chord`, with the choice recorded per edge.

**Decision.** (c):

```
spine                     if max(offset_a, offset_b) < 0.25 km and spine >= chord
chord_fallback_offset     if offset too large to trust the projection
chord_fallback_collapse   if spine < chord (projection collapse)
floored                   if the result is below min_edge_km
undefined                 if an endpoint has no coordinate  (F-021)
```

**Supersession of `D-024`.** `D-024` proposed `length_source` for the narrow
`JN::Khandala` floored/undefined case. The same column now carries the much larger
chord-vs-spine distinction. One column, one question: *how do we know this length?*
`D-024`'s Phase 2 verification change (assert measurement, not non-nullity) still
stands on its own.

**Expected effect.** +2.88% total route km, concentrated; circuity rises wherever
track curves; the `g05` conclusion `circuity_median` was computed on chords and
is biased low.

**Validation gate before shipping.** (a) no edge shorter than its own chord;
(b) the `F-029` sinuosity ranking must still place all four mountain railways in
the top 1%; (c) per-zone route km re-reconciled against `Table-19.2-Zone-wise.csv`.

**`g05` consequence.** `length_source` joins the sweep as a factor, and tolerance
× length_source becomes a required interaction cell (`F-028` coupling). The Tier A
"no artifacts" verdict has never been tested against this choice.

**IMPLEMENTED 2026-10-03 (`E-400`), with its premise corrected.** The rule above
ships unchanged. Two things stated in this ADR were wrong and are superseded by
measurement:

1. **The base was not the chord.** `F-042`: the v1.0 `length_km` was already the
   along-spine measure on non-stitch edges (98.4% match) and the chord on stitch
   edges — a de facto hybrid, reached by the structure of the build rather than
   by decision. The projected **+2.88% / +1,667 km is therefore wrong**; the
   measured effect is **+219.9 km (+0.30%)** on 1,286 edges. On this base the
   rule mainly replaces impossibly short spines *with* the chord (1,123 collapse
   cases), the reverse of what this ADR implies.
2. **Scope is consecutive station placements only.** `F-043`: this ADR is silent
   on stitch edges, and applying the rule to them anyway moved +1,073 km — 4.9×
   the specified case. All 2,252 keep their as-built length as
   `length_source = stitch_as_built`. A stitch-length rule is a separate
   decision; `W1` is where to take it.

All three validation gates pass, including (b): the shipped `sinuosity` column
ranks the four mountain railways **1, 4, 5 and 6 of 859 corridors**.

---

## D-027 — Declare attribute granularity rather than implying edge-level measurement
**Status:** accepted · **Evidence:** `F-027` (`E-300`) · **Reversible:** yes, additive

119,446 GIS segments carry 2,305 distinct corridor-level values. `gauge_code`,
`speed_kmph`, `n_tracks`, `zone_code` are corridor constants displayed per edge.

**Options.** (a) leave it — the edge table keeps implying measurements it does not
have; (b) aggregate the graph to corridor level — destroys the station-level model
that is the whole point; (c) ship `*_granularity` markers and state it in the
datasheet.

**Decision.** (c). Each inherited attribute gets a companion value in
`{segment, corridor, zone, inferred}`.

**Why it matters beyond bookkeeping.** Two edges on one corridor are not two
observations. Without this marker a downstream analysis will treat 9,689 edges as
9,689 samples and be overconfident by roughly the edge-to-corridor ratio. This is
a general hazard when building networks from segment-oriented GIS and belongs in
the paper's method section, not only in the datasheet.

**IMPLEMENTED 2026-10-03 (`E-400`).** Per-edge `*_granularity` columns in the
parquet and CSV; carried **once** at graph level in the GraphML
(`attribute_granularity`) rather than repeated on 9,689 edges, since the value is
constant per attribute. Also a manifest caveat.

---

## D-028 — Ship bridge counts with a binding cross-zone restriction, or not at all
**Status:** accepted · **Evidence:** `F-030` (`E-300`) · **Reversible:** yes

Capture rate 0.316 against the official count, range 0.006 (NFR) → 0.638 (WR).

**Options.** (a) ship `bridge_count` / `bridged_m` plainly — plants a
zone-correlated bias in the resilience module; (b) refuse entirely — discards the
only genuine segment-level attribute in the source; (c) ship with a binding
restriction plus a `bridge_capture_zone` column carrying that zone's capture rate.

**Decision.** (c), conditional: **if the restriction cannot be enforced where it is
consumed, fall back to (b).** A zone-correlated bias inside a resilience result is
worse than having no attribute.

Valid use: relative density within a zone or corridor. Invalid: absolute counts,
cross-zone comparison, any national total.

**Precedent.** This is the project's first attribute demoted *by* validation
rather than confirmed by it. Worth reporting as such — a validation section
containing only confirmations is not a validation section.

---

## D-029 — A fabricated speed must be visible in the output
**Status:** accepted · **Evidence:** `F-031` · **Reversible:** yes, additive

`speed_kmph` covers 64.38% of edges; the rest get `FALLBACK_SPEED_KMPH = 50.0`.

**Decision.** (a) add `speed_is_fallback` per edge; (b) make the fallback a
`BuildSpec` field rather than a module constant, so `g05` can vary it and measure
how much any travel-time result depends on it; (c) `travel_time_coverage()` must
be reported alongside every travel-time result, not available on request.

**Why not just document it.** The number is already documented in `weights.py`.
Documentation did not stop the value entering results indistinguishably from
measurements — the same failure as `F-021`, where a verification check passed
because an undefined quantity had been turned into a number.

**IMPLEMENTED 2026-10-03 (`E-400`).** `speed_is_fallback` true on **3,451 edges
(35.62%)**, reproducing this ADR's figure exactly from a different derivation,
plus `speed_used_kmph` making the substituted value explicit rather than implied.

---

## D-030 — Propagate corridor conflict flags to the edge table
**Status:** accepted · **Evidence:** `F-032` · **Reversible:** yes, pure join

200 corridors (8.78%) carry `any_attribute_conflict`; none of the flags reach the
edges. **Decision:** join `speed_kmph_conflict`, `gauge_conflict`,
`no_of_lanes_conflict`, `railway_zone_conflict`, `any_attribute_conflict` onto the
edges of those corridors. No new data, no judgement, one join. An arbitrated value
must announce that it was arbitrated.

---

## D-031 — Derive `state` and `district` by reverse geocoding, not by join
**Status:** accepted · **Evidence:** `F-033` · **Reversible:** yes · **New external dependency**

`state` is 45.77% on nodes and the station master offers exactly the same 48.29%
on station nodes. No in-repo source improves it. Coordinates are present on
9,094 of 9,095 nodes.

**Options.** (a) accept half-labelled nodes — blocks Module 2; (b) join harder on
the master — provably caps at 48.29%; (c) reverse geocode from coordinates against
an administrative boundary file.

**Decision.** (c). Gives state *and* district at ~100%, derived uniformly rather
than inherited patchily.

**Why the external dependency is acceptable.** It is a static, citable,
openly-licensed boundary file (GADM / Natural Earth / Survey of India), added to
`reference_data/` and hashed in the manifest like every other input. It does not
introduce a service dependency or a network call at build time.

**Validation.** Agreement against the 48.29% that already carry a state.
Disagreements are inspected and reported, never silently overwritten — the
existing value and the derived value both ship, with `state_source`.

---

## D-032 — An aggregate may validate a derived quantity; it may never populate a finer attribute
**Status:** accepted · **Evidence:** `E-300` inputs survey · **Reversible:** no — a standing rule

Several reference tables look like attribute sources and are not:
`zone_electrification_2021.csv` (zone), `gauge_history_1947_1971_2025.csv`
(national per year), `railway_key_stats` (national), `datafile.csv` (zone × gauge,
2009–11), `RS_Session_267` (zone), `Table-19.2-Zone-wise` (zone).

Electrification is the tempting one. Writing "Central Railway is 86.6% electrified"
onto every Central Railway edge **manufactures an attribute**: it carries no
information beyond `zone_code`, which the edge already has, while presenting
itself as a physical property of that track. A module could then report that
electrification predicts an outcome when it has rediscovered the zone.

**Rule.** An aggregate may be used to **validate** a derived quantity *at its own
level of aggregation*, and never to **populate** a finer-grained attribute.

This is the rule `F-030` follows (zone bridge counts used to validate, and the
attribute demoted when it failed) and the rule any future electrification work
must follow: get per-section data, or do not ship the column.

---

## D-033 — The graph stays undirected in v1, stated rather than assumed
**Status:** accepted · **Evidence:** `F-034`, `F-035` · **Reversible:** no, without a rebuild

Railways are directional; up and down lines differ in capacity, timing and
sometimes alignment. The graph is undirected and both service columns are
symmetric totals, so no directional asymmetry is representable.

**Decision.** Keep it undirected for v1 and **state the consequence**: every
bottleneck, criticality and capacity result is direction-blind. The schedule data
(`cleaned_schedules.csv`) could support a directed service layer, but that is a
second graph in a different space (`[KUR06]` service space), not an attribute of
this one — it belongs to the `V4` reproduction work, not to v1.

Recorded here because an undirected railway graph is a modelling choice a reviewer
will question, and "we didn't think about it" is a worse answer than "we scoped it
out, and here is what it costs".

## D-034 — The product is infrastructure-side decision support; the time side is out of scope and said so
**Status:** accepted · **Evidence:** `F-027`, `F-036`, `F-041`, `D-032`, `D-033`, `docs/LITERATURE.md` §1 · **Reversible:** yes, with operational data

The team wants to claim four applications: infrastructure connectivity
insight, festival-driven special-train rerouting, new-line planning, and a
multi-aspect what-if feature. Two of those collide with
`CLAUDE_COWORK_PROJECT_CONTEXT.md` §14, which lists capacity saturation,
headway and passenger demand as requiring operational data the project does
not hold, and §12, which forbids presenting Module 4 as a system that tells
Indian Railways where to build.

The literature pass makes the positioning precise: every prior
Indian-railway network paper found — through `[RST25]` in 2025, a delay
prediction GNN — works the service/time side. This project is the only
infrastructure-side construction. That is the contribution, and it is only a
contribution if its boundary is asserted rather than blurred.

**Decision.** Scope the product as **structural and strategic planning
support at the infrastructure layer**, and state explicitly that scheduling,
capacity, congestion and delay are out of scope. Specifically:

- A1 infrastructure connectivity insight — claim fully, as diagnostic
- A2 festival rerouting — **narrow to alternative-path screening**: enumerate
  physically viable paths and characterise each by single-track share, gauge
  continuity, bridge/articulation exposure, existing `service_load` and
  `suspect_long_edge` exposure. A screen, never a reroute recommendation
- A3 new-line planning — keep §12's guardrail; claim structural consequence
  of a hypothetical link, never feasibility
- A4 what-if — ship the seven of nine impact aspects that v1.0 supports;
  journey time waits for `W2`, budget allocation for `D11`
- Drop the word "operational" from all project descriptions in favour of
  "structural / strategic planning support"

**Why not the broader claim.** Demand and capacity are unheld, and `D-032`
already forbids populating a fine attribute from a zone aggregate, which is
the only demand data in the repo. Claiming rerouting would require breaking a
decision already taken on evidential grounds.

Full assessment, with the measured support for each application and the
what-if impact spec: `publication/APPLICATION_POSITIONING.md`.

## D-035 — Reconcile declared-but-unrun experiment IDs instead of deleting them
**Status:** accepted · **Evidence:** `docs/EXPERIMENTS.md` index audit · **Reversible:** yes

The registry declared `E-003`–`E-006`, `E-103`–`E-106` and `E-201` before the
work was done. Most were then answered under other IDs — `E-106`'s null models
inside `E-100`, `E-201`'s interaction grid inside `E-200`, `E-103`'s stratified
cross-source check inside `E-101` — and the index still listed them as
"planned" while also listing five completed experiments as "planned". A reader,
or the team in month seven, would go looking for `E-103` and find nothing.

**Options.** (a) delete the unrun IDs — loses the planning record, and the
paper outline cites them; (b) run them under their declared IDs — duplicates
work already done; (c) reconcile: keep every declared ID and state its
disposition (absorbed into X / superseded by Y / genuinely open).

**Decision.** (c), as a second table in the registry. Each declared ID now
resolves to one of: **absorbed** (`E-003`, `E-004`, `E-005`, `E-006`, `E-103`,
`E-106`, `E-201`), **superseded** (`E-104`, by the `W4` multi-layer plan), or
**genuinely open** (`E-105`, the two-rater audit, which needs two people and
cannot be done in software).

**Why not delete.** The planning record is itself evidence for the paper's
method section: it shows which validations were specified in advance rather
than chosen after seeing results. An ID that was planned, then answered
elsewhere, is a stronger statement than an ID that was never written down.

---

## D-036 — Split the licence by artifact class, and publish the method regardless of the dataset's terms
**Status:** accepted · **Evidence:** `publication/SOURCE_LICENCE_INVENTORY.md` · **Reversible:** yes

The repository contains **no `LICENSE` file at all**, and the primary GIS
source (`Railway_Network_.csv`, which feeds all topology, geometry and physical
attributes) has **no recorded upstream URL, publisher, download date or terms**.
The graph is a derivative work of it, so its redistribution terms gate the `C1`
artifact deposit.

**Decision.** Three separate licence decisions rather than one:

| class | licence | blocked? |
|---|---|---|
| code — `railgraph/`, experiments, `Makefile` | MIT or Apache-2.0 | **no** |
| prose — `docs/`, `publication/` | CC BY 4.0 | **no** |
| the graph artifact itself | undecided | **yes**, on the GIS source's terms |

**Why split.** It decouples `C2` (the construction method) and most of `C3`
(the validation and sensitivity study) from a licence outcome that only
threatens `C1` (the artifact). The method and the code can be deposited and
cited even if the dataset cannot, which protects two of three claims against a
risk neither of them actually carries.

**Availability statement, publishable as it stands:**

> The construction pipeline, the analysis code and the documentation are
> released under an open licence. Redistribution terms for the underlying GIS
> source have not been established, so the derived graph is described and fully
> reproducible from the pipeline, with deposit of the artifact itself pending
> that determination.

**Not legal advice.** Items 1–3 of the inventory's action table need a human,
and the GoI terms question needs the supervisor. Item 5 — adding `LICENSE`
files for our own code and prose — is unblocked and should not wait.

---

## D-037 — Verdict tiers live in code and are asserted against the published artifact
**Status:** accepted · **Evidence:** `F-044`, `F-045` (`E-401`) · **Reversible:** no, not sensibly

`E-200` shipped `verdicts_tierA.csv` — the file `C3` cites — with no script that
regenerates it, and the tier memberships existed only as prose. The untiered
file that `make` *could* produce reports **artifact** on all eight conclusions,
because it includes cells that deliberately negate a decided operator. The
number the paper cites and the number the repository could produce were
different numbers, and only the unproducible one was right (`F-044`).

**Decision.** `TIER_A`, `TIER_B_ADDS`, `TIER_C_ADDS` and `verdicts_for_tier()`
go in `railgraph/sensitivity.py`, **and `E-401` asserts on every run that they
reproduce `E-200`'s published Tier A exactly** — 8/8 verdicts, 8/8 deviations
to 1e-9.

**Why the assertion and not just the code.** Moving the definitions into code
makes them regenerable; it does not make them *right*. Without the assertion, a
later edit to either the tier list or the bands would silently produce a
different Tier A than the one three documents cite. The assertion is what makes
divergence impossible rather than merely unlikely.

**Why tiering is legitimate and not cherry-picking.** A verdict over all cells
is uninformative: `no_stitching` undoes `D-005`, and its breaking the graph is
the *evidence for* stitching, not a finding against it. The tiers must be
declared in advance and published together — all four verdict files ship, and
`VALIDATION_v1.md` reports Tier B's four artifacts rather than hiding them.

---

## D-038 — The sensitivity claim now covers derivation; it still excludes travel time, and says so
**Status:** accepted · **Evidence:** `F-045` (`E-401`) · **Reversible:** no

`E-401` added length derivation as a sweep factor and **Tier A survived: 0
artifacts, 0 verdicts changed**, with route km spanning a 2.4% band across
derivation modes.

**Decision.** State `C3` over **construction, representation and derivation**
choices — a materially stronger claim than `E-200` alone supported, and the
first time a distance-weighted conclusion in this project is known to be robust
to how distance was obtained. Two conclusions (`mean_path`, `circuity_median`)
now have their worst cell at a derivation cell, so derivation is reported as a
peer factor rather than a footnote.

**And state the remaining exclusion in the same breath.** `time_source` is
**not** a factor yet, because `W2` has not landed. Given `F-036`'s
declared-vs-observed ratio of 0.513, travel time is the factor most likely to
produce this project's first genuine Tier A artifact. The claim is therefore:
robust to how *length* was derived, untested on how *travel time* was derived.

Recorded because the temptation after a surviving sweep is to widen the claim
to "robust to derivation choices" without the qualifier, and the qualifier is
the part a reviewer would find.


## D-039 — Exports carry every attribute, verified value-by-value; nothing is dropped from GeoJSON
**Status:** accepted · **Evidence:** `F-046` · **Reversible:** yes · **Amends:** `D-016`

**Decision.** (1) Exported columns are **discovered from the graph**, never listed
by hand. (2) A null attribute is **omitted** in GraphML (absent == null), not
written as `""`. (3) Graph-level constants (`dataset_version`) are carried once at
graph level and re-attached on table exports. (4) **Every** node and edge is a
GeoJSON feature; one with no coordinate has `"geometry": null`. (5) The export
carries `export_revision` (now 2). (6) Verification compares every attribute of
every node and edge across GraphML, parquet and GeoJSON **and** every column and
value of the Phase 2 CSVs — the latter as a separate, independent check.

**Consequence for v1.0.** Its *content* is frozen and unchanged (topology, weights,
`spec_hash f9adf8ca9042`, input hashes). Its export *files* were regenerated;
their hashes differ from revision 1, recorded in `F-046`. A frozen artifact whose
export was defective is repaired, not preserved.

## D-040 — Edge geometry: trusted spine slice, labelled chord, never snapped
**Status:** accepted · **Evidence:** `F-047`, `E-402` · **Reversible:** yes · **Implements:** `W1`

**Decision.** `geometry_source = spine` only where `length_source == spine` (the
`D-026` trust rule) — the slice of the corridor spine between the two station
measures, with the **orientation rule** (`reversed_to_a` ⇒ position `L − measure`).
Otherwise `chord` (2-point, labelled), or `none` where an endpoint has no
coordinate. Slices are **not snapped** to node coordinates: stations sit up to the
recorded offset off the line and snapping would invent track. Spines of
`unknown` orientation are not sliced.

**Result.** 5,591 edges (57.7%, 56.4% of route km) carry true alignment, against a
v2.0 target of ≥85%. The remainder is stitch edges (2,251), `collapse` (1,123),
`offset` (679), `floored` (44): extending coverage needs placing stitch junctions
on spines (`W1` residual), not a looser trust rule.

**Considered and rejected.** Promoting `chord_fallback_offset` edges to spine
geometry would reach 64.7% but contradicts `D-026`, which declined those
placements; geometry should not trust what length does not.

## D-041 — The 17 small components are retained, reclassified, and listed for audit
**Status:** accepted · **Evidence:** `F-048`, `E-403` · **Amends:** `D-020`

**Decision.** Keep all 18 components (topology unchanged) but **replace** `D-020`'s
claim that they are "not a data gap" with the measured one: they are most likely
residual connection gaps (5 co-located with a giant node, 16 of 17 within the
ordinary nearest-neighbour range, 17 of 17 on `G-01`-deficit corridors),
unverified. `E-403/small_components.csv` is the candidate-link list. Joining them
is a manual audit decision, not a code change; it would add up to 17 edges and
501 km, and belongs with `E-105`'s human audit.


## D-042 — G-01 is a source-coverage gap, not a matching defect, and is not fixable in-repo
**Status:** accepted · **Evidence:** `F-051` · **Amends:** `D-025`, `GAP_ANALYSIS` G-01

Stop describing G-01 as "fix the matching in Phase 2": matching is complete against
the stations the repo has. The residual (≈9,900 incidences) needs an external
station gazetteer with coordinates; OpenStreetMap would supply one but its ODbL
share-alike licence would bind the dataset (`C1`), so adopting it is a licence
decision before it is an engineering one. `suspect_long_edge` stays as the caveat.

## D-043 — v1.2 removes 51 stitch edges that duplicate an existing route
**Status:** accepted · **Evidence:** `F-052`, `E-500`, `E-501` · **Reversible:** yes (`removed_edges.csv`)

Removed only when unsupported (same-corridor chain, or <50% of its length in its
corridor's geometry) **and** an equivalent route exists (≥2 hops; 0.85–1.15× measured
/ 0.85–1.30× chord). Sequential, longest first. v1.0 and v1.1 untouched; v1.2 is a
new topology and says so in its manifest. 56 further unsupported edges with no
equivalent route are flagged (`geometry_unsupported`), not removed.

## D-044 — Edge-level attributes from segment overlay; corridor value where the source has nothing finer
**Status:** accepted · **Evidence:** `F-053` · **Reversible:** yes, additive

New columns (`bridge_km`, `bridge_present_edge`, `tunnel_km`, `tunnel_present_edge`,
`zone_code_seg`, `n_tracks_seg`, `speed_kmph_seg`, `gauge_code_seg`,
`edge_attr_source`, `overlay_coverage`); corridor-level originals kept unchanged.
Phase 2's `0 = unknown` rule applied. Below 50% overlay coverage the corridor value
is kept and labelled.

## D-045 — Validated imputation replaces the 50 km/h constant; the gap is labelled, not hidden
**Status:** accepted · **Evidence:** `F-054` · **Supersedes:** the constant in `D-029`

`speed_used_kmph` = declared, else gauge × zone median, else gauge median; never a
constant. `speed_source` and `speed_expected_abs_error_kmph` on every edge;
`weights.travel_time_proxy` reads `speed_used_kmph`. Gauges with no declared example
(standard gauge, 6 edges) get `none`. The MNAR bias is stated as unquantified.

## D-046 — State inferred only where leave-one-out accuracy exceeds 99%; AP/TG flagged
**Status:** accepted · **Evidence:** `F-055` · **Reversible:** yes, additive (`state_best`, `state_source`)

`state` (the source value) is untouched. 2,309 nodes stay unlabelled rather than
take a lower-accuracy guess. A state-boundary dataset is the only full fix.

## D-047 — Direction and time live in the service layer; the physical graph stays undirected
**Status:** accepted · **Evidence:** `F-056`, `E-502` · **Closes:** Phase 3 plan item 6

The physical graph describes track, and the source records no running direction.
Direction, run-times and time of day are delivered in `service_layer/`, keyed to the
physical graph. Capacity and trains-per-week are declared out of reach: no input
contains them.


---

## D-048 — v1.3 ships as two variants so the OSM licence decision stays reversible

**Context.** OpenStreetMap (ODbL 1.0) closes several gaps, but copying its values makes the
released graph an ODbL database. The team has not decided. **Decision.** Every stage writes
both `graph_v1_3/open/` (OSM may only check or arbitrate between non-OSM values) and
`graph_v1_3/full/` (OSM values allowed, each tagged by a `*_source` column). Gate G4 asserts
the open variant carries no OSM-sourced value. **Consequence.** Choosing a licence later needs
no rebuild. Both variants still inherit the unresolved licence of `Railway_Network_.csv`.

## D-049 — Edge length by evidence hierarchy (E-600)

Per edge, in order: track-measured spine confirmed by the official timetable distance; the
official distance (data.gov.in 2017, else 2015); spine without an official figure; otherwise the
straight line, flagged `length_is_lower_bound`. An official distance is used only if it lies in
[0.9x straight line − 1 km, 1.15x straight line + 1 km]; below, it is a conflict (`audit/03`);
above, trains take another route (`audit/04`). Where spine and official disagree, OSM decides
if it agrees with exactly one; otherwise spine is kept and flagged (`audit/05`). Every length
is floored at the straight line on final coordinates. The 1.15 cap was chosen from
{1.15, 1.25, 1.35, 1.6} on 700 tuning trains and confirmed on a disjoint 700-train hold-out
(F-058).

## D-050 — OSM routed lengths are a check, never a length

Every rule variant that took lengths from OSM routing gave worse whole-train route totals than
the same rule without them (tuning sample: median abs 2.24-2.99% vs 1.73%), including using OSM
only for straight-line edges and with a 1.5% calibration. OSM still arbitrates spine-vs-official
disputes and validates station insertion. `OSM_LENGTHS_USED = False` in `railgraph/v13.py`.

## D-051 — A coordinate moves only if three sources agree

A station is moved to its OSM (full) or Wikidata (open) position only if the graph position is
>10 km from both, OSM and Wikidata agree within 2 km, and the move makes the node's links more
consistent with their measured lengths. Without the third test 33 stations moved and edges of
1,600 km appeared (KAVI): the code, not the place, was wrong. 5 moved; 28 go to `audit/01`.

## D-052 — State from boundary polygons

datameet/maps `States/Admin2` (36 states/UTs, post-2020, CC BY 4.0) assigns the state from the
node coordinate, replacing station-master and kNN states (D-046 superseded for v1.3).
Coverage 9,088 / 9,095; 264 differ from v1.2, mostly Andhra Pradesh → Telangana (`audit/13`).

## D-053 — Full-variant topology repairs need OSM routing evidence

Merges: a junction joins a station within 2 km whose name or Wikidata alias matches, or a
junction of the same normalised name within 1 km (16). Connectors: a small component joins the
main network along OSM track within 30 km (14 of 16). Insertions: an OSM station with a code not
in the graph is inserted into an edge only if it lies within 1 km of the edge and routing
u→s→v is within max(1 km, 5%) of u→v (488 stations, 337 edges); the parent length is split by
OSM position. Service attributes on split edges are inherited and must be rebuilt.


## D-054 — Manual corrections enter only through `audit/OVERRIDES.csv`

Audit decisions are rows in `graph_v1_3/audit/OVERRIDES.csv` (action, item, field, value,
evidence, source URL, reviewer, date), applied at assembly in both variants on every rebuild.
A row without evidence, an unknown action or an id absent from the variant stops the build
(`reject` of an id absent from a variant is logged as skipped). Nobody edits exported files by
hand: a correction that is not in the overrides file does not exist.

## D-055 — Graph v1.4 is final; the stop rule replaces the repair backlog

**Experiment:** E-707 (audit, stability recomparison) and E-708 (gated v1.4 build).

Repairs to v1.3 left articulation points and bridges **nested**: all 1,173 cut points and
all 1,256 bridges in v1.4 were already present in v1.3, and 207 false cut points were removed
without a single new one appearing. The mechanism, not chance: 129 of 137 overrides add an
edge (which can only destroy a cut point), and the 8 removals are shortcuts whose endpoints
remain joined by a train-attested path. Further repair of the same kind can only shrink those
sets again. Betweenness is the opposite: 15 of the top 50 moved under one round of repair.

Therefore v1.4 is frozen and declared fit for the **stable class** of claim (connectivity,
reachability, route distance, cut points and bridges, corridor load with `trains_per_day`) and
permanently unfit for the **unstable class** (node-level criticality ranking, absolute km,
exact centrality values) — the latter blocked by 228 absent stations, 82 duplicate node pairs
and 25.9% lower-bound lengths, none derivable from any source held.

**Stop rule.** v1.4 is amended only when an analysis result is demonstrably wrong *because of*
the graph, on a named reproducible case. A newly discovered defect is recorded as a property
of the dataset (`graph_v1_4/FITNESS.md` §6), not as a backlog item. The repair queue
regenerates from incomplete inputs and cannot be exhausted, so "fix the remaining gaps" was
never a terminating instruction.

**Reversibility:** fully reversible as to the freeze — an amendment is a new version (v1.5)
with its own gates and manifest; v1.4's files are never edited in place. The fitness
classification is reversible only by new source data (a station register with authoritative
codes and geometry), not by further repair.

## D-056 — The release has a contract, enforced by tests

**Experiment:** none needed; this is an engineering decision. Artifacts: `tests/`,
`docs/STABILITY.md`, `make test`.

"Stable baseline" was an intention with nothing enforcing it: the repository had no test
suite of any kind, so a derivation module could change its output and the release would
drift silently. `docs/STABILITY.md` now states what downstream code may rely on — the
`railgraph.release` entry point, node and edge identity, append-only schema, the counts,
CSV as canonical — and what it may not, including parquet bytes, row order and analysis
module outputs. `tests/` (30 tests) enforces it against `tests/golden.json`, which is
generated from the release and reviewed, never hand-typed.

A red test is a fork, not a chore: either something edited a frozen file (fix the cause)
or a new release is being cut (regenerate the golden values *with* a decision entry).
Editing `golden.json` to turn a test green destroys the only drift detector we have.

**It immediately caught two real defects, one of them mine:**
1. `graph_v1_4/README.md` was hand-edited on 2026-10-12 to add the FINAL banner, breaking
   its manifest hash — exactly the hand-edit D-054 forbids. Fixed at the cause: the banner
   now comes from `stage_docs`, and the release was regenerated (manifest 14 -> 15 files,
   picking up `FITNESS.md`).
2. The published caveat said 25.9% of route km is a lower bound. The measured value is
   **25.3%** (the 21.4% edge-count share is a different denominator). The figure had
   drifted from v1.3. Corrected in `railgraph/release.py` and `FITNESS.md`, and a test now
   asserts the caveat text against the measurement so they cannot diverge again.

**Reversibility:** fully reversible — deleting `tests/` restores the prior state, at the
cost of the guarantee. The contract's *content* is reversible only by cutting a new release.

## D-057 — C1 cannot be deposited on the current base source

**Evidence:** `publication/SOURCE_LICENCE_INVENTORY.md` §8 (schema verification).

`Railway_Network_.csv` is an export of Esri India's Living Atlas "Railway Tracks" layer:
eleven of its fifteen columns match that layer's declared fields in the same order, the
three extras are ArcGIS export artifacts, and no data.gov.in resource with this schema
exists. The owner's recollection of a government portal is **not supported by the
evidence**, and the inventory's own standard (§6) is that a recollection is not a licence.

The portal item's terms do not permit export for offline use, so the derived graph cannot
be deposited. **C2 and C3 are unaffected** and the availability sentence in §5 was already
written for this outcome.

**Scope consequence.** The pitch presents an internal, fully reproducible dataset plus an
open, citable method — not an open dataset. A depositable C1 requires rebuilding the
topology from the OSM extracts already in `external_data/`, which is weeks of construction
work because the corridor/spine logic is shaped around this CSV's junction semantics. That
rebuild is a roadmap item, not a sprint item.

**Reversibility:** reversible only by written permission from Esri India, or by the rebuild.

## D-058 — Scope locked; the product is corridor vulnerability

**Artifacts:** `docs/SCOPE.md`, `docs/PROJECT_OVERVIEW.md`.

The scope stayed ambiguous for months because it kept being written forward from
intentions. It is now written backward from evidence: C1 (the artifact) is v1.4, gated and
test-guarded; C2 (junction stitching, 59.4% -> 99.6%) is implemented and recorded as 179
evidence-carrying overrides; C3 (which conclusions survive construction) is E-710, E-711
and the D-055 nesting result.

**The product is one thing, not a menu:** a corridor-level vulnerability and contingency
tool — which corridors have no alternative route, what each isolates, how much daily
traffic depends on it, what a named blockage cuts off. Chosen because every input metric
is in the robust class, it answers a problem Indian Railways demonstrably faces, and it
already carries two retrodictive validations.

Eight exclusions are named with their reasons in `SCOPE.md` §3 so that none reads as an
oversight, and four roadmap items (R1 OSM rebuild, R2 deferred lengths, R3 duplicate
merge, R4 service-space projection) are costed and explicitly out of scope.

**Reversibility:** reversible by a later decision, but the exclusions are each pinned to a
data limitation rather than a preference, so reversing one requires new data, not a new
opinion.

## D-059 — Module scope locked to the analyses measured as feasible

**Evidence:** E-714. **Artifact:** "Rail-Intel — contribution, feasibility and scope lock" (Claude Doc).

Each analysis listed by the four planned modules was re-run under the dataset's two known
uncertainties: floor lengths scaled by their measured shortfall (median 1.49x), and the
v1.3 -> v1.4 repair change (E-707). Of 18 analyses, 8 are feasible as they stand, 6 only as
ranks or lower bounds, and 4 not at all: station rankings by betweenness, closeness or PageRank
(top 50 moves by 12-15 under either uncertainty; a 300-sample estimate agrees with itself on only
21 of 50), betweenness-targeted failure, the cost or feasibility of new lines, and capacity,
congestion or delay mechanisms. The module READMEs, which still describe v1.0 and list these
analyses, are superseded by this scope.

Contribution claims stated against current work: C1 the only physical, geolocated station-level
Indian-railway graph (9,095 nodes, 1.9x IIT Kharagpur's IRN); C2 junction stitching; C3
conclusion robustness, now including the measured gap between a timetable network and track
(F-028).

**Reversible:** yes — an analysis returns to scope when a new measurement shows it stable.

## D-060 — OpenStreetMap is built as a separate graph, v2.0-open

**Evidence:** E-715. **Artifact:** "Rail-Intel — build roadmap and milestones" (Claude Doc).
**Adopted:** 2026-10-19, on the instruction to proceed strictly by the roadmap.

v2.0-open is built from OpenStreetMap alone, by stages O1–O8 (filter, collapse parallel
tracks, snap stations, contract, stitch, join service, validate against v1.4.1, release), under
ODbL with attribution. It is never merged into v1.4.x: an ODbL value inside the Esri-derived
graph (D-057) would make neither publishable. D-050 stands for v1.4.x — OSM lengths are a check
there, never a value. Which graph the product uses is decided at gate G-C on evidence.

**Reversible:** yes, at G-C.

## D-061 — the build follows the roadmap's milestones and gates

**Artifact:** "Rail-Intel — build roadmap and milestones". **Adopted:** 2026-10-19.

Ten milestones (A1–A3, C1–C4, B1, D1–D2) and two gates (G-A, G-C), taken one at a time. A
milestone is done only when its gate passes as a test or recorded check. A date moves only by a
recorded change to the roadmap. Experiment numbers: E-716 the OSM build, E-717 the v1.4.1 build.

## D-062 — OpenStreetMap collapse and snap settings

**Evidence:** E-716 (milestone C1), `graph_v2_0_open/work/calib_*.csv`. **Adopted:** 2026-10-19.

- **Merge distance 15 m.** For every OSM chain of at least 300 m, the median distance to the
  nearest other track. Double track is a sharp mode at 4–8 m. 15 m is the first bin edge where
  the density falls below 5% of its peak (12–15 m: 5.5%; 15–20 m: 1.9%). Chosen from that
  table before the route-km figure was computed.
- **Minimum parallel run 100 m, gaps up to 30 m closed.** This keeps a diverging line from
  being merged at its turnout.
- **Re-join distance 30 m (2 × merge).**
- **Snap distance 100 m.** 94.6% of coded stations lie within 50 m of kept track. Beyond 75 m
  the curve is flat: about 0.1 percentage points per further 25 m to 50 m. 100 m is the first
  round edge on that flat part; at 75 m the share would be 95.24%.

**Sensitivity, measured and not used to choose:**

| Merge distance | Route km vs 69,439 |
|---|---|
| 10 m | +11.6% |
| 12.5 m | +7.6% |
| 15 m | +5.3% (track only) |
| 20 m | +3.0% |
| 25 m | +2.1% |

Gate C1a passes only for merge distances of about 13 m or more, so its margin depends on this
setting.

**Reversible:** yes, by a new decision with a new calibration.

## D-063 — OpenStreetMap station graph: stations, joins and contraction

**Evidence:** E-716 (milestone C2), `graph_v2_0_open/work/c2_*`. **Adopted:** 2026-10-19.

**Stations**
- A snapped OSM station or halt is a node if it lies inside the Survey of India outline. The
  outline comes from datameet and is used only as a filter.
- A station flagged `review_metro` is not a node unless a timetable knows its code.
- Same code within 2 km is one station: 35 of the 48 repeated codes. The other 13 are more than
  5 km apart; they become conflicts, `code~osmid`, and are listed.

**O3b, timetable codes OSM has no coded station for** (457 codes, among them Katpadi, Madurai
and Coimbatore, which OSM maps as areas)
- Each code is located from Wikidata (CC0).
- An OSM station within 300 m makes the code an alias. 300 m is just above the 202 m
  75th percentile of the OSM-to-Wikidata distance on shared codes. Most aliases are renamed codes.
- Otherwise, a station is placed on track within 100 m (the C1 snap distance).
- Otherwise, the code stays unresolved.

**O5, joins.** Every join is listed with its evidence; none rests on proximity alone beyond 100 m.
- **A:** along OSM running track, using at most 2 km of yard or station track. The largest such
  piece seen was 1.45 km.
- **A2:** a piece whose track ends within 100 m of a main-network station. This is one station
  with two gauges or two platform groups.
- **B:** a 2024 train, plus OSM track set aside as not running.
- **C:** a 2024 train and no OSM track. The timetable distance is used if it fits the v1.3 band.
- Only 2024 trains count as evidence, so a line closed since 2017 is not rejoined.

**O5 runs before O4,** on the track-level graph, so a join lands at its true point.

**O4, contraction**
- Dangling track that reaches no station is pruned.
- Degree-2 points are spliced out; where two routes join the same pair of points, the shorter stays.
- An edge of at most 3 km is dropped when another path joins its two ends within 1.2× its length
  + 0.2 km and passes a station. This removes second lines round stations.
- Junctions stay as `JN:` nodes: no distance threshold was found that separates a station's own
  junction from a nearby one (the junction-to-station distance runs evenly from 0.3 to 3 km).

**O6.** E-708's service stage, unchanged, through the v1.4 loaders.

**Reversible:** yes, by a new decision.

## D-064 — Gate C2b is counted over stations with a 2024 train

**Decided by:** Bhuvanesh Vinjamuri, 2026-10-19. **Evidence:** E-716 (C2), F-043.

The roadmap gate "at least 99.5% of stations in the main network" is counted over stations
that had a train in September 2024. Over all stations it is 98.91%: 102 of the 104 stations
outside are on suspended or closed lines that OSM still tags as running. Counted over served
stations it is 99.96% (4,691 of 4,693). Both figures are reported in every build.

**Reversible:** yes, by a later decision.

## D-065 — The collapse keeps routes; station throats are added; C1a moves to the station graph

**Evidence:** E-716 (P1, checkpoint CP1). **Adopted:** 2026-10-20 by the executor. Flagged at CP1
for your veto (V2-17).

**Why.** Rerunning the E-708 gates on the first v2.0 build found 2024 routes with a median error of
39%. Two causes:
1. **The collapse broke routes in large stations.** It kept a platform line that ends, and removed
   the through track. 530 timetable pairs were affected.
2. **O1 had set aside the crossovers and station tracks (`service=*`)** that carry through routes at
   junctions such as Madhupur, Dindigul and Vriddhachalam.

**What changed**
- **O2 check.** A removed stretch stays removed only if the kept track replaces it within
  1.3× its length + 0.2 km. 1,250 of 11,855 stretches were restored, over 7 rounds.
- **O5a throats.** Service track of at most 2 km that joins two points of kept line is added at its
  measured length, where the network between those points is longer than 1.3× the throat + 0.5 km.
  This added 731 links, 174 km.
- Both rules use geometry and OSM topology only. The timetable remains an independent test.

**Effect.**
- 2024 route median error is 0.39% and IRN agreement is 93.5%. All nine v1.4 gates pass on v2.0.
- The intermediate track km after collapse rises to 74,838 (+7.8%), so the roadmap's C1a, at ±7%,
  would fail there. C1a is now measured on the station graph as gate C2d: 70,298 km, +1.2%, pass.

**Reversible:** yes.

## D-066 — Exact physical graph; a places view for structure

**Evidence:** E-716 P2 pass 2. **Adopted:** 2026-10-20 by the executor.

The physical graph has 1,265 cycles. 2,216 of its sections lie on cycles of 5 km or less, nearly
all junction to junction: triangles, crossovers and parallel lines inside junction areas. Merging
them into the graph would distort lengths. Tested: absorbing junctions within 1 km changed 12.5% of
2024 consecutive-stop distances by more than 1%, and moved the route median error from 0.39% to
0.97%.

**So the physical graph keeps every junction and its exact lengths**, and a derived **places view**
(`open/places/`) applies one rule: track points within 1 km of each other along the track are one
place.
- Junction clusters become one junction.
- A junction within 1 km of a station becomes part of it.
- Every physical node carries `place_id`.

| | Places view | v1.4.1 |
|---|---|---|
| Stations | 9,540 | — |
| Junctions | 516 | — |
| Cycles | 496 | 682 |
| Cycles, served network | 319 | 355 |
| Cut-point agreement | 96.9% | |

**Use the physical graph for distance and routing, and the places view for structure:** degree,
cut points, redundancy.

**Reversible:** yes.

## D-067 — The release ships the open 2017 service layer; the 2024 layer is built locally

**Evidence:** E-716 P2 pass 3 (`work/p2_service_comparison.json`). **Adopted:** 2026-10-20, under
your instruction to seek permission only if the 2024 data is worth it.

| On v2.0 | 2017 (data.gov.in, GODL) | 2024 (IIT Kharagpur, licence not stated) |
|---|---|---|
| Trains | 10,725 | 3,892 |
| Served stations | 8,050 | 4,694 |
| Share of km with service | 89.2% | 85.9% |
| Trains per day | no: the file has no running days | **yes**, observed over 30 days |
| Lines opened 2018–2024 | no | **yes**: 2,595 km served only in 2024 |

- Served sections overlap at Jaccard 0.88, and trains per section correlate at Spearman 0.93 on
  shared sections.
- 2017 is wider, because it includes passenger and local trains. 2024 is newer, and is the only
  source of trains per day, which the product's "dependent trains per day" needs.

**Decision.**
- The publishable v2.0 carries the 2017 layer (`service_layer_v2_0_open/open_2017/`, scheduled
  trains per section) and the `scheduled_2017` flags.
- The 2024 layer and `served_2024` are built by `make osm-c2` from the public source, for
  in-house analysis, and stripped from the release package (P3) unless permission is given.
- A permission request to the RSTGCN authors is worth sending: low effort, and it would let the
  release carry trains per day. The release does not wait for it.

**Reversible:** yes, on permission.

## D-068 — The build reads only open data; 2024 is for checking

**Evidence:** E-716 P3. **Adopted:** 2026-10-20 by the executor, following D-067.

Until P3 the build used both timetables to decide which codes exist, which stations are
metro stations, and which pieces to join. That made the published graph depend on the 2024
data, whose licence is not stated. Now:

- The build reads the **2017 timetable** (GODL) and **Wikidata** (CC0) only. The 2024
  routes are used afterwards, to check the graph (gates C2b, C3) and for the local 2024 layer.
- A **C join** (timetable distance, no OSM track) uses 2017 trains. Two remain: Patal Pani–Dr. Ambedkar
  Nagar and Samni–Vagara, 14.3 km, marked `length_source = timetable_2017`.
- **Metro stations.** A station OSM tags subway, monorail or light rail is dropped unless a
  timetable knows its code and a neighbouring station of that code lies within 50 km. This drops
  Welcome, Mansarovar Park and St. Thomas Mount Metro (conflict codes), and
  Durgapuri (DGPI is a Lucknow metro station in OSM and a Gwalior–Sheopur halt in the timetable).
- **Same name, same place.** An uncoded station named as a coded one within 1 km is another point
  of that station (22 cases); a Wikidata code with no 2017 train can go to an uncoded station of the same name (4).
- **Shared stations.** A2 joins also fire when a station of one side stands within 100 m of the other
  side's track. This replaced two timetable joins (Coimbatore–Mettupalayam 35.5 km, Bilimora–Gandevi 5 km)
  with joins at the station, measured on track.

**Effect on the numbers:** stations 9,507, sections 13,560, route km 70,304.6 (+1.2%), components 8, cycles
498 (places). All gates still pass; 2024 route median error 0.38%, 99.2% within 5%.

**Reversible:** yes. `BUILD_TIMETABLES` in `run_c2.py`.

## D-069 — v2.0-open locked as the final dataset

**Evidence:** E-716 P3-P4, F-050. **Adopted:** 2026-10-21 by the executor. The owner defers publication and the DOI; the lock is for the pitch and later use.

`rail-intel-v2.0-open.zip` (sha256 `b1e3908167abb2aa91238046e9b25ac50a88ba3645077cb028b45331c449eeda`) is the
publishable dataset. Its data files equal release candidate rc1; the changes since rc1 are the final version
string, a `CITATION.cff` inside the package, and the deposit metadata beside it.

- Licence: ODbL 1.0 for the database (OpenStreetMap is share-alike), DbCL for the contents; attribution file lists
  OpenStreetMap, Wikidata (CC0), datameet (CC BY 4.0), data.gov.in (GODL-India).
- Built from open inputs only (D-068); the 2024 layer stays a local build (D-067).
- A change to a data file after this point is a new version. The DOI is added to the documents afterwards
  without rebuilding the package, so the hash stays.
- Reproduced byte for byte on two machines. 52 tests pass on the laptop.

**Reversible:** until the DOI is minted, yes. After, only by a new version.

---

## D-070 — Repository restructured; prior versions archived, not deleted; one timeline document

**Status:** accepted. **Adopted:** 2026-10-21 by the executor, on the owner's instruction to
clean up the repository now that v2.0-open is locked (D-069). **Binding:** yes.

**Decision.** The repository is reorganised around the locked dataset and the product that
follows it, and the per-version documentation is consolidated into one history.

1. **Superseded dataset versions are archived, not deleted.** `graph_v1`, `graph_v1_1`,
   `graph_v1_2`, `graph_v1_3` and the superseded service layers (`service_layer`,
   `service_layer_v1_3`) move to `_archive/`. `_archive/` stays on disk and is excluded from
   git. The owner chose archiving over deletion explicitly; nothing of substance is lost.
   `graph_v1_4` (frozen, D-055), `graph_v1_4_1` (the comparison baseline) and
   `graph_v2_0_open` stay in place.
2. **Only rebuildable intermediates are deleted:** `graph_v1_3/_stages/` (19 stage parquets
   plus the stage log and the `_to_delete` leftover), `experiments/cache/`, and `__pycache__`.
   Nothing in `graph_v2_0_open/work/` is removed — the test suite reads `c1_report.json`,
   `c2_report.json`, `c2_joins.csv`, `c2_throat_links.csv`, `c3_report.json`,
   `c3_cut_point_differences.csv`, `station_snaps.csv`, `calib_track_spacing.csv` and
   `unsnapped_stations.csv`, and `p2_v201_classified.csv` carries human adjudication that no
   rebuild reproduces.
3. **New empty folders for the product:** `05_product/api/` and `05_product/web/`, per the
   locked scope (D-058). Placeholders `04_analysis_modules/E-718_criticality_v2`,
   `E-719_degree_distribution_v2` and `E-720_conclusion_robustness_v2` mark the analyses that
   must be re-run on v2.0-open before any v2.0 criticality claim is made.
4. **One history document: `docs/TIMELINE.md`.** It supersedes `CHANGELOG.md`,
   `docs/PROGRESS.md`, `docs/LIMITATIONS.md`, `docs/VALIDATION_REPORT.md`,
   `docs/GRAPH_HANDOFF.md` and `docs/GRAPH_V2_ROADMAP.md`, all of which move to
   `_archive/docs_superseded/`. It carries the version ladder, the decisions and design
   changes that produced each version, the validation history, the limitations of v2.0-open,
   and an explicit "bad side" section. The live registers — `DECISIONS.md`, `FINDINGS.md`,
   `EXPERIMENTS.md`, `V2_ISSUES.md` — are unchanged and hold the detail it summarises.
5. **`README.md` is rewritten** as an accurate entry point; the Phase-2-era version is kept at
   `_archive/docs_superseded/README_pre_cleanup.md`.

**Why.** `docs/LIMITATIONS.md` was last updated 2026-10-03 and still quoted v1.0-era figures;
`README.md` described `03_graph_construction` as empty; the history was spread across a
changelog, a work log, five roadmaps and seven per-version validation files. A reader could not
establish what the current dataset is or what is wrong with it without reading all of them.

**Consequence.** `make v13` and `railgraph.config.RELEASE` still name `graph_v1_3` and
`graph_v1` as output paths; running those targets recreates the folders rather than finding
them. No test depends on an archived path: the suite's one textual reference to
`graph_v1_3/open` is a column value, not a file. **82 tests pass before and after.**

**Risk.** Git is not usable in the working copy (git-lfs missing) and the last commit predates
the v1.3 → v2.0 work, so these moves and deletions are not recoverable from git. This is why
deletion was limited to rebuildable intermediates.

**Reversible:** archiving, yes — move the folders back. The deleted intermediates, only by
re-running `make v13`.
