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
| E-000 | Phase 2 pipeline measurement set (inherited) | s01–s10 | D-001…D-015, F-001, F-004, F-005 | **complete** |
| E-001 | Independent recomputation of the contested structural figures | g00 | D-002, D-006, D-007, F-002, F-003 | **complete** |
| E-002 | g01 acceptance + construction-sensitivity preview | g01 | D-017, D-023, F-007…F-010 | **complete** |
| E-007 | Storage-format round-trip fidelity and load time | g02 | D-016, F-025 | **complete** |
| E-100 | Metric baselines, criticality, resilience, communities, null models | g03 | all downstream, D-017, F-011, F-020 | **complete** |
| E-101 | Validation battery — invariants, cross-source, audit frame | g04 | C1, C2, C3, F-018 | **complete** |
| E-102 | Per-zone route km against an independent official total | g04 | C3, F-041; resolves F-019 | **complete** |
| E-200 | Construction + representation sensitivity sweep (20 cells, tiered) | g05 | C3, D-018, F-022, F-024 | **complete** |
| E-300 | Attribute provenance and enrichment audit | g02 | C2, D-020, D-025…D-032, F-026…F-035 | **complete** |
| E-301 | Service-layer and enrichment-capacity audit | g02 | W2, D-029, F-036…F-040 | **complete** |
| E-400 | Build, validate and export graph v1.1 (provenance layer, true geometry) | g02/g05 | D-025…D-030, D-039, D-040, F-042, F-043, F-046 | **complete** |
| E-401 | Length **derivation** as a sensitivity factor | g05 | C3, closes W7 and D-026's g05 consequence | **complete** |
| E-402 | Independent audit of the released edge geometry (W1) | g02 | D-040, F-047 | **complete** |
| E-403 | Topology case inspection: components, high-degree, dissolvable | g02 | D-041, F-048, F-049 | **complete** |
| E-500 | Graph v1.2: the five known weaknesses fixed where provable (12 gates) | g02 | D-042…D-046, F-051…F-055 | **complete** |
| E-501 | v1.2 audit: removal robustness, timetable proof, conclusions | g05 | D-043, F-052 | **complete** |
| E-502 | Service layer: directed, timed, mapped to track | g02 | D-047, F-056 | **complete** |
| E-600 | Graph v1.3: external evidence, open + full variants, 7 gates, hold-out validation | g02 | D-048…D-054, F-057…F-063 | **complete** (rev 2) |
| E-601 | Conclusions on v1.3, same battery and bands as E-501 B | g05 | F-064 | **complete** |
| E-700 | Tier A proof of concept on one region (Delhi–Agra–Kanpur–Lucknow): routing, load, criticality, accessibility, circuity, observed running times | g03 | Phase 4 scope; `04_analysis_modules/E-700_tierA_poc/` | **complete** |
| E-701 | Downstream feasibility: what each external dataset adds to v1.3; 2024 routes as independent validation; infrastructure vs delay pilot | g03/g04 | Phase 4 scope; `04_analysis_modules/E-701_downstream_feasibility/` | **complete** |
| E-702 | Gap G1: station-code crosswalk — 335 unmatched 2024 codes resolved by name, position, route context and code retirement | g02 | G1 closed; `04_analysis_modules/E-702_station_code_crosswalk/` | **complete** |
| E-703 | Gap G5: trunk wiring — phantom shortcut removal and missing trunk links from official adjacency | g02 | G5 closed; `04_analysis_modules/E-703_trunk_wiring/` | **complete** |
| E-704 | Gap G6: missing links — alignment test separates absent track from chains the graph already has | g02 | G6 closed; `04_analysis_modules/E-704_missing_links/` | **complete** |
| E-705 | Gap G15: 2024 service layer, directed and timed, on the repaired graph; audit pruning 42 redundant added edges | g02 | G15 closed; `04_analysis_modules/E-705_service_layer_2024/` | **complete** |
| E-706 | Gap G16: trains per day, measured from 30 days of Sept 2024 observations and validated against the weekly running-days list | g02 | G16 closed; `04_analysis_modules/E-706_trains_per_day/` | **complete** |
| E-707 | Full graph audit: structure, attributes, validation on three references, conclusion stability, residual defects | g03/g04 | `04_analysis_modules/E-707_graph_audit/` | **complete** |
| E-708 | Build, gate and freeze graph v1.4: applies the E-702..E-706 decisions to v1.3, deterministic, 9 gates | g02/g07 | v1.4 release; `experiments/E-708_v1_4_build/` | **complete** |

### Declared IDs that were absorbed, superseded or remain open

`E-003`–`E-006` and `E-103`–`E-106`, `E-201` were declared in this registry
before the work was done and were then answered — or deliberately not answered
— under other IDs. Left unreconciled they send a reader, or the team in month
seven, looking for experiments that will never exist. Reconciled here rather
than quietly deleted, because the planning record is itself evidence
(`D-035`).

| Declared | What became of it |
|---|---|
| `E-003` degree-2 dissolution effect | **absorbed** into `E-002` (`F-009`), confirmed by `E-100`, and carried as the `dissolve_degree2` cell in `E-200`. Closed `D-017` |
| `E-004` core_v2 vs core_v4 | **absorbed** into `E-200` as the `view=core_v2` / `view=core_v4` cells (Tier B). Closed `D-018` |
| `E-005` spine-shortcut bias | **absorbed** into `E-300` part 2, then answered properly by `E-400` + `E-401`. Its ADR `D-019` is superseded by `D-026` |
| `E-006` the 18 residual components | **absorbed** into `E-300`'s inputs survey. Closed `D-020` (retain all 18) |
| `E-103` V3 cross-source, stratified | **absorbed** into `E-101` (0 cross-component contradictions; `F-018` stratifies the stitching deficit) |
| `E-104` Sen / Bhatia reproduction | **superseded** by the v2 multi-layer plan (`W4`): both become layers of our own object, reproduced natively rather than rebuilt separately |
| `E-105` V5 two-rater ground-truth audit | **genuinely open.** The 202-edge stratified frame exists (`E-101`); rating it needs two people and cannot be done in software |
| `E-106` V6 null models | **absorbed** into `E-100` (degree-preserving rewiring, Barabási–Albert control; `F-020`, `F-024`) |
| `E-201` tolerance × stitching interaction | **absorbed** into `E-200`, which runs that grid as its `interaction_cells()` (6 cells). The `damping.csv` output is its result |

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

---

## E-300 — attribute provenance and enrichment audit

**Question.** What do the edge and node attributes actually measure, and what is
recoverably missing?

**Script.** `publication/evidence/E-300_attribute_audit/run.py` (~40 s)
**Inputs.** `01_data_engineering/Railway_Network_.csv` (119,446 GIS segments),
`02_graph_inputs/graph_dataset/{station_sequences,corridors}.csv`,
`03_graph_construction/graph_v1/{nodes,edges}.parquet`,
`reference_data/RS_Session_267_AS_371_A_i.csv`,
`01_data_engineering/processed_data/cleaned_stations.csv`
**Outputs.** `report.json`, `granularity.csv`, `length_pairs.csv`,
`length_offset_bands.csv`, `corridor_sinuosity.csv`, `bridge_validation.csv`

**Five parts.** (1) granularity — does each GIS attribute vary within a corridor;
(2) length — chord vs the recoverable along-track distance, and
the regime where the along-track measure itself fails; (3) sinuosity — ranking
corridors and checking the ranking against external ground truth; (4) bridges —
whether the segment-level bridge flag is a usable inventory, validated against the
official count; (5) coverage — attribute nullity and conflict rates.

**Headline result (`F-026`).** The GIS declares **21,560** corridor–station
placements; the pipeline matched **12,305** — a **42.9% shortfall**. Where a
station is not placed, `s09` emits one long edge instead of two short ones:
**766 edges (7.9%) carry 24.5% of all route km** with ≥3 stations missed and
length >10 km, and 40.9% of those have `service_load = 0`.

**Second result (`F-029`).** Ranking 871 corridors by along-track/chord ratio
places **all four of India's recognised mountain railways in the top 6** —
Matheran (1), Darjeeling (2), Kalka–Shimla (3), Nilgiri (6) — with no terrain,
elevation or heritage input anywhere in the pipeline. The strongest external
validation the project has.

**Negative result (`F-030`).** The GIS bridge inventory captures only **31.6%** of
the official per-zone count, with capture ranging 0.006 (NFR) to 0.638 (WR).
Validation *demoted* the attribute rather than confirming it.

**Other findings generated.** `F-027` (119,446 segments carry 2,305 distinct
corridor-level values), `F-028` (chord understates by 2.88% aggregate but >5% on
17.7% of pairs, while the spine measure is impossible on 12.9%), `F-031` (36% of
travel times use an invented 50 km/h), `F-032` (200 conflicted corridors never
flagged on edges), `F-033` (`state` not recoverable in-repo), `F-034` (two service
columns of different epistemic status), `F-035` (124 genuinely different parallel
routes discarded).

**Supports.** `D-025` through `D-033` (all accepted); supersedes the scope of
`D-024`; weakens `F-019` and requires `F-015` to be re-read.

---

## E-301 — service-layer and enrichment-capacity audit

**Question.** What could the graph carry that it does not, using only data already
in the repository?

**Script.** `publication/evidence/E-301_service_layer_audit/run.py` (~60 s)
**Inputs.** `02_graph_inputs/graph_dataset/service_edges.csv`, graph v1 exports,
`01_data_engineering/processed_data/{cleaned_trains,cleaned_schedules}.csv`
(5,208 trains; 416,970 schedule rows), `02_graph_inputs/pipeline/cache/corridor_spines.parquet`
**Outputs.** `report.json`, `edge_runtime_join.csv`

**Headline result (`F-036`).** Observed run-times cover **6,479 of 9,689 edges
(66.9%)** — better coverage than the declared `speed_kmph` (64.4%) they would
replace. Implied speed median **53.5 km/h** against a declared median of
**110.0 km/h**: ratio **0.513**. Every travel-time result produced so far
understates journey time by roughly 2×. And the 50 km/h fallback used where no
declared speed exists is *closer to reality* than the declared value — the
invented constant outperforms the real attribute.

**Other findings.** `F-037` (p90 > 2× p10 on 28.8% of edges — a congestion signal
with no counterpart in the graph), `F-038` (88.5% of trains declare a return
working, 99.2% resolvable → a directed layer is buildable in-repo, revisiting
`D-033`), `F-039` (dwell time derivable on 75.0% of station nodes; 723 originating
stations; operational role entirely absent today), `F-040` (2,278 corridor spine
LineStrings, mean 336 coordinates → true per-edge alignment recoverable, replacing
the schematic chord GeoJSON).

**Consequence.** Defines the v2 workstreams in `docs/GRAPH_V2_ROADMAP.md`. W2
(observed service weights) is the critical path: largest correctness gain, fully
supported in-repo, and both the multi-layer work and Module 2 depend on it.

---

## E-007 — export format round-trip

**Question.** Does every export format reload to the same graph, and is any loss
accounted for rather than silent?

**Script.** `railgraph.io.verify_roundtrip()`, run from `g02`
**Output.** `03_graph_construction/experiments/E-007/roundtrip.json`

| format | nodes | edges | length sum Δ | size | load |
|---|---|---|---|---|---|
| GraphML | exact | exact | 0.0 | 7.51 MB | 0.83 s |
| parquet | exact | exact | 0.0 | **0.81 MB** | **0.02 s** |
| GeoJSON | −1 | −1 | — | 7.95 MB | — |

*Revision-1 results (counts and one length sum only). Superseded by export revision 2 — see `D-039` / `F-046`; current sizes 11.9 MB GraphML, 0.88 MB parquet, 11.7 MB GeoJSON.*

**Result.** parquet is 9× smaller and **42× faster** than GraphML, which decides
`D-016`: parquet is the working format, GraphML the citable primary. The GeoJSON
loss is exactly one node and its one incident edge, and the test asserts the loss
*equals the expected loss* rather than tolerating any loss.

**Finding generated (`F-021`).** Chasing that single missing feature found a real
defect: `JN::Khandala` has no coordinate, so its one stitched edge's length is an
undefined haversine that `clip(lower=0.05)` turned into `0.05 km` flagged
`is_colocated`. `VERIFICATION.txt`'s "no null edge lengths" check passes because
an undefined quantity was made non-null. Found by exporting to a format that
refuses to invent a coordinate — round-tripping through a stricter format is a
validation technique in its own right.

**Supports.** `D-016` (accepted), `F-021`, `F-025`.

---

## E-100 — metric baselines, criticality, resilience, communities

**Question.** What are the structural baselines the four Phase 4 modules check
their own work against?

**Script.** `03_graph_construction/experiments/E-100/run.py` (~8 min; exact
betweenness cached at 363 s)
**Outputs.** `report.json`, `bridge_severance.csv`, `percolation_curves.csv`,
`communities_{louvain,infomap}.csv`, `bc_convergence.csv`

Four parts: structural baselines against `QA_REPORT.txt`; bridge severance named
with service impact; percolation under four attack strategies with null-model
controls; community detection by two methodologically different algorithms scored
against railway-zone labels.

**Headline result (`F-011`).** The attack ordering is **inverted** relative to the
textbook scale-free expectation: random failure damages this network more than
betweenness-targeted attack. Control runs with the same code on a
Barabási–Albert graph reproduce the expected ordering, so the result is a
property of the network, not of the implementation. High-betweenness nodes lie
contiguously along trunk routes rather than acting as separable hubs.

**Other findings.** `F-012` (the physical network collapses at 5% removal while a
service representation implies 95%), `F-015` (stitched edges under-represented
among top severing bridges), `F-016` (the Siliguri Corridor surfaces as the
network's single worst chokepoint, unprompted — Barsoi Jn–Makuria strands 459
nodes and 136 trains), `F-017` (top-50 betweenness nodes are only 11 distinct
places; 60% are degree-2 pass-throughs, which is why corridor-level criticality is
the honest measure), `F-020` (fragility is largely a degree-sequence property).

**Supports.** `F-011`, `F-012`, `F-015`, `F-016`, `F-017`, `F-020`; baseline for
`E-200`.

---

## E-101 — validation battery

**Question.** Does the graph agree with sources that were not used to build it?

**Script.** `03_graph_construction/experiments/E-101/run.py`
**Outputs.** `report.json`, `v3_strata.csv`, `v5_audit_frame.csv`

Layers V1 (invariants), V2 (degree distribution, route km), V3 (cross-source
contradiction), V5 (stratified manual-audit frame), V6 (null models).

**Results.** Zero cross-source contradictions on adjacency (`F-018`); the degree
tail is exponential as `[KUR06]` predicts for a physical rail network; route km
+3.98% against the Year Book, which `F-019` reconciles to −0.06% by excluding
zero-station corridors **without establishing the mechanism**. A 202-edge
stratified frame was generated for manual TP/FP/FN rating; **it has not yet been
rated by two people**, so V5 is the one validation layer still open.

**Supports.** `F-018`, `F-019`, `F-020`.

---

## E-200 — construction-choice sensitivity study

**Question.** Which downstream conclusions survive the choices made while building
the graph, and which are artifacts of them?

**Script.** `03_graph_construction/experiments/E-200/run.py` (~25 min, 20 cells)
**Outputs.** `cells.csv`, `verdicts.csv`, `verdicts_tier{A,B,C}.csv`,
`damping.csv`, `attack_ordering.csv`, `rankings.json`

One-at-a-time around the shipped default across 14 factors, plus a tolerance ×
stitching interaction grid. A full factorial over nine factors is ~17,000 cells
and infeasible.

**Headline result (`F-022`).** A single verdict over all cells is uninformative —
everything looks like an artifact, which only restates that `D-001` and `D-005`
matter. Tiered instead: against the **nine genuinely open choices (Tier A), six of
eight headline conclusions are robust, two conditional, and none is an artifact**.
Adding the attributed-core views (Tier B) turns four into artifacts, which is the
evidence for `D-018`.

**Other findings.** `F-023` (stitching's damping is measure-specific — 322× for
connectivity, 1.3× for cycle structure, so the claim must be made per measure),
`F-024` (the inverted attack ordering holds in 19 of 20 cells).

**Known limitation.** The sweep varied construction and representation
*parameters*; it never varied how length or travel time were **derived**, so it
could not have detected `F-026` or `F-028`. `length_source` joins the factor list
in v1.1.

**Supports.** `D-018` (accepted), `F-022`, `F-023`, `F-024`, `F-025`.

---

## E-102 — per-zone route km against an independent official total

**Question.** Is the national route-km agreement (`F-019`) evidence of
correctness, or two errors cancelling?

**Script.** `publication/evidence/E-102_zone_route_km/run.py` (~5 s)
**Reference.** `reference_data/zone_electrification_2021.csv` — per-zone
broad-gauge route km, 2021. (Note: `Table-19.2-Zone-wise.csv`, previously cited
as the source for this check, contains passenger and freight figures, **not**
route km.)
**Outputs.** `zone_route_km.csv`, `report.json`

**Headline result (`F-041`).** Seventeen comparisons instead of one. Deviations
scatter across 34 percentage points and change sign — **−15.2% (Central) to
+19.1% (Western)**, median +7.7%, sd 9.1 pp. The national figure is zone errors
of opposite sign partially cancelling, so `F-019`'s −0.06% reconciliation is
**not evidence of correctness** and must not be cited as validation. Per-zone
totals nonetheless correlate strongly with the reference (Pearson 0.977), so the
zone-level structure is right even where the level is not.

**Unpredicted second result.** Excluding the `F-026` suspect edges makes agreement
**much worse** — national −19.85%, median absolute zone deviation 8.6% → 18.5%.
The suspect edges therefore **carry real route kilometres**: the defect is
*topological, not metric*. Track exists and its length is about right; it is
modelled as one long edge instead of several through stations never placed. So
`suspect_long_edge` is a path-analysis caveat, **not** a length filter — excluding
those edges from a distance aggregate introduces a 20% error to avoid a bias that
is not there.

**Supports.** `F-041`; resolves `F-019`; refines the usage guidance for `D-025`.

## E-400 — Build, validate and export graph v1.1 (the provenance layer)

**Date:** 2026-10-03 · **Script:** `03_graph_construction/experiments/E-400_v1_1_build/run.py`
**Implements:** `D-025`, `D-026`, `D-027`, `D-029`, `D-030`
**Outputs:** `03_graph_construction/graph_v1_1/` — `rail_graph_v1_1.graphml`,
`edges.parquet` (52 columns), `edges.csv`, `nodes.parquet`, `nodes.geojson`,
`edges.geojson`, `graph_v1_1.manifest.json`, `length_source_breakdown.csv`,
`E-400_report.json`

**Question.** Can every value in the edge table be made to declare how it was
obtained, without changing the topology or adding a data source?

**Method.** A new module `railgraph/provenance.py` derives the v1.1 columns from
the frozen Phase 2 dataset. Its parameters live in a separate `ProvenanceSpec`
rather than in `BuildSpec`, so v1.0's `spec_hash` `f9adf8ca9042` survives
unchanged and the layer is verifiably additive.

**Result — the layer.**

| | |
|---|---|
| route km | 72,201.1 → **72,421.0** (+219.9, **+0.30%**) |
| edges changed | 1,286 of 9,689 |
| `length_source` | spine 5,591 · stitch_as_built 2,252 · chord_fallback_collapse 1,123 · chord_fallback_offset 679 · floored 44 · undefined 0 |
| `sinuosity` defined | 5,591 edges, median 1.0145 |
| `suspect_long_edge` | **764 edges, 17,670 km = 24.4% of route km** |
| `speed_is_fallback` | 3,451 edges = **35.6%** |
| `any_attribute_conflict` | 1,183 edges (from the 200 conflicted corridors) |

The defect flag independently reproduces `E-300`'s 766 edges / 24.5% at
764 / 24.4%, and `speed_is_fallback` reproduces `D-029`'s 35.62% exactly. Both
were derived by a different route here, so the agreement is a check, not a
restatement.

**Result — topology is untouched** (v1.1 is additive): node count, edge count,
the edge set itself, component count, 1,412 bridges and 1,338 articulation
points all identical to v1.0.

**`D-026` validation gates.**

| gate | result |
|---|---|
| (a) no spine-sourced edge shorter than its own chord | **pass** — 0 violations |
| (b) corridor sinuosity still ranks all four mountain railways in the top 1% | **pass** — ranks **1, 4, 5, 6 of 859** (Matheran–Neral 3.530, Kalka–Shimla 1.812, Darjeeling–NJP 1.744, Mettupalayam–Udagamandalam 1.358) |
| (c) per-zone route km re-reconciled | reported, not thresholded (`F-041`): national +5.83% → +6.16%, zone median +7.69% → +7.96%, range [−15.2, +19.1] → [−14.8, +19.5], r 0.9772 → 0.9778 |

Gate (b) is the one that matters: it is computed from the **shipped `sinuosity`
column**, not from `E-300`'s separate derivation, so the attribute passes the
external check on its own. The first version of this gate matched endpoint names
exactly, found only 2 of 4, and **passed vacuously on the two it could not
locate** — corrected to fail on a missing subject, which is how it caught its own
bug.

**Format round-trip.** `length_source`, `suspect_long_edge`, `speed_is_fallback`
and `station_match_deficit` verified present and correct in GraphML (764 suspect,
3,451 fallback) and GeoJSON; `attribute_granularity` carried once at graph level
rather than on 9,689 edges. Route km agrees to 5 decimal places across parquet
and GraphML. GeoJSON retained the expected −1 feature (`JN::Khandala`, no
coordinate). *Superseded 2026-10-04 (`D-039`): GeoJSON now keeps that feature with
`geometry: null`, and the round trip compares every attribute (`F-046`).*

**Findings.** `F-042` (the v1.0 length was already the spine — `E-300`
mislabelled its baseline), `F-043` (`D-026` is silent on stitch edges; applying
the rule there anyway moved 4.9× more length than the specified case).

*Addendum, 2026-10-04.* `E-400` now also writes the true-alignment geometry
(`D-040`) and runs three further gates: **d** attribute-exact round trip in
GraphML, parquet and GeoJSON, **e** every Phase 2 CSV column and value carried,
**f** every edge has geometry or a stated reason. All pass; `E-402` audits the
geometry independently.

## E-401 — Length derivation as a sensitivity factor (closes `W7`)

**Date:** 2026-10-04 · **Script:** `03_graph_construction/experiments/E-401_derivation_sweep/run.py`
**Closes:** `W7`, and `D-026`'s stated `g05` consequence
**Outputs:** `cells_derivation.csv`, `cells_union.csv`, `verdicts_derivation.csv`,
`verdicts_union.csv`, `verdicts_tierA_plus_derivation.csv`,
`verdicts_tierA_with_derivation.csv`, `verdict_change.csv`, `rankings.json`,
`report.json`

**Question.** `E-200` returned "Tier A: 0 artifacts" over construction and
representation parameters, and said itself that it never varied **how length was
derived** — so it could not have detected `G-01` or `G-02`. v1.1 (`E-400`) made
length derivation a switchable parameter. Does the verdict survive it?

**Method.** 10 new cells, merged with `E-200`'s existing 20 rather than
recomputing them (the prior cells are unchanged; recomputing would burn 30
minutes to reproduce identical numbers):

| cells | what varies |
|---|---|
| `length=asis` | control — reproduces the v1.0 length exactly |
| `length=hybrid`, `length=spine`, `length=chord` | the derivation rule |
| `length=hybrid_offset0.10`, `_offset1.50` | the hybrid's own offset gate |
| `tol{1.0,2.0}_length{asis,hybrid}` | tolerance × length_source, the interaction `D-026` requires |

The cell's own tolerance governs spine eligibility (`pair_measures(offset_max_km=…)`),
so a tolerance=1.0 cell is not scored against the shipped 1.5 km build's spine
set — which is what makes the interaction meaningful rather than decorative.

**Control validates the harness.** `length=asis` reproduces `E-200`'s default
cell exactly: 72,201 km, mean path 1275.5, circuity 1.2506, corridor overlap
1.00. The provenance layer at `asis` is a verified no-op.

**Headline result (`F-045`). Tier A + derivation: 0 artifacts, 0 verdicts
changed.** Six robust, two conditional — identical to `E-200`'s Tier A. Route km
spans 71,445 (`chord`) to 73,193 (`spine`), a 2.4% band. Two conclusions
(`mean_path`, `circuity_median`) now have their worst cell at a derivation cell,
making derivation a peer of the construction choices for distance-weighted
measures without changing any verdict.

**Second result (`F-044`).** Reconstructing the tiers to run this exposed that
`E-200`'s `verdicts_tierA.csv` — the file the paper's `C3` claim cites — was
produced by no script in the repository. `TIER_A`/`TIER_B_ADDS`/`TIER_C_ADDS`
and `verdicts_for_tier()` now live in `sensitivity.py`, and this experiment
**asserts on every run** that they reproduce the published Tier A exactly (8/8
verdicts, 8/8 deviations to 1e-9). The assertion is the fix; the code alone
would only have moved the problem.

**Resumable by design.** Each cell costs ~100 s and completed cells are appended,
so an interrupted run continues instead of restarting. Added after a 20-minute
background run was lost to a shell exit — a 10-cell sweep that cannot be resumed
is a 10-cell sweep that gets run once and trusted.

**Still open.** `time_source` is not yet a factor — `W2` has to land first — and
`F-036`'s 2× declared-vs-observed gap makes it the factor most likely to produce
the project's first genuine Tier A artifact.


## E-402 — Independent audit of the released edge geometry (`W1`)

**Date:** 2026-10-04 · **Script:** `03_graph_construction/experiments/E-402_alignment_audit/run.py`
· **Output:** `graph_v1_1/E-402_report.json` · **Run:** `make geometry`

**Question.** Does the true-alignment geometry shipped in v1.1 sit where the track
is? Reads only the released files and the Phase 2 spines — it does **not** import
the slicer, so a slicer bug cannot also be in its own check.

**Method.** Ten checks, each of which can fail: no feature missing; null geometry
only where a coordinate is missing; coordinates inside India; chords are 2-point
and labelled (A2); spine geometry length within 1% of `length_km` (A1); WKB table
equals GeoJSON; **orientation** (first vertex nearer `from_node`); **endpoint
placement** (slice ends within the trusted offset of their nodes); every slice
vertex lies on its source spine (77,510 sampled, 5 m tolerance); geometry trust
follows `D-026` exactly.

**Result.** All pass. **The first run failed C and D** — 216 reversed edges and
2,736 with slice ends up to 271 km from their nodes — which exposed the
`reversed_to_a` orientation rule (`F-047`); A1, the roadmap's own acceptance test,
had passed throughout. After the fix: 0 reversed, worst endpoint distance 0.44 km.

Coverage (reported, not thresholded): **5,591 edges (57.7%; 56.4% of route km)** with
true alignment, 4,097 chords, 1 null geometry; roadmap target ≥85%.

## E-403 — Topology case inspection (read-only)

**Date:** 2026-10-04 · **Script:** `03_graph_construction/experiments/E-403_topology_cases/run.py`
· **Outputs:** `small_components.csv`, `high_degree_nodes.csv`,
`dissolvable_junctions.csv`, `E-403_report.json` · **Run:** `make topology`

**Question.** Phase 3 plan item 5: inspect isolated components, high-degree nodes and
`is_dissolvable` junctions without changing the topology; and settle `D-020`'s open
"real isolated lines or residual gaps?".

**Result.** (i) The 17 small components (37 nodes, 501.5 km) lie closer to the giant
than an ordinary node to its neighbour — likely residual gaps (`F-048`, `D-041`);
baselines (58.5% of corridors have a deficit; ordinary nearest-neighbour median
4.73 km) are computed, not assumed. (ii) 26 nodes have degree ≥6, **all stations**,
max 7 (`MURTAJAPUR`, `MAVLI JN`, `PANVEL`, `KALAMNA`); top 1% of nodes hold 2.5% of
edge endpoints — no hubs. (iii) All 115 dissolvable junctions straddle a corridor
boundary, 3 change gauge, 20 hit an adjacent pair (`F-049`).


## E-500 — Graph v1.2 (the five known weaknesses)

**Date:** 2026-10-04 · **Script:** `03_graph_construction/experiments/E-500_v1_2_build/run.py`
· **Outputs:** `graph_v1_2/` · **Run:** `make v12` · **Report:** `graph_v1_2/VALIDATION_v1_2.md`

Each weakness measured, then fixed only as far as the evidence allowed; 12 gates
(W1 connectivity, equivalent route, cycle-rank drop; W2 overlay length, bridge and
tunnel subset; W3 beats constant, sources valid, unimputed only where no example
exists; W4 LOO ≥ 99%; attribute-exact round trip; Phase 2 completeness except
degree). All pass. Two weaknesses were different problems from the ones described
(`F-051`, `F-053`). Five of my own bugs were caught by gates and are listed in the
report, §8.

## E-501 — v1.2 audit

**Script:** `.../E-501_v1_2_audit/run.py --part A|B` · **Run:** `make v12audit`

A: removal sets nested across six threshold settings (35–62); timetable — 32 of 39
removed edges with trains confirmed, 0 contradicted. B: all 8 conclusions within
band vs v1.0 and v1.1; meshedness uses 56% of its band.

## E-502 — Service layer

**Script:** `.../E-502_service_layer/run.py` · **Outputs:** `service_layer/` · **Run:** `make servicelayer`

19,865 directed pairs; identical to Phase 2's undirected pair set; run-times agree to
0.5 min median. Running days and capacity: not in any input.


---

## E-600 — Graph v1.3 from external evidence

`03_graph_construction/experiments/E-600_v1_3_build/run.py <stage>`; code `railgraph/v13.py`;
`make v13`. Stages: s1 node attributes · s2a official distances · s2b OSM routing (4 parts) ·
stage3 length rule · stage4 topology (full) · stage5 assemble, gates, exports · stage5b
validation (IIT KGP edges, datameet trains) · stage5c 2017 hold-out · stage6 audit lists.
Tuning scripts in `tuning/`. Results in `graph_v1_3/VALIDATION_v1_3.md`; every gate passes.


## E-601 — Do the conclusions survive v1.3?

`03_graph_construction/experiments/E-601_v1_3_conclusions/run.py open|full|report`; same
`sensitivity.measure_graph` battery and `BANDS` as E-501 B. Output `conclusions_v1_3.csv`,
`report.json`: all within band for both variants (F-064).

## E-709 — national severance criticality

**Claim tested:** the stable-class certification in D-055 is usable — cut points, bridges
and trains-per-day answer a real operational question without the unstable metrics.

**Input:** `graph_v1_4/open` via `railgraph.release`; `service_layer_v1_4` trains_per_day.
**Command:** `make sever`. **Runtime:** ~6 min (structure 2, exposure 3.5).

**Result.** 1,149 of 9,640 sections (11.9%) have no alternative route. Collapsed into
maximal bridge chains: **283 severance corridors**, 2 of them severing >200 stations.
1,166 cut points, of which 200 are real junctions (degree >= 3). 5.6% of daily service-pair
movements (2,256 of 40,174) cross a bridge, so cannot be diverted at all. Of the busiest
100 sections, 90 have a detour factor above 3x; median detour 291 km.

**Two method corrections, both forced by the first pass:**
1. Edges over-count: the Siliguri chain is 10 bridges severing the same ~455 stations.
   Corridors, not edges, are the unit — which is also the NRP's "weakest link" framing.
2. 82 bridges are one station held as two nodes, detected by a structural signature
   (< 1 km and severs exactly 1 station), not by name matching. This caught the renames
   E-705's duplicate list missed: ALD/Prayagraj Jn (206.5 trains/day), VSKP/Waltair (128.8),
   Cheoki/Prayagraj Chheoki (76.3), Daraganj/Prayagraj Sangam (15.6) — all would have
   topped the vulnerability table. Contracting E-705's own 82 pairs moved only 5 of 1,236
   bridges and 4 of 1,170 cut points, so duplicates cost this analysis 0.4%, not the much
   larger penalty they impose on a centrality ranking.

**External verification (retrodictive; disruption records were never used in construction):**
- SC0077 = the Siliguri corridor. Cutting Barsoi Jn–Makuria severs 459 stations: all 327
  the graph places in the eight NE states, plus 115 North Bengal and 17 Bihar. Recovered
  from GIS geometry with no prior knowledge of the chokepoint.
- SC0069 = Lumding–Badarpur hill section. Predicted severed set 84 stations (58 Assam,
  18 Tripura, 5 Manipur, 3 Mizoram). The 6–7 July 2025 landslide at KM 51/1-2 (Mupa–Dihakho)
  cut off exactly Tripura, Manipur, Mizoram and southern Assam; NFR cancelled 4, part-
  cancelled 3, rescheduled 7+. Predicted 10.6 dependent trains/day vs ~14 affected.
- SC0026 = Bharoli Jn–Baramula, 44.6 dependent trains/day: the corridor behind the 18
  cancellations in the August 2025 J&K flash floods.

**Verdict: claim upheld.** The stable class alone produced two independently verifiable
national findings. No unstable metric was needed or used.

## E-713 — dataset closure profile and manual audit pack

**Purpose:** a complete, measured account of graph v1.4 for closing the dataset, and stratified
samples for a manual audit. **Command:** `python 04_analysis_modules/E-713_closure_profile/profile.py . <out>`.

**Result — four defects the nine gates and 30 tests do not catch:**
1. `degree` in `nodes.csv` stale on 255 nodes (the nodes touched by v1.4's edge repairs).
2. The 129 repair-added sections carry no attributes: no gauge, zone, tracks, corridor, speed,
   service or `official_km` — 1,578.6 km.
3. All 90 sections shorter than their own straight line are repair additions: the official
   consecutive-stop length is right and an endpoint's coordinates are wrong, by up to 169 km.
4. No override has a reviewer, review date or source URL (179 of 179).

Also measured: per-section agreement with the timetable 51.0% within 5% (route level 0.72%);
the "confirmed by official" label equals roughly a 25% tolerance; Kollam Jn (151 trains/day)
absent; 29 crosswalk rows marked for review never reviewed; 17 fragments, at least 7 probable
missing links; 6 sections labelled standard gauge.

**Audit pack:** 11 CSVs, 765 rows, blank `verdict`/`note` columns, tiered by what each decides.
**Closure document:** "Rail-Intel graph v1.4 — dataset closure audit" (Claude Doc).

## E-715 — OpenStreetMap probe: what an open rebuild can give us

**Purpose:** measure, before designing v2.0-open, what the six OpenStreetMap zone extracts we
hold can supply. Read-only; nothing in v1.4 or v1.4.1 reads its output (D-050).
**Command:** `python 03_graph_construction/experiments/E-715_osm_probe/osm_probe.py . <out>`.

**Result:** 7,815 of our 8,621 coded stations and 223 of the 228 absent ones are in OSM; gauge
tagged on 96.8% and electrification on 94.9% of mainline km; but mainline totals 111,476 km
against 69,439 official (parallel tracks drawn separately), the network is in 510 pieces, and
only 11.9% of stations sit on the track. Lengths tie with ours overall (46.1% vs 48.2% within
5% of the timetable, 423 pairs) and beat ours on floor sections (15.8% vs 0%, 19 pairs). F-040.
Design consequence: roadmap stages O1–O8 (D-060).

## E-717 — graph v1.4.1 working build (roadmap milestone A1)

**Purpose:** fix the closure-audit defects that need no audit, without touching v1.4 (D-055).
E-716 is reserved for the OpenStreetMap build (D-060). **Command:** `make v141`.

Reuses E-708's stages; replaces only the graph stage. Inherits OVERRIDES.csv and the crosswalk
from v1.4 byte for byte (A3 adds the audited rows).

**Result:**
- I-01: `degree`, `component_id`, `in_giant` recomputed from the graph; 255 degrees corrected,
  component labels and giant flags already right.
- I-02: all 129 repair sections now carry `official_km` and `official_source` from their
  override's evidence (60 datagovin_2017, 59 both, 10 iitkgp_routes_2024), `edge_origin`, and
  `raised_to_chord` (12 floored). Gauge, zone, tracks and corridor are taken from neighbouring
  sections only when both ends agree on one value: unresolved 1, 3, 20 and 68. Each edge lists
  what was inferred and what was not (`repair_attrs_inferred`, `repair_attrs_unresolved`).
- Retired: `overrides_applied` (0 everywhere), `service_direct`, `service_load` (2017 counts).
- Topology, lengths and ids identical to v1.4; all 9 gates pass with identical measurements;
  the build reproduces byte for byte; v1.4 files unchanged.
- Tests: `tests/test_v1_4_1.py`, 6 new (I-04 for I-01 and I-02); suite 36 pass.

## E-716 (C1) — OpenStreetMap stages O1–O3: filter, collapse parallel tracks, snap stations

**Purpose:** roadmap milestone C1 for v2.0-open (D-060). **Command:** `make osm-c1` (~45 s,
numpy/pandas/scipy). **Output:** `graph_v2_0_open/work/` (working, not a release).

**Result:**
- **O1 filter.** 149,318 km of OSM track in; 105,957 km kept as running lines. Dropped, every
  km with a reason:
  - sidings, spurs and yards: 22,863 km;
  - lines under construction: 6,335 km;
  - dedicated freight corridor: 5,356 km;
  - abandoned: 3,066 km;
  - metro: 3,044 km;
  - industrial: 1,297 km;
  - the rest: small.
- **O2 collapse.** 10.4 M samples. Of 16,152 chains, 11,855 parallel stretches were removed,
  then 11,174 connectors (173 km, median 15 m) re-joined loose ends; 121 were left as dead ends.
  - Route km is **73,310**, +5.6% against the Year Book's 69,439. Track only: 73,137 (+5.3%).
  - The network came out less fragmented: 491 → 292 components, giant 93.8% → 95.4% of km.
- **O3 snap.**
  - 9,130 of 9,574 coded stations snapped (**95.4%**).
  - 362 of the 444 unsnapped are metro stations. Excluding them, the share is **99.1%**.
  - 24 coded stations have no running track within 100 m.
  - 53 snapped stations lie nearer a metro line than to their snap. They are flagged
    `review_metro` for C2, which joins on timetable codes.
- **Gate C1.** C1a, route km within ±7%: pass. C1b, ≥95% of coded stations snapped: pass.
- **Reproducibility.** Every CSV output is byte-identical between the cloud workspace and the
  laptop. 7 new tests; suite 43 pass.

**Method change during the milestone.**
- The first version dropped whole chains when 80% of their length was parallel. That left
  76,124 km, and the diagnosis showed 6,728 km of chains that were only partly parallel.
- The final version removes only the parallel stretch. The merge distance was not changed.

**Open, carried to C2/C3.**
- km continues to fall above 15 m: 20 m gives −1,600 km. This could be third and fourth lines
  on separate formation, or distinct lines; it cannot be told apart without imagery.
- Connectors could create a false junction at a flyover. C2/C3 check routes against the
  timetable.

## E-716 (C2) — OpenStreetMap stages O3b, O5, O4, O6: the station-level graph and its service

**Command:** `make osm-c2` (runs C1 in memory; ~2 min, 2.6 GB). **Output:**
`graph_v2_0_open/open/`, `station_code_crosswalk.csv`, `service_layer_v2_0_open/open/`, `work/c2_*`.

**Result:**
- **Stations.**
  - 9,288 snapped OSM stations; 22 lie outside India and 43 are metro.
  - 9,185 station nodes from OSM; 16 codes are conflicts.
  - O3b: 457 timetable codes had no OSM station. 372 were placed from Wikidata, 54 became
    aliases and 31 stay unresolved.
- **O5, 46 joins:**

  | Kind | Joins | km | Stations brought in |
  |---|---|---|---|
  | A, along track | 38 | 105.2 | 285 |
  | A2, shared station | 6 | 0.3 | 63 |
  | C, timetable distance | 2 | 40.5 | 21 |

- **O4.** Removed: 1,746 km of dangling track, 3,132 duplicate routes (1,812 km), and 1,137
  second lines round stations (1,201 km).
- **Graph.**
  - 11,229 nodes: 9,551 stations and 1,678 junctions.
  - 11,850 edges, **68,768 km** (−1.0% against the Year Book).
  - 16 components and 637 independent cycles; v1.4 has 682.
  - Gauge is known on 99.0% of km, electrification on 97.0%; 95.7% of the known km is electrified.
- **Service.**

  | | v2.0 | v1.4.1 |
  |---|---|---|
  | Directed pairs | 17,219 | 16,703 |
  | km carrying service | 86.9% | 80.2% |
  | Served stations | 4,691 | 4,467 |

- **Gate C2.**
  - C2a, no straight-line lengths and tags carried: **pass**. Two edges use timetable distances.
    439 sections are shorter than the straight line between their station points; in all but 6
    the gap is under 0.2 km, because a station point stands up to 100 m off its track. The 6 are
    merged same-code stations.
  - C2c, served stations at least v1.4.1's: **pass**.
  - C2b, ≥99.5% of stations in the main network: **fail as written, 98.91%**. 102 of the 104
    stations outside have no 2024 train: closed or suspended lines (Kangra narrow gauge 34,
    Shakuntala 27, Gujarat narrow gauge 11, Raipur–Dhamtari 10, Gwalior–Sheopur 9 …). Of
    2024-served stations, 99.96% are in the main network.
- **Reproducibility.** Every CSV is byte-identical between the workspace and the laptop.
  9 new tests; suite 51 pass, 1 expected failure (C2b as written).

**Carried to C3.** Junctions are separate nodes, so station degree is not comparable with v1.4.
Stations reach at most degree 4 and junctions are all degree 3, so C3 must compare cut points
with each junction attributed to its nearest station.

**E-716 (C2), amended 2026-10-19:**
- **Stations sharing a track point.** 40 OSM stations snapped to the same track point as
  another. The first build kept only one of each group, which dropped Begumpet (BMT, 55 stops
  in 2024). Now the station a timetable knows is the node, and the other codes become its
  aliases.
- **Platform numbers stored as `ref`** (for example "2") are no longer read as station codes.
- **Effect.** 9,549 stations; 4,693 served.
  - 4,680 of the 4,735 codes in the 2024 timetable are graph nodes and 14 resolve through
    aliases. 41 stay unresolved: 0.18% of 2024 stop events.
  - 17,230 directed station pairs.
- **Gate C2 passes in full** under D-064.
- Outputs are byte-identical on the laptop; suite 53 pass.

## E-716 (C3) — validation of v2.0 against v1.4.1, checkpoint CP1

**Command:** `make osm-c3`. **Report:** `graph_v2_0_open/VALIDATION_v2_0.md`.

**Results**
- All nine E-708 gates pass on v2.0, out of sample.

  | Measure | v2.0 | v1.4.1 |
  |---|---|---|
  | 2024 route median error | 0.39% | 0.72% |
  | IRN within max(1 km, 5%) | 93.5% | 82.7% |
  | 423-pair lengths within 5% | 50.6% | 48.2% |
  | All 6,832 sections within max(1 km, 5%) | 92.2% | 81.2% |

- Served network: all 60 large severances are reproduced, including Siliguri (0.989) and
  Lumding–Badarpur (1.0). Cut points agree for 95.8% of stations; every difference is sorted into
  a cause. Gate C3 passes.

**Found on the way, and fixed before CP1** (D-065)
- The first run gave a 39% median route error.
- The collapse broke routes in large stations: fixed by restoring 1,250 stretches.
- O1's removal of crossovers and station tracks cut through routes at junctions: fixed with
  731 throat links.

**Seeded:** `docs/V2_ISSUES.md`, 20 issues; 3 blocking, 1 for your decision.

## E-716 (P2) — gap closing, passes 1–5, checkpoint CP2

**Pass 1, V2-01.**
- 251 extra cut points classified. The defect: Udaipura–Tikamgarh, which has 2024 trains, was cut
  by a 30 m `construction` way. Fixed by short-gap throats (ways ≤ 0.5 km).
- What remains is routing in the served view, v1.4.1 shortcuts (V2-23), industrial track, and one
  placement.
- I tried raising the throat length to 3 km for Badarpur and reverted it: the case was a v1.4.1
  duplicate, not a v2.0 break.

**Pass 2, V2-05 and V2-04.**
- 2,216 sections lie on cycles ≤ 5 km, nearly all junction to junction.
- Absorbing them into the physical graph would distort routes: the 2024 median error went from
  0.39% to 0.97%. So the physical graph stays exact, and a places view is derived (D-066):
  496 cycles, 516 junctions, station degree up to 8.

**Pass 3, V2-19.** The 2017 GODL layer was built and compared with 2024 (D-067). It gives 8,050
served stations against 4,694, overlaps at Jaccard 0.88, and correlates 0.93. Only 2024 has trains
per day and the 2018–2024 lines.

**Pass 4.** `served_2024`, `scheduled_2017`, `line_status`, `track_lon` and `track_lat` added;
state from datameet, 99.99% filled, agreeing with v1.4.1 on 99.8% of stations.

**Pass 5.**
- 13 of 15 code conflicts resolved against the timetable. A bug that inserted a Wikidata station
  for a code that was a conflict, not missing, was fixed.
- The build now fits the laptop: c1 / joins / graph / service in 72 / 34 / 16 / 40 s.
- All outputs are byte-identical across machines; 68 tests pass.

**After P2, with every gate passing**

| Measure | Value |
|---|---|
| Stations | 9,540 |
| Junctions | 2,794 |
| Sections | 13,586 |
| Route km | 70,353 (+1.3%) |
| 2024 route median error | 0.39% |
| 2024 routes within 5% | 99.2% |
| IRN within max(1 km, 5%) | 93.6% |
| 423-pair lengths within 5% | 50.8% |
| Served-network cut-point agreement (places view) | 96.9% |
| Retrodictive cases | Siliguri 0.989, Lumding–Badarpur 1.0 |

## E-716 (P3) — release candidate v2.0-open-rc1

- Release audit found the build leaning on 2024 data and two sections at timetable lengths where real
  track exists. Fixed under D-068 (open-only build; shared-station joins; same-name merges; metro rule).
- All gates pass after the change: C2a–d, C3a–d; 2024 route median error 0.38%, 99.2% within 5%;
  93.6% of IRN pairs within max(1 km, 5%); Siliguri 0.989 and Lumding–Badarpur 1.0 reproduced.
- Served cut-point agreement 96.8%. Of 187 v2.0-only longer-loop differences: 175 served-view routing,
  7 v1.4.1 shortcuts, 3 junction attribution (the Lucknow metro station dropped), 2 industrial.
- `release.py` writes `release/rail-intel-v2.0-open-rc1/` and a deterministic zip (1.4 MB): two runs,
  identical bytes. 43 tests pass.

## E-716 (P4) — lock

Final package `rail-intel-v2.0-open` built from the same data as rc1 (all ten data files byte-identical), plus
`CITATION.cff` in the package, `.zenodo.json`, `.LOCK.md` and `.deposit_checklist.txt` beside it. Zip hash
identical on the cloud workspace and the laptop. `test_v2_p3.py` made independent of test order. The rc1 folder and zip
removed as superseded.
