# Datasheet — Rail-Intel v2.0-open

## What it is
A graph of Indian Railways' running lines. Nodes are stations (with the station code where one is
known) and junctions; edges are track sections between them, with length, gauge and electrification
where OpenStreetMap tags them. It is built from OpenStreetMap track and stations
(extract of 2026-10-03 20:20 UTC), placed against the station list of Wikidata, joined to the 2017
timetable for service, and assigned states from datameet's boundaries.

## Size
| | |
|---|---|
| Nodes | 12,301 (9,507 stations, 2,794 junctions) |
| Sections | 13,560; 70,304.6 km |
| Components | 8; the giant holds 99.73% of nodes and 99.65% of stations |
| Independent cycles | 1,267 (physical), 498 (places view) |
| Places view | 10,024 nodes (9,507 stations, 517 junctions), 10,514 sections; station degree up to 8 |

## Columns that need care
- `length_source`: `osm_track` (measured along track) or `timetable_2017` (a 2017 distance, used for
  2 sections with no OSM track). `length_chord_km` is the straight line between the ends.
- `joins`: how a section came to exist beyond plain track: `throat` (service track inside a station,
  462 sections), `join_A`, `join_A2` (pieces joined at a shared station or short gap),
  `join_C` (timetable distance). Each is listed in `provenance/`.
- `station_code`: 9,404 stations have a code. 93 have none (`OSM:<id>`);
  14 keep `code~<id>` because OSM puts one code on stations far apart, resolved against the
  timetable where it could be (see `provenance/code_conflicts.csv`).
- `coordinate_source`: `osm`, `wikidata` (351 stations placed from Wikidata onto the nearest
  track), or `osm_track` (junctions). `track_lon`/`track_lat` is where the station meets track.
- `scheduled_2017`, `trains_2017`: from the 2017 timetable. The file has no running days, so these are
  scheduled trains, not trains per day. 8,049 stations and 89.4% of route km have a 2017 train.
- `state`: filled for 99.99% of nodes (datameet Admin2, point in polygon). `zone_code` is empty:
  no open source.

## Accuracy
Section lengths are measured, not copied: the build used timetable distances in only two joins.
The checks below use a separate 2024 timetable (IIT Kharagpur) that is not redistributed.

| Check | This graph | Esri-derived v1.4.1 |
|---|---|---|
| Station-pair distances within max(1 km, 5%) of official | 93.6% | 82.7% |
| Train-route median error | 0.38% | 0.72% |
| Train routes within 5% | 99.2% | 95.7% |
| 423 benchmark sections within 5% | 50.8% | 48.2% |
| Cut points that agree with v1.4.1 (served network) | 96.8% | |
| 2017 trains routable | 10,725 trains; 12 unroutable | |

## Known properties
Written down rather than hidden; see the issue register for the full list.
- Parallel tracks are collapsed to one section; the physical graph keeps junction areas as they are,
  so it has more cycles than a station-level view. Use `places/` for structure.
- Track tagged as running but with no 2017 train stays in: 10.6% of km has no 2017 service.
- Station coverage follows OSM: 4 stations have no track; some lines closed since 2017
  leave 121 of 27,952 2017 station pairs unroutable.
- Gauge is known for 98.9% of km and electrification for 96.9%.
- The graph is a physical network. It carries no speed, capacity or timetable.

## Intended use
Network structure, criticality, accessibility and resilience analysis; a base for service layers.
Not for operations or safety-critical routing.

## Reproduction
`manifest.json` lists the inputs with hashes and the build code. The same inputs and code produce the
same files byte for byte.
