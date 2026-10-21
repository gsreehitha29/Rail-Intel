# Phase 3 — Graph Construction Roadmap

> **Author:** Bhuvanesh (Data Engineering & Provenance), as a reference
> implementation and validation harness for Sreehitha's Phase 3.
> **Date:** 2026-10-03
> **Status:** proposed — not yet started
> **Reads:** `02_graph_inputs/graph_dataset/README.md`, `docs/GRAPH_HANDOFF_V2.md` §4
> **Target:** graph v1, frozen, versioned, publishable, with the evidence trail a
> reviewer will ask for.

## 0. Why this document exists

Phase 3 is the riskiest stage of the capstone, for a reason that is not about
code difficulty. The graph is the primary research artifact; every downstream
claim inherits its construction choices. If those choices are not measured,
documented and shown to be non-arbitrary, the four analysis modules produce
numbers nobody can defend — including us, six months from now, in review.

So this roadmap is organised around a single principle:

> **Every construction choice becomes a parameter, every parameter gets measured
> against downstream conclusions, and the measurement is the contribution.**

That principle is also what makes the work publishable rather than merely done.
§2 explains why, against the literature.

### A note on ownership

Phase 3 belongs to Sreehitha. What this roadmap proposes is a **reference
implementation plus a validation harness**: a working builder she can own,
extend or replace, and an independent test battery she can run against her own
build to see whether it reproduces the invariants. The deliverables are
structured so that `g03`–`g05` (metrics, validation, sensitivity) are useful
regardless of who writes `g01`–`g02`. Agree this split with her before any code
is written.

---

## 1. What the literature says, and where we actually stand

Nine sources establish the position. Full annotated bibliography:
`docs/LITERATURE.md` (to be created in `g00`).

### 1.1 Prior work on the Indian railway network specifically

| Study | Graph built | Size | Source | Representation |
|---|---|---|---|---|
| Sen et al. 2003 (*Phys. Rev. E*) | stations linked if a train stops at both | **587 stations**, 579 trains | printed timetable | space-of-changes (P-space) |
| Ghosh et al. (*statistical analysis of the IRN*) | same family | comparable | timetable | P-space |
| Bhatia et al. 2015 (*PLOS ONE*) | O–D network weighted by train counts | **809 stations** (752 in giant component), 7,066 trains | IR website + Ixigo | service network |

Three things follow, and they are the whole argument for this project.

1. **Every published graph of Indian Railways is built from timetables.** None is
   built from infrastructure geometry. The "network" in all of them is a service
   adjacency structure, not physical track.
2. **All of them are an order of magnitude smaller.** Our shipped node table is
   9,095 — **15.5× Sen et al.** and **11.2× Bhatia et al.** — and it is
   geolocated and infrastructure-attributed, which none of theirs are.
3. **None of them could cross-validate.** With one source you can only check a
   graph against itself. We have two independent sources (119,446 GIS segments;
   416,970 timetable stop records), and the timetable was never used to build the
   physical graph — so it is available as an external test set. That is a
   capability the prior art structurally does not have.

Bhatia et al. is the most important one to read closely: it is the closest
competitor for Module 3, it uses percolation with State-of-Critical-Functionality
`SCF = FF/TF`, it finds targeted removal of 25% of stations causes near-total
collapse versus 95% for random, and it ranks recovery sequences by centrality.
It also states plainly that it does not distinguish physical damage from service
disruption. **We can.** That distinction is Module 3's angle.

### 1.2 The methodological ancestor

**Kurant & Thiran 2006, "Trainspotting"** (arXiv physics/0510151) is the paper
this project is closest to in spirit, and it must be cited as prior art for the
layering we already use. It defines three representations:

- **space-of-changes** — stations on the same vehicle form a clique; distance =
  number of transfers. (This is Sen et al.'s graph.)
- **space-of-stops** — consecutive *stops* are linked. Introduces **shortcuts**:
  edges that do not exist as infrastructure, because express trains skip stations.
- **space-of-stations** — only physically adjacent stations are linked. *"This
  graph reflects the topology of the real-life infrastructure."*

Two findings we must engage with:

- Shortcuts are not a minor nuisance. On their EU dataset, including them
  collapsed the network diameter from **184 to 48**. Our express-skip artifact
  (handoff §4.4, the `service_direct` 30/67 alternation on corridor C00786) is
  the same phenomenon, and `service_load` path projection is our fix for it.
- In space-of-stations, rail **degree distributions are exponential, not
  scale-free**. This is a falsifiable prediction about our graph and belongs in
  the validation battery (§5, V2). If we fit a power law, we have built it wrong.

Critically, **Kurant & Thiran go in the opposite direction from us**: timetable →
physical, by *detecting and removing* shortcuts. We go GIS → physical, by
*building station chains and stitching them at junctions*, and we then use the
timetable as an independent check rather than as the source. That inversion is
our methodological contribution, and it is only available to someone who has
done the data engineering Phase 1–2 did.

### 1.3 The construction-method literature

| Source | Contribution | What we take from it |
|---|---|---|
| **Karduni et al. 2016**, *Scientific Data* — "A protocol to convert spatial polyline data to network formats" | 5-step polyline→network protocol; nodes only at true intersections, not at every vertex; shipped for 80 cities | The **publication template**: a protocol + a dataset is a legitimate, citable contribution. Also validates our core premise that segment vertices ≠ graph nodes |
| **Boeing 2025**, *Transactions in GIS* — "Topological Graph Simplification Solutions to the Street Intersection Miscount Problem" | Edge simplification (remove interstitial nodes) + geometric vs **topological** node consolidation; unsimplified graphs overcount intersections by ~14% median | Our `is_dissolvable` degree-2 question is exactly his edge-simplification problem. His **topological** consolidation (merge by network distance, not Euclidean) is the right method for our 249 co-located pairs. And his **validation protocol** — stratified manual review reporting TP/TN/FP/FN rates, 98% TP / 87% TN / 13% FN — is the template for our §5 V5 audit |
| **UIC RailTopoModel / IRS 30100** (2016), basis of railML 3 | Standard conceptual model for railway topology; aggregation levels nano / micro / meso / **macro** | Vocabulary alignment. Our station-level graph sits at **meso–macro** (operation points and corridors). Saying so positions the artifact against an international standard instead of inventing terms |
| **MatchingLand** 2017, *Scientific Data* | A testbed for assessing geospatial matching methods | Precedent for publishing matching evaluation as a first-class result — which is what our 1,555 tiered junction matches with recorded spatial gaps are |

### 1.4 The analysis-side literature

- **Barthélemy 2011**, *Physics Reports* 499:1–101, "Spatial Networks" — the
  reference review. Spatially embedded networks have bounded degree (ours: max 7,
  83% at degree 2) and betweenness structured by geometry, not by hubs. Cite this
  so our degree distribution is reported as the *expected signature* rather than
  defended as a non-defect.
- **Resilience**: Bhatia et al. 2015 for the Indian case; the railway-resilience
  review in *Transport Reviews* (2020) for framing; Schneider's **R** index and
  robustness-envelope work for the protocol. Module 3 must report attack
  sequences (random / degree / betweenness / load) against a null baseline, not a
  single collapse curve.
- **Accessibility**: circuity — network distance ÷ great-circle — is the standard,
  well-established way to show a region is structurally poorly served, with a
  direct precedent in *Circuity in China's high-speed-rail network* (JTG 2019).
  Our node coordinates plus `length_km` give it directly. This keeps Module 2
  inside scope without population data.
- **Communities**: modularity maximisation has a known **resolution limit**, so
  Module 1 must run at least two methods (Louvain/Leiden **and** Infomap) and
  validate against `zone_code` as an independent label, per handoff §4.9 — never
  cluster *on* zone.

### 1.5 The one paper that is closest to our novelty claim

**Palk et al. 2026**, *Networks* (Wiley), "Robustness Assessment of Public
Transport Networks in Various Graph Representations: Systematic Review, Decision
Support, and Case Study" — doi:10.1002/net.70021.

This asks how the choice of **representation** (L-space / P-space / etc.) changes
robustness conclusions, and offers decision support for picking one. It is both
independent support for our §4.5 finding and the nearest thing to a competitor.

**Action item (blocking for the paper, not for the code): obtain the full text
via institutional access.** It is paywalled and 403s to automated retrieval. We
need to read it before claiming novelty, and we need to position against it.

Our distinction, as far as the searches reach: Palk et al. vary the
**representation** of an already-constructed network. We vary the
**construction** — tolerance, stitching, node model, dissolution, matching
confidence — which is upstream of representation and, on current evidence,
unexamined. That is where §6 goes.

### 1.6 The gap, stated for the paper

> Published graphs of the Indian railway network are derived from timetables, are
> an order of magnitude smaller than the station population, carry no geographic
> or infrastructure attributes, and cannot be externally validated because the
> timetable is both their source and their only available reference. Meanwhile
> the construction literature for spatial networks has concentrated on street
> networks, where the standard problems are over-counting and over-segmentation.
> Segment-oriented national rail GIS presents the opposite failure mode: station
> chains that fail to meet, because corridors terminate at junctions that carry
> no station. No published work quantifies how sensitive downstream criticality,
> accessibility and resilience conclusions are to the construction choices that
> resolve it.

Three claims follow, and they are what we aim to publish:

- **C1 (artifact)** — a 9,095-node geolocated, infrastructure-attributed,
  provenance-carrying **physical** station graph of Indian Railways, with a
  derived service layer, released FAIR with a datasheet.
- **C2 (method)** — a reproducible GIS→corridor→ordered-chain→**junction-stitched**
  transformation, with junction stitching as the named operator that resolves
  rail-specific chain fragmentation (59.4% → 99.6% giant component), and with the
  timetable retained as an independent validation set rather than consumed as input.
- **C3 (evaluation)** — cross-source external validation (94% agreement, 0
  cross-component contradictions) plus a **construction-choice sensitivity
  study** that reports which downstream conclusions survive the choices and which
  are artifacts of them.

C3 is the scientific core. C1 and C2 are the enabling work.

### 1.7 Venue

| Venue | Fits | Note |
|---|---|---|
| *Scientific Data* (data descriptor) | C1 + C2 | Direct precedent: Karduni 2016, MatchingLand 2017. Needs a DOI'd deposit and a datasheet |
| *Applied Network Science* / *EPJ Data Science* | C2 + C3 | Most realistic for a capstone; takes the method + sensitivity framing well |
| *Transactions in GIS* | C2 + C3 | Where Boeing 2025 landed; the right audience for construction-method work |
| *Journal of Transport Geography* | C3 + modules | Needs a stronger transport-geography interpretation, not just structure |

Decide by end of `g02`, because it changes how much of the sensitivity study is
headline versus appendix. Default assumption: **Applied Network Science**, with
the dataset deposited separately so C1 is citable on its own.

---

## 2. Design principles for the build

These are consequences of §1, not preferences.

1. **One graph, many views.** Views are parameterised functions over the single
   shipped edge list, never separate exports. Already decided in handoff §4.5;
   this roadmap makes it an API constraint, because it is what makes §6 cheap.
2. **No default weight.** Every metric call names its weight explicitly from a
   registry (`length_km`, `travel_time_proxy`, `service_impedance`, `unit`).
   Blueprint §24. A function that silently defaults to distance is a bug.
3. **Construction choices are parameters, not constants.** Anything in the
   handoff §4.8 decision register is a keyword argument with the shipped value as
   its default. If it is hardcoded, §6 cannot run.
4. **Every number in the paper is produced by a script.** No typed figures.
   *(This is not hypothetical: `docs/GRAPH_HANDOFF_V2.md` §4.3 and §4.7 currently
   carry pre-`s09` figures — 397/98 parallel pairs and 1,341/1,432
   articulation-points/bridges — that the shipped `QA_REPORT.txt` contradicts
   with 581/124 and 1,338/1,412. That is exactly the failure mode a `make tables`
   target prevents, and fixing it is a `g00` task.)*
5. **Provenance survives every transformation.** A node or edge that loses its
   `corridor_id`, confidence or offset on the way into the graph object has lost
   the thing that makes the artifact publishable.
6. **Fail loudly on invariant violation.** The builder asserts the shipped
   invariants (9,095 / 9,689 / 99.6% / 72,201 km) at load time. `s10` set this
   precedent; keep it.
7. **Frozen means frozen.** Phase 4 starts against a hashed, versioned graph.
   Post-freeze changes become v1.1 with a migration note, never an edit in place.

---

## 3. Stage plan

Numbered `g00`–`g07` to continue the `s01`–`s10` convention. All code lands in
`03_graph_construction/`.

```
03_graph_construction/
├── railgraph/                 ← importable package, not notebooks
│   ├── __init__.py
│   ├── build.py               g01  loader + view construction
│   ├── views.py               g01  parameterised views
│   ├── weights.py             g01  named weight registry
│   ├── io.py                  g02  GraphML / parquet / GeoJSON + manifest
│   ├── metrics.py             g03  the API the Phase 4 modules call
│   ├── validate.py            g04  invariant + plausibility + cross-source battery
│   ├── baselines.py           g04  prior-art reproduction + null models
│   ├── sensitivity.py         g05  construction-choice sweep
│   └── viz.py                 g06  geographic layout + audit maps
├── experiments/               machine-readable results, one dir per run id
├── graph_v1/                  the frozen release (g07)
├── notebooks/                 exploration only — never the source of a result
└── Makefile                   build · validate · sweep · tables · figures · freeze
```

### g00 — Documentation apparatus and literature scaffold  *(do this first)*

Before any graph code. Publication-grade documentation written retrospectively is
always thin, and the Phase 2 decision register already proved the opposite works.

Create:

| File | Purpose |
|---|---|
| `docs/LITERATURE.md` | Annotated bibliography + the §1.6 gap table. Every entry: full citation, what it did, what we take, how we differ |
| `docs/DECISIONS.md` | ADR register, `D-001…`. Seeded by migrating handoff §4.8's 15 decisions into the format |
| `docs/FINDINGS.md` | Numbered findings `F-001…` that are not decisions but will be cited |
| `docs/EXPERIMENTS.md` | Registry `E-001…`: config hash → result artifact → which claim it supports |
| `docs/PAPER_OUTLINE.md` | Claim → experiment ID → figure/table. The thing that makes month 7 painless |
| `docs/LIMITATIONS.md` | Consolidated and honest. Seeded from handoff §7 and the dataset README's five known limits |

ADR format — keep it this tight:

```markdown
> Note: an earlier draft pasted ADR `D-016` here mid-stage-plan. The decision
> register is `docs/DECISIONS.md`; `D-016` is resolved there (parquet working
> format, GraphML citable primary).
Date: 2026-10-xx · Status: accepted · Owner: Sreehitha · Reversible: yes (one line)
Question: ...
Options: (a) retain all 115 (b) dissolve by path contraction (c) dissolve and keep a provenance column
Evidence: E-004. Dissolving changes nodes 9,095→8,980, edges 9,689→9,574, betweenness
         top-50 overlap 0.96 (Kendall tau 0.94), mean shortest path +0.3%.
Decision: (c) ...
Why not (a)/(b): ...
Precedent: Boeing 2025 edge simplification; Porta et al. primal-graph smoothing.
```

Two rules that make this work: **no decision is accepted without an experiment
ID**, and **every ADR states its reversibility**. The handoff register already
follows both implicitly; make it explicit.

Also in `g00`: fix the stale §4.3/§4.7 figures, and pin the environment
(`requirements.txt` with exact versions + Python version — the pipeline runs on
Python 3.10, and nothing downstream should float).

**Done when:** six docs exist, the 15 Phase 2 decisions are migrated, the stale
figures are corrected, the environment is pinned.

### g01 — Builder, views, weights

`railgraph.build.load_graph(...)` → `networkx.Graph`, with:

- a strict loader asserting the shipped invariants, failing loudly on mismatch;
- every node and edge attribute carried through, provenance included;
- views as parameters, not files:
  `view ∈ {topology, core_v2, core_v4}`, `dissolve_degree2`, `prune_degree1`,
  `merge_colocated`, `gauge_constrained`, `min_match_confidence`,
  `parallel_policy ∈ {shortest, mean, multigraph}`;
- a **rebuild path** from `station_sequences.csv` so `offset_km` tolerance and
  `stitch_junctions` are live parameters rather than baked into `s09`'s output.
  This is the one piece of real engineering in `g01`: `s09`'s construction logic
  has to be callable with those two knobs. Without it §6 is impossible.
- `weights.py`: named weight functions returning an edge→float callable.
  `travel_time_proxy` must handle the 49% speed nullity explicitly — document the
  imputation or restrict the metric, never silently fill.

Why NetworkX: 9,095 nodes is small; correctness and readability beat speed, and
the Phase 4 modules will be written against it. Keep `igraph`/`graph-tool` as an
option behind the same API if exact weighted betweenness across the §6 sweep
turns out too slow (§7 risk).

**Done when:** `load_graph()` reproduces 9,095 / 9,689 / 99.6% / 72,201 km
exactly; every §4.8 decision is reachable as a parameter; a round-trip through
each view is tested.

### g02 — Storage, export, versioning, and the four open decisions

Exports, per blueprint §13 and FAIR:

| Format | For | Notes |
|---|---|---|
| GraphML | graph-native interchange | typed attributes; the citable primary |
| parquet (`nodes`/`edges`) | analysis | fastest path for Phase 4 |
| GeoJSON (edges + nodes) | maps, QGIS | WGS84, stated explicitly |
| `graph_v1.manifest.json` | reproducibility | content hashes of every input and output, library versions, git SHA, build timestamp, parameter set, DOI slot |

Settle the four open questions from handoff §6 here — **each as an ADR with a
measurement, not a preference**: storage format, the 115 dissolvable nodes,
`core_v2` vs `core_v4` as default attributed view, and whether to recompute the
spine-shortcut-affected lengths. Add a fifth: the remaining 18 components — real
branch lines or residual data gaps? Investigate before dropping (handoff §6.4).

On shortcutting specifically: it affects 17.1% of consecutive pairs with median
5% shortfall, which is a **systematic downward bias on distance-weighted
results** and harmless for topology. The honest options are recompute from raw
corridor geometry, or accept and quantify the bias by reporting every
distance-weighted result with a sensitivity band. §6 can decide this empirically
— measure whether the affected edges change any conclusion.

**Done when:** all four exports round-trip losslessly, the manifest reproduces on
a clean run, five ADRs are accepted.

### g03 — Metrics infrastructure

The API Phase 4 calls. Pure functions, keyed and cached on
`(graph_hash, weight_name, params)`, each returning a tidy DataFrame with its
config attached. No notebook-local state, no module-level mutable graph.

| Group | Functions |
|---|---|
| Local | degree, strength (`service_load`, `n_tracks`), clustering |
| Paths | shortest paths, eccentricity, mean path length, **circuity** (network ÷ great-circle) |
| Centrality | betweenness (weighted + load-weighted; exact and sampled, with a documented convergence check), closeness, PageRank, edge betweenness |
| Cuts | articulation points, bridges, 2-edge/2-vertex components, meshedness / independent cycles |
| Communities | Louvain/Leiden + Infomap, with NMI/ARI against `zone_code` |
| Service | space-P derived on demand (never materialised — ~16M rows), transfer counts, frequency- and runtime-weighted paths |

Two requirements that make this research code rather than scratch code: an
**exact baseline** (precomputed once on the frozen default graph, checked into
`experiments/`) so any later refactor is verifiable; and **approximation error
reported, never hidden** — if betweenness is sampled, the sample size and its
measured rank-correlation against the exact run are part of the output.

**Done when:** every function reproduces the QA report's baselines (1,338
articulation points, 1,412 bridges, 612 cycles, degree mean 2.13 / max 7), and
sampled betweenness has a documented convergence curve.

### g04 — Validation battery  *(the scientific spine)*

Six layers. `validate.py` runs them all and writes `docs/VALIDATION_v1.md`.

**V1 — Internal invariants.** Re-derive everything `s10` checks, from the graph
object rather than from the CSVs, plus exact match on the `degree`,
`component_id` and `in_giant_component` columns. Fails loudly.

**V2 — Structural plausibility against theory.**
- Degree distribution: fit exponential vs power law, report likelihood ratio and
  KS. **Kurant & Thiran predict exponential for space-of-stations rail.**
  Confirming it is positive evidence the construction is sound; a power-law fit
  is a red flag to chase, not a result to report.
- Bounded degree and geometrically structured betweenness, per Barthélemy 2011.
- Meshedness / independent cycles against planar-graph expectations.
- Route-km: our 71,759 geodesic km vs the Year Book 2024–25's **69,439 route km**
  is **+3.3%**, and the excess should be explainable by parallel chords and loops
  counted as separate corridors. Decompose it and state the explanation — do not
  just note the closeness.

**V3 — Cross-source external validation.** The strongest claim available, so
formalise it properly. Treat timetable adjacency as the reference set and report
precision/recall/F1 of physical edges against it, with the 3-hop skip-stop
allowance stated as the matching rule, plus the headline: **0 service pairs whose
endpoints fall in different physical components** from 10,193 adjacencies built
from 416,970 stop records. Report the agreement **stratified** — by `any_stitch`,
by match confidence, by `offset_km` band — because an aggregate 94% hides whether
the stitched edges (the novel operator) are the weak ones. This stratification is
the single most important number in the paper: it is the direct test of C2.

**V4 — Prior-art reproduction.** Rebuild **Sen et al.'s P-space graph** and
**Bhatia et al.'s service network** *from our data*, reproduce their published
statistics, then show where our physical graph diverges and why.

| Target | Their published value | What we check |
|---|---|---|
| Sen: mean distance | ≈ 2.16 | Reproduce on a comparably sized P-space subgraph |
| Sen: clustering | ≈ 0.69 (vs 0.113 random) | Reproduce; then show physical-layer clustering is *far* lower — P-space cliques are an artifact of the representation, not a property of the railway |
| Sen: degree decay | exp(−0.0085k) | Compare against our space-of-stations distribution |
| Bhatia: giant component | 752 of 809 | Reproduce; compare to our 9,058 of 9,095 |
| Bhatia: targeted collapse | ~25% removal | Re-run on the physical graph — expect a *different* answer, because physical and service fragility are not the same thing |

This converts "prior work was small and service-based" from rhetoric into
measurement, and it is cheap: both are derivable from `service_edges.csv` and the
cleaned schedules we already have.

**V5 — Stratified ground-truth audit.** Boeing's protocol, adapted. Sample ~200
edges stratified by `any_stitch` × match confidence × `offset_km` band, verify
each against an independent reference (IR route maps, zonal timetables, OSM rail),
and report TP/FP/FN **per stratum** with confidence intervals. Target the known
weak spots deliberately: the 40 rejected name-spatial conflicts, the 88 ambiguous
junction coordinates, the 207 junctions whose incident corridors disagree by >1 km,
the 635 placements over 1.5 km. Two people label independently; report
inter-rater agreement. A single global accuracy number is not worth having.

**V6 — Null models.** Degree-preserving rewiring and a distance-constrained
spatial null, so "the network is ~94% tree-like" and "14.6% of edges are bridges"
become claims *against a baseline* rather than bare figures. Also the sanity
check already noted in handoff §4.7 — that the worst bridges the graph finds are
the Fakiragram–Kokrajhar–New Bongaigaon chain, i.e. it rediscovers the Northeast
India chokepoint unprompted — written up as a face-validity result.

**Done when:** `docs/VALIDATION_v1.md` is generated end-to-end by script, V3 is
stratified, V4 reproduces both prior studies, V5 has two-rater labels.

### g05 — Construction-choice sensitivity study  *(the novelty)*

**The question:** which downstream conclusions are robust to how the graph was
built, and which are artifacts of it?

Factors, all already parameterised by `g01`, with the shipped default **bold**:

| Factor | Levels |
|---|---|
| placement tolerance `offset_km` | 1.0, **1.5**, 2.0, 3.0, ∞ |
| junction stitching | **on**, off |
| node model | **hybrid**, station-only, junction-only |
| degree-2 dissolution | **off**, on |
| view | **topology**, core_v2, core_v4 |
| parallel policy | **shortest**, mean, multigraph |
| co-located handling | **floor 0.05 km**, merge nodes |
| min match confidence | **high+medium**, high only |
| weight | **length_km**, travel_time_proxy, unit, service_impedance |

Full factorial is ~17,000 cells and infeasible. The design:

1. **One-at-a-time sweep** around the shipped default — ~30 cells, full metric
   battery each. This is the main result table.
2. **Targeted two-factor interactions** where there is a prior reason to suspect
   one. The known case: handoff §4.1 shows stitching *removes* tolerance
   sensitivity (unstitched, the giant component swings 59.4%→92.2% across
   tolerance; stitched, 99.6%→99.7%). **That interaction is itself a publishable
   finding** — a construction operator that makes the result insensitive to a
   free parameter. Confirm it across the full battery, not just connectivity.
3. **Report elasticity, not just values.** For each (factor, conclusion) pair:
   how much does the conclusion move per unit change in the choice?

Summary statistics, chosen because they are what a reviewer will ask:

- **Top-k overlap** and **Kendall τ** of the station criticality ranking across
  cells — "do the top 50 critical stations survive the construction choices?"
- Giant-component share, independent cycles, bridge share.
- Mean shortest path and total route km (the distance-weighted results, which are
  the ones shortcutting biases).
- Percolation curves and **R** index under each attack sequence.
- Circuity distribution.

Output: a sensitivity table plus a per-conclusion verdict — **robust /
conditional / artifact**. The honest expected result is that *topological
criticality rankings are stable while distance-weighted accessibility is not*; if
so, that is a finding with direct consequences for everyone who builds one of
these graphs, and it tells Modules 2 and 3 exactly how much confidence to claim.

**Scope discipline:** the one-at-a-time battery is the deliverable. Interactions
beyond tolerance×stitching are a stretch goal. This stage is the most interesting
and will eat the schedule if allowed (§7).

**Done when:** ~30 cells computed and archived under `experiments/`, every
conclusion labelled robust/conditional/artifact, the tolerance×stitching
interaction confirmed or refuted across the battery.

### g06 — Layout, visualisation, visual QA

Geographic layout from the real coordinates — the network is spatially embedded,
so force-directed layouts would discard the most informative attribute it has.

Three products:
1. **Audit map** — edges coloured by `any_stitch`, match confidence and
   `offset_km`, so weak spots are visually inspectable. Visual QA catches classes
   of error no invariant will, and it feeds V5 sampling.
2. **Paper figures** — regenerated by `make figures`, never hand-edited.
3. **Interactive national view** for the demo (blueprint §26 item 10), built on
   the frozen export, reading the same parquet as the modules.

### g07 — Freeze and release

```
graph_v1/
├── rail_graph_v1.graphml
├── nodes.parquet · edges.parquet
├── edges.geojson · nodes.geojson
├── graph_v1.manifest.json          hashes, versions, params, git SHA
├── DATASHEET.md                    Gebru et al. format
├── VALIDATION_v1.md                g04 output
├── LIMITATIONS.md
├── CITATION.cff · LICENSE
└── README.md                       data dictionary
```

Freeze criteria — **all** must hold:
1. Manifest hashes reproduce on a clean run from raw sources.
2. V1–V4 pass; V5 complete with per-stratum numbers; V6 baselines archived.
3. Every open §6 decision has an accepted ADR.
4. Datasheet complete; FAIR check done (persistent ID, metadata, licence, provenance).
5. Deposited with a DOI (Zenodo), version tagged in git.

**Phase 4 does not start before this.** All four module READMEs already say so.

---

## 4. Documentation apparatus — the three things you asked for

### Progress
`docs/PROGRESS.md`, append-only, dated, one entry per session: what was attempted,
the numbers it produced, what changed, what it blocked or unblocked. This becomes
the methods section's raw material. `CHANGELOG.md` stays as-is for the
teammate-facing view — it is already doing its job well.

### Decisions and findings
`docs/DECISIONS.md` (ADRs `D-nnn`) and `docs/FINDINGS.md` (`F-nnn`). Two hard
rules: **no decision accepted without an experiment ID**, and **every ADR states
its reversibility**. Seed from handoff §4.8's fifteen decisions, which already
follow the spirit.

### Comparisons, evals, and the rest of what a paper needs
- `docs/EXPERIMENTS.md` — registry mapping config hash → result artifact → claim.
- `experiments/<run_id>/` — machine-readable results, config, environment, timings.
- `docs/LITERATURE.md` — annotated bibliography + gap analysis (§1).
- `docs/VALIDATION_v1.md` — generated, not written.
- `docs/LIMITATIONS.md` — consolidated.
- `docs/PAPER_OUTLINE.md` — claim → experiment → figure. Maintained from `g00`
  onward, not written at the end.
- `Makefile` — `build validate sweep tables figures freeze`. **Every number and
  figure in the paper regenerates from one command.**

---

## 5. Sequence and rough effort

| Stage | Effort | Depends on | Blocks |
|---|---|---|---|
| g00 docs scaffold | 1–2 d | — | everything (soft) |
| g01 builder + views | 3–4 d | g00 | g02–g06 |
| g02 export + 5 ADRs | 2–3 d | g01 | g07 |
| g03 metrics | 3–4 d | g01 | g04, g05, Phase 4 |
| g04 validation battery | 5–7 d | g03 | g07 |
| g05 sensitivity study | 5–8 d | g03, g04 | paper |
| g06 layout + viz | 2–3 d | g02 | demo |
| g07 freeze + release | 2 d | g02, g04 | **Phase 4** |

≈ 4–6 weeks, which fits the Month-2/3 slot in the blueprint's seven-month plan.

Parallelism: `g03` and `g04` can interleave; `g06` can run alongside `g05`. The
only hard serialisation is `g01 → g03 → {g04, g05} → g07`.

**Priority if time collapses:** g01 → g03 → g04 (V1–V4) → g07 → g05 → g06. A
frozen, validated graph with no sensitivity study is a successful capstone. A
sensitivity study on an unfrozen graph is worth nothing.

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| **`g05` eats the schedule.** It is the most interesting stage | One-at-a-time battery is the deliverable; interactions are a stretch goal. Hard stop at 8 days |
| **Ownership friction with Sreehitha's Phase 3** | Agree the split before writing code: reference implementation + harness she can run against her own build. `g03`–`g05` are useful either way |
| **Exact weighted betweenness × ~30 sweep cells × 4 weights is too slow** | Sampled betweenness with a documented convergence check; exact only on the frozen default. `igraph` behind the same API if needed |
| **Rebuilding edges with live tolerance/stitching parameters means refactoring `s09`** | Extract `s09`'s construction into a callable function; `s09` keeps producing the shipped default as one call. Do this in `g01`, not later |
| **V5 audit needs an independent reference we may not be able to get at scale** | Stratified sample of ~200, not a census. IR route maps + OSM rail are sufficient for a sample. Report CIs |
| **Palk et al. 2026 may already cover our novelty** | Obtain the full text early (§1.5). If it overlaps, C3 narrows to construction-vs-representation and C1/C2 carry the paper |
| **Spine shortcutting biases every distance-weighted result** | `g02` ADR; `g05` measures whether it changes any conclusion. Worst case, report distance-weighted results with a sensitivity band |
| **Post-freeze changes** | v1.1 with a migration note. Never edit a frozen release |

---

## 7. What this roadmap deliberately does not do

- No GNN, no embeddings, no link prediction. Blueprint §13: ML comes after the
  graph is stable, and only as a controlled graph-learning experiment.
- No congestion, capacity, delay or demand claims. Blueprint §14 and §25 — the
  data does not support them, and the sensitivity study will not change that.
- No new-line recommendations. Module 4 is scenario evaluation, framed as such.
- No repository reorganisation. The phase structure works; leave it.
- No hand-editing of `02_graph_inputs/graph_dataset/`. Change the pipeline, re-run.

---

## 8. Immediate next actions

1. **Agree the ownership split with Sreehitha** — reference implementation plus
   harness, not a takeover. Blocking.
2. **Obtain Palk et al. 2026** (doi:10.1002/net.70021) via institutional access.
   Blocking for the novelty claim, not for the code.
3. **Run `g00`** — six docs, migrate the fifteen Phase 2 ADRs, fix the stale
   §4.3/§4.7 figures, pin the environment.
4. **Confirm the venue target** with Sandeep, since it changes how much of `g05`
   is headline versus appendix.
5. Then `g01`.

---

## References

Barthélemy, M. (2011). Spatial networks. *Physics Reports*, 499(1–3), 1–101.

Bhatia, U., Kumar, D., Kodra, E., & Ganguly, A. R. (2015). Network science based
quantification of resilience demonstrated on the Indian Railways Network.
*PLOS ONE*, 10(11), e0141890. arXiv:1508.03542.

Boeing, G. (2025). Topological graph simplification solutions to the street
intersection miscount problem. *Transactions in GIS*. doi:10.1111/tgis.70037.
arXiv:2407.00258.

Gebru, T., et al. (2021). Datasheets for datasets. *Communications of the ACM*,
64(12), 86–92.

Karduni, A., Kermanshah, A., & Derrible, S. (2016). A protocol to convert spatial
polyline data to network formats and applications to world urban road networks.
*Scientific Data*, 3, 160046.

Kurant, M., & Thiran, P. (2006). Extraction and analysis of traffic and
topologies of transportation networks ("Trainspotting"). *Physical Review E*,
74, 036114. arXiv:physics/0510151.

Palk, M., et al. (2026). Robustness assessment of public transport networks in
various graph representations: systematic review, decision support, and case
study. *Networks*. doi:10.1002/net.70021. **[to obtain]**

Sen, P., Dasgupta, S., Chatterjee, A., Sreeram, P. A., Mukherjee, G., & Manna,
S. S. (2003). Small-world properties of the Indian railway network. *Physical
Review E*, 67, 036106. arXiv:cond-mat/0208535.

UIC (2016). *RailTopoModel — Railway infrastructure topological model*.
International Railway Standard IRS 30100. Basis of railML 3.

Wilkinson, M. D., et al. (2016). The FAIR Guiding Principles for scientific data
management and stewardship. *Scientific Data*, 3, 160018.

Zhao, P., et al. (2019). Circuity in China's high-speed-rail network. *Journal of
Transport Geography*, 77.

*Resilience in railway transport systems: a literature review* (2020).
*Transport Reviews*, 40(4).
