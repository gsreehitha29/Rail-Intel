# Limitations

> Consolidated and honest. Everything a reviewer could reasonably raise, stated
> before they raise it. Sourced from `GRAPH_HANDOFF_V2.md` §7, the dataset
> README's known limits, and `FINDINGS.md`. Feeds the paper's §9 directly.
>
> Last updated: 2026-10-03

## 1. Limitations of the graph itself

### 1.1 Spine shortcutting — the most consequential one
**1,741 of 10,167** consecutive station pairs (17.1%) are affected; median
shortfall **5.0%**; 542 pairs > 10%; 54 > 25%.

Where a corridor contains a chord or a parallel line, the reconstructed spine can
take the shortcut the real track does not, compressing `measure_km` for stations
on the bypassed stretch. Detected on every pipeline run by
`crow_flies > sqrt(Δmeasure² + (offset_a + offset_b)²)`.

**Topology is unaffected. Distance-weighted results carry a systematic downward
bias.** This means accessibility (Module 2) and any distance-weighted centrality
inherit it. Resolution pending `D-019`; `E-005` measures whether it changes any
conclusion.

### 1.2 Attribute coverage
| Attribute | Coverage | Consequence |
|---|---|---|
| `speed_kmph` | 49.8% of corridors, **scattered not clustered** | Cannot be filtered on — requiring it collapses the graph to 771 nodes (14.6%). Any travel-time weight must state its null treatment (`D-012`) |
| `state` on nodes | 46% (4,163 of 9,095) | The station master does not record the rest. Blocks state-level aggregation |
| `zone` on nodes | 98.9%, but **4,874 of 8,997 are inferred** from corridor, not stated | Check `zone_source` before any result that depends on zone being source data |
| `declared length` | 99.9% within the V4 core | Fine, but the declared field is ~9% inflated and is not used as a weight |

### 1.3 Node identity and matching
- **474 of 9,095 nodes carry no station identity** (`operational_junction`). 46
  are degree ≥ 3 and structurally load-bearing, so they cannot be dropped.
- **40 name matches were rejected** on spatial conflict — an exact name match
  existed but sat more than 15 km away (worst case **1,620 km**). Deliberately
  not accepted. Either the junction coordinate or the station-master coordinate
  is wrong in each case; each needs manual review.
- **88 junctions have an ambiguous coordinate** (`coord_method =
  spine_end_ambiguous`): degree-1 junctions whose partner was also unresolved, so
  the coordinate is a coin-flip between two spine ends.
- **207 junctions** have incident corridors disagreeing about their location by
  more than 1 km (`cluster_spread_km > 1`).
- **11 stations share 4 coordinates** (`coordinate_shared`); at least one of each
  set is mislocated.
- **1 node of 9,095 has no coordinate.**

### 1.4 Placement quality
- Median perpendicular offset is **41 m** — good — but **643 placements exceed
  1.5 km**, and those are excluded from edge construction rather than corrected.
- **140 corridors have zero placed stations**, mostly short yard and cabin links
  with no nearby station. They still contribute their endpoint-to-endpoint edge
  via stitching.
- Independent corroboration against the GIS `noofstations` field is **moderate,
  not proof**: within ±3 on 65% of corridors, r = 0.49.

### 1.5 Topology residue
- **18 connected components.** 9,058 of 9,095 nodes are in the giant one; 37
  nodes form 17 small components, not yet classified as real isolated branch
  lines or residual data gaps (`D-020`, `E-006`).
- **2,252 of 9,689 edges carry `any_stitch = True`** — created by attaching a
  chain to a junction endpoint rather than measured between two placed stations.
  This is the novel construction operator, so its edges must be validated
  *separately* rather than inside an aggregate (`E-103`).

### 1.6 Semantics to watch
- `is_colocated` records that an edge's length **was floored**, not that the
  stations are close. One 50 m edge (`E000454`, AMPR–PGK) is unflagged. See
  `F-002`, `D-021`.
- Edge direction is **not** operational direction. GIS geometry direction is
  digitisation order; the physical layer is therefore undirected by construction
  (`D-009`).

## 2. Limitations of the source data

- **Vintage mixing.** The GIS layer, station master, timetables and the
  historical statistics are different snapshots. Zone electrification data is a
  **31 March 2021** snapshot and must never be presented as current. Every
  source-derived claim needs its vintage stated.
- **Route-km discrepancy.** Geodesic total 71,759 km against the Year Book
  2024–25's 69,439 route km, i.e. **+3.3%**, not yet decomposed (`F-004`,
  `E-102`). Expected to be parallel chords and loops counted separately; until
  decomposed it is an open question, not a validation.
- **`day` column in the schedules is unreliable** — it reaches 12 on trains that
  finish within a day. Not used at all; run-times are derived by 24-hour wrap.
  Any future use of multi-day service structure needs a different source.
- **2 stations are in Bangladesh** (`in_scope = False`). Filter on this for any
  national figure.
- The timetable snapshot predates the GIS snapshot in places; the 607 service
  pairs with an endpoint missing from the graph are partly this.

## 3. Limitations of scope — what this project does not claim

Per blueprint §14 and §25, and not negotiable by any amount of analysis on the
current data:

**Not supported:** real-time congestion, capacity saturation, actual train
delays, block-section occupancy, headway analysis, passenger or freight demand,
formal new-line feasibility, cost–benefit analysis, engineering or land
feasibility, automated new-line recommendation.

**Supported:** network representation, structure, connectivity, accessibility,
criticality, redundancy, resilience, hypothetical scenario evaluation.

Module 4 is **scenario evaluation**, framed as such. It does not tell Indian
Railways where to build.

## 4. Methodological limitations

- **Single-source topology.** The physical layer derives from one GIS dataset. We
  validate it against the timetable, which is independent — but a second
  infrastructure source (OSM rail, say) would be stronger, and we do not have one
  integrated.
- **No ground truth at scale.** The `E-105` audit is a stratified sample of ~200
  edges, not a census. Accuracy is reported per stratum with confidence
  intervals, not as a single global number.
- **Sensitivity study is one-at-a-time**, plus one targeted interaction. Full
  factorial over the nine construction factors is ~17,000 cells and infeasible,
  so higher-order interactions are unexplored and we say so.
- **Approximation in centrality.** Where betweenness is sampled rather than
  exact, the sample size and its measured rank-correlation against the exact run
  are reported with the result (`g03`).
