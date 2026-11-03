# Rail-Intel Phase 2B.1 — CSMT–Masjid Missing Connection Forensic Investigation Report

**Investigation Target:** Missing connection between Mumbai CSMT (`CSMT`) and Masjid (`MSD`)  
**Candidate Edge in Release:** `v2.0:CSMT|JN:@72.836140,19.007082` (7.7844 km Fast Line bridge)  
**Release Under Audit:** `rail-intel-v2.0-open` (Locked 2026-10-21, SHA-256: `b1e3908167abb2aa91238046e9b25ac50a88ba3645077cb028b45331c449eeda`)  
**Audit Protocol:** Read-Only Forensic Investigation. Zero modification to canonical release artifacts, source data, or Git history.  
**Audit Workspace:** `audit_phase2b1/`

---

## Executive Summary

The missing topological connection between Mumbai CSMT (`CSMT`) and Masjid (`MSD`) in the released v2.0-open graph was investigated through code-level simulation and inspection of intermediate pipeline artifacts (`network_edges.parquet`, `network_vertices.parquet`, `station_snaps.csv`).

### The Root Cause Discovery
The connection between CSMT and Masjid **did exist** in the raw OpenStreetMap extraction and survived all filtering and parallel collapse stages through Stage C1. In `network_edges.parquet`, a continuous **1.4163 km running track (`chain: 4365`, `kind: 'track'`)** ran directly from Masjid (`s3558085`) to CSMT suburban platform 1 buffer stop (`n128794`).

The connectivity disappeared in **Stage C2 (Milestone 2) during Stage O4 contraction (`prune`)**:
1. **The Snap Limitation:** Mumbai CSMT is an 18-platform terminal station represented in OSM by a single point node (`12176277888`). During station snapping, CSMT snapped to the nearest track vertex (`n289147`, Mainline Fast Line buffer stop, 21.4 m away). The parallel suburban platform buffer stop `n128794` (42.89 m west) was not mapped to any station.
2. **The Dangling Prune:** Because `n128794` was a dead-end buffer stop with no station code attached, the Stage O4 contraction algorithm (`osm_build.py:605`, `prune`) classified it as a **"dangling track ending without reaching a station"** (`d <= 1 and n not in stations`).
3. **The Destruction of the Slow Line:** `prune()` deleted vertex `n128794`. In doing so, it **permanently deleted the entire 1.4163 km running track (`n128794 <-> s3558085`)** connecting CSMT to Masjid.
4. **Why Stage O5 Missed It:** The O5 join algorithm (`o5_stitch`) only attempts to connect disconnected fragments (`frags`) to the giant component. Because Masjid was already connected northward to Parel/Dadar (and therefore already in the giant component), O5 never evaluated the severed gap between CSMT and Masjid.

---

## 1. Released Topology Verification (Task 1)

### 1.1 Node & Incident Edge Profiles
- **`CSMT` (Mumbai CSMT):** Degree **1**. Exactly one incident edge: `v2.0:CSMT|JN:@72.836140,19.007082` (7.7844 km, `joins='throat'`, line: `Central Railways Fast Line`, 779 trains).
- **`MSD` (Masjid):** Degree **1**. Exactly one incident edge: `v2.0:JN:@72.838157,18.955373|MSD` (0.3473 km, line: `Central Railway (Slow)`, 344 trains).
- **Straight-Line Distance (Chord):** **1.3364 km** (Haversine chord between station centroids).

### 1.2 Released Shortest Path between CSMT and MSD
Because no direct track exists between them, the released physical graph forces all traffic into an **8-hop, 14.2121 km detour**:

$$\text{CSMT} \xrightarrow{\text{Fast Line (7.78 km)}} \text{JN:@72.836140,19.007082} \xrightarrow{\text{Slow (1.17 km)}} \text{JN:@72.832975,18.997070} \xrightarrow{\text{0.37 km}} \text{CRD} \xrightarrow{\text{1.23 km}} \text{JN:...} \xrightarrow{\text{0.67 km}} \text{BY} \xrightarrow{\text{1.97 km}} \text{SNRD} \xrightarrow{\text{0.66 km}} \text{JN:...} \xrightarrow{\text{0.35 km}} \text{MSD}$$

- **Path Length:** **14.2121 km**
- **Detour Ratio:** **10.63x** (14.21 km / 1.34 km)

### 1.3 The 172-Train Figure in the 2017 Service Layer
In `03_graph_construction/release/rail-intel-v2.0-open/service_2017/station_pairs.csv`:
- **Record:** `from_station = 'CSMT', to_station = 'MSD'`, `n_trains_2017 = 172`, `path_km = 14.2121`, `path_sections = 8`.
- **Precisely what 172 counts:**
  In the official Ministry of Railways 2017 timetable dataset (`Train_details_22122017.csv`, data.gov.in), exactly **172 scheduled passenger train services** list `CSMT` and `MSD` as consecutive timetable stops (`stnSerialNumber` $i$ and $i+1$).
  These represent daily Central Railway Mainline Slow local trains (e.g. CSMT to Kalyan, Thane, Karjat, Kasara locals) that stop at Masjid as their very first station after departing CSMT.
  Because the physical graph lacked the 1.3 km direct track, the service builder routed all 172 trains along the 14.21 km Parel detour.

---

## 2. Stage-by-Stage Pipeline Forensic Tracing (Tasks 2 & 3)

We traced the candidate geometry through every milestone and stage using the persisted work artifacts:

```
[Raw OSM Ways] ──(O1 Keep)──> [O2 Parallel Collapse] ──> [Stage C1: network_edges.parquet]
                                                                    │
                                                              (chain 4365: 1.4163 km track
                                                               n128794 <-> s3558085 EXISTS!)
                                                                    │
                                                                    ▼
                                                         [Stage O3: Station Snap]
                                                         CSMT snaps to n289147 (Fast Line)
                                                         n128794 (Slow Line) left unsnapped!
                                                                    │
                                                                    ▼
                                                         [Stage O4: prune(G, stations)]
                                                         n128794 degree=1 & not in stations
                                                         ==> n128794 PRUNED!
                                                         ==> chain 4365 DESTROYED!
                                                                    │
                                                                    ▼
                                                         [Stage O5: o5_stitch]
                                                         CSMT & MSD both in giant
                                                         ==> O5 skips gap!
                                                                    │
                                                                    ▼
                                                         [Released Physical Graph]
                                                         CSMT degree=1, MSD degree=1
```

| Pipeline Stage | Intermediate Artifact | Status of CSMT–MSD Geometry | Details / Mechanism |
|---|---|---|---|
| **1. Raw OSM Ingestion** | `external_data/osm_india_rail` | **Present** | Continuous tracks mapped from CSMT platforms 1–4 through Masjid. |
| **2. Stage O1 (Filtering)** | `run_c1.py` / `o1_filter` | **Included** | Tracks retained as mainline running line (`railway=rail`, `usage=main`). |
| **3. Stage O2 (Parallel Collapse)** | `osm_build.py:190` | **Preserved** | Fast Line and Slow Line are 42.89 m apart at buffer stops (exceeding 15 m collapse tolerance), so both survived as separate chains. |
| **4. Stage C1 (Network Build)** | `work/network_edges.parquet` | **PRESENT (1.4163 km)** | **`n128794 <-> s3558085` exists** (`chain: 4365`, `kind: 'track'`). Connects Masjid (`s3558085`) to CSMT suburban buffer stop (`n128794`). |
| **5. Stage O3 (Station Snapping)** | `work/station_snaps.csv` | **Partial (Fast line only)** | `CSMT` (point node) snapped to `n289147` (21.4 m away). `n128794` (42.89 m away) was **left unsnapped** as an anonymous vertex. |
| **6. Stage O5a (Throats)** | `work/c2_throat_links.csv` | **No change** | Throat search evaluated crossovers near Parel and Kurla; did not create buffer-stop cross-links. |
| **7. Stage O5 (Stitching)** | `run_c2.py:144` | **Skipped** | `o5_stitch` only joins disconnected fragments (`frags`) to `giant`. Because both CSMT and MSD were connected northward, both were in `giant`. |
| **8. Stage O4 (Contraction: `prune`)** | `osm_build.py:601` (`prune`) | **DELETED / DESTROYED** | **EARLIEST STAGE OF LOSS.** `prune(G, stations)` found `n128794` with degree $\le 1$ and not in `stations`. **`prune` deleted `n128794` and destroyed edge `n128794 <-> s3558085` (1.4163 km).** |
| **9. Final Serialization** | `release/graph/edges.csv` | **Absent** | Graph serialized with `CSMT` having degree 1 and `MSD` having degree 1. |

---

## 3. Evaluation of Competing Hypotheses (Task 4)

| Hypothesis | Supporting Evidence | Contradicting Evidence | Confidence Assessment |
|---|---|---|---|
| **A. Service/Yard Track Filtering Excluded Track** | Many crossover switches in CSMT yard are tagged `service=*`. | The running line `chain 4365` was **NOT** excluded; it was tagged `kind='track'` and survived Stage O1 into Stage C1. | **REFUTED** as root cause. |
| **B. Parallel Track Collapse Merged Lines Incorrectly** | O2 collapsed parallel tracks within 15 m. | Fast and Slow buffer stops are 42.89 m apart; `network_edges.parquet` preserves both tracks in Stage C1. | **REFUTED** as root cause. |
| **C. Station Snapping Failed to Bind Parallel Platform** | `CSMT` snapped solely to `n289147` (21.4 m), leaving `n128794` (42.89 m) unsnapped. | Snapping followed its programmed nearest-neighbor rule correctly; the flaw is the single-vertex assumption for multi-platform termini. | **CONFIRMED (Primary Architectural Trigger)**. |
| **D. Throat / Stitching Restoration Missed the Gap** | `o5_stitch` did not bridge the gap. | `o5_stitch` is designed exclusively for inter-component fragment joining, not intra-giant loop restoration. | **CONFIRMED (Secondary Contributor)**. |
| **E. Contraction / Pruning Removed Necessary Track** | In `osm_build.py:605`, `prune()` explicitly identified `n128794` as a non-station leaf and deleted it, destroying `n128794 <-> s3558085`. | None. This was confirmed by deterministic simulation execution. | **CONFIRMED (Direct Immediate Mechanism)**. |
| **F. Original OSM Geometry Incomplete** | None. | OSM geometry in Stage C1 had continuous, unbroken track from Masjid to CSMT buffer stops. | **REFUTED**. |

---

## 4. Analytical Scenario Evaluation (Task 5)

We evaluated an isolated in-memory test scenario restoring the exact 1.4163 km track (`chain 4365`) between `CSMT` and `MSD` without modifying the canonical release:

### 4.1 Structural Metrics Comparison
| Graph Metric | Baseline Release (v2.0-open) | Scenario 1 (Restored 1.4163 km Edge) | Impact / Assessment |
|---|---|---|---|
| **CSMT Degree** | **1** | **2** | CSMT ceases to be a leaf dead-end |
| **MSD Degree** | **1** | **2** | Masjid ceases to be a leaf dead-end |
| **Candidate Edge Bridge Status**| **TRUE (Bridge)** | **FALSE (Non-Bridge)** | Candidate edge ceases to be a bridge |
| **Total Bridges in Graph** | 1,849 | 1,847 | -2 bridges (CSMT & MSD leaves resolved) |
| **Total Articulation Points** | 1,805 | 1,803 | -2 cut points |
| **Total Independent Cycles** | 1,267 | 1,268 | +1 cycle (15.63 km Fast/Slow loop) |
| **Candidate Loop Length** | N/A (no cycle) | **15.6284 km** | Natural 4-track South Mumbai rail loop |

### 4.2 Routing Distance Impact Comparison
| Station Pair | Baseline Route (v2.0) | Scenario 1 Route | Delta (Saved Distance) |
|---|---|---|---|
| **`CSMT -> MSD` (Masjid)** | **14.21 km (8 hops)** | **1.42 km (1 hop)** | **-12.80 km (89.9% reduction)** |
| **`CSMT -> SNRD` (Sandhurst Rd)** | **13.20 km (6 hops)** | **2.43 km (3 hops)** | **-10.77 km (81.6% reduction)** |
| **`CSMT -> BY` (Byculla)** | **11.23 km (5 hops)** | **4.40 km (4 hops)** | **-6.84 km (60.9% reduction)** |
| **`CSMT -> CHG` (Chinchpokli)** | 10.06 km (3 hops) | 5.59 km (6 hops) | -4.47 km |
| **`CSMT -> CRD` (Currey Road)** | 9.32 km (3 hops) | 6.30 km (6 hops) | -3.02 km |
| **`CSMT -> PR` (Parel)** | **8.10 km (2 hops)** | **8.10 km (2 hops)** | **0.00 km (Unchanged Fast Line)** |
| **`CSMT -> DR` (Dadar)** | **9.17 km (4 hops)** | **9.17 km (4 hops)** | **0.00 km (Unchanged Fast Line)** |
| **`CSMT -> TNA` (Thane)** | 33.56 km (17 hops) | 33.46 km (26 hops) | -0.09 km |
| **`CSMT -> KYN` (Kalyan Jn)** | 51.73 km (39 hops) | 51.64 km (48 hops) | -0.09 km |

*Key Routing Finding:* Mainline long-distance traffic to Dadar, Thane, and Kalyan continues to take the 7.78 km Fast Line corridor. Restoring the 1.42 km edge fixes all suburban traffic to Masjid, Sandhurst Road, and Byculla without distorting mainline intercity paths.

---

## 5. Answers to the Required Conclusions

### 1. Does the source geometry support a real CSMT–MSD railway connection?
**YES (Definitively).**  
The OpenStreetMap source data contains multiple continuous, electrified broad-gauge running tracks connecting Masjid platforms directly to CSMT platforms. In Stage C1 (`network_edges.parquet`), this connection was explicitly captured as **`chain: 4365` (1.4163 km)** between `s3558085` (Masjid) and `n128794` (CSMT suburban platform 1 buffer stop).

### 2. At which pipeline stage does the connectivity first disappear?
**Stage C2, during Stage O4 contraction (`prune` in `osm_build.py:601-608`).**  
The connectivity was fully intact throughout Stage C1. It disappeared when `prune()` deleted vertex `n128794` because it was a degree-1 buffer stop not present in `stations`.

### 3. What evidence establishes the root cause?
- **Intermediate Data Proof:** `work/network_edges.parquet` contains edge `n128794 <-> s3558085` with length `1.4163 km`.
- **Coordinate Proof:** `n128794` sits at `(72.83518, 18.94052)`, exactly 42.89 meters from CSMT's snapped vertex `n289147` at `(72.83559, 18.94056)` at the CSMT platform bumper blocks.
- **Code Simulation Proof:** Running `osm_build.py`'s exact `vertex_graph` and `prune` functions demonstrates that `n128794` enters the graph with degree 1, is identified as a non-station leaf, and is pruned, destroying edge `n128794 <-> MSD`.

### 4. Is a correction justified?
**YES, but in a future release (v2.1), NOT as an ad-hoc patch to v2.0-open.**  
A correction is technically and operationally justified because:
1. It restores the physical reality of 4-to-6 running tracks.
2. It eliminates a severe 10.64x detour on 172 scheduled 2017 passenger trains.
3. It correctly models candidate edge `v2.0:CSMT|JN:...` as a redundant Fast Line track rather than an artificial single-link bridge.

However, under the project's **Stop Rule (D-055)**, **no manual or partial edge patch should be applied to the frozen v2.0-open release**. The release must remain frozen for scientific reproducibility.

### 5. What must be validated before any future release change?
Before implementing a fix in v2.1, the pipeline architecture must be systematically improved rather than applying a hardcoded link:
1. **Terminal Multi-Platform Snapping Rule:** Formulate an architectural rule in `s05_station_snap` / `o3_snap` where parallel track buffer stops within a terminal station footprint (e.g. $\le 100\text{ m}$ across tracks) are bound to the same terminal station entity.
2. **National Terminal Audit:** Check other dead-end terminal stations in India (e.g. Howrah `HWH`, Chennai Central `MAS`, Sealdah `SDAH`) to determine whether parallel approach tracks were similarly pruned.
3. **Cycle Inflation Validation:** Verify that binding parallel platform buffer stops does not introduce spurious micro-cycles inside station yards.
4. **Formal Issue Registration:** Formally document this defect in `docs/V2_ISSUES.md` as issue **`V2-26: Pruning of Multi-Track Terminal Platform Approaches (CSMT–MSD)`**.
