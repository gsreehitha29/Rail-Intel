# Validation — graph v2.0-open (working build), checkpoint CP2

Produced by `make osm-c3` (`experiments/E-716_osm_v2_build/validate_c3.py`). Every figure below is
in `work/c3_report.json`.

The comparison is with the v1.4.1 working build, whose topology and lengths are v1.4's. **v2.0 was
built without timetable distances**, except for 2 joins, so every route-accuracy figure below is out
of sample for v2.0. For v1.4 the same figures are in sample (F-027).

Updated at CP2 after the P2 passes (`docs/V2_ISSUES.md`). Distances and routing are measured on the
physical graph (`open/`). Structure — bridges, cut points, cycles — is measured on its places view
(`open/places/`, D-066).

## 1. The E-708 gates, rerun on v2.0

| Measure | v2.0 | v1.4.1 | v1.4 gate |
|---|---|---|---|
| Components | 13 | 18 | ≤ 18 |
| Giant component, share of nodes | 99.27% | 99.59% | ≥ 99% |
| Edges more than 0.3 km below their straight line | 5 | 90 | ≤ 120 |
| IIT Kharagpur 2024 distances within max(1 km, 5%) | **93.6%** of 9,250 | 82.7% of 8,873 | ≥ 82% |
| 2024 train routes, median error | **0.39%** | 0.72% | ≤ 1% |
| 2024 train routes within 5% | **99.2%** | 95.7% | ≥ 94% |
| 2024 trains unroutable | 1 | 2 | ≤ 2 |
| 2017 train routes, median error | 1.10% | 1.73% | — |
| 2017 train routes within 5% | 81.5% | 75.7% | — |
| 2017 trains unroutable | 28 (V2-13) | 0 | — |
| Off-spine detour, 2024 stop triples | 41,401 km | 52,513 km | ≤ 60,000 |

All nine gates pass on v2.0.

## 2. Section lengths against timetable distances

Each cell is within 5% / within max(1 km, 5%), with the median error in brackets.

| Set | v2.0 | v1.4.1 |
|---|---|---|
| E-715's 423 pairs (the roadmap's gate) | **50.8%** / 92.9% (4.8%) | 48.2% / 81.8% (5.7%) |
| All 6,833 comparable v1.4 sections with a timetable distance | 56.1% / 92.2% (4.2%) | 51.1% / 81.2% (4.8%) |
| The 318 of those that are straight-line floors in v1.4.1 | 51.3% / 74.5% (4.8%) | 0% / 0% (43.1%) |

Timetable distances are whole kilometres, so a short section cannot be within 5%. The 1 km
allowance is the one the IRN gate uses.

## 3. Structure, by station code (8,185 codes in both)

v2.0 is read on its places view.

| | v2.0, whole graph | v1.4.1, whole graph | v2.0, served | v1.4.1, served |
|---|---|---|---|---|
| Bridges | 1,728 | 1,236 | 1,025 | 773 |
| Share of km on bridges | 17.3% | 15.2% | 11.9% | 9.7% |
| Cut points | 1,680 | 1,170 | 1,011 | 761 |
| Independent cycles | 496 | 682 | 319 | 355 |
| Cut-point stations, overlap (Jaccard) | 0.60 | | 0.72 | |
| Large severances (≥ 20 stations) matched at overlap ≥ 0.8 | 56 of 84 | | **60 of 60** | |

The served network is the sections on the shortest path between consecutive stops of a 2024 train
(V2-22). v2.0 has more bridges because it has no straight-line shortcuts: where v1.4 closes a loop
with a chord, v2.0 follows the track (V2-23).

**Retrodictive cases, served network**

| Case | v1.4.1 severs | v2.0 severs | Overlap |
|---|---|---|---|
| Siliguri corridor, Barsoi–Makuria | 384 | 451 | 0.989 |
| Lumding–Badarpur hill section | 71 | 94 | 1.0 |

On the whole graph the Siliguri severance does not reproduce. OSM carries the new Araria–Thakurganj
line, which gives the Northeast a second way in, but no 2024 train used it.

**Cut points on the served network.** 7,257 of the 7,493 stations in both graphs agree (96.85%).
Each of the 236 differences is in `work/c3_cut_point_differences.csv`.

| Difference | Cause | Stations |
|---|---|---|
| Cut point in v2.0 only | longer loop in v1.4.1 (adjudicated in `work/p2_v201_classified.csv`) | 187 |
| Cut point in v2.0 only | loop of 10 km or less in v1.4.1 | 9 |
| Cut point in v2.0 only | v1.4.1 ends at the station; v2.0 continues past it | 10 |
| Cut point in v1.4.1 only | v2.0 has a longer loop | 25 |
| Cut point in v1.4.1 only | loop of 10 km or less in v2.0 | 1 |
| Cut point in v1.4.1 only | terminus | 1 |
| Cut point in v1.4.1 only | other | 3 |

Of the 187, 177 are served-view routing (the loop exists in v2.0 and carries no 2024 shortest path),
7 are v1.4.1 shortcuts, 2 are industrial track, and 1 is a placement (Coimbatore).

## Gate C3

| Gate | Result |
|---|---|
| C3a: lengths at least as good on the 423 pairs | pass |
| C3b: the E-708 gates hold on v2.0 | pass |
| C3c: both retrodictive cases reproduced on the served network | pass |
| C3d: every served cut-point difference recorded with a cause | pass |

C3c's 0.8 overlap and C3d were defined at CP1, after measuring. C3d is a reporting rule, not a
quality bar.

The same numbers reproduce byte for byte on the laptop.
