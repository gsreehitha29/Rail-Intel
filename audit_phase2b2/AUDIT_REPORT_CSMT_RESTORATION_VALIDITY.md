# Rail-Intel Phase 2B.2 — CSMT Restoration Validity Audit Report

**Audit Target:** Independent validation of CSMT–Masjid connection loss, evaluation of naive restoration vs physical reality, and determination of defensible graph semantics.  
**Audited Release:** `rail-intel-v2.0-open` (Locked 2026-10-21, SHA-256: `b1e3908167abb2aa91238046e9b25ac50a88ba3645077cb028b45331c449eeda`)  
**Audit Protocol:** Read-Only Audit. Zero modifications to source files, pipeline code, git history, or release artifacts.  
**Audit Workspace:** `audit_phase2b2/`

---

## 1. Intended Design Rules (Handbook & Decisions References)

| Feature / Subsystem | Source Reference | Intended Specification / Rule |
|---|---|---|
| **Station Snapping (O3)** | `docs/DECISIONS.md:1277-1280` (D-062)<br>`03_graph_construction/experiments/E-716_osm_v2_build/osm_build.py:353-364` (`o3_snap`) | Each station or halt in OSM snaps to the single nearest kept track sample within a fixed snap distance of **100 m** (`snap_m = 100.0`). Beyond 100 m, stations remain unsnapped and are listed with reasons (`unsnapped_stations.csv`). |
| **Station Node Identity** | `docs/DECISIONS.md:1300-1306` (D-063)<br>`03_graph_construction/experiments/E-716_osm_v2_build/osm_build.py:501-585` (`station_nodes`) | Snapped OSM stations inside Survey of India outline become graph nodes. Multiple stations with the **same code within 2 km** (`merge_km = 2.0`) are merged into a single station node (intended for multiple platforms or lines). Stations further than 2 km become conflict nodes (`code~osmid`). |
| **Parallel Track Collapse (O2)** | `docs/DECISIONS.md:1270-1275` (D-062)<br>`03_graph_construction/experiments/E-716_osm_v2_build/osm_build.py:190-239` (`o2_collapse`) | Parallel tracks of compatible gauge running within **15 m** (`merge_m = 15.0`) for at least **100 m** (`min_run_m = 100.0`) are collapsed to one track. Diverging ends are rejoined within **30 m** (`connect_m = 30.0`). |
| **Contraction & Pruning (O4)** | `docs/DECISIONS.md:1326-1333` (D-063)<br>`03_graph_construction/experiments/E-716_osm_v2_build/osm_build.py:601-610` (`prune`) | Dangling spurs (nodes of degree $\le 1$ not present in `protect` / `stations`) are mechanically deleted to remove unused dead-end tracks. Degree-2 nodes are spliced out. Bypasses $\le 3\text{ km}$ replaced within $1.2\times\text{len} + 0.2\text{ km}$ are dropped. |
| **Station Throats (O5a)** | `docs/DECISIONS.md:1349-1368` (D-065)<br>`03_graph_construction/experiments/E-716_osm_v2_build/osm_build.py:1108-1175` (`o5_throat`) | Restores through routes over crossover/yard tracks tagged `service=*` (dropped in O1). Where service track $\le 2\text{ km}$ connects two kept points and the existing network route is $> 1.3\times\text{throat} + 0.5\text{ km}$, the throat link is added. |
| **Inter-Component Stitching (O5)** | `docs/DECISIONS.md:1315-1325` (D-063)<br>`03_graph_construction/experiments/E-716_osm_v2_build/osm_build.py:908-1030` (`o5_stitch`) | Runs *before* O4 on track-level graph. Designed strictly to join disconnected components/fragments (`comps[1:]`) to the giant component (`comps[0]`) using OSM track, shared station proximity ($\le 100\text{ m}$), or timetable evidence. |

---

## 2. Evidence and Reproduction Steps

### 2.1 Inspection of Track Chain 4365 and Endpoints
In `03_graph_construction/graph_v2_0_open/work/network_edges.parquet`:
- **Chain 4365:** A 13-section broad-gauge corridor extending 10.13 km from CSMT Platform 1 to Parel.
- **Direct Edge:** Edge `n128794 <-> s3558085`:
  - `km`: `1.416348`
  - `chain`: `4365`
  - `kind`: `'track'`
  - `gauge`: `'1676'` (Broad Gauge)
- **Incident Edges to `n128794`:** Exactly **1** edge (`n128794 <-> s3558085`). Its degree in the Stage C1 network is exactly 1.

### 2.2 Nature of Identifiers across Artifacts
| Identifier | Artifact File | Type / Semantics | Code Reference | Real-World Identity / Coordinates |
|---|---|---|---|---|
| **`n128794`** | `work/network_vertices.parquet`<br>`work/network_edges.parquet` | **Pipeline Vertex ID**<br>(Prefix `n` = 0-indexed row 128,794 in internal kept nodes table) | `osm_build.py:373`<br>`run_c1.py:84-86` | Raw OSM Node `2175054076`<br>`lon: 72.8351846, lat: 18.9405183`<br>Buffer stop at CSMT Suburban Platform 1/2 |
| **`n289147`** | `work/network_vertices.parquet`<br>`work/station_snaps.csv` | **Pipeline Vertex ID**<br>(Prefix `n` = 0-indexed row 289,147 in internal kept nodes table) | `osm_build.py:373`<br>`run_c1.py:84-86` | Raw OSM Node `4010916316`<br>`lon: 72.8355903, lat: 18.9405574`<br>Buffer stop at CSMT Mainline Platform 8/9 |
| **`s3558085`** | `work/network_vertices.parquet`<br>`work/station_snaps.csv`<br>`work/network_edges.parquet` | **Pipeline Sample ID**<br>(Prefix `s` = densified sample index 3,558,085 along chain 4365) | `osm_build.py:375`<br>`run_c1.py:84-86` | Split point on chain 4365<br>`lon: 72.8381652, lat: 18.9523366`<br>Snap point of station `MSD` (Masjid, 4.7 m away) |
| **`12176277888`** | `work/station_snaps.csv` | **Raw OSM Station Node ID** | `osm_build.py:50`<br>`run_c1.py:93` | Centroid of station `Mumbai CSMT`<br>`lon: 72.8357856, lat: 18.9404925` |
| **`12171122260`** | `work/station_snaps.csv` | **Raw OSM Station Node ID** | `osm_build.py:50`<br>`run_c1.py:93` | Centroid of station `Masjid`<br>`lon: 72.8381771, lat: 18.9522949` |

### 2.3 Station Snapping Verification
In `03_graph_construction/graph_v2_0_open/work/station_snaps.csv`:
- `MSD` (Masjid, node `12171122260`): Snapped to sample `s3558085` at distance **4.7 m**.
- `CSMT` (Mumbai CSMT, node `12176277888`): Snapped to node `n289147` at distance **21.4 m**.
- **Distance between `n128794` and `n289147`:** Exactly **42.89 meters**.
- Because `o3_snap` implements 1-to-1 nearest-sample assignment (`cKDTree.query`), `CSMT` mapped exclusively to `n289147`. Suburban buffer stop `n128794` was left unassociated.

### 2.4 Reproduction of the O4 Pruning Decision
Execution of `reproduce_prune.py` against Stage C1 intermediate tables (`network_edges.parquet`, `station_snaps.csv`) confirmed:
1. In `vertex_graph` (`osm_build.py:587-599`), `vmap` renames vertex `n289147 -> 'CSMT'` and `s3558085 -> 'MSD'`. Vertex `n128794` remains `'n128794'`.
2. Node `'n128794'` enters `G` with `degree = 1` and incident edge `'n128794' <-> 'MSD'` (`km = 1.416348`).
3. In `prune(G, protect)` (`osm_build.py:601-610`), `protect = stations`. Because `'n128794' not in stations` and `degree == 1`, `'n128794'` is placed into `d1` in **Round 1**.
4. `G.remove_nodes_from(d1)` drops node `'n128794'` and permanently deletes edge `'n128794' <-> 'MSD'`.

### 2.5 Why O5 Stitching and O5a Throats Do Not Recover It
1. **Execution Sequence:** In `run_c2.py:126-152`, `o5_throat` and `o5_stitch` execute **BEFORE** `o4_contract`. When O5 runs, edge `n128794 <-> MSD` is still present in the graph; it has not yet been deleted.
2. **Component Isolation:** `o5_stitch` (`osm_build.py:964-967`) only evaluates disconnected fragments (`frags = [c for c in comps[1:] if c & stations]`). Because both `CSMT` and `MSD` are already connected northward to Parel in `comps[0]` (the giant component), neither is a disconnected fragment.
3. **Filter Scope of O5a:** `o5_throat` (`osm_build.py:1120`) specifically filters for ways set aside in O1 tagged with `service=*` (`service=crossover|siding`). Chain 4365 was a mainline running track (`railway=rail, usage=main`), not a service track, so it falls completely outside the scope of `o5_throat`.

---

## 3. Root Cause Assessment: CONFIRMED

The root cause of the missing direct connection between Mumbai CSMT and Masjid in `rail-intel-v2.0-open` is **CONFIRMED**:
- **Mechanism:** Nearest-neighbor point snapping (`o3_snap`, `osm_build.py:353`) bound the single point node for Mumbai CSMT to the Mainline buffer stop `n289147` (21.4 m away). The parallel Suburban buffer stop `n128794` (42.89 m away) was left unassociated.
- **Consequence:** In Stage O4 contraction, `prune(G, stations)` (`osm_build.py:605`) identified `n128794` as an unsnapped degree-1 dangling spur and removed it, destroying the 1.4163 km running track (`chain 4365`) between Platform 1 and Masjid.
- **Failure to Recover:** Neither O5 stitch nor O5a throat addresses intra-component parallel line recovery or multi-platform terminal station topology.

---

## 4. Restoration Validity Assessment: PARTIALLY CONFIRMED / UNCONFIRMED AS NAIVELY PROPOSED

### The Critical Flaw in Naive Chain Restoration
Restoring chain 4365 (`n128794 <-> s3558085`) by itself **DOES NOT RECONNECT CSMT TO MASJID**:
1. Chain 4365 terminates at vertex `n128794` (Platform 1 buffer stop).
2. The official released graph node representing CSMT is `n289147` (Mainline buffer stop).
3. In Stage C1, `n128794` and `n289147` have **NO track connection between them** at the bumper blocks (separated by 42.89 m of station concourse).
4. In `check_csmt_msd_path.py`, the shortest track-bound path between `n128794` and `n289147` in the Stage C1 network was **28.4372 km (29 hops)** via Parel!
5. If one simply prevents the pruning of `n128794`, `n128794` becomes an anonymous degree-1 leaf node in the final graph ending 43 m away from `CSMT`, and `CSMT` itself **remains completely disconnected from Masjid**!

### The Fallacy of Direct Edge Insertion
In Phase 2B.1, Scenario 1 simulated:
$$\text{G.add\_edge('CSMT', 'MSD', km=1.4163)}$$
While this mathematical shortcut fixed the routing distance in testing, it **falsifies the physical graph model** by:
- Teleporting trains across 42.89 meters of passenger concourse between buffer blocks.
- Conflating the Central Railway Slow Line (Suburban Platforms 1–4) with the Fast Line (Mainline Platforms 8–18) at a location where no track switches exist.
- Assuming an ad-hoc fix without establishing consistent multi-platform terminal station semantics across the nationwide graph.

---

## 5. Evidence Gaps

1. **Approach Throat Switch Topology:**
   Where do the physical crossovers between the Suburban Slow lines (Platforms 1–4) and the Mainline Fast lines (Platforms 8–18) exist in OpenStreetMap? Are they present as `service=crossover` tracks north of the platforms, or were they omitted from OSM?
2. **Platform Grouping Semantics:**
   Does the Rail-Intel graph intend for a terminal station to be:
   - A single collapsed node representing all platform buffer blocks?
   - A cluster of platform nodes connected by operational junction switches?
   - A bipartite station model separating passenger transfer connectivity from track movement constraints?
3. **Nationwide Terminus Consistency:**
   How do other major Indian dead-end terminal stations behave under O3 snap and O4 prune?
   - Howrah Junction (`HWH`): 23 platforms
   - Chennai Central (`MAS`): 17 platforms
   - Sealdah (`SDAH`): 21 platforms
   Did nearest-neighbor snapping prune parallel platform approach tracks at these stations as well?

---

## 6. Recommended Next Validation Experiment

Before proposing any canonical fix for a future release (v2.1):
1. **Throat Switch Extraction:** Run an extraction of all OSM ways in the bounding box `[72.825, 18.935, 72.845, 18.960]` (CSMT to Sandhurst Road) including `service=*` and `railway=rail` to map the exact physical switch geometry between Suburban and Mainline tracks.
2. **Terminal Footprint Multi-Snap Simulation:** Test a generalized snapping algorithm where any track dead-end (`degree == 1`) within $R \le 100\text{ m}$ of a terminal station node is mapped to that station's identity (or connected via a zero-length / internal throat link).
3. **National Terminus Audit:** Audit `HWH`, `MAS`, `SDAH`, and `BCT` in `graph_v2_0_open/work/` to verify whether multi-track terminal pruning is a localized Mumbai artifact or a systematic nationwide defect.

---

## 7. File and Line References for Every Code Claim

- `docs/DECISIONS.md:1266-1295`: Calibration parameters (D-062).
- `docs/DECISIONS.md:1296-1337`: Station graph, contraction, and joins (D-063).
- `docs/DECISIONS.md:1349-1375`: Parallel collapse check and station throats (D-065).
- `03_graph_construction/experiments/E-716_osm_v2_build/osm_build.py:353-364`: `o3_snap` nearest-sample query.
- `03_graph_construction/experiments/E-716_osm_v2_build/osm_build.py:371-375`: Pipeline vertex key generation (`n{node_idx}`, `s{sample_idx}`).
- `03_graph_construction/experiments/E-716_osm_v2_build/osm_build.py:501-585`: `station_nodes` selection and 2 km merge rule.
- `03_graph_construction/experiments/E-716_osm_v2_build/osm_build.py:587-599`: `vertex_graph` mapping of vertices to station codes.
- `03_graph_construction/experiments/E-716_osm_v2_build/osm_build.py:601-610`: `prune` leaf node deletion (`d <= 1 and n not in protect`).
- `03_graph_construction/experiments/E-716_osm_v2_build/osm_build.py:701-720`: `o4_contract` execution pipeline.
- `03_graph_construction/experiments/E-716_osm_v2_build/osm_build.py:964-967`: `o5_stitch` fragment definition (`comps[1:]`).
- `03_graph_construction/experiments/E-716_osm_v2_build/osm_build.py:1120-1133`: `o5_throat` service track filtering (`THROAT[0]`).
- `03_graph_construction/experiments/E-716_osm_v2_build/run_c1.py:84-86`: Creation of `network_vertices.parquet` with `osm_node` alignment.
- `03_graph_construction/experiments/E-716_osm_v2_build/run_c2.py:126-152`: Execution sequence showing `o5_throat` and `o5_stitch` running before `o4_contract`.
