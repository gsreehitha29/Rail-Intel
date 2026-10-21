# Rail-Intel — timeline, versioning and honest assessment

**One document for the whole history of the dataset.** It records every version, the
decisions and design changes that produced it, how each version was validated, and what
is wrong with the result.

It replaces and consolidates: `CHANGELOG.md`, `docs/PROGRESS.md`, `docs/LIMITATIONS.md`
(stale, last touched 2026-10-03 and still describing v1.0-era figures),
`docs/VALIDATION_REPORT.md`, `docs/GRAPH_HANDOFF.md`, `docs/GRAPH_V2_ROADMAP.md`, and
the per-version `VALIDATION_*.md` / `DATASHEET.md` / `FITNESS.md` files. Those are in
`_archive/docs_superseded/`; the per-version ones travelled with their version folders.

It does **not** replace the three live registers, which hold the detail this document
summarises: `docs/DECISIONS.md` (D-001…D-069), `docs/FINDINGS.md` (F-…),
`docs/EXPERIMENTS.md` (E-…) and `docs/V2_ISSUES.md` (V2-01…V2-25).

- **Current dataset:** `v2.0-open`, locked 2026-10-21 (D-069).
- **Status:** final and in use inside the project. Public release and DOI deferred.
- **Licence:** ODbL 1.0 (database) / DbCL 1.0 (contents). Built from open data only.

---

## 1. The version ladder

| Version | Date | Base source | Nodes | Sections | Route km | Components | Status |
|---|---|---|---|---|---|---|---|
| v1.0 | 2026-09-30 | Esri/GIS corridors | 9,095 | 9,689 | 72,201.1 | 18 | superseded, archived |
| v1.1 | 2026-10-03 | Esri/GIS + provenance | 9,095 | 9,689 | 72,421.0 | 18 | superseded, archived |
| v1.2 | 2026-10-04 | Esri/GIS | 9,095 | 9,638 | 71,165.0 | 18 | superseded, archived |
| v1.3 open | 2026-10-05 | Esri/GIS + external evidence | 9,095 | 9,638 | 73,335.8 | 18 | superseded, archived |
| v1.3 full | 2026-10-05 | as above + topology repairs | 9,567 | 10,122 | 73,527.3 | 3 | superseded, archived |
| v1.4 | 2026-10-15 | v1.3 open + repairs | 9,095 | 9,759 | 74,849.7 | 18 | **frozen baseline** (D-055) |
| v1.4.1 | 2026-10-19 | v1.4 + milestone A1 build | 9,095 | 9,759 | 74,849.7 | 18 | **comparison baseline** |
| **v2.0-open** | **2026-10-21** | **OpenStreetMap only** | **12,301** | **13,560** | **70,304.6** | **8** | **final, locked** |

v2.0-open splits its 12,301 nodes into 9,507 stations and 2,794 junctions. Its route km is
**+1.25%** against the official 69,439 km; v1.4's 74,849.7 km is +7.8%. The giant component
holds 99.73% of nodes and 99.65% of stations.

Two views ship in v2.0-open (D-066):

| View | Nodes | Sections | Independent cycles | Use it for |
|---|---|---|---|---|
| physical graph | 12,301 | 13,560 | 1,267 | distance, routing — lengths are exact |
| places view | 10,024 | 10,514 | 498 | structure, degree, cut points, redundancy |

---

## 2. The history, phase by phase

### Phase 1–2 — from notebooks to a pipeline (Sept 2026)

The work began as notebooks over an Esri-derived GIS corridor layer plus a station master.

- **2026-09-28** — the notebook workflow is replaced by a reproducible graph-input pipeline.
- **2026-09-29** — the repository is reorganised into numbered phases (`01_…`, `02_…`, `03_…`).
- **2026-09-30** — the graph approach is finalised and **v1.0** ships: 9,095 nodes, 9,689 sections,
  18 components, 612 independent cycles.

The construction model was settled here and has survived every version since: a hybrid typed
node model of stations and operational junctions (D-001), degree-2 junctions retained and
flagged (D-002), corridors stitched at shared junctions (D-005), a simple graph keeping the
shortest of parallel corridors (D-006), an undirected physical layer with direction confined
to the service layer (D-009, D-047), and gauge and speed as attributes rather than filters
(D-011, D-012).

### Phase 3 opens — the apparatus (2026-10-03)

The decision register, findings register and experiment log were created, and the roadmap was
checked against the repo. This is the point at which the project started recording *why*, not
just *what*.

**v1.1** adds the provenance layer: `length_source` on every section, and the measurement of
how much of the graph is not really measured — 764 suspect long sections carrying 17,670 km,
**24.4% of route km**. Route km moves only +0.30% from v1.0, but 1,286 sections change.

Design change: **D-026 — a hybrid `length_km` with a `length_source` column.** The project
stopped pretending every length was a measurement and started labelling each one's evidence.
D-027 followed: declare attribute granularity rather than implying edge-level measurement.

### v1.2 — the five known weaknesses (2026-10-04)

Each weakness was fixed where it was provable and labelled where it was not.

- 51 stitch sections that duplicated routes already in the graph were removed (D-043, F-052).
  Sections drop to 9,638, cycles to 561, route km to 71,165 (−1,256 km).
- Attributes move to segment overlay for 9,497 sections, with a corridor fallback for 192 (D-044).
- Bridges and tunnels become edge-level where the evidence allows (D-028).
- The 50 km/h speed constant is replaced by validated imputation: mean absolute error
  **11.4 km/h** against the constant's **56.2 km/h** (D-045, F-054).
- `state` is derived by boundary polygons rather than the station master, whose values predate
  Telangana (D-031, D-046, F-055).

### v1.3 — external evidence, and the licence fork (2026-10-05)

v1.3 brought outside data in and, critically, shipped **two variants** so that the OpenStreetMap
licence question stayed reversible (D-048).

- A length evidence hierarchy (D-049), with OSM routed lengths admitted as a *check* and never
  as a length (D-050).
- A coordinate moves only where three sources agree (D-051).
- Topology repairs in the full variant require OSM routing evidence (D-053).
- Manual corrections enter only through `audit/OVERRIDES.csv` (D-054).
- The full variant inserts 488 stations, splits 339 sections, merges 16 nodes and connects 16
  small components — collapsing 18 components to 3.

### v1.4 — the stop rule (mid-Oct 2026)

v1.4 is v1.3 open plus repairs: a station-code crosswalk for current data, 8 phantom sections
removed, 129 missing links added, 42 candidates rejected as redundant, and a 2024 service layer
weighted by observed train frequency.

**D-055 — graph v1.4 is final; the stop rule replaces the repair backlog.** The project
stopped repairing and started releasing. D-056 gave the release a contract enforced by tests.

Then the wall: **D-057 — C1 cannot be deposited on the current base source.** v1.4 is
Esri-derived and therefore not redistributable. Everything built on it was unpublishable.

v1.4's measured gates: 18 components, giant share 99.59%, 90 sections below their straight
line, IRN station-pair distances within 5% **82.68%**, 2024 route median error **0.72%**,
routes within 5% **95.69%**, 2 unroutable.

### Scope lock (mid-Oct 2026)

- **D-058 — scope locked; the product is corridor vulnerability.** The deliverable is a
  corridor-level vulnerability and contingency tool, not node ranking, capacity, freight or
  real-time operation.
- **D-059 — module scope locked** to the analyses measured as feasible (E-714).
- Earlier, **D-036** had already split the licence by artifact class and committed to publishing
  the method regardless of the dataset's terms. That is what made the next step possible.

### v2.0-open — the open rebuild (2026-10-19 → 21)

**D-060 — OpenStreetMap is built as a separate graph, v2.0-open.** Not a patch on v1.4: a
second, independent construction from open data, to be compared against v1.4.1 rather than
merged into it. Pipeline E-716, following roadmap milestones and gates (D-061).

The build, in stages:

| Stage | What it does |
|---|---|
| O1 | filter OSM to running lines |
| O2 | collapse parallel tracks to one section |
| O3 | snap stations to their nearest track |
| O3b | place stations OSM lacks, from Wikidata |
| O5a | add station throat links (service track inside a station) |
| O5 | joins A, A2, B, C — join pieces at shared stations and short gaps |
| O4 | prune, splice, bypass |
| O6 | service layers: 2017 (GODL, shipped) and 2024 (local only) |

Design changes made during the build:

- **D-062** — collapse and snap settings, calibrated rather than guessed.
- **D-063** — the station graph: stations, joins and contraction.
- **D-065** — the collapse keeps routes; station throats are added; gate C1a moves to the
  station graph.
- **D-066 — an exact physical graph plus a places view for structure.** The physical graph
  keeps junction areas as OSM maps them, so its lengths are exact and its cycle count is
  inflated by yard geometry. The places view merges track points within 1 km into one place
  and is the view for redundancy and degree. This resolved V2-04 and V2-05.
- **D-067** — the release ships the open GODL 2017 service layer; the 2024 layer is built
  locally and not redistributed.
- **D-068** — the build reads only open data; 2024 is used for checking, never for building.
- **D-069 — v2.0-open locked as the final dataset.** Publication deferred.

Checkpoints: CP1 validation against v1.4.1 → CP2 gap closing in five passes → CP3 release
candidate → CP4 lock.

---

## 3. Validation history

| Measure | v1.4 / v1.4.1 | v2.0-open |
|---|---|---|
| Route km vs official 69,439 km | +7.8% | **+1.25%** |
| Station-pair distances within max(1 km, 5%) | 82.7% | **93.6%** |
| 2024 train-route median error | 0.72% | **0.38%** |
| 2024 routes within 5% | 95.7% | **99.2%** |
| 423-pair independent benchmark within 5% | 48.2% | **50.8%** |
| Cut points agreeing with the other version (served) | — | 96.8% |
| Components / giant share | 18 / 99.59% | 8 / 99.73% |

Independent checks beyond the gates: 32 stations and 13 train routes verified by hand (F-050);
Siliguri corridor overlap 0.989 and Lumding–Badarpur overlap 1.0 against the v1.4 findings;
every output byte-identical between the laptop and the cloud workspace (V2-15).

Attribute coverage in v2.0-open: gauge known for 98.9% of km (96.2% broad gauge),
electrification for 96.9% (95.8% of that electrified), state for 99.99% of nodes across 31
states and union territories, 9,404 of 9,507 stations carrying a code.

Service: 10,725 trains from the 2017 timetable, 27,952 station pairs, 8,049 stations and 89.4%
of route km with at least one scheduled train, maximum 898 scheduled trains on a section.

---

## 4. Limitations of v2.0-open

These are properties of the dataset, written down rather than hidden. Each has an ID in
`docs/V2_ISSUES.md`.

**Service and time**
- The shipped service layer is the **2017** timetable and counts **scheduled trains, not trains
  per day** — the open file has no running days. Trains-per-day needs the 2024 layer (V2-19).
- 121 of 27,952 station pairs and 12 of 10,725 trains are unroutable: lines that closed after
  2017 (V2-13).
- 10.6% of route km has no 2017 service at all. Track tagged as running stays in, flagged
  (V2-06).
- No speed, travel time, capacity, headway, block occupancy, running days, freight or
  real-time data exists anywhere in the dataset (V2-20).

**Identity and coverage**
- 93 stations have no code and carry `OSM:<id>`; 14 keep `code~<id>` because OSM puts one code
  on stations far apart. 10 of 12 conflicts were resolved against timetable neighbours; INDR
  and MHBD remain unresolved (V2-09, V2-10).
- 15 stations have no name; 4 sit with no track near them, including Kalakund and Patal Pani on
  the Mhow heritage line, which OSM does not map (V2-11).
- 41 codes in the 2024 timetable were never resolved, and Wikidata could not place 31 (V2-08).
- 1,275 stations have no service in either timetable; 104 sit outside the main network, nearly
  all on closed or suspended lines (V2-07).
- Coverage follows OpenStreetMap. Where OSM is thin, the dataset is thin, and there is no
  independent census to measure that against.

**Geometry and structure**
- 2 sections (14.3 km) take their length from the 2017 timetable because OSM has no track
  there (V2-24, `length_source = timetable_2017`). Every other length is measured along track.
- The physical graph's 1,267 cycles include real yard geometry — triangles, crossovers,
  parallel lines. **Redundancy read on the physical graph overstates alternatives**; use the
  places view's 498 (V2-05).
- 611 sections are shorter than the straight line between their station points, 6 by more than
  0.2 km; `track_lon`/`track_lat` publish where the station meets its track (V2-12).
- `zone_code` is empty. There is no open source for railway zones (V2-14).
- Gauge is unknown for 1.1% of km, electrification for 3.1% (V2-16).

**Definitional**
- "Served network" means sections on the shortest path between a train's consecutive stops. A
  route no train's path uses counts as unserved even where trains could divert over it. 177
  cut-point differences against v1.4.1 come from this definition alone (V2-22). Severance
  statements must carry the view they were measured on.

**Scope**
- Supported: network representation, structure, connectivity, accessibility, criticality,
  redundancy, resilience, hypothetical scenario evaluation.
- Not supported, and not negotiable by more analysis on this data: real-time congestion,
  capacity saturation, actual delays, headway, passenger or freight demand, formal new-line
  feasibility, cost–benefit analysis, engineering or land feasibility, automated new-line
  recommendation. Scenario evaluation is framed as evaluation; it does not tell Indian Railways
  where to build (D-034, D-058).

---

## 5. The bad side — what is genuinely wrong, weak or unfinished

This section exists so that no reviewer finds something we had not already said.

**1. The headline criticality numbers are v1.4 numbers and have not been re-run.**
E-709 (severance criticality), E-710 (degree distribution) and E-711 (conclusion robustness)
all ran on v1.4. The figures in the paper outline — 283 corridors, 11.9% of sections with no
alternative — are **v1.4 results and must not be quoted as v2.0 results**. What v2.0 measures
directly is 1,773 single-route sections, about 17.5% of the main network's km in the places
view, of which 177 would strand 20 or more stations and 10 would strand 100 or more. The two
sets of numbers are not comparable, and the re-runs are still placeholders
(`04_analysis_modules/E-718…E-720`).

**2. Two of the project's own conclusions did not survive their construction choices.**
F-025 records that two E-709 conclusions fail when the construction choices behind them are
varied. The near-tree fragility result (F-020, F-029) comes from the degree sequence, not from
geography, and the community-count result is not robust across methods (F-014). Three of the
project's more quotable claims are therefore conditional, and one earlier published caveat had
already drifted from its own measurement (F-023).

**3. The strongest independent benchmark is the one we do worst on.**
On the 423-pair benchmark, v2.0-open puts **50.8%** within 5% — against v1.4.1's 48.2%. Both
are poor. The improvement is 2.6 points. Every other accuracy measure improved far more, which
suggests the benchmark is measuring something the other checks do not, and we have not
explained it.

**4. v2.0 found real defects in v1.4.1, and they are still open.**
Seven stations in v1.4.1 carry shortcuts far shorter than the track: BNHL–BAHI at 1.5 km
against 147 km, COB–DWT at 0.1 against 10.1, HWH–BBDB straight across the Hooghly, and others
(V2-23). They are open for the Tier 1 audit (A2), which means **every analysis still resting on
v1.4 inherits them**, including the criticality results in point 1.

**5. The Siliguri finding is conditional on the view, and was stated unconditionally.**
F-046: the result holds for the network trains actually use, not for all track OSM maps. On the
full graph the Barsoi–Makuria section is not single-route, because OSM includes the
Araria–Thakurganj line that no 2017 train used. Stated as "485 stations cut off", it is true
only with "on the lines trains used in 2017" attached.

**6. No single graph is multi-source.**
v1.4 is Esri-only; v2.0-open is OSM-only. We never integrated two infrastructure sources into
one graph — we built two and compared them. The comparison is genuine validation and is the
project's main methodological strength, but the shipped artifact still rests on one source, and
a disagreement between the two is resolved by choosing, not by merging.

**7. The 2024 data problem is unresolved, not solved.**
The IIT Kharagpur RSTGCN 2024 timetable has no stated licence (V2-19). The decision to ship
2017 keeps the release clean, but it means the public dataset **cannot support
traffic-weighted criticality** — the single most useful weighting for a vulnerability tool.
"Trains per day dependent on a corridor" is a lower bound until that is fixed.

**8. The documentation registers have integrity defects.**
`docs/FINDINGS.md` reuses IDs: **F-021 to F-029 and F-040 to F-046 each appear twice**, with
different content. A citation of "F-023" is ambiguous. `docs/LIMITATIONS.md` was last updated
2026-10-03 and still reports v1.0-era figures (spine shortcutting on 1,741 of 10,167 pairs,
speed coverage 49.8%, `state` at 46%) that no version since v1.2 matches — which is why it is
superseded by this document. Both are traceability failures in a project whose main claim is
traceability.

**9. The lineage is documented but not committed.**
`git status` fails in the working copy because git-lfs is not installed, and the last commit
predates all of the v1.3 → v2.0 work. The history in this document and the registers is the
real record; the git history is not. Deletions in this repo are not recoverable from git.

**10. The base-version choice is still open.**
Whether the product is built on v2.0-open or on v1.4.1 has not been decided (G-C). v2.0-open is
the recommendation — it is open, more accurate on every measure but the 423-pair benchmark, and
has no licence wall — but until it is decided, the downstream design has two possible
foundations.

**11. Sensitivity testing is one-at-a-time.**
Full factorial over the construction factors is roughly 17,000 cells and infeasible, so
higher-order interactions between construction choices are unexplored.

**12. Audits are samples, not censuses.**
The manual audit is a stratified sample of around 200 sections, plus 32 stations and 13 trains
hand-checked for v2.0. Accuracy is reported per stratum, not as a single global truth.

---

## 6. Open items

| Item | Owner | Blocking? |
|---|---|---|
| A2 — Tier 1 audit of v1.4.1, including the 7 shortcut defects (V2-23) | Bhuvanesh | no |
| G-C — choose v2.0-open or v1.4.1 as the product base | Bhuvanesh | **yes, for the product** |
| Re-run criticality, degree and robustness on v2.0 (E-718…E-720) | — | yes, for any v2.0 claim |
| Permission for the 2024 timetable, to add trains per day | Bhuvanesh | no |
| Public release and DOI | Bhuvanesh | deferred by D-069 |
| Fix the duplicate IDs in `docs/FINDINGS.md` | — | no |
| Build the corridor vulnerability tool (`05_product/`) | — | — |

---

## 7. Repository layout after the 2026-10-21 cleanup

```
Rail-Intell/
├─ docs/                      registers and reference: DECISIONS, FINDINGS,
│                             EXPERIMENTS, V2_ISSUES, TIMELINE (this file),
│                             dictionaries, SCOPE, STABILITY, LITERATURE
├─ external_data/             open inputs: OSM extracts, Wikidata, datameet,
│                             data.gov.in timetables  (2.0 GB, not in git)
├─ reference_data/            published statistics used for validation
├─ 01_data_engineering/       source cleaning and the legacy v1 graph
├─ 02_graph_inputs/           the graph-input pipeline and its dataset
├─ 03_graph_construction/     railgraph/, experiments/, graph_v1_4 (frozen),
│                             graph_v1_4_1, graph_v2_0_open, release/,
│                             service_layer_v1_4, _v1_4_1, _v2_0_open
├─ 04_analysis_modules/       E-700…E-714 (v1.4-era), E-718…E-720 (v2.0 re-runs, empty)
├─ 05_product/                api/, web/  — the corridor vulnerability tool (empty)
├─ publication/               figures, evidence, reports
├─ tests/                     82 tests; the release contract
└─ _archive/                  graph_versions/ (v1, v1.1, v1.2, v1.3),
                              service_layers/, docs_superseded/, context/
```

Removed in the cleanup, as rebuildable intermediates: `graph_v1_3/_stages/` (19 stage
parquets and the stage log), `experiments/cache/`, `__pycache__`. Nothing in
`graph_v2_0_open/work/` was removed — the tests read it.

`_archive/` is kept on disk and excluded from git. Nothing was deleted from it; the prior
versions remain complete apart from their rebuildable stage files.

---

*Last updated 2026-10-21. Supersedes `CHANGELOG.md`, `docs/PROGRESS.md`,
`docs/LIMITATIONS.md`, `docs/VALIDATION_REPORT.md`, `docs/GRAPH_HANDOFF.md` and
`docs/GRAPH_V2_ROADMAP.md`.*
