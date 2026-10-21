# Rail-Intel — the whole project, end to end

Date: 2026-10-15 · The orientation document. Read this first; everything else is detail.
Scope and deliverables: `docs/SCOPE.md`. What the data supports: `graph_v1_4/FITNESS.md`.

---

## The project in one paragraph

Every published graph of the Indian railway network is built from timetables, so it is a
picture of the *train service*, not of the *railway*. We built the railway instead: 9,095
stations and junctions joined by 9,759 real track sections, 74,849.7 route kilometres,
derived from 119,446 GIS polyline segments and validated against timetables that were
deliberately never used to build it. It is 11× larger than the largest published
predecessor and the first that is physical, geolocated and attribute-carrying. It is
frozen as release v1.4, rebuilt by one command, protected by nine gates and 30 regression
tests, and shipped with an explicit statement of which of its own conclusions can be
trusted. Using only the conclusions that survive that test, it independently rediscovered
India's most-discussed rail chokepoint and correctly predicted the blast radius of a real
landslide.

---

## 1. Why a physical graph

The three usual complaints about prior work all follow from one choice of source:

| | Sen et al. 2003 | Bhatia et al. 2015 | **Rail-Intel v1.4** |
|---|---|---|---|
| stations | 587 | 809 | **9,095** |
| source | printed timetable | IR site + Ixigo | national GIS polylines |
| representation | space-of-changes | service / O–D | **space-of-stations (physical)** |
| geolocated | no | no | **yes** |
| track attributes | none | none | gauge, tracks, bridges, tunnels |
| external validation possible | no | no | **yes** |

A timetable graph *must* be small (it only sees served stations), *must* be
unvalidatable (its source is its only reference), and *must* be attribute-free (a
timetable records no track). Change the source and all three follow.

The one that matters most is validation. Because our topology came from geometry and
never from timetables, 416,970 timetable stop records remain as an **external test set**.
No prior study had one.

---

## 2. What exists now

**The graph.** 9,095 nodes (8,621 coded stations + 474 operational junctions), 9,759
undirected sections, 74,849.7 route km, 18 components with **99.59% in the giant one**.
Mean degree 2.15, maximum 7.

**The service layer.** 16,703 directed station pairs with observed median running times
and **trains per day** — measured, not assumed, from 30 days of September 2024 operations.

**The release.** `03_graph_construction/graph_v1_4/`, ten files: the data (CSV, parquet,
GraphML), `OVERRIDES.csv`, the crosswalk, `gates.json`, a hashed manifest, and four
documents — `FITNESS.md`, `SCHEMA.md`, `DATASHEET.md`, `VALIDATION_v1_4.md`.

---

## 3. How it was built

```
119,446 GIS segments
      → 2,279 corridors          group segments into named lines
      → reconstructed spines     a single ordered centreline per corridor
      → tiered station matching  project 8,990 stations onto the nearest spine
      → ordering                 sort stations along the spine by measure
      → ordered chains           join consecutive stations into sections
      → JUNCTION STITCHING       ← the operator that makes it a network
      → attribute enrichment     gauge, tracks, zone, state, bridges, tunnels
```

**Junction stitching is the contribution.** Corridors fragment at junctions: each line
ends at its own copy of the junction, so chains never connect and the graph shatters.
Stitching merges those copies. The giant component goes from **59.4% to 99.6%** — the
difference between a pile of lines and a network. Kurant & Thiran went timetable →
physical by *removing* shortcuts; we go GIS → physical by *building and stitching*.

**Every manual correction goes through one channel.** 179 rows in `OVERRIDES.csv`, each
carrying its evidence, reapplied on every rebuild. A row without evidence stops the build.
Nobody edits an exported file by hand — and when someone did (me, adding a banner to the
release README), the test suite caught it the same week.

**Two layers, deliberately separate.** `make repairs` *derives* decisions from evidence —
slow, reviewable. `make v14` *applies* them, gates and freezes — a minute, deterministic.

---

## 4. How it is validated

Three references, none used in construction:

| reference | what it checks | result |
|---|---|---|
| 2024 timetable (3,892 trains) | route length of real trains | median error **0.72%**, 95.69% within 5% |
| 2017 timetable (11,113 trains) | same, different vintage | median error 1.73% |
| IIT KGP IRN distances (8,873 pairs) | consecutive-stop distance | 82.68% within 5% |

Plus **nine release gates** that fail the build: no edge far below its own straight line,
every edge has a length, referential integrity, components not worse, giant component
≥99%, 2024 route accuracy, the independent reference held, ≤2 unroutable trains, off-spine
detour within budget.

Plus **30 regression tests** (`make test`) asserting counts, schema, gate thresholds,
manifest hashes, resolver behaviour on known renames, and every published finding.

---

## 5. What is proven, and what is not

This is the part that took longest to get right, and it is the project's real
contribution.

**The nesting result (D-055).** Repairs to v1.3 removed 207 false cut points and created
*none*: all 1,173 cut points and all 1,256 bridges in v1.4 were already in v1.3. That is
mechanism, not luck — 129 of 137 overrides *add* an edge, and adding an edge can only
destroy a cut point. So **"this station is a cut point" is a claim that survives further
repair.** Betweenness is the opposite: 15 of its top 50 moved under one round.

That asymmetry is the certification. The release supports one class of claim and
explicitly not another, and the line between them was measured rather than guessed.

**The robustness sweep (E-711).** Twelve cells over release version, duplicate
contraction and the classification threshold. Four conclusions robust, one conditional,
**two withdrawn as point figures.** The Lumding corridor's severed count — 84 stations —
is identical in all twelve cells. The "11.9% of sections have no alternative route"
figure is not: it ranges 11.4–14.9%, so it is now stated directionally.

**The theory check (E-710).** The project claimed the degree distribution is exponential.
Tested: over the full support an exponential is *rejected* (χ² = 15,809 on 5 dof) — the
distribution is a spike at degree 2, because 81.6% of stations are intermediate stops.
But among **junctions (k ≥ 3) it is exponential and cannot be rejected** (λ = 1.270,
χ² = 2.63 on 3 dof, p = 0.45), while a power law is rejected. Kurant & Thiran's
prediction holds, located where it has content. Scale-free is impossible anyway: maximum
degree 7 is Barthélemy's bounded-degree signature.

---

## 6. The three findings

**1. The Siliguri corridor, found from geometry alone.** Cutting Barsoi Jn – Makuria
severs 459 stations: **all 327 the graph places in the eight Northeast states**, plus 115
in North Bengal and 17 in Bihar. That is the "Chicken's Neck", India's most-discussed rail
chokepoint — identified with no prior knowledge of its significance.

**2. A real disruption's blast radius, predicted.** The model says cutting the
Lumding–Badarpur hill section isolates 84 stations: 58 Assam, 18 Tripura, 5 Manipur,
3 Mizoram. On 6–7 July 2025 a landslide blocked exactly that section; NFR cancelled 4
trains, part-cancelled 3, rescheduled 7+, and the services cut off were Tripura, Manipur,
Mizoram and southern Assam. Predicted set = observed set.

**3. The busy network has no slack.** Of the 100 busiest sections, 90 would force a detour
over 3× if lost; median detour 291 km. The Surat group (122–131 trains/day) would force
roughly 1,007 km.

---

## 7. The honest weaknesses

Stated here rather than discovered by a reviewer:

- **The dataset cannot be published.** The base GIS source is an export of Esri India's
  Living Atlas "Railway Tracks" layer — eleven of fifteen columns match in order — whose
  terms forbid offline export (D-057). Code and method are MIT / CC BY and citable; the
  artifact is internal until it is rebuilt from the OSM extracts already held.
- **25.3% of route kilometres is a straight-line floor**, not a measurement.
- **Declared speeds are unusable.** Use observed runtimes.
- **228 stations are absent**, 39 codes unresolvable, 82 node pairs are one station held
  as two. No station ranking is defensible.
- **Passenger only.** No freight, so every load figure is a lower bound. Suburban services
  are under-recorded, so 1,312 sections read zero where zero means *unmeasured*.
- **No capacity, signalling or turn restrictions**, and the graph is undirected.
- **Single-rater validation audit** — a second rater was never available.

---

## 8. Where everything lives

| path | what |
|---|---|
| `03_graph_construction/graph_v1_4/` | **the release.** Start at `README.md`, then `FITNESS.md` |
| `03_graph_construction/railgraph/release.py` | **the only supported entry point** |
| `03_graph_construction/experiments/` | 16 build experiments, E-001 … E-708 |
| `04_analysis_modules/` | 12 analysis modules, E-700 … E-712 |
| `tests/` + `docs/STABILITY.md` | the contract and its 30 tests |
| `docs/SCOPE.md` | objectives, exclusions, deliverables — **locked** |
| `docs/DECISIONS.md` | 57 ADRs, each with an experiment ID and its reversibility |
| `docs/EXPERIMENTS.md`, `docs/FINDINGS.md`, `docs/PROGRESS.md` | the registries |
| `docs/LITERATURE.md`, `docs/PAPER_OUTLINE.md` | the write-up apparatus |
| `publication/SOURCE_LICENCE_INVENTORY.md` | every input traced; §8 is the licence verdict |
| `external_data/` | open inputs, pinned by commit and hash — the R1 rebuild's raw material |

## 9. Using it

```python
import sys; sys.path.insert(0, "03_graph_construction")
from railgraph.release import load_graph, load_service, load_resolver, release_info

G    = load_graph()        # 9,095 stations, 9,759 sections
svc  = load_service()      # 16,703 directed pairs, with trains_per_day
code = load_resolver()     # code("DDU") -> "MGS";  code("QLN") -> None
release_info()             # version, gate results, the caveats
```

Never read the CSVs directly and never re-run the repairs to get a graph. Always resolve
station codes through `load_resolver()` — current railway data uses codes the graph
predates, and joining without it silently drops those stops.

| command | what it does |
|---|---|
| `make v14` | rebuild, gate and freeze the release (~1 min) |
| `make test` | the 30-test contract |
| `make v14check` | prove the rebuild reproduces |
| `make sever` | severance criticality (E-709) |
| `make degreefit` / `make robustness` | E-710 / E-711 |
| `make schema` | regenerate `SCHEMA.md` from the shipped files |

## 10. What is next

**Now:** the pitch (D7), then the corridor vulnerability tool (D8) over this release,
using robust-class metrics only.

**Roadmap, not in scope:** R1 rebuild from OSM for an openly licensable dataset · R2
adjudicate 823 deferred lengths for absolute kilometres · R3 merge duplicate nodes for a
station ranking · R4 service-space projection to reproduce Sen and Bhatia.

**The rule that keeps this stable (D-055):** v1.4 is amended only when an analysis result
is demonstrably wrong *because of* the graph, on a named reproducible case. Finding a new
defect is not grounds — defects are recorded as properties, not as backlog. Any amendment
is a new release, never an edit in place.
