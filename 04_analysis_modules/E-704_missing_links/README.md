# E-704 — gap G6: missing links

**The gap.** E-700 found 27 "missing-link candidates" in one region — pairs of stations trains run between, where the graph took a much longer way round. G5 then added 150 such links nationally from official adjacency, but refused 69 more and left 123 unexamined.

**Status: filled, and mostly by correcting the claim.** Of 110 candidates examined nationally, **88 are not missing at all** — the graph already routes them correctly. 21 genuine missing links were added and 2 gaps are too long to bridge with a single edge. The graph is slightly better on every measure and no worse on any.

## The correction that shapes this module

Consecutive stops in a timetable do **not** prove a direct link. A fast train skipping Dombivli still runs over the track through it. They prove only that track of roughly that length joins the two stations.

So an excess is a missing link only when the graph's path goes somewhere else entirely. The test is alignment: take the graph's current path and measure how far its intermediate stations sit from the straight line between the two endpoints.

- **Diva – Kopar Road** (249 trains, 4 km official, 6.12 km in the graph) runs through Dativli and Dombivli, both squarely on the line. The chain is real; the 2 km "excess" is chargeable distance against summed segments. Adding a direct edge here would bypass Dombivli — precisely the defect G5 removed.
- **Bahadurgarh – Ghevra** (27 trains, 6 km official) detours 33 km by way of Shakurbasti, nowhere near the line. The track really is absent.

Applying that test turned an apparent 110-link gap into a 21-link one.

## What was added

21 links, 195 km. Lengths come from the official distance, floored at the straight line so the graph stays physically coherent — 14 needed that floor. The largest:

| Link | Trains | Official | Graph before | Added at |
|---|---|---|---|---|
| Bahadurgarh – Ghevra | 27 | 6 km | 33.00 km | 6.80 km |
| Raipur Jn – Saraswatinagar | 25 | 2 km | 17.36 km | 2.75 km |
| New Tinsukia Jn – Tinsukia Jn | 17 | 2 km | 19.21 km | 2.36 km |
| Chittapur – Nalwar | 11 | 18 km | 28.65 km | 22.20 km |

Garifa – Hooghly Ghat is among them: 1 km official against a 1.43 km separation, a real adjacency over the Jubilee Bridge that G5 rejected for being 0.43 km short on paper.

**Two gaps are too long for one edge** and are handed to G3 as missing line segments, since a single edge there would stand in for a whole line and its stations:

- **Dibrugarh – Harmuti Jn**, 161 km official against 302.7 km in the graph. The Assam north-bank line, consistent with G1 finding North Lakhimpur, Dhemaji and Gogamukh missing.
- **Siddipet – Manoharabad**, 75 km, with no path in the graph at all. This is the disconnected component 3 that G1's `SIPT` alias also ran into.

## E-700's 27 candidates, closed out

| Disposition | Count |
|---|---|
| Resolved by G5 or G6 | 12 |
| Not missing — the graph already routes along the line | 9 |
| Length error on an existing edge → lengths gap | 5 |
| Not missing — the 2017 distance is wrong | 1 |

The last one is worth stating. **Dhaulpur – Morena**: the 2017 timetable says 16 km, the 2024 data says 27–28 km across 40 trains, the straight line is 24 km, and the graph has 27.07 km. The graph was right and the 2017 figure is wrong. Using both years together is what caught it.

## Verification

| Measure | v1.3 raw | +G5 | +G5 +G6 |
|---|---|---|---|
| edges | 9,638 | 9,780 | 9,801 |
| components | 18 | 18 | 18 |
| IRN agreement within 5% | 82.70% | 82.72% | **82.75%** |
| route error 2024 | 0.93% | 0.71% | **0.71%** |
| route error 2017 | 1.99% | 1.75% | **1.73%** |
| off-spine triples | 3,691 | 2,932 | **2,924** |
| off-spine detour | 93,773 km | 51,968 km | **51,850 km** |
| edges shorter than their straight line | 1 | 85 | 92 |

G6's effect is small by design: G5 had already taken the large detours. The value here is the 88 reclassifications, which stop a future pass from "fixing" links that were never broken.

## Files

- `g6.py` — candidate selection and the alignment test. `python g6.py <root> <G5 out dir> out`
- `verify.py` — measures v1.3 raw, +G5, +G5+G6. `python verify.py <root> <G5 out dir> out out`
- `out/links_added.csv` — the 21 links with evidence
- `out/not_missing_already_routed.csv` — the 88, each with the path that already serves it
- `out/missing_line_segments.csv` — the 2 handed to G3
- `out/e700_candidates_recheck.csv`, `out/e700_still_open_disposition.csv` — the original 27, closed out
- `out/OVERRIDES_G6.csv`, `out/verification.csv`
