# E-724 — station multi-track snap (D-073), remediation Step 5

A copy of the E-716 build (`osm_build.py`, `run_c1.py`, `run_c2.py`, `geo.py`) with one switch:

| `RAIL_O3M` | Rule | Output |
|---|---|---|
| `0` | v2.0-open as released | `out/off` |
| `1` | D-073 as first written: bind the nearest kept sample on every other chain within 100 m of the station's OSM point | `out/on` |
| `2` | **D-073 revision 1 (adopted):** measured from the OSM point *or* the track point the station snapped to | `out/on_r1` |

Outputs never go to `graph_v2_0_open`. The service stage is not run here (Step 8 does it). Run each stage in one call on a 4 GB machine:

```bash
RAIL_O3M=2 python run_c2.py --stage=c1      # ~90 s
RAIL_O3M=2 python run_c2.py --stage=joins   # ~40 s
RAIL_O3M=2 python run_c2.py --stage=graph   # ~30 s
python eval_o3m.py                          # scores every build present -> out/eval_o3m.json
```

## Flag off reproduces v2.0-open

All node and edge IDs are identical, and every graph-stage column matches value for value, in `open/nodes.csv`, `open/edges.csv`, `places/` and the crosswalk. The service and state columns are added later by the service stage.

## Results

| | v2.0 (off) | rule (on) | revision 1 (on_r1) |
|---|---|---|---|
| Route km (vs official 69,439) | 70,304.6 (+1.25%) | 69,161.3 (−0.40%) | 69,200.7 (−0.34%) |
| Nodes / junctions / edges | 12,301 / 2,794 / 13,560 | 11,798 / 2,291 / 13,021 | 11,809 / 2,302 / 13,051 |
| Bridges / cut points | 1,849 / 1,805 | 1,706 / 1,685 | 1,689 / 1,670 |
| Degree-1 stations | 307 | 266 | 263 |
| Stations in the main network | 99.65% | 99.65% | 99.65% |
| Places-view max distance error (spot pairs) | 2.39% | 1.50% | 1.52% |
| CSMT→MSD / JND→TORA / MJ→MRWS / SPN→SZN km | 14.2 / 181.2 / 524.1 / 208.4 | 1.3 / 15.8 / 522.2 / 4.2 | **1.3 / 15.8 / 15.3 / 4.2** |
| HWH→TPKR / MAS→BBQ km | 2.74 / 3.37 | 2.74 / 3.35 | 2.65 / 3.35 |
| V2-27 through stations on the line | 0/22 | 18/22 | 18/22 |

- **The lost route km are duplicate parallel lines.** Binding every track at a station makes multi-track corridors (Virar–Borivali, Howrah–Chennai, …) parallel between consecutive stations, and O4 keeps the shorter one. No v2.0 edge of 2 km or more has its endpoints moved further apart.
- **Short loops.** There are 36 new loops shorter than 0.5 km (10.1 km in total). 32 are among junctions only: fewer bypasses are dropped (1,457 → 507) because more vertices are protected. 4 touch a station (AGA, BVN, KGM, KAN). All are listed in `out/eval_o3m.json`.

## What the predictions got wrong

- **Termini stay degree 1, and that is correct.** CSMT, MAS, SDAH and CCG are each still reached by one edge. Every track out of a terminus runs through one approach corridor before the next station, and a station-level graph with parallel tracks collapsed draws that corridor as one edge. The v2.0 defect was the route (CSMT→MSD 14.2 km), not the degree; the route is fixed. The audit's "degree-1 terminal = artifact" reading holds only where a line really diverges before the next station (HWH: degree 2 after revision 1).
- **Not fixed (become properties under D-071):**
  - PRES, RPM, BNZ and GTNR stay as leaves;
  - the MAS Moore Market approach is bound but folded into the parallel main-line route by O4, so MAS→BBQ stays 3.35 km against about 1.8 km. Moore Market itself has no node (V2-29).
