# Data Dictionary — Rail-Intell

This document describes every column in the graph-relevant datasets.  
Only columns that actually exist in the files are documented here.  
Schemas were verified directly from the files on 2026-09-27.

---

## Graph Artifacts

### `rail_edges_initial.csv`

**Location:** repository root  
**Shape:** 2,257 rows × 15 columns  
**Source:** Aggregated from `Railway_Network_.csv` (116,218 filtered GIS records)  
**Produced by:** `Railway_networks_EDA.ipynb`  
**Description:** One row per unique ordered junction pair (conceptual directed edge). Multiple raw GIS sub-segments with the same junction pair are collapsed into a single row using mode/sum aggregation.

| Column | Type | Missing | Meaning | Source field |
|--------|------|---------|---------|--------------|
| `edge_id` | int | 0 | Sequential identifier (1–2,257) | Assigned |
| `fromjunction` | str | 0 | Origin junction name (free text) | `fromjunction` in `Railway_Network_.csv` |
| `tojunction` | str | 0 | Destination junction name (free text) | `tojunction` in `Railway_Network_.csv` |
| `record_count` | int | 0 | Number of raw GIS sub-segments aggregated into this edge | Computed |
| `geometry_length_m` | float | 0 | Sum of `st_lengthshape` across sub-segments (metres) | Sum of `st_lengthshape` |
| `speed` | float | 815 | Modal speed limit (km/h) across sub-segments | Mode of `speed` |
| `gauge` | str | 1 | Modal gauge type: `Broad Gauge`, `Metre Gauge`, `Narrow Gauge`, `Standard Gauge` | Mode of `type` |
| `no_of_stations` | float | 0 | Modal count of intermediate stations in the corridor | Mode of `noofstations` |
| `track_length` | float | 0 | Modal declared track length (km) | Mode of `tracklength` |
| `no_of_lanes` | float | 53 | Modal number of parallel tracks | Mode of `nooflanes` |
| `bridge_present` | bool | 0 | `True` if any sub-segment has a bridge (`bridge_yn = Y`) | Any of `bridge_yn` |
| `tunnel_present` | bool | 0 | `True` if any sub-segment has a tunnel (`tunnel_yn = Y`) | Any of `tunnel_yn` |
| `railway_zone` | str | 0 | Modal railway zone name (e.g. `Northern Railway`) | Mode of `railwayzone` |
| `zone_count` | int | 0 | Number of distinct railway zones in the sub-segments (1 = single zone; >1 = cross-zone corridor) | Count of unique `railwayzone` |
| `geometry_length_km` | float | 0 | `geometry_length_m / 1000` — total corridor length in km | Derived |

**Gauge distribution:** Broad Gauge 2,196 / Metre Gauge 32 / Narrow Gauge 27 / Standard Gauge 1 / NaN 1  
**Zone distribution:** 17 railway zones represented; 78 edges span 2 zones; 1 spans 3.

---

### `junction_nodes_initial.csv`

**Location:** repository root  
**Shape:** 2,024 rows × 10 columns  
**Source:** Derived from `rail_edges_initial.csv`  
**Produced by:** `Railway_networks_EDA.ipynb`  
**Description:** One row per unique junction name. Every name appearing as `fromjunction` or `tojunction` in the edge file has exactly one node record.

| Column | Type | Missing | Meaning |
|--------|------|---------|---------|
| `junction_name` | str | 0 | Junction name as it appears in the raw data |
| `node_id` | int | 0 | Sequential identifier (1–2,024) |
| `out_degree` | float | 0 | Number of directed edges leaving this node |
| `in_degree` | float | 0 | Number of directed edges entering this node |
| `unique_out_neighbours` | float | 0 | Number of unique adjacent nodes reachable by outgoing edges |
| `unique_in_neighbours` | float | 0 | Number of unique adjacent nodes that can reach this node |
| `total_degree` | float | 0 | `out_degree + in_degree` |
| `unique_neighbours` | float | 0 | Total unique adjacent nodes (undirected view) |
| `component_id` | int | 0 | Connected component membership (1 = largest component) |
| `normalized_name` | str | 0 | Name after whitespace-collapse and punctuation normalisation — used to detect potential duplicate junctions |

**Note:** No latitude/longitude is stored in this file. Geographic coordinates must be obtained by joining to `cleaned_stations.csv` via the name-matching results (727 of 2,024 junctions have a verified name match).

---

### `railway_components_initial.csv`

**Location:** repository root  
**Shape:** 113 rows × 6 columns  
**Source:** NetworkX connected-component analysis of `rail_edges_initial.csv`  
**Produced by:** `Railway_networks_EDA.ipynb`  
**Description:** One row per connected component of the undirected junction graph.

| Column | Type | Missing | Meaning |
|--------|------|---------|---------|
| `component_id` | int | 0 | Rank by size (1 = largest). Matches `component_id` in `junction_nodes_initial.csv` |
| `nodes` | int | 0 | Number of junction nodes in this component |
| `edges` | int | 0 | Number of edges in this component |
| `total_length_km` | float | 0 | Sum of `geometry_length_km` for all edges in this component |
| `zones` | int | 0 | Number of distinct railway zones in this component |
| `self_loops` | int | 0 | Number of self-loop edges (fromjunction = tojunction) in this component |

**Main component (component_id = 1):** 1,758 nodes / 2,101 edges / 73,567 km / 17 zones / 4 self-loops  
**Component 2 (next largest):** 8 nodes / 7 edges / 142 km / 1 zone

---

## Processed Data

### `processed_data/cleaned_stations.csv`

**Location:** `processed_data/`  
**Shape:** 8,990 rows × 12 columns  
**Source:** `railways-master/stations.json` (GeoJSON FeatureCollection)  
**Produced by:** `01_Final_Data_Preprocessing_and_Validation.ipynb`  
**Description:** Station master dataset. One row per Indian railway station. All station codes verified unique.

| Column | Type | Missing | Meaning |
|--------|------|---------|---------|
| `station_code` | str | 0 | Unique station code — **primary identifier** (e.g. `HWH`, `NDLS`, `TEN`). Always uppercase, 0 whitespace issues. |
| `station_name` | str | 1 | Full station name. 1 record has an empty name (code `P`). |
| `state` | str | 4,593 | Indian state name |
| `zone` | str | 4,532 | Railway zone abbreviation (e.g. `NR`, `ER`, `SR`) |
| `address` | str | 4,593 | Address string |
| `longitude` | float | 293 | WGS84 longitude (°E). Range: 68.97–95.73 |
| `latitude` | float | 293 | WGS84 latitude (°N). Range: 8.09–33.74 |
| `spatially_usable` | bool | 0 | `True` if both `longitude` and `latitude` are present (8,697 of 8,990) |
| `missing_geometry` | bool | 0 | `True` if longitude or latitude is null |
| `missing_metadata` | bool | 0 | `True` if `state`, `zone`, and `address` are all null |
| `missing_name` | bool | 0 | `True` if `station_name` is empty |
| `data_quality_status` | str | 0 | `complete` / `missing_metadata` / `missing_geometry` / `missing_geometry_and_metadata` |

**Quality counts:** complete 4,270 / missing_metadata 4,427 / missing_geometry 188 / missing_geometry_and_metadata 105  
**Coordinate validation:** 0 stations outside India's geographic bounds. 11 stations share coordinates in 4 groups.

---

### `processed_data/cleaned_schedules.csv`

**Location:** `processed_data/`  
**Shape:** 416,970 rows × 22 columns  
**Source:** `railways-master/schedules.json` (417,080 raw records; 110 consecutive-duplicate stops removed)  
**Produced by:** `01_Final_Data_Preprocessing_and_Validation.ipynb`  
**Composite key:** `(train_number, station_code, stop_sequence)` — verified 0 duplicates

| Column | Type | Missing | Meaning |
|--------|------|---------|---------|
| `train_number` | str | 0 | Train identifier (e.g. `"12301"`) — matches `cleaned_trains.csv` |
| `train_name` | str | 8 | Train name |
| `station_code` | str | 0 | Station code — **matches `station_code` in `cleaned_stations.csv`** |
| `station_name` | str | 2 | Station name from schedule source |
| `arrival` | str | 27,828 | Arrival time (`HH:MM:SS`); null for first stop of each train |
| `departure` | str | 27,819 | Departure time (`HH:MM:SS`); null for last stop of each train |
| `day` | float | 22,561 | Day number of the schedule (relative to journey start) |
| `id` | int | 0 | Source record identifier from `schedules.json` |
| `stop_sequence` | int | 0 | 1-indexed stop position within the train's route (no gaps verified) |
| `schedule_origin` | str | 0 | First station code in this train's schedule |
| `schedule_destination` | str | 0 | Last station code in this train's schedule |
| `stop_count` | int | 0 | Total number of stops for this train |
| `origin_match` | bool | 0 | `True` if `schedule_origin` matches `from_station_code` in train record |
| `destination_match` | bool | 0 | `True` if `schedule_destination` matches `to_station_code` in train record |
| `endpoint_consistent` | bool | 0 | `True` if both origin and destination match the train record |
| `endpoint_mismatch_type` | str | 0 | `none` / `origin_only` / `destination_only` / `both` |
| `station_master_name` | str | 2 | Station name looked up from `cleaned_stations.csv` for this stop's code |
| `station_name_match` | bool | 0 | `True` if schedule station name matches station master (normalised comparison). 0 mismatches found. |
| `missing_arrival` | bool | 0 | `True` if `arrival` is null |
| `missing_departure` | bool | 0 | `True` if `departure` is null |
| `missing_day` | bool | 0 | `True` if `day` is null |
| `schedule_data_quality` | str | 0 | `complete` (all timing fields present) / `partial` (any timing field missing) |

**Quality counts:** complete 384,012 / partial 32,958  
**Endpoint mismatch trains:** 19 (of 5,208 trains)

---

### `processed_data/cleaned_trains.csv`

**Location:** `processed_data/`  
**Shape:** 5,208 rows × 34 columns  
**Source:** `railways-master/trains.json` (GeoJSON FeatureCollection)  
**Produced by:** `01_Final_Data_Preprocessing_and_Validation.ipynb`

| Column | Type | Missing | Meaning |
|--------|------|---------|---------|
| `train_number` | str | 0 | Unique train identifier — **primary key** |
| `train_name` | str | 1 | Train name |
| `from_station_code` | str | 0 | Origin station code — matches `station_code` in station master |
| `from_station_name` | str | 0 | Origin station name |
| `to_station_code` | str | 0 | Destination station code |
| `to_station_name` | str | 0 | Destination station name |
| `zone` | str | 15 | Railway zone abbreviation |
| `type` | str | 15 | Train type (e.g. `DEMU`, `SF`, `Pass`, `Exp`) |
| `distance` | float | 15 | Total route distance (km) |
| `duration_h` | float | 15 | Journey duration — hours component |
| `duration_m` | float | 15 | Journey duration — minutes component |
| `arrival` | str | 15 | Arrival time at destination |
| `departure` | str | 15 | Departure time from origin |
| `return_train` | str | 599 | Train number of the return service (null if no return) |
| `classes` | str | 5,208 | Class string from source (always null in this dataset — all 5,208 missing) |
| `first_ac` | int | 0 | 1 if First AC available, else 0 |
| `second_ac` | int | 0 | 1 if Second AC available, else 0 |
| `third_ac` | int | 0 | 1 if Third AC available, else 0 |
| `sleeper` | int | 0 | 1 if Sleeper available, else 0 |
| `first_class` | int | 0 | 1 if First Class available, else 0 |
| `chair_car` | int | 0 | 1 if Chair Car available, else 0 |
| `geometry` | str | 0 | LineString geometry as string (route waypoints from source GeoJSON) |
| `coordinate_count` | int | 0 | Number of coordinate points in the route geometry |
| `geometry_usable` | str | 0 | Quality flag for route geometry |
| `geometry_quality_status` | str | 0 | Detailed geometry quality label |
| `missing_distance` | bool | 0 | `True` if `distance` is null |
| `distance_quality_status` | str | 0 | `complete` / `missing` |
| `missing_duration` | bool | 0 | `True` if `duration_h` or `duration_m` is null |
| `missing_classes` | bool | 0 | `True` if `classes` is null |
| `operational_data_complete` | bool | 0 | `True` if distance, duration, and classes are all present |
| `from_station_exists` | bool | 0 | `True` if `from_station_code` exists in station master |
| `to_station_exists` | bool | 0 | `True` if `to_station_code` exists in station master |
| `from_name_match` | bool | 0 | `True` if `from_station_name` matches station master name (normalised) |
| `to_name_match` | bool | 0 | `True` if `to_station_name` matches station master name (normalised) |

**Notes:** 15 trains have all operational metrics missing. 9 trains have fewer than 2 route coordinates (degenerate geometry). The `classes` column is always null for all 5,208 trains — the class information is encoded in the six binary flag columns (`first_ac` through `chair_car`).

---

## Source / Raw Data

The following raw files are the upstream sources. Do not modify them.

| File | Format | Records | Description |
|------|--------|---------|-------------|
| `Railway_Network_.csv` | CSV | 119,446 | Raw GIS railway segment table. Primary source for graph edges. |
| `Railway_Network_.geojson` | GeoJSON | 119,446 | Geometry for all GIS segments. Used for spatial endpoint extraction. |
| `railways-master/stations.json` | GeoJSON | 8,990 | Source for station master. |
| `railways-master/trains.json` | GeoJSON | 5,208 | Source for train metadata. |
| `railways-master/schedules.json` | JSON | 417,080 | Source for schedule stop records. |

---

## Reference-Only Data

These files are not integrated into the main graph pipeline.

| File | Records | Description |
|------|---------|-------------|
| `archive (5)/list_of_stations.json` | 13,147 | Station list with `station_code`, `station_name`, `region_code`. No coordinates. |
| `Indian_Railway_Stations_JSON-master/railwayStationsList.json` | 4,598 | Station list with `stnCode`, `stnName`, `stnCity`. No coordinates, no zone. |
| `gauge_history_1947_1971_2025.csv` | 56 | Historical gauge-wise route km by year. |
| `zone_electrification_2021.csv` | 19 | Zone-wise electrification status (2021). |
| `Table-19.2-Zone-wise.csv` | 37 | Zone-wise passenger/freight statistics. |
| `datafile.csv` | 36 | Zone-wise traffic and earnings (2009–10, 2010–11). |
| `RS_Session_267_AS_371_A_i.csv` | 17 | Bridge count by zone (Parliamentary data). |
