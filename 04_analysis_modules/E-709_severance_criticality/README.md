# E-709 — national severance criticality

**The question.** Which single section or station, if blocked, cuts the most of the
network off — and does any service have no alternative route at all?

Only stable-class metrics, per D-055: cut points, bridges, connectivity and
trains-per-day. No betweenness, no node-level centrality ranking. Those are the
claims the release is certified to carry, and this module is the first use of that
certification.

**Status: run, verified against two real disruptions.**

## Headline

| | |
|---|---|
| sections with no alternative route (bridges) | 1,149 of 9,640 — **11.9%** |
| ...collapsed into severance corridors | **283** |
| corridors severing >200 stations | **2** |
| stations that are cut points | 1,166, of which **200 are real junctions** (degree ≥ 3) |
| daily train movements with no alternative route | **5.6%** (2,256 of 40,174 service-pair movements/day) |
| busiest 100 sections whose loss forces a detour over 3× | **90**; median detour **291 km** |

## The two corrections the first pass forced

**1. Edges are the wrong unit.** A single-line corridor with no alternative appears as
a *chain* of consecutive bridges, each severing almost the same stations. The Siliguri
chain alone is 10 bridges all severing ~455 stations — one vulnerability counted ten
times. Maximal chains in the bridge subgraph collapse 1,149 bridges to **283 corridors**,
which is also the unit the National Rail Plan uses ("a corridor's capacity is set by its
weakest link").

**2. Eighty-two bridges are one station held as two nodes.** The signature is
structural, not a name match: *a bridge under 1 km that severs exactly one station.*
Two genuinely distinct stations 150 m apart with 200 trains a day between them and
nothing beyond does not exist. This caught the renames that E-705's 82-pair duplicate
list missed — **Allahabad Jn / Prayagraj Junction (206.5 trains/day), Vishakapatnam /
Waltair (128.8), Cheoki / Prayagraj Chheoki (76.3), Daraganj / Prayagraj Sangam (15.6)**
— all of which would otherwise have topped the vulnerability table. They are listed in
`out/intra_station_artifacts.csv` and are the correct input to a future merge.

Contracting E-705's own 82 known duplicate pairs changed only **5 of 1,236 bridges and
4 of 1,170 cut points** — so for *this* analysis the duplicate-node limitation costs
0.4%, far less than it costs a centrality ranking. The rename class above was the
damaging one, and it is now identified.

## The worst corridors

| id | corridor | sections | km | stations severed | dependent trains/day |
|---|---|---|---|---|---|
| SC0077 | Barsoi Jn – Makuria – Radhikapur | 10 | 58.7 | **455** | 58.4 |
| SC0036 | Dalkolha – Aluabari Road | 9 | 59.6 | **440** | 54.9 |
| SC0069 | Bihara – Manderdisa (Assam hill section) | 18 | 131.1 | 84 | 10.6 |
| SC0004 | Badarpur Jn – Sabroom (Tripura) | 38 | 360.0 | 38 | 8.5 |
| SC0026 | Bharoli Jn – Baramula (J&K) | 22 | 416.4 | 22 | 44.6 |
| SC0011 | Pathankot – Joginder Nagar (Kangra Valley) | 33 | 161.0 | 33 | 0.0 |

## Verification — the graph was not told any of this

**SC0077 is the Siliguri corridor, recovered from GIS geometry alone.** Cutting
Barsoi Jn – Makuria severs 459 stations: **all 327 stations the graph places in the
eight Northeast states** (292 Assam, 18 Tripura, 5 Manipur, 5 Nagaland, 3 Mizoram,
3 Arunachal, 1 Meghalaya) plus 115 in North Bengal and 17 in Bihar. That is the
"Chicken's Neck" — India's most documented rail chokepoint — identified without any
prior knowledge of it, from segment geometry and nothing else.

**SC0069 predicted the blast radius of a real event.** The module says cutting the
Lumding–Badarpur hill section severs 84 stations: 58 Assam, 18 Tripura, 5 Manipur,
3 Mizoram. On 6–7 July 2025 a landslide at KM 51/1-2 between Mupa and Dihakho blocked
exactly that section. NFR cancelled 4 trains outright, part-cancelled 3 and
rescheduled at least 7 — and the services cut off were Tripura, Manipur, Mizoram and
southern Assam. The predicted set and the observed set are the same, and the module's
10.6 dependent trains/day is the right order against ~14 trains affected.

**SC0026** (Bharoli Jn – Baramula, 44.6 dependent trains/day) is the corridor behind
the 18 train cancellations in the J&K flash floods of August 2025.

Both verifications are retrodictive: the physical graph was built from GIS segments and
validated against timetables, never against disruption records.

## Caveats that matter for reading this

- An edge is a **section, not a track**. Parallel tracks collapse to one edge, which is
  correct for topology but means "losing the section" is total blockage — a washout,
  landslide or derailment — not a single-track failure.
- 1,312 sections carry no recorded service. Suburban services are largely absent from
  the 2024 dataset, which is why the Sealdah South corridor (SC0045, 52 sections)
  shows 0 trains/day despite being intensively used. Zero here means *unmeasured*.
- Load is `trains_per_day` (E-706). Passenger only; freight is not in the data, so
  every load figure is a lower bound.
- Detour km inherit the release's 25.9% lower-bound lengths, so detours are floors too.
- The 228 absent stations mean a severed count is a count of *graph* stations.

## What this supports deciding

The National Rail Plan reports **46% of the network running above 80% capacity
utilisation** and recommends corridor-based over zone-based planning, but publishes no
ranked list of augmentation projects or scoring method. This module produces exactly
that input, reproducibly: 283 corridors with no alternative route, each with its
weakest section, the stations it isolates and the daily traffic that depends on it.
SC0077 spans Bihar and West Bengal across a zone boundary, which is the NRP's own
criticism of zone-based prioritisation made concrete.

## Files

- `sever.py` — bridges, cut points, exposure, load. `python sever.py <root> out [stage...]`
  Stages: `structure` (~2 min), `exposure` (~3 min), `load`.
- `corridors.py` — collapses bridges to corridors, classifies artifacts.
  `python corridors.py <root> out`
- `out/severance_corridors.csv` — 283 corridors, ranked
- `out/junction_cut_points.csv` — 200 junctions whose loss splits the network
- `out/bridge_dependency.csv` — per bridge, the trains/day with no alternative
- `out/intra_station_artifacts.csv` — 82 duplicate-node bridges, the merge input
- `out/top_load_detour.csv` — detour cost of losing each of the busiest 100 sections
- `out/edge_load_ranked.csv` — all 9,640 sections by trains/day
- `out/E-709_report.json`, `out/E-709_corridors.json` — every figure above
