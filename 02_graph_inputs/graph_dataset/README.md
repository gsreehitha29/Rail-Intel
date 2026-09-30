# Rail-Intell Graph Dataset — v1.0

**This is the folder to build the graph from.** Everything in it is cleaned,
normalised, internally consistent and regenerated deterministically by
`02_graph_inputs/pipeline/run_all.py` (stage `s09`). Nothing here should be
edited by hand — change the pipeline and re-run.

Produced by: Bhuvanesh (Data Engineering & Provenance)
For: Sreehitha (Graph Engineering), and Abrar's modules downstream
Generated: 2026-09-30 · dataset_version `v1.0`

---

## Start here

```python
import pandas as pd, networkx as nx

nodes = pd.read_csv("02_graph_inputs/graph_dataset/nodes.csv")
edges = pd.read_csv("02_graph_inputs/graph_dataset/edges.csv")

G = nx.Graph()
for r in nodes.itertuples():
    G.add_node(r.node_id, **{k: getattr(r, k) for k in
               ("node_type", "node_name", "longitude", "latitude",
                "zone_code", "state", "degree")})
for r in edges.itertuples():
    G.add_edge(r.from_node, r.to_node, km=r.length_km, gauge=r.gauge_code,
               tracks=r.n_tracks, speed=r.speed_kmph, load=r.service_load,
               edge_id=r.edge_id)

# 9,095 nodes · 9,689 edges · 99.6% in one component
```

That is the whole physical graph. The node and edge tables are already
resolved and deduplicated — no joining, matching or ordering left to do.

---

## Files

| File | Rows | What it is |
|---|---|---|
| `nodes.csv` | 9,095 | **The node table.** Every graph node, typed, attributed, with provenance. |
| `edges.csv` | 9,689 | **The edge table.** Physical station-to-station connections, weighted and attributed. |
| `service_edges.csv` | 10,193 | Service layer — station pairs that appear as consecutive stops on a train, with frequency and run-time. |
| `stations.csv` | 8,990 | Cleaned station master. The reference pool; not every station becomes a node. |
| `corridors.csv` | 2,279 | Cleaned corridor attributes. Join on `edges.corridor_id` for anything not already on the edge. |
| `station_sequences.csv` | 12,305 | Ordered station placements along each corridor — the input the edges were built from. Kept so edge construction can be redone under different rules. |
| `QA_REPORT.txt` | — | Regenerated every run. Read it before trusting a number. |

---

## nodes.csv

| Column | Meaning |
|---|---|
| `node_id` | Primary key. A station code (`VM`) for station nodes, or `JN::<name>` for operational junctions. |
| `node_type` | `station` (8,621) or `operational_junction` (474). |
| `station_code` | Set for station nodes only; joins to `stations.csv`. |
| `node_name` | Human-readable label. |
| `longitude`, `latitude` | WGS84. Present on 9,094 of 9,095. |
| `zone_code`, `zone_name` | Railway zone, canonical vocabulary (`SCR` / `South Central Railway`). |
| `zone_source` | `station_master` (stated, 4,123) or `corridor_inferred` (4,874). **Inferred zones are not source data** — exclude them if a result depends on zone being stated. |
| `state` | Canonical state name. Present on 4,163; the station master simply does not record the rest. |
| `in_scope` | `False` for the 2 stations located in Bangladesh. Filter on this for any national figure. |
| `junction_class` | Operational junctions only: `cabin`, `yard`, `block_hut`, `siding`, `bypass`, `chord`, … |
| `match_confidence`, `match_method`, `spatial_gap_km` | Operational junctions only: why this node has no station identity. |
| `n_corridors` | How many corridors the node sits on. |
| `coordinate_shared` | `True` for the 11 stations that share a coordinate with another station — at least one of each set is mislocated. |
| `degree` | Degree in the shipped edge list. |
| `is_dissolvable` | `True` for the 115 operational junctions at degree 2 — removable by path contraction without changing topology. Of the rest, 313 are degree-1 line ends and 46 are degree ≥3 and structurally load-bearing. |
| `component_id`, `in_giant_component` | 0 is the giant component (9,058 nodes, 99.6%). |

## edges.csv

| Column | Meaning |
|---|---|
| `edge_id` | Primary key. |
| `from_node`, `to_node` | Join to `nodes.node_id`. **Undirected** — each pair appears once. |
| `length_km` | **Use this as the weight.** True geodesic kilometres, floored at 0.05. |
| `corridor_id` | The corridor this edge came from; join to `corridors.csv`. |
| `gauge_code`, `gauge_name` | `BG` / `MG` / `NG` / `SG`. Gauge is a traversability constraint, not just a label. |
| `zone_code`, `zone_name` | Canonical zone. |
| `speed_kmph` | Sanctioned speed. **Null on ~49% of corridors — never filter on it** (see QA report). |
| `n_tracks` | 1 = single line, 2+ = double or multiple. The capacity and redundancy signal. |
| `bridge_present`, `tunnel_present` | Structure flags from the GIS layer. |
| `n_parallel_corridors` | >1 where several corridors produce the same station pair (581 edges). |
| `parallel_differs` | `True` on the 124 where the parallel routes differ by more than 1 km — these are genuinely distinct physical routes and matter for redundancy analysis. |
| `is_colocated` | `True` on the 249 edges shorter than 50 m, i.e. co-located stations. |
| `any_stitch` | `True` where the edge was created by attaching a corridor chain to its junction endpoint rather than measured between two placed stations. |
| `service_direct` | Trains listing this exact pair as consecutive stops. **Under-counts** — see below. |
| `service_load` | Trains actually traversing this edge, from projecting every service pair onto its physical path. **Use this one.** |
| `attr_complete`, `recon_clean`, `core_v2`, `core_v4` | View flags — see "Two views" below. |

## service_edges.csv

Station pairs that are consecutive stops on at least one train. `n_trains` is
the frequency; `runtime_min_median` / `_p10` / `_p90` the observed run-time
spread; `physical_hops` how many physical edges that service leg spans
(1 = direct, 2–3 = skip-stop express). The `day` column in the raw schedules
is unreliable — it reaches 12 on trains that finish within a day — so
run-times are computed by wrapping into 24 hours and the `day` column is not
used at all.

---

## Two views, not two graphs

Do not build a smaller graph. Build the full one and switch views with a flag.

- **Topology view — all 9,689 edges.** Use for criticality and resilience.
  These need the real cycle structure and no infrastructure attributes.
- **Attributed view — `core_v4` (8,047 edges) or the looser `core_v2` (8,411).**
  Use wherever an attribute enters the computation: gauge-constrained routing,
  capacity weighting, zone aggregation.

Filtering is not free. Restricting to the attributed core drops independent
cycles and pushes the share of edges that are bridges from 14.6% up past 30% —
a resilience result computed on the filtered core would overstate fragility by
roughly two and a half times, because the filter removed the alternative
routes. That is why the flags exist instead of a separate file.

---

## What was cleaned to produce this

| Problem in the source | Fix |
|---|---|
| Zone spelled in full on corridors, abbreviated on stations — the two could not be joined | One canonical `(zone_code, zone_name)` pair on both, 17 zones |
| Four zone typos: `East Coast Railwa`, `Southen Railway`, `Westem Railway`, and `North Frontier Railway` for the real Northeast Frontier Railway | Corrected in `s02`, before corridor aggregation, so they no longer inflate the zone-conflict count either |
| `?` used as a zone value on 106 stations and 275 trains | Mapped to null |
| `Orissa` and `Odisha` both present | Canonicalised to `Odisha` (65 stations) |
| 2 stations in Bangladesh, silently inside national totals | `in_scope = False` |
| 11 stations sharing 4 coordinates | `coordinate_shared = True` |
| Station zone missing on ~52% of rows | Inferred from the corridor where possible, marked `corridor_inferred`; coverage 45% → 98.9% |
| `day` column in schedules reaching 12 on same-day trains | Not used; run-times derived by 24-hour wrap |
| Service counts under-crediting edges next to express-skipped stations | `service_load` computed by path projection; coverage 80.0% → 89.9% of edges |
| Node identity unresolved — junctions and stations were separate universes | Resolved: station code where a high/medium match exists, typed operational junction otherwise |

Verified clean and needing no fix: no duplicate keys in any file, full
referential integrity across all seven cross-file relationships, no
out-of-India or zero coordinates, no whitespace or case inconsistency in any
key field, and no cross-file disagreement on station names or coordinates.

---

## Known limits carried forward

1. **Spine shortcutting** affects 17.1% of consecutive station pairs, median
   shortfall 5%, 54 pairs over 25%. It biases `length_km` downward where a
   corridor contains a chord. Harmless for topology; a systematic bias for
   distance-weighted accessibility.
2. **Speed is 49–51% complete** and the corridors that have it are scattered,
   not clustered. Requiring it collapses the graph to 771 nodes. Keep nullable.
3. **`state` is 46% complete** on nodes. The station master does not record it.
4. **88 junctions have an ambiguous coordinate** (`coord_method =
   spine_end_ambiguous`) and **40 name matches were rejected** on a spatial
   conflict — both are visible in `graph_inputs/nodes_junctions.csv`.
5. **Zone on 4,874 nodes is inferred**, not stated. Check `zone_source`.

---

## Reproducing

```bash
python 02_graph_inputs/pipeline/run_all.py     # ~50s, stages s01-s09
```

Byte-identical across independent clean runs. Requires `pandas`, `numpy`,
`networkx`, `shapely`, `scipy`, `rapidfuzz`, `pyarrow`.

Nothing in `01_data_engineering/` is modified by the pipeline — the raw
sources and the notebook outputs stay exactly as they were.
