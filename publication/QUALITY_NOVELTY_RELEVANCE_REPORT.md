# Quality, novelty and downstream relevance — graph v1.0

**Spec hash:** `f9adf8ca9042` · **Date:** 2026-10-03
**Scope:** this document answers three questions a reviewer, a teammate or a
later version of us will ask, that no single existing document answers
together: is the graph good, is it new, and is it actually useful for what
the product needs it for. It synthesizes `VALIDATION_v1.md`, `LITERATURE.md`,
`GRAPH_HANDOFF_V2.md` §4.5/§4.9 and the `04_analysis_modules/` specs rather
than restating them — every number below is sourced, not re-measured.

---

## 0. Where the build actually is

| | |
|---|---|
| **Repository root** | `C:\Users\vinja\Desktop\Rail-Intell` (this device, `bhuvaneshdell`) |
| **Graph artifact** | `03_graph_construction/graph_v1/` — `rail_graph_v1.graphml`, `nodes.parquet`, `edges.parquet`, `nodes.geojson`, `edges.geojson`, `graph_v1.manifest.json` |
| **Construction code** | `03_graph_construction/railgraph/` (the `BuildSpec`-parameterized rebuild), `03_graph_construction/experiments/E-*` |
| **Inputs it was built from** | `02_graph_inputs/graph_dataset/` (hashes pinned in the manifest) |
| **Release docs** | `03_graph_construction/graph_v1/DATASHEET.md`, `VALIDATION_v1.md` |
| **Publication support** | `publication/` — `GAP_ANALYSIS.md`, `ATTRIBUTE_ROADMAP.md`, `V1_FINAL_REPORT.md`, `evidence/E-300, E-301, E-102`, `figures/` |
| **Working record** | `docs/` — `DECISIONS.md` (33 ADRs, 0 open), `FINDINGS.md` (41), `EXPERIMENTS.md` (9), `PROGRESS.md` |
| **Downstream module stubs** | `04_analysis_modules/01..04_*` (owner: Abrar) |
| **Git state** | local only, 4 commits (`0a6c396`→`d591083`), **nothing pushed, no remote touched** per your instruction. `docs/{DECISIONS,EXPERIMENTS,FINDINGS,PROGRESS,PHASE3_GRAPH_ROADMAP}.md` are modified-not-committed; everything under `publication/`, the two release docs, `CITATION.cff` and `Makefile` are new-not-committed. |

The graph itself (`graph_v1.manifest.json`) is frozen and content-hashed: every
input file's sha256 is pinned, so "which graph" is never ambiguous. It has
**not** been re-built since `E-102` ran — `E-102` is a read against the shipped
artifact, not a rebuild, so the manifest's `spec_hash` is still current.

---

## 1. Quality report

### 1.1 Headline numbers

9,095 nodes (8,621 station + 474 operational junction) · 9,689 edges ·
72,201 route km · giant component 99.6% (9,058 nodes) · mean degree 2.13, max 7
· 1,338 articulation points · 1,412 bridges · 612 independent cycles.

### 1.2 The verdict, in one table (full detail: `VALIDATION_v1.md`)

| Layer | Result | Verdict |
|---|---|---|
| Spec invariants | 14/14 hold | **pass** |
| Phase 2→3 rebuild equivalence | identical edge set, 0 length mismatches | **pass** |
| Degree distribution vs theory | exponential tail, matches spatial-network prediction | **pass** |
| Route km, national | +3.98% vs official | **pass with caveat** |
| Route km, per-zone (`E-102`) | −15.2% to +19.1%, r=0.977 | **resolved — structure real, levels not reliable** |
| Cross-source contradiction | 0 contradictions across independent sources | **pass** |
| Sinuosity vs mountain railways | all 4 UNESCO lines in top 6 of 871, zero terrain input | **pass — strongest check we have** |
| Bridge-inventory vs Rajya Sabha Q.371 | capture 0.316, zone-biased 0.006–0.638 | **fail, reported as a negative result** |
| Attribute provenance | 4 of 6 physical attributes are corridor constants at edge granularity | **fail** |
| Station-placement completeness | 42.9% of declared placements unmatched; 766 edges / 24.5% of route km show the defect signature | **fail** |
| Construction-choice sensitivity | Tier A: 0 of 9 open-choice conclusions are artifacts | **pass** |
| Null-model fragility | fragility tracks the degree sequence, confirmed against a Barabási–Albert control | **pass** |
| Format round-trip | GraphML/parquet exact; GeoJSON loses exactly 1 node (no coordinate), accounted | **pass** |

**Net: topology is sound and well-evidenced (9 passes, 1 resolved, 1 reported
negative result). Attributes are the weak layer (2 genuine fails), and both
are quantified and bounded, not open-ended.** No defect is new or hidden —
every one was found by this project's own audits (`E-300`, `E-301`, `E-102`)
and has a tracked remedy (`ATTRIBUTE_ROADMAP.md`, `D-025`–`D-033`).

### 1.3 What "fail" actually means here, concretely

- **Attribute provenance (`F-027`):** `gauge_code`, `speed_kmph`, `n_tracks`,
  `zone_code` are constant within 96–99% of corridors but stored per edge —
  they describe the corridor, not the segment. `speed_kmph` is additionally a
  *declared maximum*: observed timetable run-times imply median 53.5 km/h
  against a declared median 110 km/h (ratio 0.513, `F-036`) — travel-time
  results using it are out by roughly 2×.
- **Station placement (`F-026`):** 21,560 declared placements, 12,305 matched.
  The defect signature (corridor missing ≥3 stations, edge >10 km) identifies
  766 edges exactly. `E-102` then showed (§1.2 row 5) this is a **topological**
  gap — missing intermediate nodes — not a **metric** one: the length on those
  edges is real, so don't filter them out of anything length-based; do treat
  them as "a shortest path through here may be skipping real stations."

### 1.4 What makes this a *quality* report rather than a pass/fail stamp

Every number above is regenerated by a script (`E-00X`/`E-1XX`/`E-2XX`/`E-3XX`
in `docs/EXPERIMENTS.md`), not asserted once and remembered. Two of the twelve
checks are reported **because they failed**, with the defect bounded in
coordinates a downstream module can act on (which edges, how much of the
graph, which direction the error points) rather than a vague caveat.

---

## 2. Novelty, validated against the literature

Full annotated bibliography: `docs/LITERATURE.md`. Summary of the three claims
the paper will make, each checked against a specific prior work rather than
asserted in the abstract:

| Claim | What it says | Checked against | Measured margin |
|---|---|---|---|
| **C1** — scale, type, attribution | 9,095-node geolocated, infrastructure-attributed **physical** graph + derived service layer, FAIR-released with a datasheet | Sen et al. 2003 (587 stations, timetable-derived), Bhatia et al. 2015 (809 stations, origin–destination) | **15.5× Sen, 11.2× Bhatia** on node count; neither prior graph carries geography or infrastructure attributes at all |
| **C2** — construction method | Reproducible GIS → corridor → ordered chain → **junction-stitched** transform, with stitching as a named operator, timetable retained as validation rather than consumed as input | Kurant & Thiran 2006 (defines physical/logical two-layer model, goes timetable→physical by *removing shortcuts*); Karduni et al. 2016, Boeing 2025 (both solve road-network *over-counting*) | We invert Kurant & Thiran's direction (GIS→physical, not timetable→physical) and solve the opposite failure mode from the road literature: chains that **fail to meet** (59.4%→99.6% giant component via stitching), not chains that over-segment |
| **C3** — validation + sensitivity | Cross-source external validation plus a tiered construction-choice sensitivity study naming which downstream conclusions survive which choices | Palk et al. 2026 (*Networks*) — nearest existing claim, varies graph **representation** | **Not yet verified — paywalled, blocking.** We vary **construction** (placement tolerance, stitching, node model, match confidence), which is upstream of representation; on title/abstract evidence this is unexamined, but the actual text must be read before this claim ships |

### 2.1 The honest state of the novelty claim

- **C1 and C2 are solid now.** The scale multiple is a fact of the data, and
  the inversion of Kurant & Thiran's direction is a real, citable
  methodological difference — it's also *why* the timetable was available as
  an independent validation set at all (the sinuosity and E-301 checks both
  depend on this).
- **C3 has one hard blocker:** `[PAL26]` has not been read. It is the single
  nearest competing claim in the entire bibliography, and until it's obtained
  (institutional access, flagged in `LITERATURE.md` §"To obtain" as **High
  priority**), C3 should be stated in internal docs as "distinct on current
  evidence," not asserted as novel in anything submitted externally.
- **The gap statement itself is falsifiable, not rhetorical** — it names a
  specific absence (no published graph both station-scale *and* externally
  validatable, because the timetable is usually the only source *and* the
  only reference) and the sinuosity result (§1.2) is the demonstration that
  having a second, independent source actually pays off: four UNESCO mountain
  railways surfaced from pure geometry, with no terrain or heritage input
  anywhere in the pipeline.

**Bottom line: the novelty claim is real and two-thirds locked down. The third
part depends on a single paper neither of us has read yet — get it before this
goes anywhere external.**

---

## 3. Usefulness to the downstream modules and the product

Four analysis modules are scoped against this graph (`04_analysis_modules/`,
owner Abrar); `GRAPH_HANDOFF_V2.md` §4.9 is the authoritative mapping. Checked
here against what v1.0 actually ships, not what was planned.

| Module | What it needs from the graph | Ships in v1.0? | Caveat that reaches it |
|---|---|---|---|
| **1 — Structure & criticality** | full topology view (all 9,689 edges), `service_load` for traffic-weighted betweenness, baseline 1,338 articulation points / 1,412 bridges, `zone_code` as an independent label (not a clustering feature) | **yes** | `zone_code` needs the 5-variant typo cleanup (§4.5 of the handoff) before any zone aggregation |
| **2 — Accessibility & connectivity** | `service_edges.csv` (`runtime_min_median`, `n_trains`), node coordinates + `length_km` for circuity, space-P transfer graph derived on the fly | **yes**, but **`speed_kmph` must not be used for travel time** — declared vs. observed ratio is 0.513 (`F-036`); use `runtime_min_median` instead, which `E-301` shows is the better-grounded number | `suspect_long_edge` (766 edges) is a live risk here specifically: a shortest path through one may silently skip real intermediate stations |
| **3 — Redundancy & resilience** | **full topology view, explicitly** — this is the module the attributed-core filters would damage | **yes** | Confirmed, not assumed: filtering to the attributed core drops independent cycles 612→328 and pushes bridge share 14.6%→35.8%, a ~2.5× fragility overstatement if the wrong view is used (§4.5 of the handoff, reproduced in the sensitivity sweep `E-200`) |
| **4 — Expansion & what-if** | candidate pairs from real data (607 service pairs with a missing graph endpoint, 40 spatially-rejected junction matches), `length_km` as cost proxy | **yes** | candidate-pair quality inherits the same 42.9% station-placement shortfall as everything else — candidates near suspect edges should be treated as lower-confidence |

### 3.1 What this means for the product, not just the modules

- **Nothing in v1.0 blocks any of the four modules from starting.** Every
  input each README lists is present and frozen.
- **The two real fails (§1.3) reach different modules differently.** Module 1
  and 3 (structure, resilience) are topology-only and are essentially
  unaffected by the attribute-provenance fail — they were already told to use
  the full view. Module 2 (accessibility) is the one that would have silently
  inherited the 2× speed error if `speed_kmph` had been used instead of the
  service layer's observed run-times — this is now an explicit instruction,
  not a hope.
- **The route-km resolution (§1.2, `E-102`) specifically de-risks Module 4.**
  Before this run, it was unknown whether excluding suspect edges would
  improve candidate-pair cost estimates. It would have made them worse by
  ~20%. Module 4 now has a stated rule instead of a guess.
- **Net relevance verdict:** the graph is fit for all four modules **as
  scoped** (full topology for 1 and 3, service layer over GIS attributes for
  2, real candidate data for 4), provided each module follows the view/column
  guidance above rather than reaching for the nearest-looking attribute. That
  guidance did not exist before this project's audits; it does now, and it is
  specific enough to put in each module's README rather than leaving it in a
  general caveats section.

---

## 4. One-paragraph summary

The graph is structurally sound and the strongest evidence for that (the
mountain-railway sinuosity check) comes from outside the pipeline entirely.
Its weaknesses are in attributes, not topology, are fully bounded (which
edges, how much, which direction), and map to concrete per-module rules
rather than a blanket warning. Against the literature, the scale and
construction-direction claims are solid; the validation-novelty claim has one
unread paper standing between "probably true" and "verified" — get it before
anything goes external. Against the product's own four modules, nothing is
blocked, and the one defect that *would* have quietly corrupted a module's
results (declared vs. observed speed, Module 2) has already been caught and
routed around.
