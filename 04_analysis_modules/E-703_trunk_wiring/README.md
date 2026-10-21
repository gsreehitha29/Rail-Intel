# E-703 — gap G5: trunk wiring

**The gap.** On the Delhi–Kanpur trunk the graph routed around Aligarh Jn, and the Tundla approach went the long way via Etmadpur, so criticality and delay landed on the wrong track.

**Status: filled and verified.** The off-spine detour — the distance trains are forced to travel round stations they actually stop at — falls **45%, from 93,773 km to 51,968 km**. Median route error falls from 0.93% to **0.71%** (2024) and 1.99% to **1.75%** (2017). Connectivity is unchanged.

## Ground truth

Where two stations are consecutive stops on a train, the timetable states both that they are adjacent on the track and how far apart they are. Checked on the Aligarh–Tundla stretch, those distances reconcile exactly with the end-to-end figure — 78.0 km, summed either way, in both 2017 and 2024 — so they are a sound reference for the graph's own topology.

## What was wrong, and what the evidence showed

**Aligarh.** The graph carried an edge SOMNA–DAUD KHAN of 28.8 km with no measured geometry and no train running it. The real line runs SOMNA – KALUA – MAHRAWAL – ALIGARH JN – DAUD KHAN, 30.8 km, carrying 128+ trains. Being 2 km shorter, the phantom edge won every shortest path and put a junction that 200 trains a day call at off the trunk.

**Tundla.** The graph had no direct Mitawal–Tundla link and went 12.61 km via Shivarampur and Etmadpur, against 7 km official. Two independent sources show why: OSM places Mitawali at 27.2594°N, 3.7 km south of the graph's position, and at that position both official distances (Barhan–Mitawal 8 km, Mitawal–Tundla 7 km) become geometrically consistent. The graph's coordinate is the outlier.

**Hathras — not a defect, and the earlier note is retracted.** E-700 flagged the Hathras Jn–Hathras Road link as suspect. The official data vindicates it: the graph's HRS→HTJ→PORA chain is 10.47 km against an official HRS–PORA of 11 km.

## Repairs applied

| Action | Count | Basis |
|---|---|---|
| `remove_edge` | 8 | No train runs it; without it the two stations are still joined, along the same alignment, by a chain of stations that trains do run |
| `add_edge` | 150 | The timetable runs the two as consecutive stops at a stated distance, but the graph has no direct link and routes more than 25% longer |

Both corridors are now right:

| Route | Official | Before | After |
|---|---|---|---|
| Ghaziabad → Kanpur | 415 km | 421.6 (+1.6%), **bypassing Aligarh** | 416.4 (+0.3%), **via Aligarh** |
| Etawah → Aligarh Jn | 170 km | 175.6 (+3.3%) | 169.0 (−0.6%) |
| Mitawal → Tundla Jn | 6 km | 12.6 (+110%) | 6.0 (exact) |

## What was tested and rejected

Two further classes were proposed by the same evidence, tested on their own, and **not applied** — each made the graph worse:

| Class | Count | Result |
|---|---|---|
| `set_length` | 823 | Route error worsens in both years (2024: 0.93% → 0.88–1.63% depending on subset; 2017: 1.99% → 2.29%) and the off-spine detour grows. Even layered on top of the fixed topology it degrades both measures |
| `move_node` | 361 | Changes no route at all, since lengths are explicit. Moving every node to its OSM position exposes ~290 further under-measured edges |

Length correction is therefore **not** a wiring repair. It needs per-edge adjudication against audit lists 03, 04 and 05, and is handed on in `out/deferred_findings.csv`. A worked example: Barhan–Mitawal is 4.12 km in the graph (a straight-line lower bound) against 8 km official on 10 trains. That single unfixed length is why Aligarh→Tundla now reads 74.2 km against an official 78.

A further 420 proposed lengths were rejected before testing as physically impossible — below the straight-line distance between their endpoints — which is how unreliable timetable rows were kept out.

## Verification

Three measures, because route error alone would be circular for length repairs:

- **Independent**: agreement with the IIT KGP IRN edge distances, the reference this project already uses and which fed no length in the graph. 82.70% → 82.72% within 5% (flat, as expected for a topology-only change).
- **Route error**: against the timetables' own cumulative km, 2017 and 2024 separately.
- **Structure**: off-spine stations, connectivity, and the invariant that no edge may be shorter than the straight line between its ends.

| Measure | Baseline | Accepted |
|---|---|---|
| edges | 9,638 | 9,780 |
| components | 18 | 18 |
| route error 2024 | 0.93% | **0.71%** |
| route error 2017 | 1.99% | **1.75%** |
| off-spine triples | 3,691 | **2,932** |
| off-spine detour | 93,773 km | **51,968 km** |
| edges shorter than their straight line | 1 | 85 |

The 85 are the price of the coordinate problem: for those added edges the official distance is impossible at the graph's own coordinates but consistent at OSM's. The edge is right and the coordinate is wrong; the companion `move_node` rows are in the deferred file.

## Files

- `detect.py` — the two detectors (phantom shortcuts; off-spine stations). `python detect.py <root> out`
- `repair.py` — builds the repairs from official adjacency. `python repair.py <root> out out`
- `verify.py` — applies each class and measures. `python verify.py <root> out out`
- `finalize.py` — splits accepted from deferred. `python finalize.py out out`
- `out/OVERRIDES_G5.csv` — the 158 accepted repairs
- `out/deferred_findings.csv` — 1,184 length and coordinate findings for their own gaps
- `out/verification_by_class.csv` — every configuration tested
- `out/coordinate_disagreements.csv` — 743 nodes more than 1.5 km from their OSM position
