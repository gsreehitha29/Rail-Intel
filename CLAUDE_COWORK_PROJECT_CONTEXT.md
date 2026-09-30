# CLAUDE COWORK HANDOFF — INDIAN RAILWAY NETWORK GRAPH MAJOR PROJECT

> ## Status: 2026-09-30 — Phases 1 and 2 complete
>
> The data engineering and graph-input work described in this document as
> *proposed* has been **built, validated and shipped**. The graph-ready dataset
> is `02_graph_inputs/graph_dataset/` (9,095 nodes, 9,689 edges, 99.6% in one
> connected component), produced deterministically by
> `02_graph_inputs/pipeline/run_all.py`.
>
> Read `CHANGELOG.md` for what changed, `docs/GRAPH_HANDOFF_V2.md` §4 for the
> finalised approach and its decision register, and
> `02_graph_inputs/graph_dataset/README.md` for the data dictionary.
>
> Sections below still describe the reasoning and the constraints, which remain
> accurate and worth reading. Where a section says something is *proposed* or
> *not yet validated*, §8 and §27 record what has since changed.


## 0. PURPOSE OF THIS HANDOFF

This document is the authoritative project-context handoff for Claude Cowork.

The project is a 7-month CSE/Data Science major/capstone project by a 3-person student team. The project started as a broad Indian Railways analytics/ML idea, but after substantial data engineering and EDA it has been deliberately reframed around a central thesis:

> **The railway graph itself is the primary research artifact and differentiating contribution.**

The downstream analytics/ML are modules operating on that graph.

Claude should treat this document as project context, but MUST inspect the actual repository before modifying code, because filenames, notebook state, outputs, and implementation details in the repository are the source of truth for current implementation status.

---

# 1. PROJECT IN ONE PARAGRAPH

We are building a digital representation of the Indian railway network as a validated, station-level, geospatial, weighted and attribute-rich graph. The graph is being constructed from heterogeneous real-world railway datasets that are messy, inconsistent and not directly graph-ready: railway GIS/infrastructure segments, station master data, train schedules, train metadata, and historical/national railway statistics. The first major contribution is therefore the data-engineering and graph-construction pipeline itself: source integration → cleaning → identity resolution → corridor extraction → station-to-network matching → station ordering → station-to-station edge construction → infrastructure/service enrichment → topology validation → versioned graph dataset. Once the graph is trustworthy, it becomes the common dataset for downstream research modules covering network structure/criticality, accessibility/service connectivity, resilience/redundancy, and hypothetical network expansion. ML is optional and comes later; it is NOT the reason for the project.

---

# 2. THE PROJECT'S CENTRAL IDEA

The key conceptual shift is:

OLD framing:
    Raw data → preprocessing → graph → ML → final result

CURRENT framing:
    Heterogeneous real-world data
             ↓
    rigorous data engineering
             ↓
    validated railway graph
             ↓
    graph is the dataset / primary artifact
             ↓
    multiple analytical modules
             ↓
    optional ML

The graph is intended to be publishable/reusable as a dataset if the final version has:
- stable node identifiers
- explicit edge semantics
- reproducible construction
- spatial validation
- source/vintage/provenance information
- confidence/matching metadata
- documented aggregation rules
- validation report
- versioning

Do NOT describe the project merely as an "ML project on Indian Railways."

Do NOT claim that the project predicts congestion, train delays, capacity, or actual line construction unless appropriate operational/demand data is later added.

The defensible current language is:
- railway network representation
- network structure
- connectivity
- accessibility
- criticality
- resilience
- redundancy
- hypothetical network expansion / scenario analysis
- graph-based railway analytics

---

# 3. ORIGINAL CONCEPTUAL PROJECT

The original conceptual proposal was broader and already included:
- historical railway statistics
- railway GIS/station data
- graph construction
- degree/betweenness/closeness/PageRank
- communities
- robustness
- station feature construction
- PCA/K-Means clustering
- link prediction
- reproducible data package
- interactive analytical platform

The original proposal explicitly treats the work as a data-science/graph analytics system and does NOT intend to replace formal railway planning.

The revised graph-centric direction preserves these components but reorganises them:
- Graph construction = mandatory core
- Network structure/criticality = primary downstream module
- Accessibility/service connectivity = major candidate module
- Resilience/redundancy = major candidate module
- Expansion/what-if = extension
- ML = optional final layer

The team has ~7 months. It is intentionally acceptable to complete two downstream directions deeply rather than four superficially.

---

# 4. WHY THE GRAPH IS HARD

The core difficulty is not calculating graph metrics.

The difficult problem is converting heterogeneous real-world railway information into a defensible graph.

The raw railway GIS data is segment-oriented. It is NOT already a station-to-station edge list.

A conceptual transformation is:

    raw GIS segments
          ↓
    conceptual railway corridors
          ↓
    identify stations lying on / associated with corridors
          ↓
    order stations physically along each corridor
          ↓
    generate consecutive station-to-station physical edges
          ↓
    enrich edges with infrastructure/service attributes
          ↓
    validate graph

Example:

    Raw corridor:
    A ==================================== B

    Stations:
    A ---- S1 ---- S2 ---- S3 ---- B

    Final physical graph edges:
    A-S1
    S1-S2
    S2-S3
    S3-B

A whole A-B corridor must NOT automatically become one station-level edge if intermediate stations exist.

---

# 5. CURRENT CORE DATASETS / PREPROCESSED DATASETS

The project work has established four main graph-relevant datasets.

## 5.1 Railway GIS / Infrastructure Dataset

Known file:
    Railway_Network_.csv

Role:
    physical network foundation

Contains fields such as:
- fromjunction
- tojunction
- speed
- type/gauge
- noofstations
- tracklength
- railwayzone
- nooflanes
- bridge/tunnel indicators
- geometry-derived information

Current EDA baseline previously established:
- ~119,446 raw railway records
- ~2,305 distinct valid junction-pair corridors
- ~51.4 GIS segments per valid junction-pair corridor on average

IMPORTANT:
Raw record count != graph edge count.

Multiple GIS segments can correspond to the same conceptual corridor.

The railway layer therefore needs an intermediate corridor interpretation before station-level graph construction.

## 5.2 Station Master

Known file:
    stations.json

Role:
    canonical graph node layer

Contains:
- station identity
- station code
- station name
- geographic coordinates / geometry
- other station metadata where available

Current EDA baseline:
- ~8,990 station features
- ~96.7% with geometry

The intended identity hierarchy is:
1. station_code where reliable
2. normalised station name as supporting identity
3. spatial/geometric evidence for matching
4. never blindly trust name equality alone

The station data guide emphasises:
- station_code as join key
- station name normalisation
- latitude/longitude
- geometry
- explicit CRS/spatial handling
- provenance

## 5.3 Schedule Dataset

Known file:
    schedules.json

Role:
    service-level enrichment / validation

Current EDA baseline:
- ~417,080 schedule records
- ~5,208 unique train numbers
- ~8,539 unique station codes

Contains service sequence information such as:
- train number
- station code
- arrival/departure
- day/service information

IMPORTANT:
Schedules should enrich/validate the physical graph.
A train schedule transition is not automatically proof of a physical edge.

## 5.4 Train Metadata

Known file:
    trains.json

Role:
    train/service metadata associated with schedule layer.

---

# 6. HISTORICAL / CONTEXT DATA

The project also contains:
- historical gauge data
- national railway statistics
- zone electrification data
- Railway Year Book / national contextual statistics

These are not the primary topology source.

They are useful for:
- domain context
- historical interpretation
- graph attribute enrichment where temporally compatible
- contextual analysis

CRITICAL:
Every dataset needs a data-vintage field where possible.

Do not mix historical snapshots and current network claims without stating the time period.

The project documentation specifically warns that some zone-electrification information is a 31-March-2021 snapshot and must not be represented as a 2025 measurement.

---

# 7. IMPORTANT EDA FINDINGS

The EDA has already established several important facts.

## 7.1 Railway data is not graph-ready

The railway CSV contains many segment records that collapse into far fewer endpoint-pair corridors.

This proves that:
- segment records cannot simply become graph edges
- corridor aggregation is necessary
- graph semantics must be explicitly defined

## 7.2 Attribute conflicts exist

Within the same junction-pair corridor, attributes such as:
- speed
- type/gauge
- noofstations
- tracklength
- railwayzone
- nooflanes

can vary between raw GIS records.

Therefore:
- do NOT simply take first row
- do NOT silently overwrite
- aggregation rules must be field-specific

Examples:
- length may need sum/geometry-derived calculation
- speed may need min/max/representative statistic depending on meaning
- bridge/tunnel indicators may need OR/coverage logic
- gauge may need dominant/explicit multi-value representation
- zone may need consistency checking
- missing values should remain explicit where not safely inferable

## 7.3 Data-quality issues

Previously identified issues include:
- speed: substantial missingness and zero values
- railwayzone: missing values
- noofstations: missing/zero values
- tracklength: missing/zero values
- nooflanes: missing/zero values and some negative values
- gauge/type: missing/blank values
- missing from/to junction values

The current preprocessing philosophy is:
> Unknown is a valid state. Do not silently impute unsupported railway facts.

## 7.4 Station geometry is usable but must be validated

Most station features have coordinates/geometry.

This makes spatial matching feasible, but not automatically correct.

Need to validate:
- nearest railway segment/corridor
- distance to network
- ambiguous nearby lines
- stations near junctions
- stations serving multiple lines
- stations absent from GIS
- CRS correctness

## 7.5 Schedules are an independent evidence layer

Schedules can be used to:
- enrich station service features
- count services
- derive service connectivity
- validate some station sequences

But schedule order must not be treated as the sole definition of physical topology.

---

# 8. WHAT HAS BEEN VERIFIED VS WHAT IS STILL PROPOSED

This distinction is critical.

## Validated / established

- Raw railway data is segment-oriented.
- Corridor aggregation is necessary.
- Station data provides a viable spatial node layer.
- Station codes are a strong candidate integration key.
- Schedule data can provide service-level enrichment.
- The data is sufficiently structured to support a graph construction pipeline.
- The overall graph architecture is technically feasible.

## Now built and empirically validated (2026-09-30)

Everything this section previously listed as proposed-but-unvalidated has been
implemented and measured:

- **station-to-corridor matching** — tiered and spatially constrained, 1,555
  high/medium-confidence junction matches, every one carrying method, name
  score, spatial gap and confidence
- **station ordering along corridor geometry** — 12,305 ordered placements
  across 2,138 corridors, true geodesic distance-along-line, median
  perpendicular offset 41 m, zero non-monotonic corridors
- **final station-to-station edge generation** — 9,689 edges, built by chaining
  ordered stations and stitching each chain at its junction endpoints
- **handling of branches/junctions at full scale** — hybrid typed node model;
  junction stitching takes the giant component from 59.4% to 99.6%
- **handling of parallel physical routes** — 581 station pairs produced by more
  than one corridor, 124 of them genuinely distinct, flagged rather than collapsed
- **graph-wide topology validation** — `s10_verify_dataset.py` re-derives 27
  integrity checks from the shipped files on every run and fails loudly
- **final graph dataset quality** — full referential integrity, one canonical
  zone vocabulary across nodes and edges, deterministic byte-identical rebuild

The accurate wording is now:

> A station-level graph dataset has been constructed from the preprocessing
> outputs and independently validated: internally by a 27-check integrity
> suite, and externally by the schedule layer, which was never used to build
> it and which agrees with it on 94% of service adjacencies with zero
> cross-component contradictions.

What remains genuinely open is listed in `docs/GRAPH_HANDOFF_V2.md` §6, and
none of it blocks downstream work.

---

# 9. PROPOSED GRAPH ARCHITECTURE

## 9.1 Node model

Each station node should eventually include:

IDENTITY:
- station_id
- station_code
- canonical station_name

SPATIAL:
- latitude
- longitude
- geometry
- CRS

ADMINISTRATIVE:
- state
- railway zone
- division if reliable

INFRASTRUCTURE:
- gauge where reliable
- electrification where reliable
- other station-level infrastructure attributes

SERVICE:
- train count
- service frequency
- route count
- other schedule-derived features

GRAPH-DERIVED:
- degree
- weighted degree
- betweenness
- closeness
- PageRank
- articulation-point status
- community
- other derived measures

PROVENANCE:
- source
- data vintage
- matching method
- matching confidence
- quality flags

## 9.2 Edge model

Each physical edge should mean:

> A defensible physical railway connection between two canonical station nodes.

Potential attributes:
- source_station_id
- target_station_id
- geometry
- distance_km
- gauge/type
- speed
- track length
- lanes
- bridge/tunnel indicators
- railway zone
- service count/frequency
- source dataset
- data vintage
- matching method
- confidence
- quality flags

The graph should be weighted, but the exact default weight must be decided carefully.

Possible weights:
- physical distance
- travel-time proxy
- infrastructure impedance
- service-weighted cost

Do NOT arbitrarily define a weight before deciding what question that weight represents.

---

# 10. STATION LINKING — PROPOSED APPROACH

The expected construction approach is:

### Step 1 — Canonicalise station identity
Use station_code where reliable.
Normalise names for supporting matching.

### Step 2 — Clean railway GIS endpoints
Remove/quarantine records without usable endpoints.

### Step 3 — Build corridor candidates
Aggregate repeated GIS endpoint pairs into conceptual corridors while preserving segment-level evidence.

### Step 4 — Spatial station association
Use station coordinates/geometry against railway geometry.

Do not use unrestricted nearest-neighbour matching.

Use:
- distance thresholds
- geometry proximity
- corridor membership
- name/code evidence where available
- ambiguity checks
- confidence classes

### Step 5 — Station ordering
For stations associated with the same corridor:
- project station points onto corridor geometry
- derive position along the geometry
- order stations along the physical route

### Step 6 — Generate consecutive station edges
For ordered:
    A, S1, S2, S3, B

create:
    A-S1
    S1-S2
    S2-S3
    S3-B

### Step 7 — Handle branches/junctions
Do not force a simple linear interpretation where geometry indicates branching.

### Step 8 — Enrich edges
Attach infrastructure attributes with explicit aggregation rules.

### Step 9 — Service enrichment
Use schedules as a separate service layer.

### Step 10 — Validate
Run topology, spatial, statistical and manual checks.

---

# 11. CRITICAL GRAPH VALIDATION CHECKS

Before downstream analysis, validate:

## Node checks
- expected station coverage
- duplicate station IDs
- duplicate station codes
- missing geometry
- implausible coordinates
- isolated stations

## Edge checks
- self-loops
- duplicate edges
- suspiciously long edges
- zero/negative distances
- invalid geometries
- impossible jumps
- contradictory attributes
- unexplained parallel edges

## Topology checks
- connected components
- degree distribution
- articulation points
- bridge edges
- suspicious degree-1 concentration
- unexpected disconnected regions

## Spatial checks
- edge geometry follows railway network
- station lies on/near assigned corridor
- station order is geographically sensible

## Independent evidence checks
- compare selected routes with schedule sequences
- manually inspect representative corridors
- inspect high-centrality nodes
- inspect unusual edges
- compare against known railway geography

The graph should not be considered final until these checks pass.

---

# 12. THE FOUR DOWNSTREAM RESEARCH MODULES

These are modules, not four separate projects.

## MODULE 1 — NETWORK STRUCTURE & CRITICALITY

Question:
> How is the railway network structurally organised, and which nodes/edges are disproportionately important?

Methods:
- degree
- weighted degree
- betweenness
- closeness
- PageRank
- articulation points
- bridges
- communities
- structural bottlenecks

Purpose:
- understand network organisation
- identify structurally important stations/corridors
- establish that the graph is analytically meaningful

This is the most natural first downstream module.

---

## MODULE 2 — ACCESSIBILITY & SERVICE CONNECTIVITY

Question:
> How well connected is the railway network from a station/service perspective?

Possible measures:
- service frequency
- train counts
- number of reachable destinations
- direct connectivity
- indirect connectivity
- shortest service paths where data permits
- station accessibility profiles

Potential outputs:
- accessibility maps
- connectivity distributions
- regional comparisons
- station/service profiles

This is relevant to both public-facing connectivity analysis and planning-oriented network assessment.

---

## MODULE 3 — REDUNDANCY & RESILIENCE

Question:
> How much redundancy exists, and what happens when important nodes/edges are removed?

Possible experiments:
- random edge removal
- random node removal
- targeted removal of high-centrality nodes
- targeted corridor removal
- largest connected component
- path-length change
- connectivity degradation
- alternative path availability

Purpose:
- quantify structural dependence
- understand vulnerability
- distinguish robust vs highly dependent network regions

This does NOT require claiming actual disruption probabilities.

---

## MODULE 4 — NETWORK EXPANSION / WHAT-IF ANALYSIS

Question:
> What happens to network structure if hypothetical connections are added?

Possible candidate edges can be generated using:
- spatial proximity
- connectivity gaps
- existing network structure
- geographic constraints
- accessibility improvement

Evaluate hypothetical additions by:
- change in shortest paths
- change in connectivity
- reduction in components
- change in redundancy
- accessibility improvement
- centrality redistribution

IMPORTANT:
This is scenario analysis, NOT an automated system that tells Indian Railways where to build.

Do not claim engineering feasibility, economic feasibility, land feasibility, demand feasibility, or policy feasibility without those datasets.

---

# 13. ML POSITIONING

ML is intentionally delayed.

Potential ML:
- station clustering
- link prediction
- candidate-edge ranking
- graph embeddings
- future GNN work

The original project concept included:
- PCA/K-Means station profiling
- link prediction

But ML should only be introduced after:
1. graph is stable
2. graph metrics are understood
3. features are well-defined
4. train/test leakage is controlled

Link prediction must be a controlled graph-learning experiment.

It must NOT be described as:
> "The model predicts where Indian Railways should build new railway lines."

Possible safer formulation:
> "The experiment evaluates whether graph structure and station attributes can recover held-out connectivity relationships."

---

# 14. WHAT THE PROJECT CAN CLAIM

Supported / defensible:
- digital representation of railway network
- station-level graph
- infrastructure-aware graph
- service-enriched graph
- structural analysis
- centrality/criticality
- connectivity
- accessibility
- resilience
- hypothetical scenario analysis
- graph dataset / reusable research artifact

Requires additional operational data:
- real-time congestion
- capacity saturation
- actual train delays
- block-section occupancy
- headway analysis
- passenger demand
- freight demand
- formal new-line feasibility
- cost-benefit analysis

If someone asks about "congestion", explain that the current project is primarily modelling NETWORK STRUCTURE and CONNECTIVITY. Operational congestion/capacity requires additional traffic and operational datasets.

---

# 15. REAL-WORLD VALUE

The project should not claim to replace railway engineering/planning.

Potential value:

RAILWAY / PLANNING:
- network criticality
- connectivity gaps
- redundancy
- structural vulnerability
- scenario analysis
- infrastructure-aware network visualisation

PUBLIC:
- connectivity visualisation
- accessibility views
- service connectivity
- understandable network structure
- route/network dependency insights

RESEARCH:
- reusable graph dataset
- documented preprocessing pipeline
- railway graph benchmark/data foundation
- future graph-learning research

The strongest contribution is a reusable representation and methodology, not an automated policy decision system.

---

# 16. GRAPH AS A PUBLISHABLE DATASET

Target final dataset package:

    stations.parquet / stations.csv
    rail_edges.parquet / rail_edges.csv
    rail_edges.geojson
    graph.graphml
    graph.gpickle
    service_edges.parquet
    station_features.parquet
    data_dictionary.md
    provenance.md
    validation_report.md
    version_manifest

The graph should be independently usable from the application.

A good graph dataset should document:
- node semantics
- edge semantics
- units
- missingness
- source
- vintage
- construction rules
- matching rules
- confidence
- validation
- version

---

# 17. TEAM STRUCTURE

Three-person team.

## Bhuvanesh — Data Engineering & Provenance

Primary work:
- source integration
- preprocessing
- schema design
- station/corridor matching preparation
- EDA
- QA
- data versioning
- provenance
- graph-ready datasets

Current major contribution:
The preprocessing/EDA layer that makes graph construction possible.

## Sreehitha — Graph Engineering

Primary work:
- graph construction
- node/edge creation
- topology
- graph storage
- graph layout/visualisation
- graph validation
- graph metrics infrastructure

## Third teammate — Network Intelligence / Domain Modules

Current direction should NOT be forced into ML.

Potential responsibility:
- accessibility
- resilience
- scenario analysis
- service connectivity
- downstream analytics
- optional ML after graph is stable

This gives the third teammate a real research workstream while preserving flexibility.

---

# 18. SEVEN-MONTH PLAN

## Month 1
Freeze data model and provenance.
Finish preprocessing QA.

Output:
- versioned graph-input tables
- data dictionary
- preprocessing documentation

## Month 2
Construct and validate station-level physical graph.

Output:
- Graph v1
- topology validation report

## Month 3
Graph enrichment + structural analysis.

Output:
- centrality
- components
- bridges
- communities
- criticality

## Month 4
Accessibility/service module.

Output:
- service-enriched graph
- accessibility analysis

## Month 5
Resilience + hypothetical expansion.

Output:
- failure simulations
- scenario analysis

## Month 6
Selective ML + dashboard/prototype + graph publication package.

Output:
- one strong ML experiment if feasible
- interactive visualisation
- graph dataset package

## Month 7
Freeze, validate, document, write and present.

Output:
- final graph
- reproducible code
- final report/paper
- demo
- publication-oriented dataset

PRIORITY IF TIME COLLAPSES:
1. validated graph
2. graph structure/criticality
3. one additional strong domain module
4. documentation/dashboard
5. ML

---

# 19. RECOMMENDED RESEARCH CONTRIBUTION

Do not claim a novel graph algorithm.

The stronger contribution is:

> A reproducible data-engineering and network-modelling methodology for converting heterogeneous railway infrastructure, station and service information into a validated station-level railway graph with explicit semantics, provenance and rich attributes, followed by multiple analytical views of that graph.

Possible contribution categories:

DATA:
- curated graph-ready railway dataset

METHOD:
- railway segment → corridor → station graph transformation

GRAPH:
- weighted, attribute-rich station-level network

ANALYTICS:
- criticality/accessibility/resilience/expansion modules

SOFTWARE:
- reproducible pipeline and analytical interface

RESEARCH ARTIFACT:
- reusable railway graph dataset

---

# 20. REPOSITORY EXPECTATIONS

Claude Cowork should inspect the repository before changing anything.

First determine:
- repository structure
- README
- notebooks
- source code
- data directories
- preprocessing scripts
- outputs
- graph code
- requirements/environment files
- git history if available
- existing tests
- existing documentation
- current branch/state

Important known/project-related files from the work so far include:
- Railway_Network_.csv
- stations.json
- schedules.json
- trains.json
- Indian railway data pack / station data guide
- project conceptual document
- EDA/preprocessing notebooks and outputs
- Railway Year Book/reference material

However, do NOT assume these exact files are currently in the repository root.
Search the repository and map actual paths.

Create a repository inventory before making architectural changes.

---

# 21. EXPECTED REPOSITORY ARCHITECTURE

The final repository should move toward something like:

    project-root/
    ├── README.md
    ├── docs/
    │   ├── project_architecture.md
    │   ├── data_dictionary.md
    │   ├── graph_schema.md
    │   ├── graph_validation.md
    │   ├── provenance.md
    │   └── research_modules.md
    │
    ├── data/
    │   ├── raw/
    │   ├── interim/
    │   ├── processed/
    │   └── graph/
    │
    ├── notebooks/
    │   ├── 01_data_audit/
    │   ├── 02_preprocessing/
    │   ├── 03_station_matching/
    │   ├── 04_graph_construction/
    │   ├── 05_graph_validation/
    │   └── 06_graph_analysis/
    │
    ├── src/
    │   ├── ingestion/
    │   ├── preprocessing/
    │   ├── matching/
    │   ├── graph/
    │   ├── validation/
    │   ├── analysis/
    │   └── utils/
    │
    ├── outputs/
    │   ├── figures/
    │   ├── reports/
    │   └── graph_stats/
    │
    ├── tests/
    ├── requirements.txt / pyproject.toml
    └── LICENSE

This is a TARGET architecture, not a claim that the current repository already has this exact structure.

Do not reorganise the repository blindly. Inspect first and preserve useful existing work.

---

# 22. ENGINEERING PRINCIPLES

1. Reproducibility over manual editing.
2. Never silently fabricate/impute railway facts.
3. Preserve source/vintage/provenance.
4. Keep raw data immutable.
5. Separate raw → interim → processed → graph.
6. Make transformations deterministic.
7. Keep physical topology separate from service topology.
8. Do not let schedules define physical infrastructure.
9. Do not let names alone define station identity.
10. Use spatial validation for station-to-network matching.
11. Keep uncertainty/confidence explicit.
12. Validate before analytics.
13. Avoid premature ML.
14. Avoid claims unsupported by current data.
15. Keep the final graph exportable independently of the application.

---

# 23. IMPORTANT GRAPH SEMANTICS

There may eventually be multiple graph layers.

### Physical graph
Nodes = stations
Edges = physical railway connections

### Service graph
Nodes = stations
Edges = service/travel relationships supported by schedules

### Enriched physical graph
Physical graph + service/infrastructure attributes

Do NOT collapse these concepts casually.

A station pair connected by a train schedule is not necessarily equivalent to a newly inferred physical edge.

The physical graph is the core.

---

# 24. IMPORTANT WEIGHTING ISSUE

Do not decide "edge weight = distance" merely because distance is available.

Weights depend on analytical purpose.

Examples:

For physical/geographic analysis:
    weight = distance_km

For travel-time proxy:
    weight = distance / representative_speed

For service accessibility:
    weight may incorporate service frequency or service time

For resilience:
    weights may represent impedance/cost rather than physical distance

The project may therefore maintain:
- distance_km
- travel_time_proxy
- service_frequency
- infrastructure attributes

and choose the analytical weight explicitly per experiment.

Never hide the meaning of a graph weight.

---

# 25. CRITICAL LIMITATIONS

The current project is NOT:
- a real-time railway control system
- an operational traffic simulator
- a railway capacity estimator
- a passenger demand model
- an engineering design tool
- an economic feasibility tool
- an automated new-line recommendation engine

Unless new datasets are added, avoid those claims.

The project IS:
- a network representation
- a graph dataset
- a graph analytics platform
- a reproducible data-engineering pipeline
- a foundation for future railway network research

---

# 26. WHAT SUCCESS LOOKS LIKE

Minimum successful capstone:

1. Clean/reproducible source pipeline.
2. Canonical station layer.
3. Validated station-to-network matching.
4. Validated station-level physical graph.
5. Graph exported as reusable dataset.
6. Structural analysis of graph.
7. One strong domain module.
8. Reproducible documentation.
9. Clear limitations.
10. Working demonstration/visualisation.

Strong version:

All above +:
- service layer
- resilience
- what-if expansion
- selected ML
- interactive platform
- publication-quality graph package

---

# 27. CURRENT STATUS

Current stage:

    DATA ENGINEERING / EDA            ✅ complete
             ↓
    graph-input pipeline              ✅ complete  (s01-s08)
             ↓
    graph dataset + verification      ✅ complete  (s09, s10)
             ↓
    GRAPH CONSTRUCTION                ← current work (Sreehitha, Phase 3)
             ↓
    graph analysis modules            Phase 4 (Abrar)

The validation stage was not skipped. It runs on every pipeline execution and
its output is `02_graph_inputs/graph_dataset/VERIFICATION.txt`.

The next major technical objective is still NOT "train an ML model."

It is:

> **Load the shipped graph, prove its topology is defensible, and freeze it as
> graph v1 before any downstream analysis runs against it.**

# 28. IMMEDIATE NEXT WORK

Phase 3 — graph construction (Sreehitha):

1. Read `02_graph_inputs/graph_dataset/README.md`, then
   `docs/GRAPH_HANDOFF_V2.md` §4.
2. Load `nodes.csv` and `edges.csv` into the graph library of choice.
3. Settle the four remaining choices in `docs/GRAPH_HANDOFF_V2.md` §6 —
   storage format, the 115 dissolvable nodes, `core_v2` vs `core_v4`, and
   whether to recompute the shortcut-affected edge lengths.
4. Export graph v1 in interoperable form per blueprint §13 — GraphML plus
   parquet node/edge tables plus GeoJSON edge geometry.
5. Build the metrics infrastructure the four modules will call into.
6. Produce the graph-level validation report and freeze graph v1.

Phase 4 — analysis modules (Abrar): do not start against an unfrozen graph.
`docs/GRAPH_HANDOFF_V2.md` §4.9 states what each of the four modules gets from
the dataset and which view it should use.

Do not delete or overwrite existing EDA work. Do not hand-edit anything in
`02_graph_inputs/graph_dataset/` — change the pipeline and re-run.

# 29. WHAT CLAUDE SHOULD NOT DO

Do NOT:
- jump directly to GNNs
- build a graph by blindly treating GIS rows as edges
- use station names as unique IDs without validation
- use nearest-neighbour matching with no threshold/confidence
- make schedules the physical graph
- silently fill missing infrastructure values
- claim congestion prediction from current data
- claim new-line recommendations
- claim graph validity without topology validation
- reorganise the entire repository before understanding it
- delete existing notebooks/outputs
- introduce complex infrastructure before proving the simple pipeline
- optimise prematurely

---

# 30. THE PROJECT'S CORE RESEARCH STORY

The final academic narrative should be:

> Indian railway information is distributed across heterogeneous sources that were not designed to directly form a unified network representation. The project develops a reproducible preprocessing and geospatial integration pipeline that reconciles infrastructure segments, station identities and service information. This pipeline produces a station-level railway graph with explicit topology, spatial relationships, infrastructure attributes and provenance. The graph is then treated as the primary dataset for studying network structure, criticality, connectivity, accessibility, resilience and hypothetical network changes. Machine learning is considered only as a downstream graph-learning experiment after deterministic graph construction and validation.

That is the project.

---

# 31. ONE-SENTENCE VERSION

> **Build a trustworthy digital graph of the Indian railway network from messy real-world data, validate the graph as a reusable dataset, and use it as the foundation for structural, accessibility, resilience and hypothetical network-expansion research.**

---

# 32. FINAL GUIDANCE FOR CLAUDE

Treat the graph as the hero.

Treat preprocessing as a research contribution, not clerical cleaning.

Treat graph construction as a scientific/data-engineering problem.

Treat validation as mandatory.

Treat ML as optional.

Treat downstream modules as consumers of the graph.

Treat all current numerical EDA counts as a baseline that should be reverified from the repository before publication.

When uncertain about an existing implementation, inspect the repository instead of assuming.

The project's differentiator is not "we used NetworkX."

The differentiator is:

> **We built and validated the network representation itself from heterogeneous real-world railway data, and that graph becomes the reusable dataset on which the rest of the research is built.**
