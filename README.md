# Rail-Intell — Indian Railway Network Analysis

A data-engineering and graph-analysis project for the Indian Railway Network.

## Project Overview

This is a 7-month, 3-person capstone project building a validated, station-level
graph of the Indian railway network: Bhuvanesh (data engineering & provenance —
this repo's Phase 1–2 work), Sreehitha (graph engineering — Phase 3), Abrar
(network intelligence / domain modules — Phase 4).

The repository is organized by project phase, in the order the work happens:

```
Rail-Intell/
├── 01_data_engineering/     ← Phase 1: raw data, cleaning, EDA (Bhuvanesh)
├── 02_graph_inputs/         ← Phase 2: reproducible pipeline → validated graph-input package (Bhuvanesh)
├── 03_graph_construction/   ← Phase 3: build the actual graph object (Sreehitha)
├── 04_analysis_modules/     ← Phase 4: four downstream analysis modules (Abrar)
├── docs/                    ← Cross-phase documentation and handoff briefings
└── reference_data/          ← Reference-only source material (not part of the pipeline)
```

Each phase folder that doesn't yet have code has its own `README.md` pointing to
what it depends on and where to start.

---

## Phase 2 output: the current graph-ready hand-off

> **For the graph-design teammate:** read `02_graph_inputs/graph_dataset/README.md`,
> then `docs/GRAPH_HANDOFF_V2.md` §4 for why the dataset is shaped the way it is.

Phase 1 (EDA/preprocessing) and Phase 2 (the graph-input pipeline) are both
complete and validated. Phase 2's output — the `graph_inputs/` package below —
is the current hand-off point for Phase 3 graph construction.

### Graph Dataset (the hand-off — build from this)

`02_graph_inputs/graph_dataset/` is the cleaned, normalised, node- and
edge-resolved dataset. Read its `README.md` first; it is the data dictionary.

| File | Rows | Description |
|------|------|-------------|
| `02_graph_inputs/graph_dataset/nodes.csv` | 9,095 | **The node table** — 8,621 stations + 474 operational junctions, typed, attributed, with provenance |
| `02_graph_inputs/graph_dataset/edges.csv` | 9,689 | **The edge table** — geodesic-weighted physical connections with gauge, tracks, zone, service load |
| `02_graph_inputs/graph_dataset/service_edges.csv` | 10,193 | Service layer — frequency and observed run-time per station pair |
| `02_graph_inputs/graph_dataset/stations.csv` | 8,990 | Cleaned station master |
| `02_graph_inputs/graph_dataset/corridors.csv` | 2,279 | Cleaned corridor attributes |
| `02_graph_inputs/graph_dataset/station_sequences.csv` | 12,305 | Ordered station placements — the input edges were built from |
| `02_graph_inputs/graph_dataset/QA_REPORT.txt` | — | Regenerated every run |
| `02_graph_inputs/graph_dataset/VERIFICATION.txt` | — | 27 integrity checks, re-derived from the shipped files every run |

The graph: **9,095 nodes, 9,689 edges, 99.6% in one connected component,
72,201 route km.** One canonical zone vocabulary across nodes and edges, full
referential integrity, deterministic rebuild.

### Intermediate package (Phase 2 working files)

`02_graph_inputs/graph_inputs/` holds the 12 intermediate tables the dataset was
built from — canonical junctions, corridor spines, station matches, placements.
Keep them: they let edge construction be redone under different rules.

| File | Rows | Description |
|------|------|-------------|
| `02_graph_inputs/graph_inputs/nodes_junctions.csv` | 2,029 | Canonical junctions: coordinates, class, station match + confidence |
| `02_graph_inputs/graph_inputs/corridor_station_sequence.csv` | 12,305 | Stations ordered along each corridor, with geodesic distance-along-line |
| `02_graph_inputs/graph_inputs/corridors_enriched.csv` | 2,279 | Corridor attributes, geodesic length, reconstruction status |
| `02_graph_inputs/graph_inputs/QA_SUMMARY.txt` | — | Machine-generated integrity report |

See `docs/GRAPH_INPUTS_DICTIONARY.md` for the full column dictionary of every
file in the package, and `docs/VALIDATION_REPORT.md` for what was checked and
which limitations are known (in particular: "spine shortcutting", affecting
~17% of consecutive station pairs — documented, not hidden).

### Phase 1 outputs (raw + cleaned data this pipeline is built on)

#### Legacy graph (v1, superseded by the Phase 2 package above)

| File | Rows | Description |
|------|------|-------------|
| `01_data_engineering/legacy_graph_v1/rail_edges_initial.csv` | 2,257 | Conceptual directed edges — one per unique junction pair |
| `01_data_engineering/legacy_graph_v1/junction_nodes_initial.csv` | 2,024 | Junction nodes with degree statistics and component membership |
| `01_data_engineering/legacy_graph_v1/railway_components_initial.csv` | 113 | Connected-component summary (main component: 1,758 nodes / 2,101 edges) |

#### Station master

| File | Rows | Description |
|------|------|-------------|
| `01_data_engineering/processed_data/cleaned_stations.csv` | 8,990 | Cleaned station master — 8,697 with coordinates, 0 duplicate codes |

#### Service data (validated, not currently used as graph edges)

| File | Rows | Description |
|------|------|-------------|
| `01_data_engineering/processed_data/cleaned_schedules.csv` | 416,970 | Stop records for 5,208 trains — validated against station master |
| `01_data_engineering/processed_data/cleaned_trains.csv` | 5,208 | Train metadata with quality flags |

### Documentation

| File | Description |
|------|-------------|
| `CHANGELOG.md` | **What changed and when** — read this first if you have been away |
| `02_graph_inputs/graph_dataset/README.md` | **The data dictionary** for the hand-off dataset |
| `docs/GRAPH_HANDOFF_V2.md` | **Start here** — current handoff briefing for the graph-design phase |
| `docs/GRAPH_INPUTS_DICTIONARY.md` | Column-level schema for the `02_graph_inputs/graph_inputs/` package |
| `docs/VALIDATION_REPORT.md` | Independent validation of the preprocessing layer, gaps found, and how each was closed |
| `docs/GRAPH_HANDOFF.md` | Superseded v1 handoff, kept for provenance (see banner at top) |
| `docs/DATA_DICTIONARY.md` | Column-level schema for the Phase 1 processed datasets |

---

## Notebooks (Phase 1)

Located in `01_data_engineering/notebooks/`. Each now starts with an added
"path fix" cell (inserted during the 2026-09-29 reorg) that changes the
working directory to `01_data_engineering/` before running, so every relative
path inside — `railways-master/...`, `processed_data/...`, `Railway_Network_.*`
— still resolves exactly as it did before the move.

| Notebook | Purpose | Status |
|----------|---------|--------|
| `Railway_networks_EDA.ipynb` | EDA of `Railway_Network_.csv`; produces the legacy edge/node/component CSVs | Complete |
| `01_Final_Data_Preprocessing_and_Validation.ipynb` | Cleans stations, trains, schedules; spatial analysis | Complete. Superseded (for graph-input purposes) by `02_graph_inputs/pipeline/`. |
| `Untitled.ipynb` | Historical statistics EDA (gauge history, electrification) | Exploratory — no output files |

---

## Repository Structure

```
Rail-Intell/
├── 01_data_engineering/
│   ├── Railway_Network_.csv          ← Raw GIS network (119,446 segments)
│   ├── Railway_Network_.geojson      ← Raw GIS geometry (88 MB)
│   ├── railways-master/              ← Raw source data (JSON)
│   │   ├── stations.json
│   │   ├── trains.json
│   │   ├── schedules.json
│   │   └── README.md
│   ├── processed_data/
│   │   ├── cleaned_stations.csv      ← Station master (8,990 stations)
│   │   ├── cleaned_trains.csv        ← Train metadata (5,208 trains)
│   │   └── cleaned_schedules.csv     ← Schedule stops (416,970 records)
│   ├── notebooks/
│   │   ├── 01_Final_Data_Preprocessing_and_Validation.ipynb
│   │   ├── Railway_networks_EDA.ipynb
│   │   └── Untitled.ipynb
│   └── legacy_graph_v1/              ← Superseded v1 junction graph
│       ├── rail_edges_initial.csv
│       ├── junction_nodes_initial.csv
│       └── railway_components_initial.csv
│
├── 02_graph_inputs/
│   ├── pipeline/                     ← Reproducible pipeline (run_all.py, ~50s)
│   │   ├── config.py                 ← Paths, controlled vocabularies, geodesy
│   │   └── s01..s10_*.py             ← Ten deterministic stages
│   ├── graph_dataset/                ← ★ BUILD FROM THIS — cleaned, normalised
│   │   ├── README.md                 ← data dictionary; read first
│   │   ├── nodes.csv                 ← 9,095 resolved graph nodes
│   │   ├── edges.csv                 ← 9,689 weighted, attributed edges
│   │   ├── service_edges.csv         ← frequency + run-time per station pair
│   │   ├── stations.csv / corridors.csv / station_sequences.csv
│   │   └── QA_REPORT.txt · VERIFICATION.txt
│   └── graph_inputs/                 ← intermediate tables (12 files)
│       ├── nodes_junctions.csv
│       ├── corridor_station_sequence.csv
│       ├── corridors_enriched.csv
│       └── QA_SUMMARY.txt
│
├── 03_graph_construction/            ← Sreehitha's phase (empty — see its README.md)
│
├── 04_analysis_modules/              ← Abrar's phase (empty — each subfolder has a README.md)
│   ├── 01_network_structure_criticality/
│   ├── 02_accessibility_connectivity/
│   ├── 03_resilience_redundancy/
│   └── 04_expansion_whatif/
│
├── docs/
│   ├── GRAPH_HANDOFF_V2.md           ← Graph teammate: read this first
│   ├── GRAPH_INPUTS_DICTIONARY.md
│   ├── VALIDATION_REPORT.md
│   ├── GRAPH_HANDOFF.md              ← superseded v1
│   └── DATA_DICTIONARY.md            ← Column schemas for Phase 1 datasets
│
├── reference_data/                   ← Reference-only material, not part of the pipeline
│   ├── Indian_Railway_Stations_JSON-master/
│   ├── archive (5)/
│   └── (historical statistics PDFs/CSVs/xlsx)
│
├── .gitattributes
├── .gitignore
└── CLAUDE_COWORK_PROJECT_CONTEXT.md
```

---

## Large Files

The following files are too large for standard Git commits and are tracked via
Git LFS (`.gitattributes` matches by extension: `*.geojson`, `*.json`, `*.csv`,
`*.xlsx`, so this applies regardless of which folder a file lives in):

| File | Size | Note |
|------|------|------|
| `01_data_engineering/Railway_Network_.geojson` | ~88 MB | Required for spatial analysis |
| `01_data_engineering/railways-master/schedules.json` | ~78 MB | Raw source |
| `01_data_engineering/processed_data/cleaned_schedules.csv` | ~62 MB | Processed output |
| `01_data_engineering/railways-master/trains.json` | ~14 MB | Raw source |
| `01_data_engineering/processed_data/cleaned_trains.csv` | ~13 MB | Processed output |
| `01_data_engineering/Railway_Network_.csv` | ~13 MB | Raw source |
