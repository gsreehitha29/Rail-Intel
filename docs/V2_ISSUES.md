# v2.0-open issue register

Seeded at CP1 (2026-10-20). Updated at **CP4** (2026-10-21): v2.0-open locked for deposit (D-069). Nothing here blocks the deposit. A pass fixes one
cause, rebuilds, reruns all gates and tests, then updates this register. **Blocking** means v2.0
cannot be released until the issue closes. **Property** means it is written into the datasheet and
stays. **No item now blocks release.**

| ID | Issue | Measured size | Class | Resolution | Status |
|---|---|---|---|---|---|
| V2-01 | Cut points in v2.0 only, where v1.4.1 has a loop v2.0 lacks (served network) | was 251 on 116 lines; now 187 | — | Pass 1. Each case classified (`work/p2_v201_classified.csv`). **Fixed in v2.0:** a 30 m way tagged `construction` broke Udaipura–Tikamgarh, which has 2024 trains; short construction or disused ways (≤ 0.5 km) may now be throats. **Remaining:** 177 served-view routing (V2-22): v2.0 has the loop, but no 2024 train is routed over part of it. 7 are v1.4.1 shortcuts (V2-23). 2 are industrial track v2.0 excludes. 1 is a station placement (V2-21). | **closed** |
| V2-02 | Cut points in v1.4.1 only, where v2.0 has a loop v1.4.1 lacks | 25 | property | Expected to be lines newer than v1.4's source; not checked one by one | property |
| V2-03 | Cut-point differences the classifier cannot name | 3 (CHHU, MNWL, UHP) | property | Listed | property |
| V2-04 | Junctions are separate nodes, so station degree is not comparable | 2,794 junctions | — | Pass 2, D-066. `place_id` on every node, and a **places view** (`open/places/`): 9,540 stations and 516 junctions; stations reach degree 8 (v1.4.1: 7) | **closed** |
| V2-05 | Cycles inflated (1,263 against 682) | 2,216 sections on cycles ≤ 5 km, nearly all junction to junction | — | Pass 2, D-066. They are real track geometry (triangles, crossovers, parallel lines in yards). The physical graph keeps them, so lengths stay exact. The places view has **496 cycles** (served network 319; v1.4.1 682 / 355) and is the view for redundancy | **closed** |
| V2-06 | Track tagged running with no 2024 train | 19.2% of edges, 14.1% of km | — | Pass 4. `served_2024`, `scheduled_2017` and `line_status` on every edge and station | **closed** |
| V2-07 | Stations outside the main network, all but two on closed or suspended lines | 104 (D-064) | property | `line_status`; 1,275 stations have no service in either timetable | property |
| V2-08 | 2024 timetable codes not resolved; Wikidata could not place 31 | 41 codes, 0.18% of 2024 stops (largest: SMVJ 24, CBCC 16, BRY 16, MULK 16) | property | Listed in `work/c2_wikidata_placement.csv` | property |
| V2-09 | Code conflicts: same code more than 2 km apart | 12 (was 15; D-068 drops 3 metro stations) | — | Pass 5. 10 resolved: the candidate whose network distances match the timetable takes the code (median ≤ 0.4 km off). INDR and MHBD stay `code~osmid` (no timetable neighbour) | **closed** |
| V2-10 | Uncoded OSM stations | 110 | property | — | property |
| V2-11 | Stations with no section | 6: Kalakund and Patal Pani (the Mhow heritage line, unmapped in OSM), Lanela, Mandla Fort, Hili, Samni | property | — | property |
| V2-12 | Sections shorter than the straight line between station points | 611, 6 by more than 0.2 km | — | Pass 4. `track_lon` and `track_lat` (where the station meets its track) published beside the OSM station point | **closed** |
| V2-13 | 2017 trains unroutable on v2.0 | 12 (was 32) | property | Lines closed since 2017 | property |
| V2-14 | State and zone empty | — | — | Pass 4. State for 99.99% of nodes, from datameet Admin2 (CC BY 4.0), agreeing with v1.4.1 on 99.8% of stations. **Zone stays empty**: no open source | closed (state); zone property |
| V2-15 | The C2 build exceeded the laptop's limits | — | — | Pass 5. Slim cache and per-component searches; build split into c1 / joins / graph / service. Laptop: 72 / 34 / 16 / 40 s. **Every output byte-identical** between the laptop and the cloud workspace | **closed** |
| V2-16 | Gauge or electrification unknown | 1.1% / 3.2% of km | property | — | property |
| V2-17 | Gate C1a measured on the station graph (C2d), D-065 | — | decision | Explained at CP2; stands unless you object | adopted, open to veto |
| V2-18 | Joins at a timetable distance | 2 edges, 40.5 km | property | — | property |
| V2-19 | The 2024 service data (IIT Kharagpur RSTGCN) has no stated licence | — | — | Pass 3, D-067. **The release ships the open GODL 2017 layer** (`service_layer_v2_0_open/open_2017/`). The 2024 layer is rebuilt by anyone from the public source with `make osm-c2`, and is not redistributed. Asking permission is optional: what 2024 adds is set out in D-067 | **closed for release** |
| V2-20 | No speed or travel-time attribute on sections | — | property | Observed run times stay in the 2024 layer | property |
| V2-24 | Two sections take a 2017 timetable length because OSM has no track | Patal Pani–Dr. Ambedkar Nagar, Samni–Vagara; 14.3 km | property | `length_source = timetable_2017` (D-068) | property |
| V2-25 | OSM maps some stations twice, once coded and once not | 22 merged by name within 1 km; 4 more by Wikidata name | — | D-068 | **closed** |
| V2-21 | A Wikidata-placed station sits on one line of a multi-line station | 1 seen (Coimbatore Jn, Mettupalayam side) | property | Listed | property |
| V2-22 | Served network means sections on the shortest path between a train's consecutive stops; a route no train's path uses counts as unserved even where trains could divert over it | 177 cut points differ on this account alone | property | Severance statements carry "on the 2024 served network"; physical alternatives are read on the whole graph | property |
| V2-23 | v1.4.1 defects found by v2.0: shortcuts far shorter than the track | 7 stations (BNHL–BAHI 1.5 km against 147 km; COB–DWT 0.1 against 10.1; HWH–BBDB across the Hooghly; and others) | v1.4.1 | Passed to v1.4.1's Tier 1 audit (A2); not a v2.0 issue | open for A2 |
