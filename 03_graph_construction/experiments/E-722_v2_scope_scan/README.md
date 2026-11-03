# E-722 — v2.1 scope scan (remediation plan, Step 1)

Read-only measurement against `rail-intel-v2.0-open` and its Stage C1 work files. Nothing in the release or the build is changed.

```bash
python terminal_prune_scan.py 100     # and 200: replays O4 prune, finds pruned track near stations
python unresolved_codes.py            # 2017 timetable codes that resolve to no node
```

Outputs are in `out/`:
- `terminal_prune_scan_r{100,200}.csv`: pruned pieces whose buffer stop lies within R of a station the piece does not attach to.
- `lost_station_links_r200.csv`: the pieces that joined two stations, with 2017 timetable support and the release detour.
- `degree1_stations.csv`: all 307 degree-1 stations, classified by how many 2017 trains pass through rather than start or end.
- `unresolved_codes_2017.csv`: the 87 unresolved codes and their candidate targets.

## Measurements

| Question | Result |
|---|---|
| Pruned track near a station (100 m / 200 m) | 79 / 138 stations; 7 / 14 pieces linked two stations |
| Degree-1 stations | 307: 22 are through stations shown as dead ends (≥ 80% of 2017 trains pass through), 89 are termini or mixed, 196 have under 10 trains |
| Busiest bridges in v2.0 | The top 4 (CSMT 779, SDAH 745, HWH 697, MSD 344 trains) are all dead-end-station artifacts; 13 of the 48 bridges with ≥ 100 trains end at a degree-1 station |
| Unresolved 2017 codes | 87 codes / 2,149 stop rows. 10 are renames confirmed by E-702, 10 are name matches to review, 2 are renames found manually (ALD→PRYJ, ACOI→PCOI), 65 have no candidate |
| Stations missing from the OSM station extract | Moore Market (MMCC, 267 trains), Vashi (185), Ravli Jn (192), Sanpada, Wadala Rd. The track is present |
| 1,458 unscheduled stations | 15 are explained by unresolved codes; 1,442 have codes absent from the 2017 timetable (data coverage) |
| v2.0 downstream results | E-718/719/720 have not been run yet; no published v2.0 figure is affected |

## Stop-rule test (D-055) and proposed scope

The test: an analysis result is demonstrably wrong because of the graph, on a named reproducible case.

| ID (proposed) | Item | Named wrong result | Proposal |
|---|---|---|---|
| V2-26 | Terminal buffer stops pruned (CSMT, HWH SER lead, MAS MMC); lost station links JND–TORA, MJ–MRWS, SPN–SZN | CSMT→MSD 14.21 km for 1.34 km (172 trains each way); JND→TORA 181 km for 13.4 km; MJ→MRWS unroutable; top-4 bridges are artifacts | **v2.1** |
| V2-27 | Through stations shown as dead ends on a stub (22, e.g. MDP, CRP, SZM, BHS, TMR, RPM; KGP, RJT, PRLI borderline) | MDP (122 trains) and CRP (56) leaf edges counted as bridges; the stations can never be cut points | **v2.1**, same station-model decision as V2-26 (Step 4) |
| V2-28 | Station-code renames missing from the crosswalk (22 codes incl. BCT, MGS, ALD, HBJ, FD, PBH) | MMCT, DDU, PRYJ and RKMP show 0 scheduled trains in 2017 | **v2.1** |
| V2-29 | Stations absent from the OSM station extract (MMCC, VSH, RVJ, …; 65 codes with no candidate) | Trains skip them; routing distance unaffected | **property** (v2.2: needs a station source) |
| V2-30 | Throat tag spread onto long spliced sections (111 edges) | None found; misleading only if someone filters on it | **property** + datasheet warning |
| V2-31 | Sealdah South divisional model | None until restored | **hold** (decided in Step 4) |
| — | DSS\|STJT, GRX\|MBDD and 7 other short-vs-chord edges; ANVT throat; Thakurganj–Araria; TKMG\|UDPR; KKD gap; INDR/MHBD | None known | **Step 7 manual pass**; enters v2.1 only on a "fix" verdict |
| — | Places-graph adjacency, throat filtering, timetable-length joins (V2-24), isolated stations | — | **property** (Step 2 documentation) |
| — | Howrah Goods stub; Mumbai Central yard tracks 804/806/630 | — | **keep pruned** (audit no-go confirmed) |
| — | 1,442 stations with no 2017 timetable stop | — | **property** (data coverage) |
