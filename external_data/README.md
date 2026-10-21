# external_data — datasets acquired 2026-10-05

Downloaded to close the gaps in `claude/data-requirements-v1-2.md` (project doc).
Every file was fetched from a pinned GitHub commit. URL, commit, byte size,
SHA-256 and retrieval time per file are in `download_manifest.json`.
Only GitHub was reachable from the build environment, so all sources below are
GitHub copies; the licence column states the licence of the **original** data.

**Nothing here is wired into the graph yet.** These are inputs for v1.3.

| Folder | What it is | Original source | Licence (as found) | Closes |
|---|---|---|---|---|
| `timetable_2017_datagovin/` | Indian Railways timetable, 22 Dec 2017: 11,113 trains, 186,124 stop rows, cumulative `Distance` per stop | data.gov.in (OGD India), mirrored in `itzmeanjan/indian-railway` | GODL-India for the data (mirror repo is MIT, covering its code) | edge lengths, missing stations, speeds |
| `timetable_2015_datagovin/` | Same format, 3 Aug 2015: 2,810 trains, 69,006 rows | data.gov.in, mirrored in `Anuj0803/Indian-Railway-Trains-TimeTable` | GODL-India (mirror has no licence file) | cross-check of the 2017 file |
| `iitkgp_rstgcn_network_2024/` | IIT Kharagpur RSTGCN data: `IRN_edges.csv` (consecutive-stop distances), `stations_zones_mapping.json` (4,735 stations), Sept 2024 routes and delays | `KoyenaChowdhury/RSTGCN`; paper: IEEE T-ITS 2026, arXiv:2510.01262 | **No licence stated.** Use for research with citation; do not redistribute without asking the authors | edge lengths, zones, delays |
| `state_boundaries_datameet/` | `Admin2.*` shapefile: 36 states/UTs (includes Telangana, Ladakh, merged DNH&DD) | `datameet/maps` | CC BY 4.0 (repo README); geoBoundaries lists the same data as CC BY 2.5 IN | states, AP/Telangana split |
| `india_outline_soi_datameet/` | `india-soi.geojson`, India outline dissolved from Census 2011 / Survey of India districts | `datameet/maps` | CC BY-SA 2.5 / ODbL (per upstream README) | correct boundary for published maps |
| `running_days_prasenjit27/` | 5,208 trains with weekly running days; 8,990 stations | `prasenjit-27/Indian-Railway-Data` | MIT, **origin of running days not stated** | running days (checks only) |

## Relevance checks (run against graph v1.2)

- **Official distances.** The three timetable sources together give an official
  stop-to-stop distance for **6,995 of 9,638 edges (72.6%, 69.8% of km)**,
  including 1,571 of the 2,735 straight-line edges and 66 of the 261 edges shorter
  than their straight line. The sources agree with each other: same pair within
  2 km in 94.4% (2015 vs 2017) and 96.3% (2017 vs 2024) of cases.
- **Our lengths vs official.** On matched edges the median ratio is 1.008, but only
  60% are within 10%. For 5% of edges the official distance is at least 26% shorter
  than ours, and for another 5% it is at least 58% longer. This needs an
  edge-by-edge look before replacing lengths.
- **Missing stations.** 759 station codes appear in the timetables but not in the
  graph. The 2017 timetable covers 87.9% of our 8,621 station nodes.
- **States.** Point-in-polygon assigns a state to 2,301 of the 2,308 stateless
  nodes that have coordinates. Agreement with station-master labels is 95.2%; most
  differences are naming (Delhi NCT/Delhi) or old Andhra Pradesh labels now in
  Telangana. Of the 388 AP-ambiguous nodes, 149 fall in Telangana.
- **Zones.** The IIT KGP mapping covers 50 of the 98 nodes with no zone. It agrees
  with our zone on only 85.9% of shared nodes, so check this before using it.
- **Running days (prasenjit).** Running days look real (4,369 daily trains, the rest
  1 to 6 days a week) and the station list matches datameet for 8,697 of 8,990
  stations. Its per-stop `distance` field is **0 for every non-origin stop**, so it
  carries no distance information.

## Still to download by hand (DONE 2026-10-05, see below)

Both sites are blocked from the build environment. Download in a browser and put
the files in the folders named below.

**Wikidata stations** → `external_data/wikidata_stations/`. Open
https://query.wikidata.org, paste the query below, run it, then Download → CSV.
Licence: CC0.

```sparql
SELECT ?item ?code ?itemLabel ?coord ?adminLabel ?stateLabel ?altLabels WHERE {
  ?item wdt:P5696 ?code .
  OPTIONAL { ?item wdt:P625 ?coord }
  OPTIONAL { ?item wdt:P131 ?admin }
  OPTIONAL { ?item wdt:P131+ ?state . ?state wdt:P31 wd:Q131541 }
  OPTIONAL { SELECT ?item (GROUP_CONCAT(DISTINCT ?a; separator="|") AS ?altLabels)
             WHERE { ?item wdt:P5696 [] ; skos:altLabel ?a . FILTER(LANG(?a)="en") } GROUP BY ?item }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```
(`Q131541` is "state of India". Add `wdt:P197` for adjacent stations if wanted.)

**OpenStreetMap rail** → `external_data/osm_india_rail/`. Get the free
shapefile download for India from https://download.geofabrik.de/asia/india.html
(if India is split into zones there, download each zone). Keep
`gis_osm_railways_free_1.*` and `gis_osm_transport_free_1.*`. Licence: ODbL.
Use for checking only until the team decides on share-alike.

## Licence notes found while doing this

- `01_data_engineering/railways-master/` is byte-identical to `datameet/railways`
  (all four files match upstream git blob hashes), and that repository's README
  states **CC0**.
- `01_data_engineering/Railway_Network_.csv` has exactly the field names of Esri
  India's Living Atlas layer "Railway Network of India" (owner `esri_IN_content`;
  credits Indian Railways, India Rail Info, Esri India; built partly from
  OpenStreetMap). That item states the **Esri India Master Terms of Use** and that
  users are **not permitted to export data for offline use**. If this is where the
  file came from, the derived graph probably cannot be released as open data.
  Needs confirmation from whoever downloaded it.

## Added by hand 2026-10-05 (Bhuvanesh)

| File | Content | Licence | Check |
|---|---|---|---|
| `*-zone-261003.osm.pbf` (6 files, 1.7 GB) | Geofabrik India sub-regions: central, eastern, north-eastern, northern, southern, western | ODbL 1.0 | all six read completely; OSM data timestamp 2026-10-03 20:20 UTC |
| `wikidata_stations.csv` | 9,661 rows, 9,585 station codes, 9,651 with coordinates, 625 with aliases | CC0 | `stateLabel` column is empty (the state sub-query matched nothing) |

SHA-256 and sizes are in `download_manifest.json` (folder `.`).

`osm_india_rail/` holds what was extracted from the six zone files: rail ways
(`rail_ways_<zone>.parquet`, with node lists and WKB lines) and station-like nodes
(`rail_stations_<zone>.parquet`). Derived from OSM, so ODbL applies.
`osm_india_rail/_to_delete/` holds a leftover from an interrupted run; safe to delete.

### What the new data shows (against graph v1.2)

- **OSM rail network:** 112,028 rail ways; 111,476 km of main-line track excluding
  industrial/military/tourist lines (track km, not route km: double lines are
  usually two ways). Gauge is tagged on 96.8% of that, electrification on 94.9%,
  **maximum speed on only 7.6%**, and the `tracks` tag almost never.
- **OSM stations:** 10,302 stations and halts, 9,574 with a station code. They match
  7,816 graph stations (90.7%). 8,990 of 9,094 graph nodes with coordinates snap to
  the OSM network within 1.5 km.
- **Lengths:** on 4,992 edges with an official timetable distance, the OSM
  shortest path is within max(1 km, 5%) of the official figure for **82.4%** of
  edges, against 75.0% for our current length and 72.0% for the straight line.
  For 10-50 km edges: 87% (OSM) vs 43-70% (ours).
- **Missing stations:** 1,618 OSM station codes are not in the graph. 773 lie within
  1 km of an existing edge (389 of them on suspect-long edges) and would split 523
  edges, including 205 of the 739 suspect-long ones. 269 lie more than 5 km from
  any edge (lines absent from the graph). Of the 570 timetable codes missing from
  the graph, 536 can now be located (OSM 511, Wikidata 445).
- **Missing coordinates:** 166 of the 293 master stations without coordinates get
  one (OSM 157, Wikidata 121).
- **Small components:** OSM track joins 15 of the 17 small components to the main
  network, 5 of them at 0 km and most within 6 km.
- **Dead-end junctions:** for 145 of 262 snapped dead-end junctions, OSM shows a
  branching point within 300 m, so the missing branch is real.
- **Junction identity:** 119 junctions match a Wikidata station name or alias within
  3 km; for 14 of them that station is already a separate graph node (duplicates).
- **Location errors:** 34 graph stations are more than 10 km from both their OSM and
  their Wikidata position, so the graph coordinate is probably wrong. Wikidata
  coordinates equal the graph's for about 90% of stations, so Wikidata is not an
  independent check of location; OSM is (80.3% within 0.5 km).
- **Zones:** OSM station `operator` gives a zone code for 79 of the 98 zone-less
  nodes (IIT KGP adds none beyond those).
- **Speeds:** still open. OSM `maxspeed` covers 7.6% of main-line km, and speeds
  derived from the fastest timetabled train are worse than the current method
  (MAE 24.1 vs 11.4 km/h in grouped cross-validation).
