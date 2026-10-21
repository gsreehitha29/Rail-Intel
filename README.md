# Rail-Intel — a station-level graph of the Indian railway network

A reproducible, geospatial and graph-based representation of Indian Railways, built from
open data, and the corridor-vulnerability analysis built on it.

**Current dataset: `v2.0-open`, locked 2026-10-21.** 12,301 nodes (9,507 stations,
2,794 junctions), 13,560 track sections, 70,304.6 route km — **+1.25%** against the official
69,439 km. Built only from OpenStreetMap, Wikidata, datameet and data.gov.in, and released
under ODbL 1.0.

> **Read [`docs/TIMELINE.md`](docs/TIMELINE.md) first.** It is the single history of the
> project: every version, the decisions and design changes behind it, how each was validated,
> its limitations, and an honest account of what is still wrong or unfinished.

---

## Where things are

```
Rail-Intell/
├── docs/                      Registers and reference documentation
├── external_data/             Open inputs (OSM, Wikidata, datameet, timetables) — 2.0 GB, not in git
├── reference_data/            Published statistics used for validation
├── 01_data_engineering/       Source cleaning, EDA, the legacy v1 junction graph
├── 02_graph_inputs/           The graph-input pipeline and its validated dataset
├── 03_graph_construction/     The graph builds, the release, and the service layers
├── 04_analysis_modules/       Downstream analyses (E-7xx experiments)
├── 05_product/                The corridor vulnerability tool — empty, to be built
├── publication/               Figures, evidence and reports
├── tests/                     82 tests, including the release contract
└── _archive/                  Superseded versions and docs — on disk, out of git
```

### `03_graph_construction/` — the dataset itself

| Path | What it is |
|---|---|
| `release/rail-intel-v2.0-open/` | **the final dataset**: `graph/`, `places/`, `service_2017/`, `provenance/`, datasheet, licence, manifest |
| `release/rail-intel-v2.0-open.zip` | the deterministic release package (sha256 in `SHA256SUMS`) |
| `graph_v2_0_open/` | the v2.0 working build and its validation evidence (`work/`) |
| `graph_v1_4/` | the frozen Esri-derived baseline. **Never edit in place** (D-055) |
| `graph_v1_4_1/` | the accuracy-comparison baseline for v2.0 |
| `service_layer_v2_0_open/` | 2017 (shipped, GODL) and 2024 (local only, D-067) service layers |
| `railgraph/` | the v1.x construction library |
| `experiments/E-716_osm_v2_build/` | the v2.0-open pipeline: O1–O6, validation, release packaging |

The dataset ships two views (D-066):

- **`graph/`** — the physical graph. Lengths are exact. Use it for distance and routing.
- **`places/`** — track points within 1 km merged into one place. Use it for structure:
  degree, cut points, redundancy.

### `05_product/` — the upcoming product

Empty by design. The scope (D-058) is a corridor-level vulnerability and contingency tool
answering: which corridors have no alternative route, what each isolates, how much traffic
depends on it, and what a named blockage cuts off.

- `05_product/api/` — a queryable interface over the locked graph
- `05_product/web/` — the map and corridor views

### `04_analysis_modules/`

`E-700`–`E-714` are the v1.4-era analyses. `E-718`–`E-720` are empty placeholders for the
re-runs of criticality, degree distribution and conclusion robustness on v2.0-open — **those
analyses have not yet been re-run, so their published figures are v1.4 figures** (see
`docs/TIMELINE.md` §5).

---

## Documentation

| File | What it holds |
|---|---|
| `docs/TIMELINE.md` | **Start here.** Versions, decisions, design changes, validation, limitations, the bad side |
| `docs/DECISIONS.md` | The decision register, D-001 … D-069, with the reasoning for each |
| `docs/FINDINGS.md` | Every measured finding, F-… (note: some IDs are reused — see TIMELINE §5.8) |
| `docs/EXPERIMENTS.md` | The experiment log, E-… |
| `docs/V2_ISSUES.md` | The v2.0-open issue register, V2-01 … V2-25, with status |
| `docs/SCOPE.md` | Objectives, deliverables and what is explicitly out of scope |
| `docs/STABILITY.md` | What the release promises, and what the tests enforce |
| `docs/DATA_DICTIONARY.md` | Column schema for the Phase 1 processed datasets |
| `docs/GRAPH_INPUTS_DICTIONARY.md` | Column schema for `02_graph_inputs/graph_inputs/` |
| `docs/GRAPH_HANDOFF_V2.md` | The graph-design handoff briefing |
| `docs/PHASE3_GRAPH_ROADMAP.md` | The Phase 3 roadmap and its gates |
| `docs/LITERATURE.md`, `docs/PAPER_OUTLINE.md` | Positioning and the paper's structure |
| `02_graph_inputs/graph_dataset/README.md` | Data dictionary for the Phase 2 hand-off dataset |

---

## Running things

```bash
pip install -r requirements.txt
python -m pytest tests -q          # 82 tests
make help                          # all build targets
```

The v2.0-open build, in stages (laptop timings ≈ 82 s / 34 s / 29 s / 50 s):

```bash
make osm-c1        # filter, collapse parallel tracks, snap stations
make osm-c2        # Wikidata placement, joins, the station graph, service
make osm-c3        # validation against v1.4.1
make osm-release   # the deterministic release package
```

The build is deterministic: the same inputs and code produce byte-identical outputs, verified
across two machines. `manifest.json` lists every input with its hash.

---

## Licence and attribution

The dataset is a derived database of OpenStreetMap, licensed **ODbL 1.0**, contents under
**DbCL 1.0**. Sources: OpenStreetMap (ODbL), Wikidata (CC0), datameet maps (CC BY 4.0),
data.gov.in Train Details 2017 (GODL-India). See `LICENSE`, `LICENSES.md` and the release's
`ATTRIBUTION.md`.

The 2024 timetable (IIT Kharagpur RSTGCN) has no stated licence and is **not redistributed**;
it is used for validation only (D-067, D-068).

`graph_v1_4` and everything derived from it are Esri-derived and **not redistributable**
(D-057). That is why v2.0-open exists.

---

## Large files

`.gitattributes` routes `*.geojson`, `*.json`, `*.csv` and `*.xlsx` through Git LFS by
extension. The largest are `01_data_engineering/Railway_Network_.geojson` (~88 MB),
`railways-master/schedules.json` (~78 MB) and `processed_data/cleaned_schedules.csv` (~62 MB).
`external_data/` (2.0 GB) and `_archive/` are excluded from git entirely — `external_data/`
is rebuilt from `external_data/download_manifest.json`.

> **Note:** git-lfs is not installed in the current working copy, so `git status` fails there
> and the last commit predates the v1.3 → v2.0 work. Treat `docs/TIMELINE.md` and the
> registers as the authoritative history, not the git log.

---

*Project: Bhuvanesh Vinjamuri. Last restructured 2026-10-21.*
