# rail-intel-v2.0-open — known properties found after the lock

The locked package (`rail-intel-v2.0-open.zip`, sha256 `b1e39081…eeda`) is unchanged; its
`DATASHEET.md` is covered by `SHA256SUMS` and is not edited. This file sits beside the lock
record and lists what the Phase 2 audit (Nov 2026) established about the release. Issue IDs refer to
`docs/V2_ISSUES.md`; scope decision D-071.

## Fixed in v2.1 (do not rely on these parts of v2.0-open)

- **Major termini are dead ends (V2-26).** CSMT, HWH, MAS, MMCT and SDAH have degree 1; platform
  approaches were pruned in the build. Their approach edges are reported as bridges (the four
  busiest bridges in the graph are of this kind), and some short trips route far round:
  CSMT→MSD 14.21 km for 1.34 km; JND→TORA 181 km for 13.4 km; MJ→MRWS unroutable.
- **Some through stations hang off the line (V2-27).** 22 stations where most 2017 trains pass
  through (e.g. MDP, CRP, SZM, BHS, TMR, RPM) sit on a stub as degree-1 leaves. Do not read
  their degree, cut-point status or stub bridges as real.
- **Renamed stations carry no 2017 trains (V2-28).** The 2017 timetable uses older codes
  (BCT, MGS, ALD, HBJ, FD, PBH, …) that the crosswalk does not map, so MMCT, DDU, PRYJ, RKMP and
  others show `scheduled_2017 = False` / `trains_2017 = 0` on their own edges.

## Properties that stay

- **Never filter on `joins` (V2-30).** `joins='throat'` marks every section that *contains* a
  throat link, up to 33.5 km long, not the throat alone. Dropping those edges splits the graph from
  8 components into 54 and cuts off CSMT and Anand Vihar.
- **Places-graph adjacency is not train service.** Absorbing junctions makes 1,245 station pairs
  directly adjacent in `places/`. Distances are preserved; use `service_2017/` for service.
- **Some timetable stops have no node (V2-29).** 65 codes (Moore Market, Vashi, Ravli Jn, …)
  are absent from the OSM station extract; trains skip those stops, route length is unaffected.
- **1,442 stations have no 2017 trains** because their codes do not appear in the 2017
  timetable at all. This is coverage of the source, not a graph defect.
- **Two sections use a timetable length** (V2-24, already in the datasheet).
- **Sealdah South** is not modelled as a separate terminal (V2-31, on hold).
