# Railway Graph Handoff

> **Prepared for:** Graph-Design Teammate  
> **Phase:** EDA + Data-Preprocessing → Graph Construction  
> **Status:** Initial junction-level railway representation is complete.  
> The final station-level graph has **NOT** been built yet.

---

## 1. Current Project State

The data-engineering phase has completed the following:

- **Railway network EDA:** 119,446 raw GIS segments from `Railway_Network_.csv` have been cleaned, zone-standardised, and aggregated into a junction-level graph representation stored as CSV files.
- **Station master:** 8,990 Indian railway stations (from `railways-master/stations.json`) have been cleaned, coordinate-validated, and quality-flagged.
- **Train metadata:** 5,208 trains have been parsed and cleaned.
- **Schedule data:** 416,970 stop records have been validated against the station master and quality-flagged.
- **Spatial analysis (partial):** GeoJSON endpoint extraction and name-based junction–station matching have been performed. A haversine coordinate-distance validation was implemented but **not executed** in the current notebook version (see [Section 7](#7-station-network-spatial-validation)).

The **graph-construction phase has not started**. The files listed below are the handoff point.

---

## 2. Current Graph Artifacts

### `rail_edges_initial.csv`

| Property | Value |
|----------|-------|
| Location | `rail_edges_initial.csv` (repository root) |
| Row count | **2,257 directed conceptual edges** |
| Source | `Railway_Network_.csv` — 119,446 raw GIS segments |
| Produced by | `Railway_networks_EDA.ipynb` |

**What one row means:** A unique ordered junction pair `(fromjunction → tojunction)`. Each pair may have been represented by 1–711 raw GIS geometry sub-segments; these are aggregated here to one logical edge.

**Important columns:**

| Column | Meaning |
|--------|---------|
| `edge_id` | Sequential identifier (1–2,257) |
| `fromjunction` | Origin junction name (text, e.g. "Tirunelveli Junction") |
| `tojunction` | Destination junction name (text) |
| `record_count` | Number of raw GIS sub-segments this edge aggregates |
| `geometry_length_km` | Sum of GIS geometry lengths across all raw sub-segments (km) |
| `speed` | Modal speed limit for this corridor (km/h) — **815 edges missing** |
| `gauge` | Modal gauge type: Broad Gauge (2,196), Metre Gauge (32), Narrow Gauge (27) |
| `no_of_stations` | Modal count of intermediate stations in corridor |
| `track_length` | Modal declared track length (km) |
| `no_of_lanes` | Modal number of tracks/lanes — **53 edges missing** |
| `bridge_present` | `True` if any sub-segment has `bridge_yn = Y` |
| `tunnel_present` | `True` if any sub-segment has `tunnel_yn = Y` |
| `railway_zone` | Modal railway zone (e.g. "Northern Railway") |
| `zone_count` | Number of distinct zones in this edge's raw sub-segments (78 edges cross 2 zones) |

> **Aggregation method:** Categorical attributes use the **statistical mode** of the raw sub-segments. `geometry_length_km` is the **sum**. `bridge_present`/`tunnel_present` are `True` if **any** sub-segment flags them. This means attribute values may not perfectly represent every sub-segment of a long corridor.

---

### `junction_nodes_initial.csv`

| Property | Value |
|----------|-------|
| Location | `junction_nodes_initial.csv` (repository root) |
| Row count | **2,024 junction nodes** |
| Produced by | `Railway_networks_EDA.ipynb` |

**Relationship to edges:** Every unique junction name appearing as `fromjunction` or `tojunction` in `rail_edges_initial.csv` has one row here.

**Important columns:**

| Column | Meaning |
|--------|---------|
| `junction_name` | Junction name as it appears in the raw data |
| `node_id` | Sequential identifier (1–2,024) |
| `out_degree` | Number of edges leaving this node (directed) |
| `in_degree` | Number of edges entering this node (directed) |
| `total_degree` | `out_degree + in_degree` |
| `unique_neighbours` | Unique adjacent nodes (undirected) |
| `component_id` | Connected component this node belongs to (see below) |
| `normalized_name` | Name after whitespace/punctuation normalisation — used for duplicate detection |

> **No lat/lon in this file.** Geographic coordinates are only available for the 727 junctions whose names were matched to the station master by name normalisation (see [Section 4](#4-critical-identity-problem)).

---

### `railway_components_initial.csv`

| Property | Value |
|----------|-------|
| Location | `railway_components_initial.csv` (repository root) |
| Row count | **113 connected components** |
| Produced by | `Railway_networks_EDA.ipynb` |

**Why this matters:** The railway junction network is **not a single connected graph**. There are 113 disjoint components. Before building any algorithm that assumes global connectivity (e.g., shortest path, centrality across the whole network), the component structure must be understood.

**Important columns:**

| Column | Meaning |
|--------|---------|
| `component_id` | Component rank by size (1 = largest) |
| `nodes` | Number of junction nodes in this component |
| `edges` | Number of edges in this component |
| `total_length_km` | Total track length represented by this component |
| `zones` | Number of distinct railway zones in this component |
| `self_loops` | Number of self-loop edges (fromjunction = tojunction) |

**Largest component (component_id = 1):**  
1,758 nodes / 2,101 edges / ~73,567 km / 17 railway zones / 4 self-loops

The remaining 112 components include 89 isolated junction pairs (2 nodes each).

---

## 3. Station Master

**File:** `processed_data/cleaned_stations.csv`  
**Produced by:** `01_Final_Data_Preprocessing_and_Validation.ipynb`  
**Source:** `railways-master/stations.json`

| Property | Value |
|----------|-------|
| Total stations | **8,990** |
| Unique station codes | **8,990** (0 duplicates) |
| With coordinates | **8,697** (96.7%) |
| Without coordinates | **293** |

**Important columns:**

| Column | Meaning |
|--------|---------|
| `station_code` | Unique uppercase station code (e.g. `HWH`, `NDLS`) — **primary identifier** |
| `station_name` | Full station name |
| `state` | Indian state (missing for 4,593 stations) |
| `zone` | Railway zone abbreviation (e.g. `ER`, `NR`) |
| `address` | Address string (missing for 4,593 stations) |
| `longitude` | WGS84 longitude — present for 8,697 stations |
| `latitude` | WGS84 latitude — present for 8,697 stations |
| `spatially_usable` | `True` if both longitude and latitude are present |
| `data_quality_status` | `complete` / `missing_metadata` / `missing_geometry` / `missing_geometry_and_metadata` |

**Quality breakdown:**

| Status | Count |
|--------|-------|
| `complete` | 4,270 |
| `missing_metadata` (no state/zone/address) | 4,427 |
| `missing_geometry` (no coordinates) | 188 |
| `missing_geometry_and_metadata` | 105 |

**Role in graph construction:** If you build a station-level graph (nodes = stations identified by `station_code`), this is your node table. All coordinates fall within India's geographic bounds. The `station_code` is used as the primary key across all cleaned datasets.

---

## 4. Critical Identity Problem

> **Railway network junction names ≠ station codes. These are two different identifier systems.**

The raw GIS dataset (`Railway_Network_.csv`) identifies locations by **junction names** — free-text strings like `"Tirunelveli Junction"`, `"Madgaon Junction"`, `"Badarpur Junction"`.

The station master uses **station codes** — short uppercase codes like `"TEN"`, `"MAO"`, `"BPB"`.

These were **not designed to be directly joined**. A name-based matching was performed:

| Status | Count |
|--------|-------|
| Total unique junction names in GeoJSON | 2,066 |
| Matched to station master by name normalisation | **727** |
| Currently unmatched (no station master entry found) | **1,339** |

The 727 matched junctions have station-master coordinates available. The **1,339 unmatched junctions currently have no verified geographic coordinates** in this repository.

**Implication:** A junction-level graph built directly from `rail_edges_initial.csv` uses text junction names as node identifiers. A station-level graph built from `cleaned_stations.csv` uses station codes. Bridging these two representations is the **core next task** for the graph-design phase.

---

## 5. Junction Name Normalisation

During EDA, junction names were normalised (whitespace collapsed, punctuation spacing corrected). After normalisation, **36 junction name groups** were found where multiple original names collapse to the same normalised form.

**What this means:** These 36 groups *may* represent the same physical junction entered with slightly different spacing or punctuation in different parts of the raw data.

**What this does NOT mean:** It is not confirmed from the repository that all 36 groups are genuine physical duplicates. Some may be legitimately different junctions with similar names.

**Action required (not performed):** Each of the 36 groups should be inspected. If confirmed as duplicates, they should be merged before finalising the node table. The current `junction_nodes_initial.csv` retains all original names.

The 36 groups are identified in `junction_nodes_initial.csv` via the `normalized_name` column — multiple rows sharing the same `normalized_name` form one such group.

---

## 6. Connected Components

The railway junction network has **113 connected components** when treated as an undirected graph.

| Component | Nodes | Edges | Length (km) | Zones |
|-----------|-------|-------|-------------|-------|
| 1 (main) | 1,758 | 2,101 | ~73,567 | 17 |
| 2 | 8 | 7 | ~142 | 1 |
| 3 | 6 | 5 | ~281 | 2 |
| 4–10 | 4–5 | 3–5 | varies | 1–2 |
| 11–113 | 2–3 | 1–2 | small | 1 |

89 of the 112 non-main components are **isolated junction pairs** (2 nodes, 1 edge).

**Why components matter:**
- Algorithms like shortest-path and centrality only operate within a connected component unless explicitly designed otherwise.
- The 89 isolated pairs may represent: (a) real but disconnected branch lines, (b) data gaps where the connecting junction name does not match, or (c) data errors. **Do not simply merge them** without understanding which case applies.
- The `component_id` column in `junction_nodes_initial.csv` lets you filter to the main component for initial analysis.

---

## 7. Station-Network Spatial Validation

A spatial methodology was implemented in `01_Final_Data_Preprocessing_and_Validation.ipynb` to validate whether the GIS corridor endpoint coordinates (extracted from `Railway_Network_.geojson`) are geographically consistent with the station master coordinates.

**What was completed and verified:**
- GeoJSON endpoint extraction: 236,878 endpoint records, 117,943 unique spatial points
- Corridor boundary detection: 2,210 clean corridors identified
- Name-based junction–station matching: 727 of 2,066 junctions matched
- Name-matched junctions' distance to network geometry: mean 86.7 m, median 30.6 m (696 of 727 within 100 m)
- Corridor endpoint table built for 2,210 clean corridors
- Name-matched corridors: **270 of 2,210** corridors have both endpoints name-matched to station master

**What was NOT executed:**

> The haversine coordinate-distance validation (Cells 211–219 of the notebook, after the status note at Cell 210) was **not run**. The code computes the distance between corridor endpoint coordinates and station master coordinates for the 270 matched corridors, and classifies them by threshold (≤0.1 km, ≤0.5 km, ≤1 km, ≤2 km).
>
> **No threshold results have been verified from this notebook.** The graph teammate should treat the 270-corridor matching as a starting point, not a validated spatial join.

---

## 8. Schedules and Trains

### `processed_data/cleaned_schedules.csv`

| Property | Value |
|----------|-------|
| Rows | 416,970 stop records |
| Unique trains | 5,208 |
| Unique stations | 8,539 |
| Composite key duplicates | 0 |
| Station codes validated against station master | All 8,539 present; 0 mismatches |
| Complete records (all timing fields present) | 384,012 (92.1%) |
| Partial records (missing arrival, departure, or day) | 32,958 (7.9%) |

**Role in the repository:** Schedules are used as **validation data** — confirming that station codes in the schedule exist in the station master and that train endpoints are consistent. They have **not been converted to network edges or OD matrices** in any executed notebook code.

Schedules *could* be used to derive station-to-station service connectivity (consecutive stops within a train define a service link). This has not been implemented.

### `processed_data/cleaned_trains.csv`

| Property | Value |
|----------|-------|
| Rows | 5,208 trains |
| Unique train numbers | 5,208 (0 duplicates) |
| Missing operational metrics | 15 trains |
| Trains with degenerate geometry (<2 route coordinates) | 9 |

**Role:** Train metadata (origin station, destination station, type, distance, duration, accommodation class flags, route geometry). Not used as physical track edges.

---

## 9. Recommended Starting Files

Open these files in this order:

| Priority | File | Purpose |
|----------|------|---------|
| 1 | `rail_edges_initial.csv` | Physical edge list — your primary graph source |
| 2 | `junction_nodes_initial.csv` | Node table with degree and component membership |
| 3 | `railway_components_initial.csv` | Connectivity overview — decide which components to include |
| 4 | `processed_data/cleaned_stations.csv` | Station master — use when building a station-level node set |

Also read:
- `Railway_networks_EDA.ipynb` — understand how the edge/node files were produced
- `01_Final_Data_Preprocessing_and_Validation.ipynb` — understand how stations/trains/schedules were cleaned

---

## 10. Things NOT To Assume

| Assumption | Reality |
|------------|---------|
| Junction name = station code | **False.** These are different identifier systems. Only 727 of 2,066 junctions are name-matched. |
| Every junction has a corresponding station | **Not established.** 1,339 junctions have no verified station-master match. |
| Every graph component should be merged into one | **Do not do this.** 113 components exist for structural reasons. Investigate before merging. |
| Schedule stop transitions = physical railway edges | **Not established.** Schedules record service stops, not physical track. |
| The haversine validation (Cells 211–219) is complete | **False.** Those cells have no executed outputs. |
| Every raw GIS segment = one graph edge | **False.** Up to 711 raw sub-segments aggregate to a single conceptual edge. |
| Speed values are complete | **False.** 815 of 2,257 edges are missing speed. |
| The network is fully connected | **False.** 113 connected components; 89 are isolated junction pairs. |

---

## 11. Next Graph-Design Task

> **Do not start here without reading Sections 4 and 7 above.**

The immediate next task is:

**Resolve the junction-level representation (`rail_edges_initial.csv` / `junction_nodes_initial.csv`) into a reliable station-level representation.**

This means:
1. Investigating the 36 junction-name normalisation groups and merging confirmed duplicates.
2. Determining a method to assign geographic coordinates to the 1,339 currently unmatched junctions (e.g., spatial proximity to `Railway_Network_.geojson` centroids, fuzzy name matching against the station master, or manual lookup).
3. Deciding whether the final graph should use junction nodes, station nodes, or a hybrid representation.
4. Executing and interpreting the haversine validation (Cells 211–219 of the preprocessing notebook) for the 270 name-matched corridors.
5. Deciding how to treat the 112 non-main connected components.

**The methodology for graph construction is the graph teammate's responsibility.** The EDA phase has established the data foundations; it has not prescribed the graph model.


## 12. Validation Results (Final Technical Pass)

A final validation pass was executed on the existing repository data. The following results are VERIFIED from the repository's native analysis logic:

### 12.1. Haversine Spatial Validation (Corridor Endpoints)
**Status: EXECUTED AND VERIFIED**
A minimal compatibility fix was applied to the column mappings, allowing the spatial validation to complete.
- **Evaluated:** 270 corridors (where both endpoints exactly name-matched to the passenger station master).
- **Matching Algorithm:** Total geographic distance (haversine) comparing the GIS segment endpoints to the station master coordinates. Resolves orientation automatically by taking the minimum of (Start→Station1 + End→Station2) vs (Start→Station2 + End→Station1).

**Distance Statistics (Total gap for BOTH endpoints combined):**
- **Count:** 270 corridors evaluated
- **Min:** 0.003 km (3 meters)
- **Median:** 0.655 km (655 meters)
- **Mean:** 7.868 km
- **Max:** 1068.7 km

**Threshold Counts (Corridors where BOTH endpoints pass):**
- ≤ 0.1 km: 31 / 270
- ≤ 0.5 km: 114 / 270
- ≤ 1.0 km: 172 / 270
- ≤ 2.0 km: 219 / 270
- ≤ 5.0 km: 249 / 270

**Outliers:**
- **51** corridors failed the 2 km threshold for at least one endpoint.
- Notable extreme outliers include a >1,000 km mismatch (Algapur to Ramnathpur), which clearly indicates the station master and GIS network share names for geographically different locations (e.g. same name in different states), or a massive digitization error. 
### 12.2. The 36 Junction-Name Normalization Groups
**Status: READY FOR MERGE (Graph-Team Decision)**
The 36 normalization groups (e.g., `"Dadri"` vs `"Dadri "`) are **almost certainly the same physical junctions**. 
- Evidence: In nearly every case, these typographic variants (trailing spaces, double spaces, newlines) split the network into different connected components, usually with one of the variants having a degree of 1. 
- Conclusion: The raw data contains spacing artifacts. Merging these 36 groups by their `normalized_name` will seamlessly reconnect dozens of disjoint components into the main network graph.

### 12.3. Uncoordinated Junctions (1,277 Nodes)
**Status: PARTIALLY RESOLVABLE**
Of the final 2,024 junction nodes, **747** were matched to the passenger station master. The remaining **1,277** currently lack coordinates.
- **260 nodes** are explicit operational infrastructure and *should not* match a passenger station master. These include:
  - 241 Cabins
  - 7 Block Huts
  - 6 Yards
  - 5 Bypasses
  - 1 Track/Chord/Line
- **1,017 nodes** have regular names or "Halt" designations and are likely passenger stations missing from the master or spelled differently.
- Recommendation: Coordinate assignment for the 260 operational nodes must be done geographically (e.g., using the `Railway_Network_.geojson` line geometries) rather than by station master lookups.

### 12.4. Self-Loops (5 Total, 4 in Main Component)
**Status: GENUINE NETWORK ARTIFACTS**
The 5 self-loop edges (`fromjunction == tojunction`) vary significantly in nature:
- **Station/Yard Loops (<0.5 km):** `Khairar Junction` (0.23 km), `Pipar Road Junction` (0.48 km). These are likely internal station turning triangles or yard loops digitized as segments.
- **Bypass/Chord Loops (1–3.5 km):** `Magnesite Bypass Cabin` (1.04 km), `Ahiran Halt` (3.27 km). Likely balloon loops or local bypasses reconnecting to the same junction.
- **Large Loop (11.69 km):** `Biratnagar`. This is either a genuine circular track branch or a data missing an intermediate junction.
- Recommendation: Do not blindly delete. Treat as valid cyclic sub-graphs or yard infrastructure based on length.
