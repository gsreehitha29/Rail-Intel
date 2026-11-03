# Rail-Intel Phase 2C — Nationwide Terminal Station Topology Audit Report

**Audit Objective:** Determine whether the CSMT O3 station snapping + O4 pruning failure pattern is localized to Mumbai or systematic across major Indian terminal stations.  
**Scope:** `HWH` (Howrah Junction), `MAS` (Chennai Central), `SDAH` (Sealdah), `MMCT / BCT` (Mumbai Central), with comparative baseline from `CSMT` (Mumbai CSMT).  
**Release Audited:** `rail-intel-v2.0-open` (Locked 2026-10-21, SHA-256: `b1e3908167abb2aa91238046e9b25ac50a88ba3645077cb028b45331c449eeda`).  
**Audit Protocol:** Read-Only Audit. Zero modification to canonical release artifacts, source data, or Git history.  
**Audit Workspace:** `audit_phase2c/`

---

## Executive Summary

The investigation demonstrates **definitively that the CSMT station snapping and pruning failure is NOT an isolated anomaly**. It is a **systematic, architectural flaw** inherent in the v2.0-open pipeline's point-to-track snapping (`o3_snap`) and contraction pruning (`prune`).

### Key Audit Findings
1. **Universal Degree-1 Collapse:**  
   Every audited major terminus station in India—`HWH` (23 platforms), `MAS` (17 platforms), `MMCT` (9 platforms), `SDAH` (21 platforms), and `CSMT` (18 platforms)—has collapsed to **`degree = 1`** in the released physical graph.
2. **Systematic Buffer Stop Pruning:**  
   In all audited terminals, OSM source data mapped multiple parallel platform tracks terminating at buffer blocks. Because `o3_snap` binds a station centroid to only its single nearest track sample, **all other parallel buffer stops within the station complex were left unsnapped**. In Stage O4, `prune(G, stations)` mechanically classified these unsnapped dead-ends as dangling spurs and deleted them, destroying running lines of up to **38.85 km** in length.
3. **Suburban Division Severance:**  
   At dual-division terminal complexes (where suburban EMU lines run alongside intercity mainline trains):
   - **CSMT:** Central Railway Slow Line (Platforms 1–4) pruned; direct 1.42 km connection to Masjid severed.
   - **MAS:** Chennai Central Suburban Terminal at Moore Market Complex (Platforms 13–17) pruned; chains 25 and 26 severed.
   - **MMCT:** Western Railway Suburban Line approaches pruned; station code mismatch (`BCT` vs `MMCT`) caused **0 scheduled trains** in the 2017 release.
   - **HWH:** South Eastern Railway Terminal 2 suburban approach (Chain 8315, 5.91 km) and Howrah–Bandel suburban buffer stop pruned.
   - **SDAH:** Southern division suburban approaches (Chain 3867, 3.41 km) pruned.

---

## 1. Station-by-Station Findings

### 1.1 Howrah Junction (`HWH`) — 23 Platforms
- **Ground Truth Structure:** India's busiest terminal, divided into Terminal 1 (Platforms 1–15, Eastern Railway) and Terminal 2 (Platforms 16–23, South Eastern Railway).
- **Source OSM Representation:** Point node `3321321335` (`ref=HWH`, `lon: 88.34281, lat: 22.58287`).
- **Snapping in O3:** Centroid snapped to Terminal 1 buffer stop `n72370` (`osm_node: 1189845425`) at distance **68.5 m**.
- **Stage C1 Vertices & Pruning:**
  - 11 C1 vertices existed within 500m of Howrah.
  - **9 of them were PRUNED in Stage O4.**
  - **Pruned Terminal 2 (SER) Leads:** `n357842` (173.8 m from centroid, buffer stop for SER suburban tracks to Tikiapara/Kharagpur, Chain 8315: 5.91 km), `n357845` (194.7 m, Chain 8301: 1.71 km).
  - **Pruned ER Suburban Buffer Stops:** `n450058` (169.9 m, Chain 13110: 1.34 km), `n450066` (144.4 m, Chain 7972: 1.26 km), `n33979` (109.9 m, Chain 928: 1.13 km), and Howrah–Bandel line buffer lead `n450061` (162.3 m, Chain 7959: 38.86 km).
- **Released Graph State:** Released node `HWH` has `degree = 1`, connected exclusively via `v2.0:HWH|JN:@88.335725,22.586746` (0.78 km). All South Eastern Railway direct platform approaches were deleted.
- **Status:** **CONFIRMED SYSTEMATIC PRUNING DEFECT.**

---

### 1.2 Chennai Central (`MAS`) — 17 Platforms
- **Ground Truth Structure:** Platforms 1–12 serve intercity mail/express trains (Southern Railway). Platforms 13–17 constitute the Chennai Central Suburban Terminal at Moore Market Complex (MMC), serving suburban trains towards Arakkonam and Gummidipundi.
- **Source OSM Representation:** Point node `2481969291` (`ref=MAS`, `lon: 80.27596, lat: 13.08242`).
- **Snapping in O3:** Centroid snapped to Mainline buffer stop `n6021` (`osm_node: 303283541`) at distance **48.6 m**.
- **Stage C1 Vertices & Pruning:**
  - 24 C1 vertices existed within 500m of Chennai Central.
  - **7 of them were PRUNED in Stage O4.**
  - **Pruned MMC Suburban Buffer Stops:**
    - `n876`: **56.42 m** from MAS centroid (`osm_node: 247678922`, degree 1, Chain 26: 2.51 km).
    - `n872`: **73.22 m** from MAS centroid (`osm_node: 247678612`, degree 1, Chain 25: 0.51 km).
    - `n161021`: 152.9 m (`osm_node: 2272877322`, Chain 5269: 1.10 km).
    - `n6025`: 184.3 m (`osm_node: 303283940`, Chain 144: 1.01 km).
    - `n335497`: 253.1 m (`osm_node: 5307984948`, Chain 5729: 3.59 km).
  - Notice: Both `n876` (56.4 m) and `n872` (73.2 m) were **well within the 100m snap threshold**, but because `o3_snap` only selects the single nearest vertex (`n6021`), they were ignored and subsequently pruned!
- **Released Graph State:** Released node `MAS` has `degree = 1`, connected exclusively via `v2.0:JN:@80.274327,13.090880|MAS` (0.9305 km, 185 trains in 2017). The entire Moore Market Complex suburban terminal was deleted.
- **Status:** **CONFIRMED SYSTEMATIC PRUNING DEFECT.**

---

### 1.3 Mumbai Central (`MMCT / BCT`) — 9 Platforms
- **Ground Truth Structure:** Platforms 1–4 serve Western Railway suburban commuter traffic (local code `BCT`). Platforms 5–9 serve long-distance intercity express trains (local code `MMCT`).
- **Source OSM Representation:** Point node `2630075008` (`ref=MMCT`, `station=terminal`, `lon: 72.81932, lat: 18.96959`).
- **Snapping in O3:** Centroid snapped to Mainline terminal buffer stop `n22595` (`osm_node: 527995852`) at distance **32.7 m**.
- **Stage C1 Vertices & Pruning:**
  - 9 C1 vertices existed within 500m of Mumbai Central.
  - **7 of them were PRUNED in Stage O4.**
  - **Pruned Suburban & Parallel Buffer Stops:**
    - `n22597`: **38.27 m** from centroid (`osm_node: 527995867`, Chain 630: 0.47 km).
    - `n447529`: **42.05 m** from centroid (`osm_node: 7551775616`, Chain 804: 0.22 km).
    - `n401673`: 140.3 m from centroid (Chain 3929: 4.27 km towards Bandra suburban).
    - `s697654`: 238.5 m from centroid (Chain 806: 5.24 km).
- **The Missing Station Code Catastrophe (`BCT`):**
  - OSM only held code `MMCT`. The official 2017 timetable dataset scheduled services to `BCT`.
  - Because `BCT` was not placed in `station_snaps.csv` or mapped as an alias, `BCT` does not exist in the released graph.
  - Released node `MMCT` has `degree = 1`, incident edge `v2.0:JN:@72.820770,18.976712|MMCT` (0.78 km), and **`trains_2017 = 0`**!
- **Status:** **CONFIRMED SYSTEMATIC PRUNING DEFECT + CODE RESOLUTION DISCONNECT.**

---

### 1.4 Sealdah (`SDAH`) — 21 Platforms
- **Ground Truth Structure:** Divided into Sealdah North/Main (Platforms 1–14, serving Ranaghat, Bongaon, Dankuni) and Sealdah South (Platforms 15–21, an isolated terminal serving Budge Budge, Diamond Harbour, Canning, Namkhana).
- **Source OSM Representation:** Two nodes existed: `252584722` (`ref=SDAH`) and `5587888046` (`ref=SDAH`).
- **Snapping in O3:**
  - `252584722` snapped to sample `s3458960` (40.1 m).
  - `5587888046` snapped to buffer stop `n125689` (97.8 m).
  - Under D-063 (`merge_km = 2.0`), both nodes were mapped to `graph_node = 'SDAH'`.
- **Stage C1 Vertices & Pruning:**
  - 8 C1 vertices existed within 500m of Sealdah.
  - **4 of them were PRUNED in Stage O4.**
  - **Pruned Approaches:** `n130256` (179.4 m, Chain 3867: **3.41 km** southern approach lead), `n125694` (345.3 m, Chain 4199: 0.06 km), `n125711` (461.0 m, Chain 4201: 0.21 km).
- **Released Graph State:** Released node `SDAH` has `degree = 1`, connected exclusively via `v2.0:JN:@88.375098,22.569743|SDAH` (0.5512 km, 745 trains in 2017).
- **Status:** **CONFIRMED SYSTEMATIC PRUNING DEFECT.**

---

## 2. Nationwide Terminal Evidence Table

| Terminal Code | Station Name | Real-World Platforms | Released Graph Degree | Vertices within 500m (C1) | Vertices Pruned in O4 | Max Pruned Track Length | Pruned Suburban Division / Key Approach | Defect Status |
|---|---|---|---|---|---|---|---|---|
| **`CSMT`** | Mumbai CSMT | 18 | **1** | 23 | **21** | 10.26 km (chain 4365) | Central Railway Slow Line (Plat 1–4, Masjid connection) | **Confirmed Defect** |
| **`HWH`** | Howrah Junction | 23 | **1** | 11 | **9** | 38.86 km (chain 7959) | South Eastern Railway Terminal 2 & Bandel Suburban buffer leads | **Confirmed Defect** |
| **`MAS`** | Chennai Central | 17 | **1** | 24 | **7** | 3.59 km (chain 5729) | Moore Market Complex Suburban Terminal (Plat 13–17) | **Confirmed Defect** |
| **`MMCT`** | Mumbai Central | 9 | **1** | 9 | **7** | 5.24 km (chain 806) | Western Railway Suburban local lines (0 timetable trains) | **Confirmed Defect** |
| **`SDAH`** | Sealdah | 21 | **1** | 8 | **4** | 3.41 km (chain 3867) | Sealdah South suburban division leads | **Confirmed Defect** |

---

## 3. Confirmed Defects vs Suspected Defects vs Expected Behavior

### 3.1 Confirmed Systematic Defects
1. **Multi-Track Buffer Stop Pruning:**
   The algorithm `prune(G, stations)` in `osm_build.py:601-610` unconditionally removes any vertex with `degree <= 1` not in `stations`. In every terminus station, parallel platform buffer stops that do not win the single-point 1-to-1 nearest-neighbor query in `o3_snap` are deleted. This destroys parallel approaches and creates artificial single-link bottlenecks.
2. **Artificial Degree-1 Terminal Collapse:**
   All 5 audited major terminal complexes in India (representing 88 total platform tracks) collapsed to `degree = 1`. In real railway operations, these stations have independent running lines for suburban and mainline traffic that do not merge into a single physical track.
3. **Suburban Division Timetable Blindspot:**
   Suburban timetable services (e.g., CSMT–MSD local trains, BCT local trains, MMC Chennai locals) are either forced into multi-kilometer reverse detours over mainline bridges or dropped entirely (`trains_2017 = 0`).

### 3.2 Expected Behavior (What the Pipeline Did Right)
1. **Pass-Through Stations:**
   At ordinary through-stations (e.g. Byculla, Dadar, Thane, Kalyan), stations have `degree >= 2`, tracks continue linearly, and station snapping successfully retains through-connectivity without pruning.
2. **Giant Component Inclusion:**
   All 5 terminals survived into the giant component (`in_giant = True`), meaning intercity long-distance connectivity was preserved via the single retained mainline throat link.

---

## 4. Why the Current Graph Semantics Are Inadequate

The Rail-Intel v2.0 graph model makes three invalid semantic assumptions regarding major terminal stations:

1. **The Single-Point Station Fallacy:**
   The pipeline assumes a passenger railway station can be represented as a single 0-dimensional point in Euclidean space snapped to a single track sample. While acceptable for a 2-platform wayside station, this assumption fails catastrophically for terminal complexes spanning 20+ tracks and multiple administrative railway divisions.
2. **The "Dangling Spur = Garbage" Fallacy:**
   `prune(G, stations)` assumes that any dead-end track that ends without reaching a station is an unused industrial siding or spur that should be discarded. At a dead-end passenger terminus, **every platform track is a dead-end buffer stop**. Treating unsnapped buffer stops as garbage mechanically destroys legitimate running lines.
3. **The Single-Layer Topological Funnel:**
   By contracting all terminal tracks into a single degree-1 node, the graph forces suburban commuter networks and national freight/intercity networks to share the same physical throat edge, creating false topological criticality (spurious bridges).

---

## 5. Recommended Next Validation Experiment & Architectural Roadmap (v2.1)

To prepare a robust, defensible solution for the future v2.1 roadmap without violating Stop Rule D-055:

1. **Formulate Terminal Footprint Multi-Snapping (`o3_terminal_snap`):**
   In `osm_build.py:353` (`o3_snap`), implement a multi-platform terminal rule:
   - Identify terminal buffer stops (`degree == 1` at chain origin/termination).
   - Any buffer stop falling within the terminal station polygon or within $R \le 100\text{ m}$ of a terminal station node is bound to that station's identity (or linked via a designated station concourse connector).
2. **Timetable Division Code Crosswalk (`s06_crosswalk`):**
   Explicitly map dual-code terminals (`MMCT` $\leftrightarrow$ `BCT`, `HWH` $\leftrightarrow$ `HWHG`, `MAS` $\leftrightarrow$ `MMC`) during O3b Wikidata/timetable placement so suburban schedules are not dropped.
3. **Terminal Yard Crossover Preservation:**
   Evaluate whether approach crossovers tagged `service=*` near terminals should be unconditionally preserved in Stage O1 when they fall within $1.5\text{ km}$ of a terminal station centroid.
