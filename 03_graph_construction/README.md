# 03 — Graph Construction (Phase 3)

> **Current release: graph v1.3** (`graph_v1_3/open/` and `graph_v1_3/full/`, built by E-600, `make v13`).
> See `graph_v1_3/README.md` and `graph_v1_3/VALIDATION_v1_3.md`. v1.0–v1.2 below are kept for provenance.


**Owner:** Sreehitha (Graph Engineering) · **Reference implementation and
validation harness:** this folder · **Status:** graph v1.0 frozen, v1.1 released,
all validation gates passing (2026-10-04).

This phase turns the Phase 2 graph dataset into the formal station-level railway
graph, validates it, and exports it for the Phase 4 analysis modules. **It does
not rebuild the topology from raw GIS.** `nodes.csv` and `edges.csv` are loaded as
shipped; a rebuild path exists only so the sensitivity study can vary
construction choices, and is checked to reproduce `edges.csv` exactly (`D-023`).

## 1. What the graph is

| | |
|---|---|
| Nodes | **9,095** — 8,621 stations + 474 operational junctions |
| Edges | **9,689** physical track connections, undirected, simple (no self-loops, no duplicates) |
| Route length | **72,201.1 km** (v1.0) · 72,421.0 km (v1.1, hybrid length) |
| Components | **18** — giant component **9,058 nodes (99.6%)**, 17 small ones (37 nodes, 501 km) |
| Structure | mean degree 2.13, max 7 · 1,412 bridges · 1,338 articulation points · 612 independent cycles · meshedness 0.034 · tree-likeness 0.937 |
| Weight | `length_km` (primary); `unit`, `travel_time_proxy`, `service_impedance` also provided (read VALIDATION §7 before using `travel_time_proxy`) |

It is a **physical infrastructure** graph. Train *service* (which trains stop where,
and for how long) is a separate layer and is deliberately not mixed into it.

## 2. Start here

```python
import sys; sys.path.insert(0, "03_graph_construction")
from railgraph import load_graph
G = load_graph()          # NetworkX Graph; raises InvariantError unless
                          # 9,095 / 9,689 / 18 / 9,058 / 72,201 km all reproduce
```

Or with no project code at all (this is exactly Sreehitha's milestone):

```python
import pandas as pd, networkx as nx
n = pd.read_csv("02_graph_inputs/graph_dataset/nodes.csv")
e = pd.read_csv("02_graph_inputs/graph_dataset/edges.csv")
G = nx.Graph()
G.add_nodes_from((r.node_id, r._asdict()) for r in n.itertuples(index=False))
G.add_edges_from((r.from_node, r.to_node, r._asdict()) for r in e.itertuples(index=False))
```

**Which artifact?**

| use | folder | note |
|---|---|---|
| the graph exactly as the Phase 2 plan specifies | `graph_v1/` | `length_km` is the shipped value; **the baseline** |
| the same graph plus provenance and real track geometry | `graph_v1_1/` | identical topology; `length_km` re-derived (+0.30%), original kept as `length_km_v10` |
| **the corrected graph — recommended for analysis** | `graph_v1_2/` | v1.1 minus 51 proven duplicate edges, plus edge-level bridges/tunnels/zone, validated speeds and states (`VALIDATION_v1_2.md`) |
| train service: direction, run-times, time of day | `service_layer/` | directed pairs keyed to the physical graph (`E-502`) |

## 3. Phase 3 plan → repository

| # | Plan item | Status | Where |
|---|---|---|---|
| 1 | Load `nodes.csv` / `edges.csv` into NetworkX | **done** | `railgraph.load_graph()`, `build.shipped_tables()` |
| 2 | Keep station + junction node model and every attribute | **done** | all 22 node columns; checked value-by-value (`D-039`) |
| 3 | Physical edges, `length_km` weight, infrastructure attributes | **done** | all 22 edge columns incl. `bridge_present`, `tunnel_present`, `gauge`, `n_tracks`, `speed` |
| 4 | Validate vs QA/verification results | **done** | `railgraph.assert_invariants()`; `graph_v1/VALIDATION_v1.md` |
| 5 | Inspect junctions, high-degree nodes, small components, dissolvables | **done** | `E-403` — read-only; topology unchanged |
| 6 | Keep physical graph distinct from the service layer | **done and exported** | `service_layer/` — directed, timed, mapped to physical paths (`D-047`, `E-502`); physical edges carry only the aggregates |
| 7 | Associate edge geometry for spatial work | **done for 57.7% of edges** | v1.1 `edges.geojson` + `edge_geometry.parquet` (`D-040`, `E-402`) |
| 8 | Export a reusable artifact | **done** | GraphML + parquet + GeoJSON + manifest, verified (`D-039`) |
| 9 | Document structure, validation, assumptions, limitations | **this file** + the two `VALIDATION` files and `graph_v1/DATASHEET.md` | |

## 4. Files

```
graph_v1/      frozen v1.0           graph_v1_1/     v1.1 (additive)
  rail_graph_v1.graphml  11.9 MB       rail_graph_v1_1.graphml  18.4 MB
  nodes/edges.parquet     0.88 MB      nodes/edges.parquet       1.6 MB (56 edge cols)
  nodes/edges.geojson    11.7 MB       nodes/edges.geojson      35.4 MB (true alignment)
  graph_v1.manifest.json (hashes)      edge_geometry.parquet     7.7 MB (WKB)
  DATASHEET.md, VALIDATION_v1.md       edges.csv, VALIDATION_v1_1.md, E-400/E-402 reports
railgraph/     builder, metrics, validation, provenance, geometry, sensitivity, I/O
experiments/   E-001 … E-403, one folder each, each with a runnable script
```

All formats carry the same attributes. A null is an **absent** attribute in
GraphML (it has no null). Graph-level constants (`dataset_version`) are stored once
on the graph and re-attached on table exports.

## 5. Geometry — how it is associated with the graph

An edge between two consecutive stations is a slice of its corridor's spine
(`02_graph_inputs/pipeline/cache/corridor_spines.parquet`) between the two stations'
`measure_km` (`railgraph/geometry.py`). Each edge records how it got its geometry:

| `geometry_source` | edges | meaning |
|---|---|---|
| `spine` | 5,591 (57.7%; 56.4% of km) | true alignment, slice of the corridor spine; length agrees with `length_km` to ≤1e-5 |
| `chord` | 4,097 | straight 2-point line between the endpoints — schematic; used where D-026 does not trust the spine (stitch edges 2,251, collapse 1,123, offset 679, floored 44) |
| `none` | 1 | an endpoint has no coordinate (`JN::Khandala`); GeoJSON feature kept with `geometry: null` |

The slice is **not snapped** to node coordinates (stations sit up to 0.25 km off
the line; snapping would invent track). **Trap:** `measure_km` follows the Phase 2
orientation; for the 1,090 `reversed_to_a` corridors the stored line runs the other
way, so the position is `L − measure_km` (`F-047`). A slicer that ignores this
passes every length check and draws half the network in the wrong place.

## 6. Validation — what was checked, and what it shows

| check | result |
|---|---|
| Counts / components / giant / self-loops / duplicates / missing endpoints | reproduce QA report exactly; `in_giant_component` and `degree` columns equal a recomputation |
| Rebuild path vs shipped `edges.csv` | identical (`E-002`) |
| Export round trip, **every attribute** of every node and edge | GraphML, parquet, GeoJSON exact — 350,570 values each |
| Export vs Phase 2 CSVs | every column and value carried |
| Geometry audit (10 checks) | all pass (`E-402`) |
| v1.1 additive | topology bit-identical; mountain railways rank 1, 4, 5, 6 of 859 by sinuosity (gate b) |
| Sensitivity | 8 conclusions: 0 artifacts across 30 cells incl. length derivation (`E-200`, `E-401`) |
| Attribute provenance | **4 of 6 attributes do not measure what they claim** (corridor constants shown per edge, fallback speeds) — flagged in the data, not hidden |

## 7. Topology cases (`E-403`)

- **Small components:** 17, all but one within the ordinary nearest-neighbour range of
  the giant; five share a coordinate with a giant node; all on corridors with the
  station-matching deficit. Most likely residual connection gaps, **unverified**
  (`F-048`, `D-041`). Retained; candidate links in `E-403/small_components.csv`.
- **High degree:** 26 nodes with degree ≥6, all stations, max 7 — bounded degree, no
  hubs; the top 1% of nodes hold 2.5% of edge endpoints.
- **Dissolvable junctions:** 115, all degree 2, all on a corridor boundary, 3 change
  gauge, 20 lie on an already-adjacent pair. **Not dissolved** (`D-017`, `F-049`).

## 8. Assumptions and limitations

The five weaknesses listed for the paper were each re-measured and fixed as far as
the evidence allows in **v1.2**. What persists is listed in full in
`graph_v1_2/VALIDATION_v1_2.md` §7. In short:

1. **Missing stations (G-01)** were not a matching failure. The stations are in no
   in-repo source, so ≈9,900 incidences **cannot be added here**. What they caused,
   51 straight-line duplicate edges, is removed in v1.2 with proof. 56 further
   unsupported edges are flagged, and `suspect_long_edge` covers 23.3% of km.
2. **Granularity:** bridges, tunnels and zone are now edge-level. Speed, gauge and
   track count are corridor-level **in the source itself**.
3. **Speeds:** 35.4% of edges have no declared speed. They now carry a validated
   estimate (±11.4 km/h) instead of 50 km/h (±56). The estimate is likely biased
   high on those edges, by an amount that could not be measured.
4. **State:** 74.6% coverage (was 45.8%). 388 "Andhra Pradesh" labels are ambiguous
   with Telangana, and 25.4% of nodes are still unlabelled.
5. **Model:** direction and time are in `service_layer/`. The physical graph is
   undirected by design. **There is no capacity information and no running-days
   information in any input.**
6. No capacity, congestion, demand or feasibility claims. The what-if module is
   scenario analysis only.
7. Source licences are unresolved (`publication/SOURCE_LICENCE_INVENTORY.md`).

## 9. Reproduce

```
make build      invariants + rebuild equivalence        make v11       build/validate/export v1.1
make exports    re-export v1.0, verify vs Phase 2 CSVs  make geometry  audit v1.1 geometry
make topology   E-403 case inspection                   make all       everything (~1h)
make v12        build v1.2 (E-500, 12 gates)            make v12audit  removal proof + conclusions (E-501)
make servicelayer  directed, timed service layer (E-502)
```

## 10. Read

`docs/DECISIONS.md` (47 ADRs; `D-042`–`D-047` are the v1.2 decisions) ·
`docs/FINDINGS.md` (56) · `graph_v1_2/VALIDATION_v1_2.md` · `docs/EXPERIMENTS.md` · `graph_v1/DATASHEET.md` ·
`graph_v1/VALIDATION_v1.md` · `graph_v1_1/VALIDATION_v1_1.md` · `docs/GRAPH_V2_ROADMAP.md`.
Do not hand-edit `02_graph_inputs/graph_dataset/` — change the pipeline and re-run.
