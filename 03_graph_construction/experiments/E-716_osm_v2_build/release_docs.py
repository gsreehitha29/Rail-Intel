"""Text of the release package (E-716 P3). Each value is formatted with release.figures()."""

README = """# Rail-Intel {version}

A station-level graph of the Indian railway network, built from open data only.

- {stations:,} stations and {junctions:,} junctions; {edges:,} sections; {route_km:,.1f} route km
  ({route_km_vs_official:+.1f}% against the official 69,439 km).
- Every section length is measured along OpenStreetMap track, except {timetable_lengths} sections
  ({timetable_km} km) taken from the 2017 timetable where OSM has no track (`length_source`).
- Licence: ODbL 1.0 for the database, see LICENSE and ATTRIBUTION.md. Sources are all open.

| Folder | What |
|---|---|
| `graph/` | the physical graph: `nodes.csv`, `edges.csv`, `station_code_crosswalk.csv`. Exact lengths. Use it for distance and routing |
| `places/` | the same network with track points within 1 km merged into one place. Use it for structure: degree, cut points, redundancy |
| `service_2017/` | scheduled trains per consecutive-stop pair from the 2017 timetable. `graph/edges.csv` carries `trains_2017` per section |
| `provenance/` | every join, throat link, Wikidata placement and code-conflict decision, with its evidence |
| `DATASHEET.md` | what the data is, how it was made, what it can and cannot do |
| `manifest.json`, `SHA256SUMS` | every file, row count and hash, and the inputs it was built from |

Version: {version}. {status}

How to cite: see `CITATION.cff`.
"""

DATASHEET = """# Datasheet — Rail-Intel {version}

## What it is
A graph of Indian Railways' running lines. Nodes are stations (with the station code where one is
known) and junctions; edges are track sections between them, with length, gauge and electrification
where OpenStreetMap tags them. It is built from OpenStreetMap track and stations
(extract of {osm_date}), placed against the station list of Wikidata, joined to the 2017
timetable for service, and assigned states from datameet's boundaries.

## Size
| | |
|---|---|
| Nodes | {nodes:,} ({stations:,} stations, {junctions:,} junctions) |
| Sections | {edges:,}; {route_km:,.1f} km |
| Components | {components}; the giant holds {giant_share}% of nodes and {stations_in_main}% of stations |
| Independent cycles | {cycles:,} (physical), {place_cycles} (places view) |
| Places view | {place_nodes:,} nodes ({place_stations:,} stations, {place_junctions} junctions), {place_edges:,} sections; station degree up to {max_station_degree_places} |

## Columns that need care
- `length_source`: `osm_track` (measured along track) or `timetable_2017` (a 2017 distance, used for
  {timetable_lengths} sections with no OSM track). `length_chord_km` is the straight line between the ends.
- `joins`: how a section came to exist beyond plain track: `throat` (service track inside a station,
  {throats} sections), `join_A`, `join_A2` (pieces joined at a shared station or short gap),
  `join_C` (timetable distance). Each is listed in `provenance/`.
- `station_code`: {stations_coded:,} stations have a code. {stations_uncoded} have none (`OSM:<id>`);
  {stations_conflict} keep `code~<id>` because OSM puts one code on stations far apart, resolved against the
  timetable where it could be (see `provenance/code_conflicts.csv`).
- `coordinate_source`: `osm`, `wikidata` ({stations_wikidata} stations placed from Wikidata onto the nearest
  track), or `osm_track` (junctions). `track_lon`/`track_lat` is where the station meets track.
- `scheduled_2017`, `trains_2017`: from the 2017 timetable. The file has no running days, so these are
  scheduled trains, not trains per day. {stations_2017:,} stations and {km_2017}% of route km have a 2017 train.
- `state`: filled for {states_share}% of nodes (datameet Admin2, point in polygon). `zone_code` is empty:
  no open source.

## Accuracy
Section lengths are measured, not copied: the build used timetable distances in only two joins.
The checks below use a separate 2024 timetable (IIT Kharagpur) that is not redistributed.

| Check | This graph | Esri-derived v1.4.1 |
|---|---|---|
| Station-pair distances within max(1 km, 5%) of official | {irn}% | {irn_v14}% |
| Train-route median error | {route_med}% | {route_med_v14}% |
| Train routes within 5% | {route5}% | {route5_v14}% |
| 423 benchmark sections within 5% | {e715}% | {e715_v14}% |
| Cut points that agree with v1.4.1 (served network) | {cut_agree}% | |
| 2017 trains routable | {trains_2017:,} trains; {route17_unroutable} unroutable | |

## Known properties
Written down rather than hidden; see the issue register for the full list.
- Parallel tracks are collapsed to one section; the physical graph keeps junction areas as they are,
  so it has more cycles than a station-level view. Use `places/` for structure.
- Track tagged as running but with no 2017 train stays in: {km_no_2017}% of km has no 2017 service.
- Station coverage follows OSM: {stations_isolated} stations have no track; some lines closed since 2017
  leave {pairs_2017_unroutable} of {pairs_2017:,} 2017 station pairs unroutable.
- Gauge is known for {gauge_known}% of km and electrification for {elec_known}%.
- The graph is a physical network. It carries no speed, capacity or timetable.

## Intended use
Network structure, criticality, accessibility and resilience analysis; a base for service layers.
Not for operations or safety-critical routing.

## Reproduction
`manifest.json` lists the inputs with hashes and the build code. The same inputs and code produce the
same files byte for byte.
"""

LICENSE = """Open Database License (ODbL) v1.0 applies to this database ({version}).
Full text: https://opendatacommons.org/licenses/odbl/1-0/

You are free to share, create works from, and adapt this database, provided you
attribute it (see ATTRIBUTION.md), share alike any adapted database under the ODbL, and keep it open.

The individual contents are available under the Database Contents License (DbCL) 1.0:
https://opendatacommons.org/licenses/dbcl/1-0/
"""

ATTRIBUTION = """# Attribution — Rail-Intel {version}

Contains information from:

- OpenStreetMap, (c) OpenStreetMap contributors, ODbL 1.0 — track geometry, station positions, gauge,
  electrification. https://www.openstreetmap.org/copyright. Extract of {osm_date} (Geofabrik).
- Wikidata, CC0 — station codes and positions for stations OSM does not map with a code.
- datameet maps (Admin2 state boundaries), CC BY 4.0 — the `state` column.
  https://github.com/datameet/maps
- data.gov.in, Train Details timetable of 22 Dec 2017, Government Open Data License - India (GODL) —
  scheduled trains per section. https://data.gov.in
- Survey of India outline via datameet, used to exclude points outside India.

This database is a derived database of OpenStreetMap and is licensed under the ODbL.
"""

CITATION = """cff-version: 1.2.0
title: >-
  Rail-Intel: a station-level graph of the Indian railway network, built from open data ({version})
message: >-
  If you use this dataset, please cite it. It is a derived database of OpenStreetMap
  and is licensed under the ODbL 1.0; DATASHEET.md states what it supports and what it does not.
type: dataset
version: "{version}"
date-released: "{date}"
license: ODbL-1.0
abstract: >-
  A graph of Indian Railways' running lines: {stations:,} stations and {junctions:,} junctions
  joined by {edges:,} track sections, {route_km:,.1f} route km. Section lengths are measured along
  OpenStreetMap track, with gauge, electrification and state, and scheduled trains per section from
  the 2017 timetable. Built only from open inputs (OpenStreetMap, Wikidata, datameet, data.gov.in),
  with a places view for structural analysis, a record of every join and decision, and a manifest
  that reproduces the files byte for byte.
keywords:
  - railway network
  - Indian Railways
  - spatial network
  - network science
  - OpenStreetMap
  - graph dataset
  - reproducibility
authors:
  - family-names: Vinjamuri
    given-names: Bhuvanesh
"""

DOCS = {"CITATION.cff": CITATION, "README.md": README, "DATASHEET.md": DATASHEET, "LICENSE": LICENSE, "ATTRIBUTION.md": ATTRIBUTION}
