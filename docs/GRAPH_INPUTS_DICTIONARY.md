# Data Dictionary — `02_graph_inputs/graph_inputs/` (intermediate package v1.0)

> **This documents the intermediates, not the hand-off.**
> The dataset to build the graph from is `02_graph_inputs/graph_dataset/`, and its
> own `README.md` is the dictionary for it. The tables below are the working
> files that dataset was assembled from — canonical junctions, corridor
> spines, station matches, placements. They are still shipped and still
> regenerated every run, because they let edge construction be redone under
> different rules. You do not need them to build the graph.


Every file here is produced by `02_graph_inputs/pipeline/run_all.py` from the raw sources only.
The whole package regenerates deterministically in ~30 seconds. Nothing in this
folder should be hand-edited — change the pipeline and re-run.

Producer for every file: `02_graph_inputs/pipeline/` (stage noted per table).
Sources: `Railway_Network_.csv`, `Railway_Network_.geojson`, `01_data_engineering/processed_data/cleaned_stations.csv`.

---

## Primary hand-off tables

These two are what graph construction consumes.

### `nodes_junctions.csv` — 2,029 rows (stage 08)

One row per canonical junction. This is the candidate node table for a
junction-level graph, and the anchor set for a station-level graph.

| Column | Meaning |
|---|---|
| `junction_id` | Stable identifier `J00001`… Use this as the node key, not the name. |
| `canonical_junction_name` | Whitespace/newline-normalised junction name. Unique. |
| `junction_class` | `station_like`, `cabin`, `yard`, `block_hut`, `bypass`, `chord`, `siding`, `goods`, `loco`, `gate`, `bridge`. Operational classes are *not expected* to appear in a passenger station master — a missing match there is not a data gap. |
| `n_raw_variants` / `raw_variants` / `merged_from_variants` | How many raw source spellings collapsed into this junction, and which. 36 junctions merged ≥2 variants. |
| `longitude`, `latitude` | WGS84 coordinate **derived from corridor geometry**, not from the station master. Present for 2,028 / 2,029. |
| `coord_method` | `spine_end_consensus` (1,403 — multiple corridors agree), `spine_end_by_elimination` (537), `spine_end_ambiguous` (88 — degree-1 junction whose partner was also unresolved; treat as low confidence). |
| `n_incident_corridors`, `n_corridors_agreeing`, `agreement_ratio` | Consensus strength behind the coordinate. |
| `cluster_spread_km` | Max distance between the agreeing corridor ends. Median 154 m. >1 km on 207 junctions = inspect. |
| `match_method` | `exact_name`, `relaxed_name`, `fuzzy_name`, `spatial_only`, `exact_name_out_of_radius`, `none`. |
| `station_code`, `station_name` | Matched station-master entry, or blank. |
| `name_score` | 100 for exact/relaxed; rapidfuzz WRatio for fuzzy. |
| `spatial_gap_km` | Distance between the junction's geometry coordinate and the matched station. The primary trust signal. |
| `match_confidence` | `high` (1,206), `medium` (349), `low` (200), `rejected_name_spatial_conflict` (40), `none` (234). **Filter on this.** |
| `nearest_station_code`, `nearest_station_km` | The purely spatial alternative, always reported. |
| `corridor_degree` | Number of corridors incident to this junction. |

### `corridor_station_sequence.csv` — 12,305 rows (stage 07)

**The core deliverable.** Which stations lie on each corridor, in physical order.

| Column | Meaning |
|---|---|
| `corridor_id` | FK to `corridors_enriched.csv`. |
| `corridor_a`, `corridor_b` | The corridor's two canonical junctions. `measure_km = 0` is at `corridor_a`. |
| `sequence_index` | 1-based position along the corridor. Verified monotonic in `measure_km` for all 2,278 corridors. |
| `station_code`, `station_name` | FK to `01_data_engineering/processed_data/cleaned_stations.csv`. |
| `station_longitude`, `station_latitude` | Station-master coordinate. |
| `measure_km` | **True geodesic** distance along the corridor spine from `corridor_a`, in km. **Inter-station distance is a subtraction of two measures** — this is your edge weight. Guaranteed monotonic within a corridor and never greater than the spine's own length. |
| `offset_km` | **True geodesic** perpendicular distance from the station to the spine. Median 41 m. 643 placements exceed 1.5 km — weak, consider excluding. |
| `is_corridor_endpoint` | First or last station in this corridor's sequence. |
| `station_n_corridors` | How many corridors this station was placed on. 1,001 stations sit on >2 corridors (parallel/adjacent lines) — an ambiguity to resolve when building edges. |

---

## Corridor tables

### `corridors_enriched.csv` — 2,279 rows (stage 08) — *use this one*

`corridors.csv` (stage 02) plus reconstruction and station-placement columns.
Superset of `corridors.csv`; that file is kept only as the raw stage-02 output.

| Column | Meaning |
|---|---|
| `corridor_id` | Stable identifier `C00001`… |
| `corridor_a`, `corridor_b` | Canonical junction names, **sorted** — the corridor key is an unordered pair, because physical track A–B is the same infrastructure as B–A. |
| `observed_directions` | `a_to_b`, `b_to_a`, or `both` (8 corridors) — preserves the direction(s) the raw source recorded, so a directed view is still derivable. |
| `segment_count` / `n_segments` | Raw GIS sub-segments aggregated into this corridor (1 to 712). |
| `geodesic_length_km` | **True great-circle length of the corridor geometry. Use this as a distance weight.** |
| `declared_shape_length_km` | Sum of the source `st_lengthshape` field. Systematically ~9% larger (median ratio 1.0902) because the source value is computed in a projected CRS. Kept for traceability only. |
| `length_inflation_ratio` | `declared / geodesic`. |
| `spine_length_km`, `spine_coverage`, `spur_length_km` | Reconstructed main path length, its share of total corridor geometry, and the remainder (sidings/branches). |
| `reconstruction_status` | `clean_path` (2,166), `fragmented` (72), `path_with_spurs` (38), `loop` (2), `degenerate_no_edges` (1). |
| `n_components` | Connected pieces of the corridor's own geometry. >1 means a physical/digitisation gap. |
| `speed_kmph`, `gauge`, `no_of_lanes`, `railway_zone`, `declared_no_of_stations`, `declared_track_length_km` | Modal value across the corridor's segments. |
| `<attr>_conflict`, `<attr>_n_distinct` | Whether segments disagreed on that attribute and how many distinct values existed. 200 corridors have ≥1 conflict. |
| `<attr>_zero_segments` | Count of segments where the attribute was `0`. **Zeros are treated as UNKNOWN (NaN), never imputed** — this is why `speed_kmph` is missing on 1,144 corridors here versus 815 in the old file. |
| `bridge_present`, `tunnel_present` | True if any segment flagged one. |
| `zone_count` | Distinct railway zones spanned (59 corridors span >1). |
| `is_self_loop` | `corridor_a == corridor_b` (5 corridors). |
| `n_stations_found`, `station_count_delta`, `median_offset_km` | Station placement result and its disagreement with the GIS `noofstations` attribute. |
| `orientation` | `as_built` or `reversed_to_a` — whether the spine was flipped to make measure 0 = `corridor_a`. |

### `corridor_paths.csv` — 2,279 rows (stage 04)

Reconstruction diagnostics per corridor: `status`, `n_nodes`, `n_components`,
`n_terminals`, `spine_coverage`, `n_parallel_segments`, `n_degenerate_segments`,
`main_component_share`, `snap_tolerance_m` (10 m — endpoints closer than this
were treated as the same node).

### `corridor_sequence_summary.csv` — 2,278 rows (stage 07)

Per-corridor station-placement summary, including
`spine_geodesic_km` (the length `measure_km` is relative to),
`max_gap_between_stations_km` (a long gap suggests stations missing from the
master) and `station_count_delta` versus the declared attribute.

---

## Provenance / audit tables

### `junctions_canonical.csv` — 2,029 rows (stage 01)
Canonical junction list with raw variants. Superseded by `nodes_junctions.csv`
for consumption; kept as the stage-01 audit record.

### `junction_name_crosswalk.csv` — 2,066 rows (stage 01)
Raw source spelling → canonical name, with `needed_normalisation` (57),
`had_embedded_newline` (8) and `had_edge_whitespace` (50). This is the audit
trail for the whitespace bug that split the old graph into extra components.

### `junction_coordinates.csv` — 2,029 rows (stage 05)
Coordinate derivation detail. Folded into `nodes_junctions.csv`.

### `junction_station_matches.csv` — 2,029 rows (stage 06)
Full matching detail including `n_stations_within_radius` and every rejected
candidate reason. Folded into `nodes_junctions.csv`.

### `segments_quarantined.csv` — 1,004 rows (stage 02)
Raw GIS segments excluded from all corridors because both endpoint names are
missing. Retained rather than silently dropped. All 1,004 are
`both_endpoints_missing`.

### `QA_SUMMARY.txt`
Machine-generated integrity report, rewritten on every pipeline run.

---

## Known limits of this package

1. 88 junction coordinates rest on an ambiguous degree-1 assignment (`coord_method = spine_end_ambiguous`).
2. 40 junctions have an exact name match that is geographically impossible (>15 km away) and were deliberately left unmatched rather than accepted.
3. 1,001 stations sit within 2 km of more than two corridors; deciding which corridor "owns" such a station is a graph-engineering choice.
4. 140 corridors have no station placed within 2 km — mostly short yard/cabin links.
5. 72 corridors remain geometrically fragmented; their spine covers only the largest piece (`main_component_share`, median 0.815).
6. Station placement agrees with the GIS `noofstations` attribute within ±3 on 65% of corridors (correlation 0.49). Moderate corroboration, not proof — the two count slightly different things.
7. **Spine shortcutting.** The spine is the shortest path through the corridor's own geometry between its two ends. Where a corridor contains a chord or a parallel line, that shortcut can become the spine, and stations on the bypassed stretch are then projected onto it - compressing their `measure_km`. Measured on 10,167 consecutive station pairs: 1,741 (17.1%) show an along-line distance shorter than geometrically possible, median shortfall 5.0%, with 542 pairs above 10% and 54 above 25%. Affects `clean_path` corridors too (17%), so `reconstruction_status` does not predict it. Re-measured on every pipeline run - see the SPINE SHORTCUT CHECK section of `QA_SUMMARY.txt`. Detect affected pairs yourself with: `crow_flies > sqrt(delta_measure**2 + (offset_a + offset_b)**2)`.
8. Schedules have not been used anywhere in this package. They remain an independent evidence layer.
