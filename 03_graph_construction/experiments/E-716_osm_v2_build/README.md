# E-716 — graph v2.0-open from OpenStreetMap (D-060)

A second, independent graph built from OpenStreetMap alone, by stages O1–O8 of the build
roadmap. Kept apart from v1.4.x (Esri-derived, not redistributable) so that this one can be
published under ODbL. numpy, pandas and scipy only.

| Milestone | Stages | Command | Status |
|---|---|---|---|
| C1 | O1 filter · O2 collapse parallel tracks · O3 snap stations | `make osm-c1` (~40 s) | done 2026-10-19 |
| C2 | O3b Wikidata placement · O5a throats · O5 joins · O4 contract · O6 service | `make osm-c2` (~4 min, three steps) | done 2026-10-19 (D-063, D-064, D-065) |
| C3 | O7 validate against v1.4.1 | `make osm-c3` (~1 min) | done 2026-10-20, checkpoint CP1 |
| C4 | O8 release | — | |

Output (working, not a release): `03_graph_construction/graph_v2_0_open/` — `open/nodes.csv`, `open/edges.csv`
and `station_code_crosswalk.csv` in the v1.4 schema; `work/` for reports and audit lists; the 2024 service
layer in `service_layer_v2_0_open/open/` (E-708's stage, unchanged).

## How C1 works

- **O1 filter.** Keeps `railway=rail|narrow_gauge` with no `service` tag, usage main, branch,
  freight, passing loop or untagged, and not operated by a non-IR body (decision table
  `NOT_IR`: DFC, RRTS, industrial, port, foreign, museums). Every dropped km is counted by reason.
- **O2 collapse.** Track is sampled every 10 m in EPSG:7755 metres. Taking the shortest chains
  first, any stretch that runs within 15 m of another kept, gauge-compatible track for at least
  100 m is removed, so of two side-by-side tracks one remains. Only the parallel stretch goes,
  not the whole chain. Loose ends left by a removal are re-joined to kept track within 30 m.
- **O2 check (D-065).** After the collapse, each removed stretch is tested: its two ends are put on
  the kept track and the distance between them along the network is measured. If the kept track does
  not replace the stretch (more than 1.3x its length + 0.2 km, or no path), the stretch is restored.
  Repeated until nothing more is restored. Geometry only.
- **O3 snap.** Each OSM station or halt joins the nearest kept track within 100 m; the rest are
  listed with the reason (usually a metro station).

The 15 m, 100 m and 30 m settings are read from calibration tables written by the run
(`calib_track_spacing.csv`, `calib_snap_distance.csv`) and fixed as D-062.

## How C2 works

- **Stations.** Snapped OSM stations inside India's outline, less metro stations no timetable knows.
  Same code within 2 km is one station (several platforms or lines); further apart it is a conflict, listed.
- **O3b.** 440 timetable codes have no coded OSM station (Katpadi, Madurai, Coimbatore among them: OSM
  maps them as areas, which the extract does not hold). From Wikidata (CC0): an OSM station within 300 m
  makes the code an alias (mostly renamed codes: JHS→VGLJ, HBD→NDPM); else a station is placed on track
  within 100 m; else the code stays unresolved.
- **O5a station throats (D-065).** Through routes in stations often run over crossovers and station
  tracks tagged `service=*`, which O1 sets aside. Where such track (at most 2 km) joins two points of
  kept line and the network between them is more than 1.3x the throat + 0.5 km, it is added at its
  measured length. Listed in `work/c2_throat_links.csv`.
- **O5 joins**, each with its evidence in `work/c2_joins.csv`:
  A along OSM running track with at most 2 km of yard track; A2 a piece whose track ends within 100 m of a
  main-network station (one station, two gauges); B a 2024 train plus OSM track set aside as not running;
  C a 2024 train and no OSM track, at the timetable distance if it fits the v1.3 band.
- **O4.** Dangling track pruned; degree-2 points spliced out (a duplicate route keeps the shorter); a
  second line of up to 3 km round a station dropped. Junctions stay as `JN:` nodes.
- **Code conflicts.** Where one code sits on two stations more than 2 km apart, the candidate whose
  network distances to timetable neighbours match takes the code; the other keeps `code~osmid`.
- **Places view (D-066).** Track points within 1 km along the track are one place: junction clusters
  become one junction, a junction within 1 km of a station joins it. `place_id` on every physical node;
  the view is written to `open/places/`. Lengths in `open/` stay exact.
- **O6.** E-708's service stage on this graph, through the v1.4 loaders (2024, local build only, D-067),
  then `service17.py`: the open GODL 2017 timetable on the same graph (`service_layer_v2_0_open/open_2017/`).
- **Attributes.** `served_2024`, `scheduled_2017`, `line_status`; `state` from datameet Admin2 (CC BY 4.0);
  `track_lon`/`track_lat` where the station meets its track.

## Running it

`make osm-c1`, then `make osm-c2`, which runs four stages: `--stage=c1` caches C1 outside the repo,
in `~/.cache/rail-intel/`; then `--stage=joins`, `--stage=graph`, `--stage=service`. Then `make osm-c3`.

On the laptop the stages take 72, 34, 16 and 40 s, and the outputs are byte-identical to the cloud build.
