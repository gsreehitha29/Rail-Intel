# Railway Graph Handoff — v2

> **For:** Sreehitha (Graph Engineering)
> **From:** Bhuvanesh (Data Engineering & Provenance)
> **Supersedes:** `docs/GRAPH_HANDOFF.md` (v1). Read this one.
> **Status (2026-09-30):** Approach finalised and the dataset is built. The
> node and edge tables ship in `02_graph_inputs/graph_dataset/` —
> load them and start. §4 is why they are shaped the way they are; §4.8 is
> the decision register; §4.9 maps the decisions to the four modules.

---

> **Figure provenance (added 2026-10-03).** §4.3, §4.4 and §4.7 originally
> carried figures measured before `s09` existed. They were recomputed
> independently from the shipped edge list (`E-001`) and corrected here; the
> discrepancy and its lesson are recorded as `F-003`. Where this document and
> `02_graph_inputs/graph_dataset/QA_REPORT.txt` ever disagree again, **the QA
> report wins** — it is regenerated every run, this document is prose.

## 1. What changed since v1

v1 handed over a junction-level edge list plus a list of unresolved problems.
Those problems are now closed. Everything below is produced by
`02_graph_inputs/pipeline/run_all.py`, which rebuilds the entire package from the raw files in
about 30 seconds with no notebook kernel state involved.

| v1 blocker | Status now |
|---|---|
| Junction names ≠ station codes; only 727 of 2,066 junctions matched | **1,555 of 2,029 junctions** have a high/medium-confidence station match, every match carries a method + spatial gap + confidence flag |
| 1,339 junctions had no coordinates | **2,028 of 2,029 junctions now have coordinates**, derived from corridor geometry rather than guessed from the station master |
| 36 whitespace/newline duplicate junction names | Merged into canonical names; full raw→canonical crosswalk retained |
| "Can corridor geometry be walked to order stations?" — looked like only ~15% | **95% of corridors (2,166 / 2,279) reconstruct as a clean end-to-end path**; 99.9% yield a usable ordered spine |
| Stations were never ordered along corridors | **12,305 ordered station placements** across 2,138 corridors, with distance-along-line |
| Conflicting corridor counts (2,305 / 2,290 / 2,257) | One rule, one script, one number: **2,279 canonical corridors** |
| Intermediate work existed only in notebook cell output | Every table is exported to `02_graph_inputs/graph_inputs/`, regenerable on demand |

The v1 feasibility worry was based on a measurement that asked the wrong
question. It counted endpoint degree **globally** across all 118k segments, so a
corridor whose ends joined a *neighbouring* corridor looked malformed. Measuring
inside each corridor's own geometry — which is what matters for ordering
stations along it — shows the data is in far better shape than v1 implied.

---

## 2. Start here

```
02_graph_inputs/graph_inputs/
├── nodes_junctions.csv             ← candidate node table (2,029 junctions)
├── corridor_station_sequence.csv   ← ordered stations per corridor (12,305 rows)  ★
├── corridors_enriched.csv          ← corridor attributes + geometry metrics (2,279)
├── corridor_paths.csv              ← per-corridor reconstruction diagnostics
├── corridor_sequence_summary.csv   ← per-corridor placement summary
└── ...provenance/audit tables
```

Column-level detail: `docs/GRAPH_INPUTS_DICTIONARY.md`.

> ### The dataset is now built — start from it, not from these intermediates
>
> `02_graph_inputs/graph_dataset/` holds the cleaned, normalised, node- and
> edge-resolved tables produced by the approach in §4. Node identity is
> resolved, vocabularies are unified, the service layer is derived, and
> `nodes.csv` + `edges.csv` load straight into NetworkX. Read that folder's
> `README.md` first. The files listed above remain as the intermediates it
> was built from, so you can rebuild edges under different rules if you want
> to — but you no longer have to.
Integrity report: `02_graph_inputs/graph_inputs/QA_SUMMARY.txt` (regenerated every run).

---

## 3. How station-level edges are built (historical — `s09` now does this)

`corridor_station_sequence.csv` is already sorted. Consecutive rows within a
`corridor_id` are physically adjacent stations on that corridor, and the
distance between them is a subtraction:

```python
import pandas as pd

seq = pd.read_csv("02_graph_inputs/graph_inputs/corridor_station_sequence.csv")
seq = seq[seq.offset_km <= 1.5]                      # drop weak placements
seq = seq.sort_values(["corridor_id", "measure_km"])

nxt = seq.groupby("corridor_id").shift(-1)
edges = pd.DataFrame({
    "corridor_id":   seq["corridor_id"],
    "from_station":  seq["station_code"],
    "to_station":    nxt["station_code"],
    "distance_km":   nxt["measure_km"] - seq["measure_km"],
}).dropna(subset=["to_station"])
```

> ### This snippet is kept to explain the mechanism, not to be run
>
> **On its own it produces a graph that is only 59.4% connected** — it omits
> the junction stitching described in §4.1. `s09_graph_dataset.py` implements
> the complete construction, and its output is `edges.csv` in the dataset
> folder. Use that. This section remains so the edge semantics are legible
> rather than a black box.

That is deliberately **not** shipped as a file. Edge semantics are yours: whether
an edge means "adjacent stops on a physical corridor", how to treat a station
that sits on several corridors, whether to keep parallel corridors as parallel
edges, and what offset threshold counts as "on the line" are all graph-design
decisions. The inputs are built so that every one of those choices is a filter
over columns already present, not a re-derivation from raw.

Attach infrastructure attributes by joining `corridor_id` to
`corridors_enriched.csv` (gauge, speed, lanes, zone, bridge/tunnel).

---

## 4. The agreed approach

Sandeep signed off on this on 2026-09-30, and `s09_graph_dataset.py` implements
it — so `graph_dataset/` is this section, executed. The measurement behind each
decision is kept here so the reasoning stays auditable, and every choice is
still reversible: the intermediates it was built from are all still shipped.

### 4.1 Stitch corridors at their shared junctions — this is the one that matters

Corridors meet at **junctions**, not at stations. If a junction has no confident
station identity, or its station was not placed on both of the corridors that
meet there, the two station chains never touch and the network shatters. Measured
on the shipped package:

| Build | Nodes | Edges | Components | Giant component | Cycles (mu) |
|---|---|---|---|---|---|
| Station chains only, `offset_km <= 1.5` | 8,598 | 8,816 | 50 | **59.4%** | 268 |
| Station chains only, `offset_km <= 2.0` | 8,610 | 8,989 | 24 | 92.2% | 403 |
| **Chains + stitched at junctions, `<= 1.5`** | 9,095 | 9,689 | 18 | **99.6%** | 612 |
| Chains + stitched at junctions, `<= 2.0` | 9,102 | 9,810 | 14 | 99.7% | 722 |

Two things follow. First, stitching is worth ~40 points of connectivity. Second,
**once you stitch, the placement threshold stops mattering** (99.6% vs 99.7%),
where unstitched it swings 59.4% to 92.2%. Stitching does not just connect the
graph, it makes it stable against the very choices listed in §6.

A worked example, `Villupuram Junction` (matched to station `VM`, confidence
`high`, spatial gap 0.42 km, five incident corridors):

```
C00786  Chengalpattu Jn -> Villupuram Jn    ... MYP @97.0km, VM @103.0km   contains VM
C00852  Cuddalore Port  -> Villupuram Jn    ... SXR @39.7km, VM  @48.1km   contains VM
C01565  Katpadi Jn      -> Villupuram Jn    ... VKM @151.3km, VM @158.5km  contains VM
C02061  Puducherry      -> Villupuram Jn    ... VRA @29.4km, VM  @37.9km   contains VM
C02267  Villupuram Jn   -> Vriddhachalam Jn   first station KDMD @18.7km   DOES NOT contain VM
```

Four chains share the `VM` node and connect naturally. The fifth starts 18.7 km
along its own spine, because the first stretch out of Villupuram has no placed
station — so that branch and everything beyond it (355 stations) floats away as a
separate component. Stitching adds the one edge `VM — KDMD` and reattaches it.

```python
# after building each corridor's chain, attach it to its two junction endpoints
chain = [node_for(corridor_a)] + list(grp.station_code) + [node_for(corridor_b)]
chain = [x for i, x in enumerate(chain) if x and (i == 0 or x != chain[i-1])]
# and: corridors with zero placed stations still connect their two endpoints
```

### 4.2 Node model: hybrid, with typed nodes

Three options; the measurements pick one.

| Model | Nodes | Giant component | Problem |
|---|---|---|---|
| Junction-only | 2,029 | 88.2% | Abandons the station-level thesis |
| Station-only | 8,598 | 59.4% | Silently drops 474 junctions, 101 of them `corridor_degree >= 3` |
| **Hybrid (proposed)** | 9,095 | **99.6%** | Needs an explicit `node_type` |

Proposed rule: a node is a **station** where a confident station identity exists,
and an **operational junction node** where it does not — typed explicitly, so the
graph states where it asserts a passenger station versus merely a topology point.

Of the 474 junction nodes that carry no station identity, measured against the
shipped edge list: **46 are degree >= 3** and structurally load-bearing,
**115 are degree 2** and can be dissolved by path contraction (merge the two
incident edges, sum the lengths — the standard degree-2 smoothing used in
street-network primal graphs), and **313 are degree 1**, i.e. line ends rather
than pass-throughs, which can be pruned but not dissolved.

`nodes.is_dissolvable` marks exactly the 115. They are kept in the shipped
dataset rather than dissolved, because dissolving is a one-line operation on
your side while un-dissolving is not, and the flag costs nothing.

### 4.3 Edge model

Undirected, weighted by `measure_km` differences (already true geodesic km), with
corridor attributes joined on `corridor_id`, plus provenance on every edge
(`corridor_id`, both endpoint offsets, both endpoint match confidences).

Measured edge cases you will hit:

- **581 station pairs are produced by more than one corridor**, but only **124**
  differ in length by more than 1 km. Suggestion: keep a simple `Graph` carrying
  the shortest, with `n_parallel_corridors` as an attribute — a `MultiGraph`
  complicates every downstream algorithm for 124 real cases. If Module 3 wants to
  count genuinely distinct parallel routes, those 124 are the ones that matter
  (`parallel_differs`).
- **249 edges come out at ~zero length** (co-located stations). Resolved by
  `D-007`: kept as separate nodes, length floored at 0.05 km, `is_colocated`
  flagged. Note `F-002` — that flag records the flooring, not the shortness.
- **Gauge is a traversability constraint, not just a label.** 2,217 of 2,279
  corridors are Broad Gauge; 31 Metre, 29 Narrow, 1 Standard. Those 60 are not
  interoperable with the rest, so decide whether a shortest path may cross them.
- **`no_of_lanes` is a usable capacity/redundancy signal**: 1,055 single-line
  corridors vs 1,166 double-or-more. Speed is only usable on 1,135 of 2,279.

### 4.4 Optional second layer: the schedules now pay for themselves

§6 still says schedules are an independent evidence layer. They are — and I
tested how much evidence. Against the stitched graph, of 10,193 unique service
adjacencies derived from 416,970 stop records:

| Check | Result |
|---|---|
| Service pairs with both stations present in the physical graph | **94.0%** |
| ...of those, already a direct physical edge | **80.9%** |
| ...resolving within 3 physical hops (skip-stop signature) | **97.4%** |
| ...whose endpoints fall in *different* physical components | **0** |
| Physical edges carrying at least one direct service | **80.0%** |

Two networks built from independent sources — one from GIS geometry, one from
timetables, neither used to construct the other — agreeing to that degree is the
strongest validation statement this project can make. It also yields 373,041
usable inter-station run-times (median 7 min) and per-edge train frequency
(median 21 trains, max 285), which makes time-weighted and load-weighted analysis
possible.

**One trap if you use service counts as edge weights.** Counting only *direct*
consecutive-stop pairs under-credits every edge next to a station that expresses
skip. Real example, corridor C00786:

```
CGL -TRX    2.6 km   30 direct services     <- TRX is skipped by 37 trains
TRX -OV     5.8 km   30
OV  -PTM    4.7 km   67
PTM -KGZ    7.9 km   67
...
MMK -PQM    6.5 km   30                     <- PQM skipped
PQM -MLMR   4.4 km   30
MLMR-ACK    2.9 km   67
```

The 30/67 alternation is not a traffic pattern, it is an artifact: 67 trains run
the corridor, 37 of them skip TRX, PQM, PCLM and NMO. The fix is to project each
service pair onto its physical path and credit **every** edge on that path, not
just the endpoints. That projection is also what turns the service layer into a
resilience tool: cut a physical edge and you can report how many trains and how
many origin-destination pairs lose their route, instead of only reporting that a
component fragmented.

### 4.5 Which subset of the data to build on

The question behind this section: what is the **largest** slice of the network that has both
adequate attribute coverage and sound structure? The short answer is that you do not have to drop
to a region to get one.

**A single zone is far too small.** Every zone was profiled; the biggest connected zone-level graph
is Northern Railway at 1,028 nodes, then Western 779, Southern 752, South Central 746. Filtering
nationally on attribute quality instead gives 7,386-7,983 nodes — roughly **seven times** the best
single zone, and it still spans all sixteen zones.

**Size against quality, measured.** Each row is the giant component after applying that filter and
rebuilding:

| Subset | Corridors | Nodes | Edges | Cycles | Bridges |
|---|---|---|---|---|---|
| Full graph, no filter | 2,279 | 9,058 | 9,669 | 612 | 14.6% |
| **V1** gauge + zone + lanes all present, no conflict | 2,042 | **7,983** | 8,454 | 472 | 25.1% |
| **V2** V1 + Broad Gauge only | 1,988 | **7,780** | 8,241 | 462 | 25.3% |
| **V4** V2 + clean reconstruction (connectors kept) | 1,921 | **7,386** | 7,796 | 411 | 30.4% |
| V5 V2 + clean reconstruction + >=2 stations placed | 1,525 | 6,890 | 7,217 | 328 | 35.8% |

Note what the last two columns do. Every filter deletes real track, and deleted track was carrying
alternative routes: independent cycles fall from 612 to 328 and the share of edges that are bridges
climbs from 14.6% to 35.8%. **A resilience analysis run on the filtered core would overstate
fragility by about two and a half times** — not because the network is fragile, but because the
filter removed the redundancy.

So the recommendation is **two views of one graph, not one smaller graph**:

- **Topology view — the full 9,058-node graph.** Use it for Module 1 criticality and Module 3
  resilience, which need the real cycle structure and do not depend on infrastructure attributes.
- **Attributed core — V2 (7,780 nodes) or V4 (7,386).** Use it wherever an attribute enters the
  computation: gauge-constrained routing, capacity-weighted or speed-weighted analysis, zone
  aggregation. Carry it as an edge flag (`attr_complete`, `core_v2`) rather than a separate export,
  so a module can switch views without rebuilding.

V2 versus V4 is a real choice: V4 additionally requires a clean spine reconstruction, which makes
station ordering more trustworthy, and costs 394 nodes. V2 is the larger, slightly looser core.

**Speed is the one attribute you must not filter on.** It is present on only 1,135 of 2,279
corridors (49.8%), and — this is the important part — those corridors are scattered rather than
clustered, so requiring speed collapses the giant component to **771 nodes (14.6%)**. Speed has to
stay a nullable attribute on an otherwise complete graph. Everything else is fine: within the V4
core, gauge, lanes, zone and the bridge/tunnel flags are at 100% and declared length at 99.9%.

**Profile of the V4 core**, so you can check a build against it:

```
nodes                 7,386   (7,056 station-identified + 330 operational junction)
edges                 7,796   single connected component
route km             57,516
attributes            gauge / lanes / zone / bridge-flag  100%,  declared length 99.9%,  speed 51.1%
placement quality     median offset 42 m; 565 of 10,336 placements over 1.5 km
zone spread           all 16 zones; largest Northern 215 corridors, smallest SE Central 57
service layer         7,808 service pairs fall entirely inside it; 80.5% of core edges
                      carry at least one direct service; 5,118 of 5,208 trains touch it
```

**One cleanup needed before any zone-level aggregation.** `railway_zone` carries five label
variants that are the same zone spelled differently: `Northeast Frontier Railway` (17 corridors)
duplicates `North Frontier Railway` (121), and `Southen Railway` (3), `East Coast Railwa` (1) and
`Westem Railway` (1) are typos of existing zones. 48 corridors have no zone at all. Merge the
variants before grouping by zone, or the smaller zones will be undercounted.

### 4.6 Suggested build order

Stages `s09` and `s10` now cover the data half of this; the rest is Phase 3.

| Stage | Does | Status |
|---|---|---|
| `s09_graph_dataset.py` | Node identity, vocabularies, edge construction, service layer, coupling | **done** — writes `graph_dataset/` |
| `s10_verify_dataset.py` | Re-derives every guarantee from the shipped files, fails loudly | **done** — writes `VERIFICATION.txt` |
| `g01` | Load into your graph library of choice; decide on the 115 dissolvable nodes | yours |
| `g02` | Graph storage and export — GraphML, parquet, GeoJSON edges (blueprint §13) | yours |
| `g03` | Metrics infrastructure the four modules call into | yours |
| `g04` | Layout and visualisation | yours |
| `g05` | Graph-level validation report | yours |

### 4.7 What you should get if you follow this

So you have something to check your build against:

```
nodes                 9,095   (8,621 station + 474 operational junction)
edges                 9,689
components               18   giant = 9,058 nodes (99.6%)
degree                 mean 2.13, max 7; 82.8% of nodes are degree 2
independent cycles      612   -> the network is ~94% tree-like
articulation points   1,338   (14.8% of giant-component nodes)
bridges               1,412   (14.6% of giant-component edges)
```

Two of those deserve comment. The degree distribution topping out at 7 with no
hubs is the expected signature of a spatially embedded network, not a defect. And
a network where 14.8% of edges are bridges has very little redundancy — which
makes "where is the redundancy" a more interesting Module 3 question than
"is it resilient". As a sanity check that this is real rather than an artifact,
the worst bridges the graph finds are the Fakiragram — Kokrajhar — New Bongaigaon
chain in Assam, each severing 340-460 stations: the graph independently
rediscovers the Northeast India connectivity chokepoint without being told about
it.

---

### 4.8 Decision register

Everything that §6 listed as open, resolved. Each is implemented in `s09` and
visible as a column, so none of them is baked in irreversibly.

| Question | Decision | Why |
|---|---|---|
| Node granularity | Hybrid: station where a confident match exists, typed `operational_junction` otherwise | Station-only fragments to 59.4%; junction-only abandons the station-level thesis |
| Degree-2 junctions | Kept, flagged `is_dissolvable` (115 of them) | Dissolving is one line downstream; reversing it is not |
| Match confidence | `high` + `medium` (1,555 junctions) | Medium carries a recorded spatial gap, so it is filterable rather than risky |
| Placement tolerance | `offset_km <= 1.5` for edges; all 12,305 placements shipped with `used_for_edges` | Stitching makes the graph insensitive to this, so take the tighter one |
| Corridor-to-corridor connection | Stitch every chain to its two junction endpoints | 59.4% -> 99.6% giant component |
| Parallel corridors | Simple graph, shortest edge kept, `n_parallel_corridors` and `parallel_differs` retained | Only 124 pairs are genuinely different routes; a MultiGraph taxes every algorithm for all 9,689 |
| Co-located stations | Kept as separate nodes, length floored at 0.05 km, `is_colocated` flagged | Merging destroys station identity, which accessibility needs |
| Self-loops | Dropped from the edge list, retained in `corridors.csv` | 5 yard and balloon loops, no analytical value as edges |
| Directedness | Undirected physical layer; the service layer keeps direction | GIS direction is digitisation order, not operation |
| Edge weight | `length_km`, true geodesic | The source length field is ~9% inflated |
| Gauge | Edge attribute and a traversability constraint, not a filter | 60 non-BG corridors are genuinely not interoperable |
| Speed | Nullable attribute, never a filter | 49% coverage and scattered; filtering collapses the graph to 771 nodes |
| Data subset | Two views on one graph via `core_v2` / `core_v4` flags, not a smaller export | Filtering pushes bridges from 14.6% past 30% and would overstate fragility |
| Service layer | L1 + L2 + coupling shipped; space-P derived on demand, not materialised | Space-P would be roughly 16 million rows; the recipe is three lines |
| Service weighting | `service_load` (path-projected), with the naive `service_direct` kept for comparison | Direct counting under-credits every edge beside an express-skipped station |

### 4.9 What each module gets

The four downstream modules are views of this one dataset, not four datasets.

**Module 1 — Network Structure & Criticality.** Use the full topology view.
Degree is already on `nodes`; `length_km` gives distance-weighted centrality and
`service_load` gives traffic-weighted betweenness — the pair that separates a
real bottleneck (high betweenness *and* high load) from a reconstruction
artifact (high betweenness, no trains). 1,338 articulation points and 1,412
bridges are precomputed in the QA report as a baseline. `zone_code` is an
independent label to validate community detection against, rather than a
feature to cluster on.

**Module 2 — Accessibility & Service Connectivity.** Needs `service_edges.csv`:
`runtime_min_median` gives genuinely time-weighted shortest paths rather than
topological proxies, and `n_trains` gives frequency. Derive the space-P transfer
graph on the fly from the schedules for transfer-count accessibility. Node
coordinates plus `length_km` give circuity (network distance over great-circle),
which is the standard way to show a region is poorly served. Use service
frequency as the mass term in a gravity accessibility index — the blueprint
rules out population data, and frequency keeps the module inside scope.

**Module 3 — Redundancy & Resilience.** Use the full topology view, and say so
in the writeup: this is the module the `core_*` filters would actively damage.
The interesting features are already there — `parallel_differs` marks the 124
genuinely distinct parallel routes, `n_tracks` separates 1,055 single-line
corridors from the double-and-above, and `service_load` converts a topological
cut into a service-impact statement ("this edge strands N trains"), which is the
thing that makes the module more than a textbook percolation exercise.

**Module 4 — Network Expansion & What-If.** Candidate edges come from the data
rather than from imagination: the 607 service pairs with an endpoint missing
from the graph, the 40 junctions whose name match was rejected on a spatial
conflict, and whatever low-redundancy regions Module 3 surfaces. Score each on
change in mean shortest path, independent cycles, bridge count and accessibility,
with `length_km` between the candidate endpoints as the cost proxy. Frame as
scenario evaluation only, per blueprint §6 and §9.

---

## 5. Use `geodesic_length_km`, not the source length field

The source `st_lengthshape` field is **~9% inflated** (median ratio 1.0902) —
it was computed in a projected CRS, not on the ground. Totals:

| Measure | Total |
|---|---|
| Sum of `st_lengthshape` | 78,126 km |
| True geodesic length of the same geometry | **71,759 km** |
| Indian Railways Year Book 2024–25 route km | 69,439 km |

The geodesic figure is the credible one. `corridors_enriched.geodesic_length_km`
and `corridor_station_sequence.measure_km` are both true great-circle
kilometres. The old `rail_edges_initial.csv` `geometry_length_km` column carries
the inflation — do not use it as a weight.

---

## 6. What is still genuinely yours to decide

The modelling questions this section used to list are settled in §4.8 and
implemented in `graph_dataset/`. What is genuinely still open is smaller, and
none of it blocks starting.

1. **Graph storage format.** GraphML, parquet node/edge tables, pickle, or a
   graph database. The blueprint §13 asks for interoperable tabular plus
   graph-native; which graph-native is your call.
2. **The 115 dissolvable nodes.** `is_dissolvable` marks them. Dissolving gives
   a graph where every non-station node is load-bearing; keeping them preserves
   provenance. One line either way.
3. **`core_v2` vs `core_v4`** for attribute-weighted work. Both flags ship.
   V4 additionally requires a clean spine reconstruction, so station ordering is
   more trustworthy, at the cost of 364 edges.
4. **The remaining 18 components.** 9,058 of 9,095 nodes are in the giant one;
   the rest are small isolated pairs and triples. Investigate whether they are
   real branch lines or residual data gaps before dropping them.
5. **The 40 rejected name-spatial conflicts.** Worth a manual pass — each is a
   junction whose exact name match sits more than 15 km away, so either the
   junction coordinate or the station-master coordinate is wrong.
6. **Spine shortcutting.** Accept and document, or recompute the affected edge
   lengths from raw corridor geometry. Affects 17.1% of consecutive pairs,
   median 5%. Topology is unaffected; distance-weighted results are not.

## 7. Known weak spots — read before trusting a number

| Item | Count | What it means |
|---|---|---|
| `coord_method = spine_end_ambiguous` | 88 | Degree-1 junction whose partner was also unresolved; coordinate is a coin-flip between two spine ends |
| `match_confidence = rejected_name_spatial_conflict` | 40 | Exact name match exists but >15 km away (worst: 1,620 km). Deliberately **not** accepted. Either the junction coordinate or the station-master coordinate is wrong — worth manual review |
| `cluster_spread_km > 1` | 207 | Incident corridors disagree about where the junction is |
| `offset_km > 1.5` | 635 placements | Station is far from the line it was assigned to |
| Corridors with 0 stations placed | 140 | Mostly short yard/cabin links with no nearby station |
| `station_count_delta` vs GIS `noofstations` | ±3 on 65% | Independent corroboration is moderate (r = 0.49), not proof |
| Spine shortcutting | 1,741 of 10,167 station pairs (17.1%) | Where a corridor contains a chord or parallel line, the spine can take it and compress the `measure_km` of stations on the bypassed stretch. Median shortfall 5.0%; 542 pairs >10%, 54 >25%. Detect with `crow_flies > sqrt(Δmeasure² + (offset_a + offset_b)²)` — it is re-measured on every pipeline run |

---

## 8. Reproducing everything

```bash
python 02_graph_inputs/pipeline/run_all.py        # ~50s, rebuilds graph_inputs/ AND graph_dataset/ from raw sources
```

Stages: `s01` canonical junctions → `s02` corridors → `s03` geometry extraction
→ `s04` spine reconstruction → `s05` junction coordinates → `s06` station
matching → `s07` station sequences → `s08` assemble + QA → `s09` graph dataset
→ `s10` verify dataset. Ten stages. Each is idempotent and documented in its own
module docstring. Requires `pandas`, `numpy`, `networkx`, `shapely`, `scipy`,
`rapidfuzz`, `pyarrow` — exact versions in `requirements.txt`.

Nothing in `01_data_engineering/processed_data/`, the notebooks, or the original
`*_initial.csv` files was modified. The v1 artifacts remain exactly as they
were for comparison.
