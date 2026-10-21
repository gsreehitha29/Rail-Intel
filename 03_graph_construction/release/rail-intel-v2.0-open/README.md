# Rail-Intel v2.0-open

A station-level graph of the Indian railway network, built from open data only.

- 9,507 stations and 2,794 junctions; 13,560 sections; 70,304.6 route km
  (+1.2% against the official 69,439 km).
- Every section length is measured along OpenStreetMap track, except 2 sections
  (14.3 km) taken from the 2017 timetable where OSM has no track (`length_source`).
- Licence: ODbL 1.0 for the database, see LICENSE and ATTRIBUTION.md. Sources are all open.

| Folder | What |
|---|---|
| `graph/` | the physical graph: `nodes.csv`, `edges.csv`, `station_code_crosswalk.csv`. Exact lengths. Use it for distance and routing |
| `places/` | the same network with track points within 1 km merged into one place. Use it for structure: degree, cut points, redundancy |
| `service_2017/` | scheduled trains per consecutive-stop pair from the 2017 timetable. `graph/edges.csv` carries `trains_2017` per section |
| `provenance/` | every join, throat link, Wikidata placement and code-conflict decision, with its evidence |
| `DATASHEET.md` | what the data is, how it was made, what it can and cannot do |
| `manifest.json`, `SHA256SUMS` | every file, row count and hash, and the inputs it was built from |

Version: v2.0-open. Final release: the files and their hashes are fixed (see manifest.json and SHA256SUMS).

How to cite: see `CITATION.cff`.
