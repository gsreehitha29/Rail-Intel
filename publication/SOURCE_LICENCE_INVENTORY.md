# Source licence inventory

**Date:** 2026-10-04 · **Purpose:** reduce the "licence review" blocker on the
DOI deposit from an open question to a short list of genuinely undecidable
cases. **This is an engineering inventory, not legal advice** — the
undetermined rows need a human decision, and one of them needs the supervisor.

**Method.** Every input listed in `graph_v1.manifest.json` plus everything in
`reference_data/`, traced to the artifact in this repository that evidences its
origin. Where the repository contains no licence evidence, the row says so
rather than guessing: an inferred licence is worse than a known gap, because it
looks settled.

---

## 1. Primary inputs (the ones the graph is built from)

| Source | What it feeds | Origin evidence **in this repo** | Licence status |
|---|---|---|---|
| `01_data_engineering/Railway_Network_.csv` / `.geojson` — 119,446 GIS segments | all topology, geometry, gauge, speed, tracks, zone, bridge/tunnel flags | `corridors.csv.source_file` = `Railway_Network_.csv` for all 2,279 corridors. **No upstream URL, publisher, download date or terms recorded anywhere in the repository.** | **UNDETERMINED — blocking.** This is the single most important gap: it is the primary source for the entire artifact |
| `01_data_engineering/railways-master/{stations,trains,schedules}.json` | station master, train metadata, 416,970 stop records | `railways-master/README.md` credits Sanjay Bhangar and Sajjad Anwar, pointing to `sajjad.in/2016/08/gathering-indian-railways-data/`. A GitHub-style repository snapshot with **no LICENSE file included** | **UNDETERMINED.** Attribution is clear and recorded; terms are not. The upstream repository must be checked for a licence |
| `02_graph_inputs/graph_dataset/*` (7 files) | the frozen Phase 2 dataset the graph is built from | derived in-repo by `02_graph_inputs/pipeline/run_all.py`; hashes pinned in the manifest | **Ours to licence**, but inherits whatever the two rows above permit |

**The dependency that matters.** The graph is a derivative work of the GIS
dataset. If that dataset's terms prohibit redistribution of derivatives, the
artifact cannot be deposited under an open licence regardless of what the team
decides about its own code. **No further licence decision is worth making until
the first row is resolved.**

---

## 2. Reference data (validation only, never built into the graph)

These are used to *check* the graph, not to populate it, which is a materially
weaker use — but a deposited validation script that reads them still
redistributes them.

| File | Used by | Origin | Status |
|---|---|---|---|
| `1782901055294INDIANRAILWAYSYEARBOOK2024-25ENGLISH.pdf` | route-km validation (`F-019`) | Indian Railways Year Book 2024–25 — an official Government of India publication | Government publication; **GoI terms apply (likely permissive for reuse with attribution under NDSAP/GODL-India), to be confirmed** |
| `zone_electrification_2021.csv` | `E-102`, `E-400` gate (c) | per-zone BG route km + electrification | Derived from official figures; **no source URL recorded** |
| `RS_Session_267_AS_371_A_i.csv` | bridge-count validation (`F-030`) | Rajya Sabha Session 267, Q.371 — a parliamentary answer | Parliamentary record; **GoI terms, to be confirmed** |
| `Table-19.2-Zone-wise.csv` | **nothing** — was mis-cited as a route-km source (corrected in `E-102`) | zone-wise passengers/freight/earnings | Unused; **candidate for removal** |
| `PASSENGERS_AND_GOODS_CARRIED_AND_EARNINGS_1.xls`, `railway_key_stats_2023_24_2024_25.csv`, `Railway_Key_Statistics_1950-51_to_2013-14.txt`, `gauge_history_1947_1971_2025.csv`, `indian_railways_data_pack.xlsx`, `datafile.csv`, `Data_Bank.pdf` | **nothing currently** (`gauge_history` assessed and ruled out as `D-15`) | official statistics compilations | Unused; **do not deposit** what is not cited |
| `Indian_Railway_Stations_JSON-master/` | not used in the shipped build | station code/name/city JSON; README has no licence | Unused; **no LICENSE file** |
| `25826mimicassignment.pdf`, `Bhuvanesh-Sreehita-Abrar Project Idea.pdf` | internal | team documents | Internal — **exclude from any deposit** |

---

## 3. Our own outputs

| Artifact | Recommended licence | Note |
|---|---|---|
| `railgraph/` package, `experiments/`, `publication/evidence/*/run.py`, `Makefile` | **MIT or Apache-2.0** — code | unconstrained by the sources; `CITATION.cff` already exists |
| `docs/`, `publication/*.md` | **CC BY 4.0** — prose | unconstrained |
| `graph_v1/`, `graph_v1_1/` — the graph itself | **cannot be decided yet** | derivative of the GIS dataset; blocked on §1 row 1 |

Splitting the licence this way means the **method and the code can be
deposited and cited even if the dataset cannot** — which protects claim `C2`
(the construction method) and most of `C3` from a licence outcome that only
threatens `C1` (the artifact).

---

## 4. What a human has to do

| # | Action | Owner | Blocks |
|---|---|---|---|
| 1 | Establish where `Railway_Network_.csv` came from and under what terms | **Bhuvanesh** (acquired it) | **`C1` deposit — everything else is downstream** |
| 2 | Check the `railways-master` upstream repository for a LICENSE | Bhuvanesh | service layer redistribution |
| 3 | Confirm GoI reuse terms (GODL-India / NDSAP) for the Year Book and the Rajya Sabha answer | Bhuvanesh, with the supervisor | validation-script deposit |
| 4 | Decide whether unused `reference_data/` files ship at all | team | nothing — but shipping uncited data with unknown terms is pure downside |
| 5 | Pick the code and prose licences, add `LICENSE` files | team | nothing; can be done today |

**There is no `LICENSE` file anywhere in the repository right now** — not for
our own code either. Item 5 is unblocked, costs nothing, and should not wait
for items 1–3.

---

## 5. Recorded position

`D-036`. The honest statement for the paper's availability section until item 1
resolves:

> The construction pipeline, the analysis code and the documentation are
> released under an open licence. Redistribution terms for the underlying GIS
> source have not been established, so the derived graph is described and fully
> reproducible from the pipeline, with deposit of the artifact itself pending
> that determination.

That sentence is publishable as it stands, and it keeps `C2` and `C3` intact
regardless of how item 1 resolves.

## 6. Owner statement (2026-10-04)

Bhuvanesh Vinjamuri (data lead, who acquired the inputs): all inputs are
"open-source, found on random websites".

Recorded as a **user assertion, not a verified licence**. It does not close the
item in section 4, because:
- "Open" / "publicly downloadable" is not a licence. Without an explicit licence
  (ODbL, CC-BY, MIT, ...), default copyright applies and redistribution is not granted.
- "Random websites" means no recorded URL, publisher, retrieval date or terms,
  so the claim cannot be checked or cited.
- Share-alike licences (e.g. ODbL from OpenStreetMap-derived data) would
  bind the derived graph (C1); attribution-only ones would not.

Still needed per input: source URL, publisher, retrieval date, the licence text
as shown on that site (or a note that none is stated), and a saved copy of the page.
Until then the C1 dataset deposit stays gated; code (C2) and prose are unaffected.

## 7. Findings from source tracing (2026-10-05)

- **`railways-master` is datameet/railways, CC0 — verified.** All four files
  (`README.md`, `stations.json`, `trains.json`, `schedules.json`) match the git blob
  hashes of `github.com/datameet/railways` at HEAD, and that README states CC0.
  Section 4 item 2 can be closed once the team accepts this evidence.
- **`Railway_Network_.csv` — probable origin found, restrictive terms.** Its 15
  columns match the "Railway Tracks" layer of Esri India's Living Atlas service
  `Railway/IN_Railway_Network` (item "Railway Network of India", owner
  `esri_IN_content`, modified Jan 2025; credits "Indian Railways, India Rail Info,
  Esri India"; described as updated using OpenStreetMap and Ministry of Railways
  data). The item's licence is the **Esri India Master Terms of Use** and states
  that **users are not permitted to export data for offline use**. This is a schema
  match, not proof; Bhuvanesh to confirm where the file was downloaded from. If
  confirmed, the C1 deposit cannot proceed on this source, and the graph would
  need rebuilding from open inputs (see `external_data/README.md`).

## 8. Verification of the base source (2026-10-15)

Section 4 item 1 is now **closed on the evidence, against the owner's recollection.**

Asked where `Railway_Network_.csv` came from, the data lead answered "data.gov.in or
another government portal". That is not supported:

- The CSV's header is `objectid, id, fromjunction, tojunction, speed, type, noofstations,
  tracklength, railwayzone, nooflanes, bridge_yn, tunnel_yn, iso_countrycode, remark,
  st_lengthshape`.
- Layer 1 ("Railway Tracks", Polyline) of Esri India's Living Atlas service
  `livingatlas.esri.in/server1/rest/services/Railway/IN_Railway_Network/MapServer`
  declares `objectid, fromjunction, tojunction, speed, type, noofstations, tracklength,
  railwayzone, nooflanes, bridge_yn, tunnel_yn, iso_countrycode, shape` — **eleven of our
  fifteen columns, in the same order.**
- The three extras are export artifacts, not evidence against: `st_lengthshape` is what
  ArcGIS names a computed `ST_Length(shape)` column when `shape` is dropped on export, and
  `id` is that layer's declared **Display Field** although no field of that name is listed.
- A search for those column names returns the Esri India service as the only match.
  **No data.gov.in resource with this schema was found.**

**Conclusion.** The file is an export of the Esri India Living Atlas layer, whose portal
item carries the Esri India Master Terms of Use ("users are not permitted to export data
for offline use"). The REST endpoint itself states no licence and has empty copyright text,
so the restriction comes from the portal item, not the service metadata.

**Consequence for scope.** C1 (the artifact) cannot be deposited on this source. C2 (the
method) and C3 (the evaluation) are unaffected, and the availability sentence in §5 is
already written for exactly this outcome. The open rebuild (Path B) stays the route to a
depositable C1: the Esri item describes its own content as built from OpenStreetMap and
Ministry of Railways data, and the Geofabrik OSM extracts for all five zones are already in
`external_data/` with URLs, commits and hashes pinned. That rebuild is **weeks of
construction work, not days** — the pipeline's corridor/spine logic is shaped around this
CSV's `fromjunction`/`tojunction` semantics, which OSM ways do not carry — so it belongs in
the product roadmap, not in a one-week sprint.

This is an engineering determination from schema evidence, not legal advice. If the team
wants C1 deposited, the rebuild is the clean path; asking Esri India for written permission
is the only shortcut.
