# E-702 — gap G1: station-code crosswalk

**The gap.** 335 station codes used by current (Sept 2024) railway data have no node in graph v1.3, so 3,719 stop records — 4.4% of all stops — were silently dropped by any join. The cause is a wave of station renamings (Mughalsarai → DDU, Allahabad → Prayagraj, Habibganj → Rani Kamalapati) plus stations and lines the graph never had.

**Status: filled and verified.** Stop coverage rises from **95.6% to 98.6%**, recovering **2,524 stop records**, with route accuracy unchanged (median error 0.92% → 0.93%).

## How each code was resolved

No hand-written rename list. Every decision rests on four signals plus two hard vetoes:

| Signal | What it is |
|---|---|
| name | Fuzzy match against the node's name, plus OSM `old_name`/`alt_name`/`official_name` and Wikidata aliases |
| position | Distance from an OSM/Wikidata coordinate anchor to the node |
| route | The unknown code sits between two stops the graph knows, with cumulative km on each. A true alias reproduces both km gaps when walked over the graph |
| retired | **The decisive one.** A rename retires the old code. Of the renames confirmed by hand (MGS, JHS, HBJ, CSTM, BCT, GR, MUV, HBD, UHP, BIH, FD, ALD, ACOI), not one still appears in the 2024 timetables |

**Veto 1 — co-occurrence.** A code cannot be an alias of a node that the same train also calls at. This is what separates `Ayodhya Cantt → FAIZABAD JN` (correct: code retired, 0.02 km away) from `Ayodhya Cantt → AYODHYA` (wrong: both stations are live and 10 trains call at both).

**Veto 2 — still live.** If the candidate's own code still runs in 2024, it was never renamed away. This rejected `New Barauni → BARAUNI JN`: both are live stations 1.9 km apart.

A rename is one-to-one, so when two codes claimed the same node the better-supported claim won and the other went to review. That is what separated New Haflong from Jatinga.

## Results

| Outcome | Codes | 2024 stops |
|---|---|---|
| **alias** — the graph has this station under another code | 68 | 2,524 |
| **missing_station** — anchored, but the graph has no such station | 228 | ~1,000 |
| **unresolved** — needs a human look | 39 | ~195 |

All 68 aliases have a retired old code. 7 were accepted without name support; every one is within 0.25 km of its node, i.e. the same point.

## Verification

Routing the 2024 trains twice, with and without the crosswalk:

| | before | after |
|---|---|---|
| stop rows matched | 81,336 (95.6%) | 83,860 (98.6%) |
| median route error | 0.92% | 0.93% |
| adjacent duplicate stops | 0 | 0 |

56 of 65 measurable aliases leave route error unchanged (±1%). The six that move it are all **exact name matches within 0.9 km**, so they are not bad mappings — they expose defective track in the graph, and are leads for G6/G9:

- `BVU` Balipara and `MZS` Murkongselek (+145%) sit on the Assam corridor already known to carry a 132 km edge with 18 declared stations and none matched.
- `HMY` Harmuti (+17%), `CBY` Khambhat (+8%), `ARPR` Alirajpur (+6%), `KTGG` Karatagi (−15%).

One alias, `SIPT` → `JN::Siddipet`, targets a node in disconnected component 3, which leaves 2 trains unroutable. The mapping is right; the disconnection is gap G4.

## Notable findings

- **Kollam Jn (QLN) is absent from the graph** — 151 stops in one month, the single biggest unmatched station. The nearest node is Kilikollur, 5.4 km away and a different live station.
- 228 stations are genuinely missing, concentrated on lines the graph lacks: the Assam north bank (North Lakhimpur, Dhemaji, Gogamukh), the Nangal–Una line (Anandpur Sahib, Nangal Dam, Rupnagar), the Hassan–Bengaluru line (Shravanabelagola, Channarayapatna) and the Tamil Nadu coastal line (Pattukkottai, Peravurani, Mutupet). These feed G3.

## Files

- `build_crosswalk.py` — resolver. `python build_crosswalk.py <root> out`
- `verify.py` — applies the crosswalk, re-routes, measures. `python verify.py <root> out out`
- `resolve.py` — shared helper; every later join should use it rather than matching codes itself
- `out/crosswalk.csv` — one row per code with evidence, score and verification columns
- `out/OVERRIDES_G1.csv` — the 68 aliases as override rows
- `out/report.json`, `out/verification.json`

## Thresholds

Accept at score ≥ 2.0; anchor search 25 km; alias distance ≤ 6 km; route tolerance max(4 km, 18%); name strong ≥ 0.86, weak ≥ 0.62. All are in `TH` at the top of the script and are echoed into `report.json`.
