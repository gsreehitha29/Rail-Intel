# Schema reference — graph v1.4

**Generated** by `04_analysis_modules/E-712_dataset_package/gen_schema.py` from the
shipped files. Do not edit: regenerate with `make schema`. Every count below is measured,
which is why this file exists — the hand-maintained dictionary drifted from the schema and
`docs/DATA_DICTIONARY.md` still describes a pre-v1.4 shape.

Read `FITNESS.md` before using the data and `docs/STABILITY.md` before building on it.
The supported entry point is:

```python
import sys; sys.path.insert(0, "03_graph_construction")
from railgraph.release import load_graph, load_service, load_resolver, release_info
```

## The four columns that decide whether an analysis is valid

| column | file | why it matters |
|---|---|---|
| `length_is_lower_bound` | edges | 25.3% of route km is a straight-line floor, not a measurement. Any kilometre total must say so. |
| `speed_used_kmph`, `travel_time_min` | edges | Declared speeds are unusable. Use `observed_speed_kmph` from the service layer. |
| `service_load` vs `trains_per_day` | edges / service | Distinct-train counts overstate daily traffic 2.03× and reorder 49 of the 100 busiest sections. |
| `in_giant` | nodes | 0.41% of nodes sit outside the giant component and are unreachable from it. |

## Tables

### `open/nodes.csv` — 9,095 rows, 24 columns

| column | type | non-null | distinct | example | meaning |
|---|---|---|---|---|---|
| `node_id` | str | 9,095 (100%) | 9,095 | `AA` | Primary key. Stable for the lifetime of the release (docs/STABILITY.md). Usually the station code. |
| `node_type` | str | 9,095 (100%) | 2 | `station` | `station` or `junction` - a junction is an operational point with no passenger stop. |
| `node_name` | str | 9,095 (100%) | 9,023 | `ATARIA` | Station name as it appears in the source. Not normalised; renames coexist (see FITNESS.md §6). |
| `station_code` | str | 8,621 (95%) | 8,621 | `AA` | Indian Railways station code where one is known. Join through `load_resolver()`, never directly. |
| `longitude` | float64 | 9,094 (100%) | 9,072 | `80.861033` | WGS84 decimal degrees. |
| `latitude` | float64 | 9,094 (100%) | 9,075 | `27.172457` | WGS84 decimal degrees. |
| `coordinate_source` | str | 9,095 (100%) | 2 | `v1.2` | Which input supplied the position. |
| `state` | str | 9,088 (100%) | 31 | `Uttar Pradesh` | State or union territory, assigned by point-in-polygon against datameet Admin2 (D-052). |
| `state_source` | str | 9,095 (100%) | 2 | `polygon_datameet_ccby4` | How `state` was derived. |
| `zone_code` | str | 8,997 (99%) | 17 | `NER` | Indian Railways zone (NFR, SR, ...). |
| `zone_source` | str | 9,095 (100%) | 3 | `station_master` | How `zone_code` was derived. |
| `state_v12` | str | 6,786 (75%) | 27 | `Uttar Pradesh` | The state this node carried in v1.2, kept for audit. |
| `state_v12_disagrees` | bool | 9,095 (100%) | 2 | `False` | True where the polygon assignment overrode the v1.2 label. |
| `code_identity_suspect` | bool | 9,095 (100%) | 2 | `False` | True where the station code may not identify this place - do not key on it. |
| `coord_fixed` | bool | 9,095 (100%) | 2 | `False` | Which release corrected this node's coordinates, if any. |
| `node_origin` | str | 9,095 (100%) | 1 | `v1.2` | The release or repair module that introduced this node. |
| `merged_from` | float64 | 0 (0%) | 0 | `—` | Node ids merged into this one during construction. |
| `match_confidence` | str | 474 (5%) | 3 | `rejected_name_spatial_confli` | Confidence of the station-to-geometry match that placed this node. |
| `match_method` | str | 474 (5%) | 6 | `exact_name_out_of_radius` | Which matching tier placed it. |
| `overrides_applied` | int64 | 9,095 (100%) | 1 | `0` | Count of OVERRIDES.csv rows that touched this node. |
| `dataset_version` | str | 9,095 (100%) | 1 | `v1.4-open` | Release tag, constant within a release. |
| `component_id` | int64 | 9,095 (100%) | 18 | `0` | Connected component index; 0 is the giant component. |
| `in_giant` | bool | 9,095 (100%) | 2 | `True` | True for the 99.59% of nodes in the giant component. |
| `degree` | int64 | 9,095 (100%) | 7 | `2` | Number of incident sections. Bounded at 7 - see E-710. |

### `open/edges.csv` — 9,759 rows, 35 columns

| column | type | non-null | distinct | example | meaning |
|---|---|---|---|---|---|
| `from_node` | str | 9,759 (100%) | 6,168 | `AA` | Endpoint node_id. Undirected: the pair is unordered. |
| `to_node` | str | 9,759 (100%) | 6,152 | `IJ` | Endpoint node_id. |
| `origin` | str | 9,759 (100%) | 3 | `graph_v1_3/open` | The release this edge came from. |
| `edge_id` | str | 9,759 (100%) | 9,759 | `E000001` | Primary key. Stable for the lifetime of the release. |
| `length_km` | float64 | 9,759 (100%) | 8,345 | `10.604767` | **The length to use.** Route kilometres along track between the two stations. |
| `length_source` | str | 9,759 (100%) | 8 | `spine` | How `length_km` was obtained. `lower_bound_straight_line` means it is a floor, not a measurement. |
| `length_is_lower_bound` | bool | 9,759 (100%) | 2 | `False` | **Check this before summing kilometres.** True where `length_km` is a straight-line floor. |
| `length_chord_km` | float64 | 9,758 (100%) | 9,749 | `10.592509741739208` | Great-circle distance between the endpoints. `length_km` is never below it. |
| `official_km` | float64 | 6,936 (71%) | 67 | `2.0` | Consecutive-stop distance from a timetable, where one exists. Never used to build topology. |
| `official_source` | str | 6,936 (71%) | 2 | `datagovin_2017` | Which timetable supplied `official_km`. |
| `official_conflict` | object | 9,630 (99%) | 2 | `False` | True where official sources disagree with each other beyond tolerance. |
| `official_detour` | object | 9,630 (99%) | 2 | `False` | True where the official distance implies a detour the geometry does not show. |
| `official_sources_disagree` | object | 9,630 (99%) | 2 | `False` | True where two timetables disagree on this pair. |
| `spine_disagrees_official` | object | 9,630 (99%) | 2 | `False` | True where the reconstructed spine length disagrees with the official distance. |
| `raised_to_chord` | object | 9,630 (99%) | 2 | `False` | True where a sub-chord length was raised to the straight-line distance. |
| `length_km_v12` | float64 | 9,630 (99%) | 9,457 | `10.604767` | The length this edge carried in v1.2, kept for audit. |
| `speed_used_kmph` | float64 | 9,624 (99%) | 26 | `90.0` | Declared sectional speed from the source. **Unusable** - use observed runtimes from the service layer. |
| `speed_source` | str | 9,630 (99%) | 5 | `declared_segment` | Where the declared speed came from. |
| `edge_origin` | str | 9,630 (99%) | 1 | `v1.2` | Construction stage that created this edge. |
| `corridor_id` | str | 9,630 (99%) | 2,024 | `C00876` | The reconstructed corridor this section belongs to. |
| `gauge_code` | str | 9,629 (99%) | 4 | `BG` | BG, MG or NG. |
| `zone_code` | str | 9,473 (97%) | 17 | `NER` | Indian Railways zone. |
| `n_tracks` | float64 | 9,571 (98%) | 4 | `1.0` | Declared track count. A row is a *section*, not a track: parallel tracks collapse to one edge. |
| `bridge_present_edge` | object | 9,446 (97%) | 2 | `True` | A civil bridge lies on this section (from the source's flag, not a graph bridge). |
| `tunnel_present_edge` | object | 9,446 (97%) | 2 | `False` | A tunnel lies on this section. |
| `service_direct` | float64 | 9,630 (99%) | 199 | `22.0` | Count of trains calling at both endpoints consecutively. |
| `service_load` | float64 | 9,630 (99%) | 239 | `24.0` | Distinct trains traversing this section. **Overstates daily traffic 2.03x** - use trains_per_day. |
| `suspect_long_edge` | object | 9,630 (99%) | 2 | `False` | Flagged as implausibly long for manual review. |
| `geometry_unsupported` | object | 9,630 (99%) | 2 | `False` | True where no source geometry supports this section. |
| `geometry_source` | str | 9,630 (99%) | 3 | `spine` | Which geometry supported it. |
| `station_match_deficit` | float64 | 9,628 (99%) | 54 | `-4.0` | Difference between declared and matched station counts on the parent corridor. |
| `speed_expected_abs_error_kmph` | float64 | 9,630 (99%) | 2 | `0.0` | Validated error estimate on the declared speed. |
| `travel_time_min` | float64 | 9,624 (99%) | 8,429 | `7.069844666666666` | Derived from `speed_used_kmph`, therefore **unusable**; kept for audit only. |
| `service_source` | str | 9,630 (99%) | 1 | `recomputed_v1.3` | Which service build populated the service columns. |
| `dataset_version` | str | 9,759 (100%) | 1 | `v1.4-open` | Release tag. |

### `service_layer_v1_4/open/service_edges_directed.csv` — 16,703 rows, 13 columns

| column | type | non-null | distinct | example | meaning |
|---|---|---|---|---|---|
| `from_station` | str | 16,703 (100%) | 4,460 | `AADR` | Origin station code. Resolve with `load_resolver()`. |
| `to_station` | str | 16,703 (100%) | 4,458 | `UHL` | Destination station code. |
| `n_trains` | int64 | 16,703 (100%) | 89 | `5` | Distinct trains on this ordered pair. Overstates daily traffic. |
| `trains_per_day` | float64 | 16,703 (100%) | 701 | `3.833` | **The load measure to use.** Distinct dates observed / 30, from September 2024 (E-706). |
| `runtime_min_median` | float64 | 16,200 (97%) | 534 | `24.0` | Observed median running time, minutes. |
| `runtime_min_p10` | float64 | 16,200 (97%) | 1,398 | `21.3` | 10th percentile observed running time. |
| `runtime_min_p90` | float64 | 16,200 (97%) | 1,582 | `27.4` | 90th percentile observed running time. |
| `n_runtime_obs` | int64 | 16,703 (100%) | 79 | `4` | Observations behind the runtime figures. |
| `is_direct_physical_edge` | bool | 16,703 (100%) | 2 | `False` | True where the pair is one section in the physical graph. |
| `physical_path_km` | float64 | 16,653 (100%) | 8,403 | `27.17622` | Shortest physical route distance between the pair. |
| `physical_hops` | float64 | 16,653 (100%) | 66 | `3.0` | Sections on that route. |
| `observed_speed_kmph` | float64 | 16,076 (96%) | 14,557 | `67.9406` | physical_path_km / runtime. **Use this, not declared speed.** |
| `physical_graph_release` | str | 16,703 (100%) | 1 | `graph_v1_4/open` | Which graph release the routing used. |

## Other files in the release

| file | what it is |
|---|---|
| `open/rail_graph_v1_4_open.graphml` | the same graph as GraphML, for tools that prefer it |
| `open/nodes.parquet`, `open/edges.parquet` | convenience copies; **not byte-reproducible** across machines, CSV is canonical |
| `OVERRIDES.csv` | 179 manual decisions with evidence, reapplied on every build (D-054) |
| `station_code_crosswalk.csv` | 68 aliases, 228 absent stations, 39 unresolved codes |
| `gates.json` | the nine release gates, their thresholds and measured values |
| `graph_v1_4.manifest.json` | SHA-256 per input and output, with a `byte_reproducible` flag |
| `FITNESS.md` | what this graph supports, what it never will, and the rule for changing it |
| `VALIDATION_v1_4.md` | the validation report, generated by the build |

## Service layer views

`load_service(what=...)` takes `edges` (directed station pairs, above), `hourly`
(departures by hour), `per_edge` (trains over each physical section) and `frequency`
(per-train running days).

## Completeness

All columns are documented.
