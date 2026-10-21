# E-715 — OpenStreetMap probe: what an open rebuild can give us, measured

**Status:** done (2026-10-19). Read-only: nothing in v1.4 or v1.4.1 reads its output (D-050 stands).

**Question.** Can the OpenStreetMap zone extracts we already hold support an openly licensed
rebuild of the graph (v2.0-open), and what engineering would it need?

**Run.** `python3 03_graph_construction/experiments/E-715_osm_probe/osm_probe.py . 03_graph_construction/experiments/E-715_osm_probe/out`
Inputs: `external_data/osm_india_rail/rail_{stations,ways}_*.parquet` (six zones), plus the v1.4 release
(`open/nodes.csv`, `open/edges.csv` with its `official_km` column, `station_code_crosswalk.csv`). Output: `out/E-715_osm_probe.json`.

"Mainline" below = `railway` in {rail, narrow_gauge}, `usage` not industrial/military/tourism, no `service` tag.

## Results

| Measure | Value |
|---|---|
| Mainline track length | 111,476 km in 55,809 ways (official route km 69,439; v1.4 74,850) |
| Tag coverage, share of mainline km | gauge 96.8%, electrified 94.9%, maxspeed 7.6%, tracks 0.02% |
| Electrified, share of tagged km | 96.7% |
| Topology | 611,929 nodes, 510 components, giant holds 93.0% of km, 115 components over 10 km, 9,801 junction nodes, 2,892 dead ends |
| Stations | 10,302 station/halt; 9,573 with a code; 9,433 unique codes; 11.9% sit on mainline track |
| Our coded stations found in OSM | 7,815 of 8,621 (90.6%) |
| Our 228 missing stations found in OSM | 223, Kollam Jn (QLN) included |
| OSM codes not in our graph | 1,618 (unchecked; may include metro, sidings, closed halts) |
| Length vs timetable, 423 pairs | OSM 46.1% within 5% (median error 5.67%); v1.4 48.2% (5.72%) |
| Same, on 19 v1.4 floor sections | OSM 15.8% within 5%; v1.4 0% |

**Caveat on the length comparison.** It uses only pairs whose two stations both sit on OSM track (11.9% of
stations), routes over the uncollapsed track, and samples 800 edges with `official_km` (423 routable). It is
indicative, not a full comparison; C3 in the roadmap repeats it on the collapsed, snapped graph.

## What it means

- Parallel tracks are separate ways: length cannot be summed until they are collapsed (+61% over official).
- The network is fragmented like our source was, and stations are points beside the line: a rebuild needs
  collapse, snapping, contraction and stitching stages. Design: roadmap stages O1–O8 (D-060).
- Code coverage is strong, so stations join on codes; gauge and electrification are usable attributes.
- Lengths tie overall; OSM is better exactly where v1.4 is weakest (floor sections).
- Licence: ODbL, share-alike. A derived graph must be released under ODbL and kept apart from the
  Esri-derived v1.4.x (D-057).
