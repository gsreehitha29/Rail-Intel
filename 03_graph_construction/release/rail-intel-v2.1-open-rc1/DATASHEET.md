# Datasheet — Rail-Intel v2.1-open-rc1

## What it is
A graph of Indian Railways' running lines. Nodes are stations (with the station code where one is
known) and junctions; edges are track sections between them, with length, gauge and electrification
where OpenStreetMap tags them. It is built from OpenStreetMap track and stations
(extract of 2026-10-03 20:20 UTC), placed against the station list of Wikidata, joined to the 2017
timetable for service, and assigned states from datameet's boundaries.

## Size
| | |
|---|---|
| Nodes | 11,809 (9,507 stations, 2,302 junctions) |
| Sections | 13,051; 69,200.7 km |
| Components | 8; the giant holds 99.72% of nodes and 99.65% of stations |
| Independent cycles | 1,250 (physical), 420 (places view) |
| Places view | 9,924 nodes (9,507 stations, 417 junctions), 10,336 sections; station degree up to 6 |

## Columns that need care
- `length_source`: `osm_track` (measured along track) or `timetable_2017` (a 2017 distance, used for
  2 sections with no OSM track). `length_chord_km` is the straight line between the ends.
- `joins`: how a section came to exist beyond plain track: `throat` (service track inside a station,
  309 sections), `join_A`, `join_A2` (pieces joined at a shared station or short gap),
  `join_C` (timetable distance). Each is listed in `provenance/`.
- `station_code`: 9,404 stations have a code. 93 have none (`OSM:<id>`);
  14 keep `code~<id>` because OSM puts one code on stations far apart, resolved against the
  timetable where it could be (see `provenance/code_conflicts.csv`).
- `coordinate_source`: `osm`, `wikidata` (351 stations placed from Wikidata onto the nearest
  track), or `osm_track` (junctions). `track_lon`/`track_lat` is where the station meets track.
- `scheduled_2017`, `trains_2017`: from the 2017 timetable. The file has no running days, so these are
  scheduled trains, not trains per day. 8,065 stations and 89.9% of route km have a 2017 train.
- `state`: filled for 99.99% of nodes (datameet Admin2, point in polygon). `zone_code` is empty:
  no open source.

## Accuracy
Section lengths are measured, not copied: the build used timetable distances in only two joins.
The checks below use a separate 2024 timetable (IIT Kharagpur) that is not redistributed.

| Check | This graph | Esri-derived v1.4.1 |
|---|---|---|
| Station-pair distances within max(1 km, 5%) of official | 94.0% | 82.7% |
| Train-route median error | 0.31% | 0.72% |
| Train routes within 5% | 99.3% | 95.7% |
| 423 benchmark sections within 5% | 51.3% | 48.2% |
| Cut points that agree with v1.4.1 (served network) | 97.4% | |
| 2017 trains routable | 10,729 trains; 12 unroutable | |

## Changes from v2.0-open
Three defects found by the Phase 2 audit are fixed (D-071); everything else is unchanged in method.
- **Stations bind every track within 100 m (D-073).** v2.0 attached each station to one track point.
  Platform tracks at termini were then pruned, and some through stations were left on a stub off
  the line. A short trip into CSMT, for example, was routed 14.2 km for 1.3 km. v2.1 binds the
  nearest point of every kept track within 100 m of the station's OSM point or track point. No track
  is added and no coordinate moves.
- **Renamed stations carry their 2017 trains (D-072).** 19 older timetable codes (BCT, MGS, ALD,
  HBJ, FD, PBH, ...) are added to `station_code_crosswalk.csv` as aliases.
- **Edge ids carry the version:** `v2.1:<u>|<v>` (places view `v2.1p:`). Node ids are unchanged.

## Known properties
Written down rather than hidden; see the issue register for the full list.
- A station node joins every track at the station. A path through a station node may therefore be a
  passenger transfer, not a through train movement, as at the CSMT concourse. Termini usually have
  degree 1: every track leaves through one approach corridor, drawn as one section.
- Never filter on `joins`: `throat` marks every section that *contains* a throat link, some over
  30 km long, and dropping them cuts off termini.
- Four through stations still sit on a stub (PRES, RPM, BNZ, GTNR). The Chennai Moore Market
  approach is folded into the main-line route (MAS to BBQ 3.35 km against about 1.8 km). Some
  timetable stops have no station in OSM (Moore Market, Vashi, Ravli Jn) and are skipped.
- A station merged from several OSM points reports one point's coordinate, so `length_chord_km`
  can exceed `length_km` where the track meets the station at another point.
- Parallel tracks are collapsed to one section; the physical graph keeps junction areas as they are,
  so it has more cycles than a station-level view. Use `places/` for structure.
- Track tagged as running but with no 2017 train stays in: 10.1% of km has no 2017 service.
- Station coverage follows OSM: 4 stations have no track; some lines closed since 2017
  leave 85 of 27,997 2017 station pairs unroutable.
- Gauge is known for 98.8% of km and electrification for 96.7%.
- The graph is a physical network. It carries no speed, capacity or timetable.

## Intended use
Network structure, criticality, accessibility and resilience analysis; a base for service layers.
Not for operations or safety-critical routing.

## Reproduction
`manifest.json` lists the inputs with hashes and the build code. The same inputs and code produce the
same files byte for byte.
