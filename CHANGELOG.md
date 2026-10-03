# Changelog

Dated entries for anything that changes what a teammate should do. Newest first.

---

## 2026-09-30 — Graph approach finalised, dataset shipped

**For Sreehitha:** the data half is done. Build from
`02_graph_inputs/graph_dataset/`, not from `graph_inputs/`.

### What is new

`02_graph_inputs/graph_dataset/` — the cleaned, normalised, node- and
edge-resolved dataset. Node identity is resolved, vocabularies are unified, the
service layer is derived, and `nodes.csv` + `edges.csv` load straight into
NetworkX with no joining, matching or ordering left to do.

```
nodes.csv              9,095   8,621 stations + 474 operational junctions
edges.csv              9,689   geodesic-weighted, attributed, service-loaded
service_edges.csv     10,193   frequency + observed run-time per station pair
stations.csv           8,990   cleaned station master
corridors.csv          2,279   cleaned corridor attributes
station_sequences.csv 12,305   ordered placements the edges were built from
README.md                      the data dictionary — read this first
QA_REPORT.txt                  regenerated every run
VERIFICATION.txt               27 integrity checks, re-derived every run
```

The graph: **9,095 nodes, 9,689 edges, 99.6% in one connected component,
72,201 route km.**

Two new pipeline stages build and check it — `s09_graph_dataset.py` and
`s10_verify_dataset.py` — both wired into `run_all.py`. The full pipeline is
now ten stages and takes about 50 seconds, byte-identical across clean runs.

### What changed in the approach

All of it is recorded in `docs/GRAPH_HANDOFF_V2.md` §4.8 as a decision
register, and §4.9 maps each decision to what the four analysis modules need.
The three that change how the graph is built:

1. **Corridor chains are stitched at their shared junctions.** Building chains
   alone yields a graph that is only 59.4% connected — corridors meet at
   junctions, not at stations, so where a junction carries no station the two
   chains never touch. Stitching takes the giant component to 99.6% and, as a
   side effect, makes the graph insensitive to the placement threshold.
2. **Node model is hybrid and typed.** A node is a station where a confident
   station match exists, and a typed `operational_junction` where it does not.
   Dropping the unmatched junctions loses 46 that are structurally load-bearing.
3. **Two views on one graph, not a smaller graph.** `core_v2` / `core_v4` flags
   mark the attribute-complete subset. Do not build a filtered graph and run
   resilience on it — filtering removes real alternative routes and pushes the
   bridge share from 14.6% past 30%, overstating fragility by roughly 2.5×.

### Data inconsistencies fixed

A full scan of every data file across nine dimensions found the following, all
now fixed in the pipeline rather than by hand:

| Problem | Fix |
|---|---|
| Node and edge zone used **different vocabularies** — corridors spelled zones in full, stations used abbreviations, so the two could never be joined | One canonical `(zone_code, zone_name)` pair everywhere, 17 zones |
| Four zone typos, incl. `North Frontier Railway` for the real Northeast Frontier Railway (121 corridors under the wrong name) | Corrected in `s02`, before corridor aggregation |
| `?` used as a zone value on 106 stations and 275 trains | Mapped to null |
| `Orissa` and `Odisha` both present | Canonicalised to `Odisha` |
| 2 Bangladesh stations inside national totals | `in_scope = False` |
| 11 stations sharing 4 coordinates | `coordinate_shared = True` |
| Station zone missing on ~52% of rows | Inferred from corridor where possible, marked `corridor_inferred`; coverage 45% → 98.9% |
| **`day` column in schedules reaching 12** on trains that finish within a day — would have corrupted every travel-time calculation | Not used at all; run-times derived by 24-hour wrap |
| Service counts under-crediting every edge beside an express-skipped station | `service_load` computed by path projection; edge coverage 80.0% → 89.9% |

Verified clean and needing no fix: no duplicate keys in any file, full
referential integrity across all seven cross-file relationships, no
out-of-India or zero coordinates, no whitespace or case inconsistency in any
key field, no cross-file disagreement on station names or coordinates.

### Correction to an earlier figure

An earlier handoff draft said 428 junction nodes were degree-≤2 and
dissolvable. Measured against the real edge list that is wrong: **115** are
degree 2 and dissolvable, **313** are degree 1 (line ends — prunable, not
dissolvable), **46** are degree ≥3 and load-bearing. `nodes.is_dissolvable`
marks exactly the 115.

### What is still open

Nothing blocking. Four choices remain, all recorded in
`docs/GRAPH_HANDOFF_V2.md` §6: graph storage format, whether to dissolve the
115, `core_v2` vs `core_v4` as the default attributed view, and whether to
recompute the edge lengths affected by spine shortcutting (17.1% of
consecutive pairs, median 5% shortfall) or accept and document the bias.

---

## 2026-09-29 — Repository reorganised into phases

Files moved into `01_data_engineering/`, `02_graph_inputs/`,
`03_graph_construction/`, `04_analysis_modules/`, `docs/` and
`reference_data/`. Pipeline paths, notebook working directories and all
documentation cross-references were updated with the move; the pipeline
rebuilds byte-identically from the new locations.

---

## 2026-09-28 — Graph-input pipeline replaces the notebook workflow

The eight-stage pipeline under `02_graph_inputs/pipeline/` replaced
notebook-cell-output intermediates. It closed the seven gaps raised in
`docs/VALIDATION_REPORT.md`: corridor count unified to 2,279, junction names
canonicalised, coordinates derived from corridor geometry for 2,028 of 2,029
junctions, station matching made tiered and spatially constrained, and 12,305
stations ordered along their corridors with true geodesic distance.

---

## 2026-10-03 — Phase 3 opened: roadmap, documentation apparatus, graph builder

**For Sreehitha:** there is now a working, invariant-checked builder in
`03_graph_construction/railgraph/`, and three measured findings that change what
graph v1 should be. Read `docs/PHASE3_GRAPH_ROADMAP.md`, then `docs/FINDINGS.md`
F-007, F-009 and F-010.

Phase 3 remains yours. What is here is a reference implementation plus a
validation harness you can run against your own build — `railgraph.load_graph()`
raises `InvariantError` if a build does not reproduce the shipped
9,095 / 9,689 / 99.6% / 72,201 km.

### New

- `docs/PHASE3_GRAPH_ROADMAP.md` — research-backed `g00`–`g07` plan, ~4–6 weeks.
- `docs/LITERATURE.md` — 9 sources annotated, gap analysis, three paper claims.
  The decisive point: **every published graph of the Indian railway network is
  timetable-derived** (Sen et al. 2003: 587 stations; Bhatia et al. 2015: 809).
  Ours is 9,095, physical, and cross-validatable because the timetable was never
  used to build it.
- `docs/DECISIONS.md` — 23 ADRs. 15 migrated from `GRAPH_HANDOFF_V2.md` §4.8,
  6 open, 2 new accepted. No decision is accepted without an experiment ID.
- `docs/FINDINGS.md`, `docs/EXPERIMENTS.md`, `docs/PAPER_OUTLINE.md`,
  `docs/LIMITATIONS.md`, `docs/PROGRESS.md`.
- `03_graph_construction/railgraph/` — `BuildSpec` (12 parameters), strict
  loader, 4 representation transforms, named weight registry.
- `requirements.txt` — pinned.

### Findings that change graph v1

| | Finding | Consequence |
|---|---|---|
| **F-007** | Junction stitching damps placement-tolerance sensitivity by **322×** (0.23 pp vs 74.61 pp) | The headline result for the paper's method claim |
| **F-009** | Dissolving the 115 degree-2 junctions **destroys 22 independent cycles** and is order-dependent | **`D-017`: do not dissolve.** It is not the free operation street-network practice assumes |
| **F-010** | `match_conf='high'` only gives **more** nodes (9,438 vs 9,095) — rejecting a match splits a node, it does not delete one | Stricter matching is not safer; it manufactures 349 topology points |
| **F-008** | `offset_km` maxes at 1.9989 — `s07` already caps at 2 km | Tolerance has 3 distinct levels, not 5 |

### Corrected

- `docs/GRAPH_HANDOFF_V2.md` §4.3, §4.4, §4.7, §8 carried pre-`s09` figures
  contradicting `QA_REPORT.txt` (`F-003`). Six regions fixed — 397→581 and 98→124
  parallel pairs, 183→249 co-located, 1,341→1,338 articulation points,
  1,432→1,412 bridges, degree mean 2.05→2.13, 98.0%→97.4% three-hop, 8→10
  stages. A provenance banner now states that the QA report wins any future
  disagreement.
- `F-002` / `D-021`: `is_colocated` records that an edge's length *was floored*,
  not that the stations are close. Edge `E000454` (AMPR–PGK) is 50 m and
  unflagged. `railgraph` adds unambiguous `length_below_floor` and
  `is_short_edge` alongside it.

### Unchanged

Nothing in `01_data_engineering/`, `02_graph_inputs/pipeline/` or
`02_graph_inputs/graph_dataset/` was modified. Phase 3 reimplements `s09`'s
construction under `D-023` rather than refactoring it, and asserts equivalence
on every run.
