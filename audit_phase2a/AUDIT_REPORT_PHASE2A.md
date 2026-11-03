# Rail-Intel Phase 2A — Read-Only Structural and Provenance Audit Report

**Audit Execution Date:** 2026-11-01  
**Auditor:** Antigravity AI (Pair Programming Assistant)  
**Target Dataset:** `rail-intel-v2.0-open` (Final Locked Release, 2026-10-21)  
**Safety Protocol:** Strict Read-Only Execution. Zero modifications to canonical release data, working graph, source data, or Git history.  
**Audit Workspace:** `audit_phase2a/`

---

## 1. Release Identity & Cryptographic Verification

### 1.1 Canonical Archive Hash Verification
The official release archive was verified via SHA-256 computation against the lock record (`03_graph_construction/release/rail-intel-v2.0-open.LOCK.md`) and manifest:

- **Canonical Zip Archive:** `03_graph_construction/release/rail-intel-v2.0-open.zip`
- **File Size:** 1,429,701 bytes
- **Expected SHA-256:** `b1e3908167abb2aa91238046e9b25ac50a88ba3645077cb028b45331c449eeda`
- **Computed SHA-256:** `b1e3908167abb2aa91238046e9b25ac50a88ba3645077cb028b45331c449eeda`
- **Archive Status:** **VERIFIED (Byte-identical)**

### 1.2 Package Internal Files Verification
Every single member inside the zip archive matches the exact expected SHA-256 and byte length recorded in `manifest.json` and `SHA256SUMS`:

| Relative Path | Size (Bytes) | SHA-256 (computed) | Match Status |
|---|---|---|---|
| `graph/edges.csv` | 1,381,342 | `4d7ee12a47cf35ffdaea78bc6fc1fd23d09fc2688978f4cea37dde6452779001` | **PASS (Exact)** |
| `graph/nodes.csv` | 1,322,472 | `f14a93649429befe2fee5ab3becd11f6c131590ed9bd9cee4d500f882ccae6c0` | **PASS (Exact)** |
| `graph/station_code_crosswalk.csv` | 2,546 | `882471f1f01401e6cb824da12bc7a7ef04493dfff5a974b684e68c6c16521e23` | **PASS (Exact)** |
| `places/edges.csv` | 405,202 | `7332fe998049abb6300ce7d5b48e50cc81b5128b18d200cb3320c79099f616e9` | **PASS (Exact)** |
| `places/nodes.csv` | 685,476 | `a6ee5a86af8d3600fb378ad593b75a671672dfc27ca208c8059e25ceb7e94adc` | **PASS (Exact)** |
| `provenance/code_conflicts.csv` | 838 | `916957800a6d45c8c81b439b0aae3d8e8362c04d94a55d63194cfe94097c6b8a` | **PASS (Exact)** |
| `provenance/joins.csv` | 1,217 | `4ce922e5dc0b3ea15597e9d2177ddecd76e392137d4a94c95a4199149be55274` | **PASS (Exact)** |
| `provenance/throat_links.csv` | 34,520 | `66f8ac562c3fae4f66fdce6c7f1053ab692e9a33719d374f907666625bdfbf39` | **PASS (Exact)** |
| `provenance/wikidata_placements.csv` | 110,345 | `7ac6745a78f61e4b12d0ff2af8ce389552b359aef110d9ff4cdb6fdacad0fe8c` | **PASS (Exact)** |
| `service_2017/station_pairs.csv` | 563,777 | `7da6d38d889b64f05e4e7e9bc50eb81a808aad5ea964fca5cf1b924f93f767cf` | **PASS (Exact)** |
| `manifest.json` | 8,485 | `9523565ab25835283f25f277c101e7ba3bfc2d40318f480317c27a51a3490253` | **PASS (Exact)** |
| `ATTRIBUTION.md` | 799 (zip) / 813 (disk)* | `3078f63c8e896cabe977b057c37aba23f0c2699dea575ca0bd54daca6f774026` | **PASS (LF match)** |
| `CITATION.cff` | 1,137 (zip) / 1,165 (disk)*| `908528d98116853282810c967199c0e937b7c31d5c414af3ee35900b4830fb05` | **PASS (LF match)** |
| `DATASHEET.md` | 3,621 (zip) / 3,685 (disk)*| `6598ca384f3e7a718a337d3fc80fbdb73598d93aab0ed7811ba5ade399764fcc` | **PASS (LF match)** |
| `LICENSE` | 447 (zip) / 455 (disk)* | `2e69c723c398cb61566f78eb73b02971a4f16f877bbb9243a05f20dec60cd899` | **PASS (LF match)** |
| `README.md` | 1,360 (zip) / 1,382 (disk)*| `c6a9de8d93290ac75601b52bcb8fa567a4aef4cf3d363f719871b718240a13c4` | **PASS (LF match)** |

*\*Note: On-disk text/markdown files reflect Windows CRLF checkout normalization (+1 byte per line). When normalized `\r\n` $\rightarrow$ `\n`, hashes match 100%. All data tables (`*.csv`) on disk are bit-for-bit identical to the zip archive and manifest without normalization.*

---

## 2. Part A — Structural Integrity Audit Results

Audited using pure Python standard library and `networkx 3.6.1`. Complete machine-readable output in `audit_phase2a/results/part_a_structural_audit.json`.

| Integrity Metric | Physical Graph (`graph/`) | Places Graph (`places/`) | Status |
|---|---|---|---|
| **Total Nodes** | **12,301** | **10,024** | Expected |
| - Stations | 9,507 | 9,507 | Exact 1:1 match |
| - Operational Junctions | 2,794 | 517 | Reduced by 2,277 (81.5%) |
| **Total Edges** | **13,560** | **10,514** | Expected |
| **Total Route Length** | **70,304.64 km** | **69,842.13 km** | Expected (-462.5 km) |
| **Duplicate Node IDs** | **0** | **0** | Clean |
| **Duplicate Edge IDs** | **0** | **0** | Clean |
| **Missing Edge Endpoints** | **0** | **0** | Clean (100% referential integrity) |
| **Self-loops (`u == v`)** | **0** | **0** | Clean |
| **Duplicate Unordered Pairs** | **0** | **0** | Clean (simple graph) |
| **Edge ID vs Endpoint Match** | **0 mismatches** | **0 mismatches** | Clean (`v2.0:u\|v` format valid) |
| **Missing / Out-of-Bounds Coords**| **0** | **0** | Clean (all inside WGS84 India box) |
| **Invalid / Zero Lengths** | **0** | **0** | Clean (min: 0.0102 km, max: 83.4 km) |
| **Degree Column Discrepancy** | **0** | **0** | Clean (stored == recomputed) |
| **Max Degree** | **4** | **8** | Bounded (no hub artifacts) |
| **Mean Degree** | **2.2047** | **2.0978** | Expected |
| **Isolated Nodes (degree 0)** | **4** | **4** | Listed (`KKD`, `LNLA`, `MFR`, `Hili`) |
| **Dead-end Junctions (degree 1)**| **0** | **0** | Clean (all pruned) |
| **Degree-2 Junctions** | **0** | **0** | Clean (all spliced) |
| **Connected Components** | **8** | **8** | Component count identical |
| - Giant Component Size | 12,268 nodes (99.73%) | 9,991 nodes (99.67%) | Expected |
| - Giant Stations Count | 9,474 stations (99.65%) | 9,474 stations (99.65%) | Exact match |
| - Non-Giant Components | 7 (33 nodes, 33 stations) | 7 (33 nodes, 33 stations) | Exact match |
| **Bridges Count** | **1,849** | **1,799** | -50 in places view |
| **Articulation Points (Cut Vertices)**| **1,805** | **1,747** | -58 in places view |
| - Station Cut Vertices | 1,500 | 1,628 | +128 in places view (absorption) |
| **Independent Cycle Count** | **1,267** | **498** | -769 cycles (60.7% collapsed) |

### 2.1 Chord vs. Length Comparison Details
- **Edges Shorter than Station Crow-Flies Chord:**
  - $\Delta > 0\text{ m}$: 226 edges in Physical graph (due to station point offset from track).
  - $\Delta > 200\text{ m}$: **9 edges** in Physical graph (`audit_phase2a/anomalies/physical_shorter_than_station_chord_gt_200m.csv`).
  - $\Delta > 300\text{ m}$: **5 edges** in Physical graph.
- **Top 3 Extreme Negative Chord Discrepancies (Shorter than straight line):**
  1. `v2.0:DSS|STJT` (Dalsingh Sarai to Sathajagat): Length = 3.3262 km, Chord = 4.6219 km ($\Delta = -1.295\text{ km}$).
  2. `v2.0:GRX|MBDD` (Gaura to Maa Barahi Devi Dham): Length = 10.0931 km, Chord = 11.3341 km ($\Delta = -1.241\text{ km}$).
  3. `v2.0:JN:@77.141397,28.641970|KRTN` (Delhi Ring Railway to Kirti Nagar): Length = 0.7685 km, Chord = 1.7024 km ($\Delta = -0.934\text{ km}$).
  *Root Cause:* The station geographic centroid in OSM was mapped on station buildings or approach roads up to 1 km away from the actual running track platform. When stations are projected onto track (`track_lon`, `track_lat`), the discrepancy drops substantially.
- **Edges Shorter than Track Coordinates Chord by > 200 m:** **7 edges** (e.g. `DSS|STJT` and `GRX|MBDD` persist because OSM station point itself is mislocated or track curve geometry is simplified).
- **Edges Longer than 50 km:** **3 edges** (all verified long corridors: `Thakurganj - Araria New Line` 83.4 km; `Bolangir - Khurda` 72.9 km; `Seoni to Uchhera` 50.3 km). No edges exceed 90 km.
- **Extreme Sinuosity ($\text{Length} / \text{Chord} > 3.0$ and $\text{Length} > 5\text{ km}$):** Exactly **5 edges**, 100% confined to famous mountain railway loops and tunnels:
  - Darjeeling Himalayan Railway: `CBS|RTG` (sinuosity 8.12), `CBS|TDH` (sinuosity 4.47).
  - Kalka-Shimla Railway: `DMP|SWO` (sinuosity 3.30).
  - Matheran Hill Railway: `AMNA|WTP` (sinuosity 4.90), `JTT|WTP` (sinuosity 3.78).
- **Near-Zero Chord ($< 50\text{ m}$):** 240 edges in Physical graph (junction turnouts to platform tracks); contracts to only 5 edges in Places graph.

---

## 3. Part B — Provenance Reconciliation

Complete machine-readable audit in `audit_phase2a/results/part_b_provenance_reconciliation.json`.

### 3.1 Throat Links Reconciliation
- **Provenance Rows:** 745 rows in `provenance/throat_links.csv`.
- **Released Edges Carrying `joins='throat'`:** **462 edges**.
- **Explanation of Discrepancy:**
  The 745 records represent intermediate vertex-to-vertex throat segments identified in Stage O5a. During Stage O4 (pruning, degree-2 splicing, and bypass contraction), series of throat segments and adjoining track were spliced together into 462 canonical sections.
- **Critical Topology Finding:**
  - **19 throat edges act as single-link bridges.** Removing all throat edges shatters the railway network from 8 components into **54 disconnected components**, stranding 386 nodes!
  - 106 throat edges have **zero alternative path** when removed.
  - Critical terminal entrances depend on throat links:
    - `v2.0:CSMT|JN:@72.836140,19.007082` (Mumbai CSMT approach): 779 daily scheduled trains!
    - `v2.0:ANVT|JN:@77.328571,28.660788` (Delhi Anand Vihar Terminal): 68 daily scheduled trains!
  - **Splicing Artifact:** 111 released edges tagged `joins='throat'` are longer than 2.0 km (up to 33.5 km on `JN:...|SMT`, and 19.5 km on `TKMG|UDPR`). This occurred because when a short 30 m throat gap was bridged, the entire spliced section between adjacent stations inherited the `throat` provenance tag.

### 3.2 Network Joins Reconciliation
- **Provenance Rows:** 16 rows in `provenance/joins.csv`.
- **Released Edges Carrying `joins='join_*'`:** **16 edges** (Exact 1:1 match).
  - `join_A2` (Shared station / transfer $\le 100\text{ m}$): **10 edges**.
  - `join_A` (Yard track gap $\le 2\text{ km}$): **4 edges**.
  - `join_C` (Timetable distance fallback): **2 edges**.
- **The Two Timetable-Distance Joins (Stage C):**
  1. `v2.0:DADN|PTP` (Dr. Ambedkar Nagar to Patal Pani): 5.3011 km (Chord = 5.30 km).
  2. `v2.0:SAMN|VGRA` (Samni to Vagara): 9.0000 km (Chord = 8.27 km).
  Both edges represent lines where OSM lacked active running line geometries. Both edges are bridges leading to degree-1 dead-end stations (`PTP` and `VGRA`).
- **Impact of Stage A/A2 Joins:**
  The 14 micro-joins (ranging from 3.8 m to 92.6 m) bridged physical station gaps across different track gauges. Without them, 180 stations across 14 heritage/branch lines (Kalka-Shimla, Nilgiri Mountain, Matheran Hill, Dholpur, Bilimora-Waghai, Pulgaon-Arvi, Pachora-Jamner, Pathankot) would be completely disconnected from the national network.

### 3.3 Wikidata Placements Reconciliation
- **Provenance Rows:** 960 rows in `provenance/wikidata_placements.csv`.
- **Fates:**
  - `not_in_timetable`: 531 (stations in Wikidata but absent from Indian Railways timetable, e.g. RRTS stations, rapid transit, non-operational halts).
  - `inserted`: **351** (stations inserted onto OSM track, matching `manifest.json` `"stations_wikidata": 351`).
  - `alias`: 47 (codes resolved as aliases to existing OSM stations within 300 m).
  - `unresolved`: 27 (timetable codes that could not be placed or snapped to track).
  - `alias_by_name`: 4.
- **Reconciliation:** All 351 inserted stations exist in `graph/nodes.csv` with `coordinate_source == 'wikidata'`.

### 3.4 Code Conflicts Reconciliation
- **Provenance Rows:** 12 duplicate station codes in `provenance/code_conflicts.csv`.
- **Resolution:**
  - 10 codes were successfully resolved: the physical station matching timetable distance retained the clean station code, while the geographic outlier received `code~<osmid>`.
  - 2 codes were unresolved: `INDR` and `MHBD` (no timetable neighbours in graph; both stations received `code~<osmid>`).
- **Graph Representation:** Exactly 14 nodes in `graph/nodes.csv` carry `~` in their `node_id` (10 from resolved pairs + 4 from the 2 unresolved pairs), matching `"stations_conflict": 14` in `manifest.json`.

---

## 4. Part C — Places Graph Comparison

Complete machine-readable audit in `audit_phase2a/results/part_c_places_comparison.json`.

### 4.1 Station Preservation & Contraction
- **Station Count:** Exactly 9,507 stations in Physical graph and 9,507 stations in Places graph (100% preservation, 0 missing, 0 extra).
- **Junction Contraction:** 2,277 junction vertices (81.5%) were collapsed into station representatives or central junction clusters within 1 km.
- **Top Absorbing Stations:**
  - `DSB` (Sadar Bazar, Delhi): Absorbed 48 junction nodes (degree rose to 8).
  - `KGP` (Kharagpur Junction): Absorbed 47 junction nodes (degree = 5).
  - `KYN` (Kalyan Junction, Mumbai): Absorbed 39 junction nodes (degree = 6).
  - `TPKR` (Tikiapara, Kolkata): Absorbed 22 junction nodes (degree = 5).
  - `BVI` (Borivali, Mumbai): Absorbed 18 junction nodes (degree = 4).

### 4.2 Newly Implied Station Adjacency
- Direct station-to-station edges in Physical graph: 7,765 edges.
- Direct station-to-station edges in Places graph: 9,010 edges.
- **Newly Adjacent Station Pairs:** **1,245 pairs** (`audit_phase2a/anomalies/places_newly_adjacent_station_pairs.csv`).
  - *Example:* `AAK` (Ankaikila) and `ANK` (Ankai). In the physical graph, they are connected via an intermediate junction `AAK - JN:... - ANK` (2 hops, 4.9432 km). In the places graph, the junction was absorbed, creating a direct edge `AAK|ANK` of length 4.9432 km.
  - **Distance Preservation:** The newly created direct edge lengths in the places graph match the physical multi-hop shortest paths to sub-meter precision (mean difference < 0.001 km).

### 4.3 Routing Distance Preservation
Across 145 inter-city OD pairs evaluated (spanning Delhi, Mumbai, Kolkata, Chennai, Bengaluru, Guwahati, etc.):
- Delhi (`NDLS`) to Mumbai (`CSMT`): 1371.52 km (Physical) vs 1383.34 km (Places) $\rightarrow$ 0.86% difference.
- Delhi (`NDLS`) to Howrah (`HWH`): 1437.31 km (Physical) vs 1458.45 km (Places) $\rightarrow$ 1.47% difference.
- **Maximum Error:** Across all 145 national pairs, the maximum distance error between the Physical and Places graph is **2.39%**.

---

## 5. Categorized Audit Findings & Anomalies

### 5.1 Structural Failures
**NONE.**  
The release passes 100% of hard referential integrity checks: 0 duplicate node IDs, 0 duplicate edge IDs, 0 missing endpoints, 0 self-loops, 0 duplicate edges, 0 degree mismatches, and 0 invalid coordinates.

### 5.2 Suspicious Anomalies
1. **Severe Negative Chord Discrepancies ($> 1\text{ km}$):**
   - `DSS|STJT` (Dalsingh Sarai to Sathajagat): 1.295 km shorter than straight-line chord.
   - `GRX|MBDD` (Gaura to Maa Barahi Devi Dham): 1.241 km shorter than straight-line chord.
   *Risk:* Track geometry may be truncated or missing intermediate alignment, or station coordinates are placed on distant town centers.
2. **Long Spliced Sections Carrying `throat` Tag:**
   111 edges tagged `joins='throat'` exceed the 2.0 km throat threshold (up to 33.5 km). While benign (a splicing artifact where a 30 m throat caused the entire inter-station section to inherit the tag), it misleads analysts who assume the entire 33.5 km section was an artificial throat link.
3. **Critical Dependence on Unverified Service Tracks:**
   19 throat links are bridges into major terminals (e.g., CSMT Fast Line, Anand Vihar Terminal). If any of these 19 links were erroneously digitized in OSM, major passenger terminals become completely disconnected.

### 5.3 Expected Modelling Behavior
1. **Extreme Sinuosity (5 Edges):** 100% matched to mountain railways (Darjeeling Himalayan, Kalka-Shimla, Matheran Hill Railway).
2. **Isolated Nodes (4 Stations):** Kalakund (`KKD`), Lanela (`LNLA`), Mandla Fort (`MFR`), and Hili (`OSM:1472108324`). These represent heritage lines (Mhow-Kalakund), suspended branch lines, or cross-border stations where connecting track is absent in OSM.
3. **Near-Zero Chords (240 Physical Edges):** Turnout and crossover track links between parallel platforms and junction throats.

### 5.4 Unresolved Items
1. **Station Code Conflict Stalemate (`INDR` and `MHBD`):** Both station pairs remain unresolved with `code~<osmid>` tags because neither had timetable neighbours in the 2017 timetable graph to arbitrate distance.
2. **Mhow Heritage Line Gap:** `PTP` (Patal Pani) is joined to `DADN` via timetable distance (5.3 km), but its connection to `KKD` (Kalakund) remains missing, leaving `KKD` as an isolated degree-0 component.

---

## 6. Topology Risks Ranked by Potential Impact

| Rank | Risk Description | Severity | Impact on Downstream Analysis |
|---|---|---|---|
| **1** | **Terminal Severance from Throat Tag Filtering** | **HIGH** | If an analyst drops `joins == 'throat'` edges assuming they are all low-confidence service tracks, 46 terminal and branch networks (including Mumbai CSMT and Delhi Anand Vihar) are completely severed. |
| **2** | **Understated Inter-Station Route Distances (`DSS|STJT`, `GRX|MBDD`)** | **MEDIUM** | Sections shorter than crow-flies distance by $> 1\text{ km}$ will distort shortest-path routing and train speed imputations across these specific corridors. |
| **3** | **Topological Adjacency Conflation in Places Graph** | **MEDIUM** | In the places graph, 1,245 station pairs appear directly adjacent (degree up to 8). Analysts must not treat this topological adjacency as direct train service or single-track movement without checking service layer routes. |
| **4** | **Unvalidated Timetable-Distance Bridges (`PTP|DADN`, `SAMN|VGRA`)** | **LOW-MEDIUM**| These 2 edges (14.3 km) are pure straight-line/timetable joins with zero OSM track geometry. Downstream physical clearance, speed, or electrification studies cannot run on them. |
| **5** | **Heritage & Suspended Line Fragmentation** | **LOW** | 7 small components (33 nodes) remain disconnected from the giant component, reflecting real-world gauge breaks or line closures rather than network modeling errors. |

---

## 7. Shortlist of Cases for Independent Manual Validation

We recommend the following 8 specific cases for manual ground-truth validation:

1. **`v2.0:DSS|STJT` (Dalsingh Sarai to Sathajagat, Bihar):**
   *Length:* 3.3262 km vs Straight-line Chord: 4.6219 km. Check Google Satellite / OpenStreetMap to confirm why track distance is 1.295 km shorter than crow-flies distance.
2. **`v2.0:GRX|MBDD` (Gaura to Maa Barahi Devi Dham, UP):**
   *Length:* 10.0931 km vs Straight-line Chord: 11.3341 km. Validate station coordinates against official Survey of India benchmarks.
3. **`v2.0:CSMT|JN:@72.836140,19.007082` (Mumbai CSMT approach throat):**
   *Length:* 7.7844 km, 779 daily trains. Verify the exact track switch geometry where the Fast Line connects to terminal platforms.
4. **`v2.0:ANVT|JN:@77.328571,28.660788` (Delhi Anand Vihar Terminal throat):**
   *Length:* 1.8413 km, 68 daily trains. Confirm whether the throat link represents true operational running line vs service yard spur.
5. **`v2.0:TKMG|UDPR` (Tikamgarh to Udaipura, MP):**
   *Length:* 19.5123 km. Spliced section carrying `throat` tag due to a 30 m construction gap. Verify whether this section is now fully commissioned broad gauge.
6. **`v2.0:JN:osm1359838385|PWKHI` (Thakurganj - Araria New Line):**
   *Length:* 83.396 km. Longest edge in the physical graph. Verify whether this new line is operational, under construction, or acts as a physical bypass around the Siliguri corridor.
7. **`v2.0:DADN|PTP` (Dr. Ambedkar Nagar to Patal Pani):**
   *Length:* 5.3011 km (`length_source = timetable_2017`). Verify physical track presence on the ground.
8. **`v2.0:SAMN|VGRA` (Samni to Vagara):**
   *Length:* 9.0000 km (`length_source = timetable_2017`). Verify line status and physical track presence.

---

## 8. Exact Commands to Reproduce This Audit

All scripts are self-contained in `audit_phase2a/scripts/` using Python standard library and pure-Python `networkx`. Run from repository root:

```bash
# 1. Verify release archive and member checksums
python audit_phase2a/scripts/verify_release_hashes.py

# 2. Execute Part A: Structural integrity checks on Physical and Places graphs
python audit_phase2a/scripts/audit_part_a_structural.py

# 3. Execute Part B: Provenance reconciliation (throats, joins, wikidata, conflicts)
python audit_phase2a/scripts/audit_part_b_provenance.py

# 4. Execute Part C: Places graph vs Physical graph comparative analysis
python audit_phase2a/scripts/audit_part_c_places.py
```

All machine-readable results will be regenerated in `audit_phase2a/results/` and anomaly tables in `audit_phase2a/anomalies/`.
