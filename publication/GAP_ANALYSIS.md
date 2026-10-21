# Gap and naivety analysis — graph v1

**Status:** complete · **Evidence:** `E-300` (`publication/evidence/E-300_attribute_audit/`)
**Scope:** every attribute the graph currently carries, every source in the repo
that could supply more, and the representational choices the model itself makes.

Every number below is produced by `E-300/run.py` and reproduces on a clean run.
Nothing here is recalled or estimated.

---

## How to read this

Gaps are classed by what kind of problem they are, because the fix differs:

| Class | Meaning |
|---|---|
| **S** | the attribute does not measure what its name says (semantics / granularity) |
| **R** | the information exists in the repo and was dropped (recoverable) |
| **X** | the information does not exist in the repo (needs an external source) |
| **M** | a property of the graph model itself, not of any attribute |

Severity is about downstream consequence, not about how wrong the number is:

| Severity | Meaning |
|---|---|
| **critical** | materially biases results the capstone will actually report |
| **major** | changes a specific module's conclusions |
| **moderate** | costs precision; a documented workaround exists |
| **latent** | harmless today, will bite when a module reaches for it |

---

## Summary

| ID | Gap | Class | Severity | Recoverable |
|---|---|---|---|---|
| **G-01** | 42.9% of corridor–station incidences never matched; long edges stand in for missing stations | R | **critical** | partly, in Phase 2 |
| **G-02** | length provenance was unstated — `F-042` later showed the shipped value was already the along-spine measure on non-stitch edges and the chord on stitch edges, i.e. an undeclared hybrid. **Resolved in v1.1** (`E-400`): the `D-026` hybrid ships with `length_source` per edge, +0.30% route km | R | **major, resolved** | shipped |
| **G-03** | `speed`, `gauge`, `n_tracks`, `zone` are corridor constants stored as edge attributes | S | **major** | no — document it |
| **G-04** | `speed_kmph` absent on 35.6% of edges; the travel-time weight silently invents 50 km/h | S | **major** | no — gate the weight |
| **G-05** | `bridge_present` is a boolean OR over segments; true 96% of the time, so it carries ~no information | S/R | **moderate** | yes, with a caveat |
| **G-06** | Phase 2 found attribute conflicts on 200 corridors and never told the edge table | R | **moderate** | yes, trivially |
| **G-07** | `state` present on 45.8% of nodes and **not** recoverable from any in-repo source | X | **major** for Module 2 | external only |
| **G-08** | zone/national reference tables are aggregates and cannot legally become edge attributes | S | **latent** | n/a — a trap to avoid |
| **G-09** | the graph is undirected, atemporal, uncapacitated, and collapses parallel routes | M | **major**, scoped | design choice |


---

## Status after graph v1.2 (2026-10-04)

Every gap was re-measured before it was fixed. Proof for each is in
`03_graph_construction/graph_v1_2/VALIDATION_v1_2.md`; the residual-gap register is §7 there.

| ID | Status | What changed | What still persists |
|---|---|---|---|
| **G-01** | **re-diagnosed; partly fixed** | Not a matching failure: 0 unplaced master stations within 1.5 km of any deficit spine (`F-051`). The damage it did — 51 straight-line stitch edges duplicating real routes — is removed (`D-043`), proven by connectivity, cycle rank and timetables | ≈9,900 incidences of stations that no in-repo source contains; 56 unsupported edges kept and flagged. **Not fixable in-repo** |
| G-02 | resolved (v1.1) | — | — |
| **G-03** | **fixed where the source allows** | edge-level bridge/tunnel/zone/tracks by segment overlay, 99.9% length agreement (`D-044`) | speed/gauge/tracks are corridor-level **in the source itself** (≤0.45% of km differs) |
| **G-04** | **substitution fixed; gap not** | constant 50 (MAE 56 km/h) → gauge×zone median (MAE 11.4), labelled per edge (`D-045`) | 35.4% of edges have no declared speed; MNAR bias unquantified; 6 SG edges unimputable |
| G-05 | fixed | `bridge_present_edge` + `bridge_km` replace the corridor-wide OR (96.1% → 81.8% of edges) | — |
| G-06 | resolved (v1.1) | — | — |
| **G-07** | **partly fixed** | 45.8% → 74.6% coverage at 99.5% LOO accuracy (`D-046`) | 25.4% unlabelled; source predates Telangana — 388 AP labels ambiguous |
| G-08 | unchanged (latent trap) | — | — |
| **G-09** | **direction and time delivered in the service layer** (`D-047`) | `service_layer/`: directed, timed, mapped to track | physical graph undirected by design; capacity and running days exist in no input |

---

## G-01 — The network is missing roughly two fifths of its stations, and long edges are standing in for them

**Class:** R · **Severity: critical** · **Evidence:** `E-300` part 5, `length_pairs.csv`

This is the most consequential thing in this document and it was not previously
recorded anywhere.

The GIS declares, per corridor, how many stations lie on it (`noofstations`).
Summed across the corridors the graph uses:

| | |
|---|---|
| station placements the GIS declares | **21,560** |
| station placements the pipeline matched | **12,305** |
| shortfall | **9,255 (42.9%)** |

These are corridor–station *incidences*, not unique stations — a station on three
corridors counts three times. But the consequence is structural: where a station
was not placed, `s09` does not create two short edges through it. It creates **one
long edge spanning the gap**.

Edge population by how many stations its corridor is missing:

| corridor shortfall | edges | share | route km | share of route km |
|---|---|---|---|---|
| found ≥ declared (clean) | 4,854 | 50.1% | 29,130 | 40.4% |
| 1–2 missed | 1,892 | 19.5% | 13,492 | 18.7% |
| 3–5 missed | 879 | 9.1% | 7,291 | 10.1% |
| 6–10 missed | 869 | 9.0% | 8,948 | 12.4% |
| **>10 missed** | **1,193** | **12.3%** | **13,309** | **18.4%** |

Only half the edges sit on a corridor whose stations fully resolved. A defect
signature of **≥3 stations missed and edge longer than 10 km** isolates
**766 edges (7.9%) carrying 17,722 km — 24.5% of the network's entire route km.**
Of those, 40.9% have `service_load = 0`: no scheduled train traverses them as a
single hop, which is what you would expect if the edge is an artifact rather
than a real link.

The worst instances are unambiguous:

| from | to | edge km | corridor spine km | stations declared | found | service |
|---|---|---|---|---|---|---|
| NIZAMABAD | PEDDAPALLI | 136.0 | 175.3 | 16 | 2 | 0 |
| Balipara | Harmuti Jn | 132.6 | 132.5 | 18 | 0 | 0 |
| MYSORE JN | YESVANTPUR JN | 125.6 | **1.4** | 26 | 2 | 0 |
| RAMGANJ MANDI | Khilchipur | 123.7 | 123.7 | 13 | 1 | 0 |

MYSORE JN → YESVANTPUR JN is a 125.6 km edge laid on a corridor whose spine is
1.4 km long. That is not a sparse corridor; it is a wrong edge.

**Why it matters.** A 136 km single hop is a shortcut in every path computation.
It shortens shortest paths, concentrates betweenness onto edges that do not
correspond to real track, deflates circuity, and makes the network look better
connected and more redundant than it is. Modules 1, 2 and 3 all consume exactly
these quantities. This also reframes `F-015` (stitched edges under-represented
among top bridges) and `F-019` (the route-km coincidence): both were computed on
a network where a fifth of the length is suspect.

**Honest bound.** `noofstations` is itself a corridor-level GIS constant
(G-03) and was never audited. Some shortfall is legitimate — goods-only points,
closed halts, stations absent from our master list. So 42.9% is an **upper bound
on error**, not a count of mistakes. The defect-signature subset (766 edges,
service_load = 0 on 40.9%) is the defensible core.

**Action.** Two separable things. (1) Phase 2 owns the matching recall problem:
`declared_no_of_stations` gives a per-corridor target, so station-matching recall
is measurable for the first time — the project has never had that metric. (2)
Phase 3 can ship the defect flag immediately without touching Phase 2. → `D-025`.

---

## G-02 — `length_km` is a straight line, and the real distance was already computed

**Class:** R · **Severity: major** · **Evidence:** `E-300` part 2

This answers idea (1) in the brief directly: *"Length — the haversine distance
between the coordinates of both the connected nodes."* That is what the graph
does today. It is also one of its naive points.

`station_sequences.csv` carries `measure_km` — the distance of each station
**along the corridor spine**. The true along-track distance between consecutive
stations is a subtraction. It was computed in Phase 2 and then not used.

Over 9,247 consecutive pairs:

| | |
|---|---|
| total chord km (shipped) | 57,961.6 |
| total along-track km (available) | 59,628.7 |
| **understatement** | **1,667.1 km (2.88%)** |

The aggregate looks small. The distribution does not:

| percentile | along-track / chord |
|---|---|
| p50 | 1.0052 |
| p90 | 1.0877 |
| p95 | 1.1557 |
| p99 | 1.4841 |
| max | 13.05 |

**17.7% of pairs are understated by more than 5%; 8.6% by more than 10%; 2.6% by
more than 25%.** The error is not noise — it is concentrated exactly where track
curves, which is exactly where terrain constrains the network.

### But the spine measure cannot simply be swapped in

**12.9% of pairs report an along-track distance *shorter than the straight line*,
which is geometrically impossible.** The cause is projection collapse, and it is
cleanly monotonic in how far the station sits off the spine:

| max offset from spine | pairs | impossible | median ratio |
|---|---|---|---|
| < 0.1 km | 7,158 | 1.8% | 1.009 |
| 0.1–0.25 km | 456 | 11.2% | 1.004 |
| 0.25–0.5 km | 375 | 36.3% | 0.979 |
| 0.5–1.0 km | 660 | 58.6% | 0.924 |
| **1.0–1.5 km** | **598** | **81.8%** | **0.644** |

Two stations far from the spine project onto nearly the same spine position, so
their separation along it collapses toward zero while their actual separation is
a kilometre.

Note what this implies about `D-004`: the `offset_km ≤ 1.5` tolerance admits the
1.0–1.5 km band, which is precisely where the spine measure dies. **The tolerance
choice and the length-source choice are coupled** — a new interaction for the
`g05` sweep, which has so far treated tolerance as a one-factor variable.

So the naivety is two-sided and the honest answer is neither pure chord nor pure
spine: the chord ignores real sinuosity, but it is immune to projection collapse.
→ hybrid length with explicit provenance, `D-026`.

---

## G-03 — The sinuosity the chord destroys is real signal, not noise

**Class:** evidence for G-02 · **Evidence:** `E-300` part 3, `corridor_sinuosity.csv`

Ranking the 871 corridors with at least 3 trustworthy pairs by along-track/chord
ratio, with **no terrain, elevation, gradient or heritage input anywhere in the
pipeline**:

| rank | corridor | sinuosity | |
|---|---|---|---|
| **1** | Matheran ↔ Neral Jn NG | 2.653 | Matheran Hill Railway (UNESCO tentative) |
| **2** | Darjeeling ↔ New Jalpaiguri Jn | 2.007 | Darjeeling Himalayan Railway (**UNESCO 1999**) |
| **3** | Kalka ↔ Shimla | 1.875 | Kalka–Shimla Railway (**UNESCO 2008**) |
| 4 | Padua ↔ Shrungavarapukota | 1.688 | Araku ghat section |
| 5 | Barkhera ↔ Budni | 1.643 | Budni ghat, Itarsi–Bhopal |
| **6** | Mettupalayam ↔ Udagamandalam | 1.509 | Nilgiri Mountain Railway (**UNESCO 2005**) |

**All four of India's recognised mountain railways rank in the top 6 of 871
corridors — the top 0.7%.** The rest of the top 12 is Baramula–Jammu Tawi
(Himalayan), Castle Rock–Kulem (Braganza ghat), Lonavla–Palasdhari (Bhor ghat)
and Dantewara–Jagdalpur (Bastar hills). Every one is a known mountain section.

This is an external validation the pipeline could not have gamed, and it converts
G-02 from a precision complaint into a substantive one: the chord does not merely
round distances down, it **erases the topographic constraint that makes these
corridors what they are**. For the paper this is also an asset in its own right —
a construction-quality check that uses ground truth from outside the data.

---

## G-04 — Edge attributes are corridor constants wearing edge clothing

**Class:** S · **Severity: major** · **Evidence:** `E-300` part 1, `granularity.csv`

This answers idea (2): *"Gauge type — refer to the gauge datasets … based on
railway region."* The reality is finer than region but far coarser than edge.

Share of corridors in which the attribute takes a single value across all its
segments:

| GIS attribute | constant within corridor | granularity |
|---|---|---|
| `type` (gauge) | **99.09%** | corridor |
| `noofstations` | 98.87% | corridor |
| `nooflanes` (→ `n_tracks`) | 97.09% | corridor |
| `tracklength` | 97.44% | corridor |
| `speed` | 96.62% | corridor |
| `railwayzone` | 96.62% | corridor |
| `tunnel_yn` | 96.23% | corridor |
| **`bridge_yn`** | **16.92%** | **segment** |

**119,446 GIS segments carry only 2,305 distinct corridor-level values.** When an
edge reports `speed_kmph = 110`, that is not a measurement of that edge; it is a
corridor-wide constant repeated onto it. The effective sample size for every
attribute except `bridge_yn` is 2,305, not 119,446 and not 9,689.

**Why it matters.** Any statement of the form "edge A is faster / wider / of a
different gauge than edge B" is unsupported whenever A and B are on the same
corridor. Two edges on one corridor are not two observations. Regressions,
correlations or significance tests over edge attributes will be overconfident by
roughly the ratio of edges to corridors.

`bridge_yn` is the one genuine exception and is treated in G-05.

**Action.** This is not recoverable — the source has no finer data. It must be
declared: per-attribute `*_granularity` provenance on the edge table, and an
explicit statement in the datasheet. → `D-027`.

---

## G-05 — `bridge_present` discards real segment data; the richer version is zone-biased

**Class:** S/R · **Severity: moderate** · **Evidence:** `E-300` part 4, `bridge_validation.csv`

This answers idea (3): *"refer to the infrastructure datasets and link them to the
corresponding edges."* There is genuine infrastructure data, and it is the only
true segment-level attribute in the source — but it does not survive validation
as an absolute measure.

The GIS splits its polylines **at structures**: 48.05% of segments are flagged
`bridge_yn = Y`, and their median length is **22.7 m** against **686.4 m** for
unflagged segments. The flagged segments are the bridge decks themselves. So
per-edge **bridge count** and **bridged metres** are both derivable.

Today the graph stores a boolean OR across the segments an edge spans, which is
`True` on **96% of edges** — a flag that is almost always true carries almost no
information.

### Validation against the official count

Rajya Sabha Q.371 gives bridges per zone. Comparing with GIS bridge segments:

| | |
|---|---|
| GIS bridge segments | 51,811 |
| official bridges | 163,810 |
| **overall capture rate** | **0.316** |
| Spearman (rank) | 0.703 |
| Pearson | 0.499 |
| capture range | **0.006 (NFR) → 0.638 (WR)** |

The GIS captures under a third of the bridges, and the shortfall is **severely
zone-dependent**: Northeast Frontier Railway shows 47 bridge segments against an
official 7,804 — essentially nothing, in one of the most bridge-dense terrains in
the country.

**Verdict:** derive the richer attribute, but it is **not fit for cross-zone
comparison or for any absolute count**. It is defensible only as a relative,
within-zone or within-corridor density. Shipping it without that restriction
would plant a zone-correlated bias in the resilience module. → `D-028`.

This is the clearest case in the project of an attractive attribute that
validation demotes rather than confirms, which is worth saying in the paper.

---

## G-06 — A third of travel times are a constant we invented

**Class:** S · **Severity: major** · **Evidence:** `E-300` part 5

| attribute | non-null on edges |
|---|---|
| `length_km` | 100.00% |
| `gauge_code` | 99.99% |
| `n_tracks` | 99.38% |
| `service_load` | 100.00% |
| **`speed_kmph`** | **64.38%** |

`speed_kmph` is missing at source for half the corridors (49.8% non-null there).
`weights.py` fills the gap with `FALLBACK_SPEED_KMPH = 50.0`.

So the `travel_time_proxy` weight is a blend: 64% derived from a corridor-level
declared speed (itself G-04), and **36% derived from a constant we chose**. Any
accessibility isochrone, travel-time centrality or reachability result inherits
that composition, and nothing in the output distinguishes the two.

**Action.** The weight must refuse to hide this: emit a per-edge
`speed_is_fallback` mask, report coverage with every travel-time result, and make
the fallback an explicit `BuildSpec` parameter so the sweep can vary it. → `D-029`.

---

## G-07 — Phase 2 detected attribute conflicts and never told the edge table

**Class:** R · **Severity: moderate** · **Evidence:** `E-300` part 5

`corridors.csv` already carries conflict flags:

| flag | corridors | share |
|---|---|---|
| `speed_kmph_conflict` | 14 | 0.61% |
| `gauge_conflict` | 11 | 0.48% |
| `no_of_lanes_conflict` | 65 | 2.85% |
| `railway_zone_conflict` | 59 | 2.59% |
| **`any_attribute_conflict`** | **200** | **8.78%** |

On 200 corridors the "corridor constant" is not constant, and Phase 2 arbitrated
a value. **None of these flags reach the edge table.** An edge on a conflicted
corridor presents an arbitrated value with no marker that arbitration happened.

Cheap to fix, and it is the same principle as `F-021`/`D-024`: an inferred value
must be distinguishable from a measured one. → `D-030`.

---

## G-08 — `state` is 45.8% and no in-repo source can fix it

**Class:** X · **Severity: major for Module 2** · **Evidence:** `E-300` part 5

| | |
|---|---|
| `state` on nodes | 45.77% |
| `state` on station nodes | 48.29% |
| `state` obtainable from `cleaned_stations.csv` | **48.29% — identical** |

The station master has nothing the graph lacks. This is the one gap with no
in-repo answer.

It also blocks real work: any accessibility, equity or regional-disparity
analysis — the core of Module 2 — needs a state or district label, and half the
nodes have none.

**But the input for a proper fix is complete:** coordinates are present on
9,094 of 9,095 nodes. Reverse geocoding against an administrative boundary file
(GADM, Survey of India, or Natural Earth) yields state *and* district at 100%
coverage, derived uniformly rather than inherited from a patchy master. That is
strictly better than the 48% we could inherit, and it is reproducible.

This is the one genuinely new external dependency the project should take on. → `D-031`.

---

## G-09 — Zone and national reference tables cannot become edge attributes

**Class:** S · **Severity: latent (a trap)** · **Evidence:** `E-300` part 5 inputs

This answers idea (4): *"refer to the other datasets and add more useful
attributes."* Several reference tables look like attribute sources and are not:

| file | granularity | legitimate use |
|---|---|---|
| `zone_electrification_2021.csv` | **zone** (17 rows) | validation target only |
| `gauge_history_1947_1971_2025.csv` | **national, per year** | context / validation |
| `railway_key_stats_2023_24_2024_25.csv` | **national** | validation target |
| `datafile.csv` | zone × gauge, 2009–11 | context; too old |
| `RS_Session_267_AS_371_A_i.csv` | **zone** | validation target (used in G-05) |
| `Table-19.2-Zone-wise.csv` | **zone** | validation target (route-km check) |

Electrification is the tempting one. There is no per-segment electrification data
in this repo — only "zone X has 3,336 of 3,853 BG route km electrified". Writing
`electrified = 0.866` onto every Central Railway edge would **manufacture an
attribute**: it adds no information beyond the zone label already present, while
presenting itself as an edge property. A downstream module could then "discover"
that electrification predicts something, when it has only rediscovered the zone.

**Rule adopted:** an aggregate may be used to *validate* a derived quantity at its
own level of aggregation, never to *populate* a finer-grained attribute. → `D-032`.

This is a case where the right action is to write down that we will not do
something, and why.

---

## G-10 — Model-level naivety

**Class:** M · **Severity: major, scoped** · Design choices, not defects — but they bound what can be claimed.

**Undirected.** Railways are directional: up and down lines differ in capacity,
timing and sometimes alignment. The graph is undirected and both service columns
are symmetric totals. No directional asymmetry is representable at all. Any
"bottleneck" result is therefore direction-blind.

**Two service columns with different epistemic status.** `service_direct`
(trains observed stopping at both ends consecutively) and `service_load` (trains
projected onto the physical path, including expresses that skip both ends) differ
on 36.5% of edges; mean 36.3 vs 49.5. On **1,031 edges `service_direct = 0` while
`service_load > 0`** — carried only by trains that stop at neither end. One is
observation, the other inference, and the column names do not say so.

**Parallel routes collapsed.** `parallel_policy = "shortest"` keeps one edge where
several corridors connect the same pair: 581 edges (6.0%) have ≥1 parallel, and on
**124 of them the parallels carry genuinely different attributes** (different
gauge, speed or track count). Those alternatives — real redundancy — are not in
the graph. For a resilience study, discarding redundancy is the one thing you
most want to avoid; `D-013`'s two-view approach addresses attribute filtering but
not this.

**Atemporal and uncapacitated.** One snapshot, no construction dates, no
electrification state, no capacity, no gradient, no axle-load class. The graph
cannot answer "what changed" or "what saturates", only "what connects".

→ documented as scope boundaries in `LIMITATIONS.md`; `D-033` records the
directionality decision explicitly rather than leaving it implicit.

---

## What this changes about claims already made

Honest accounting, since several of these touch results already recorded:

| Existing finding | Status after this audit |
|---|---|
| `F-019` route-km reconciles to −0.06% | **weakened.** 24.5% of route km sits on defect-signature edges (G-01); the agreement is less meaningful than it looked |
| `F-015` stitched edges under-represented among top bridges | **needs re-reading.** Long stitched edges are matching artifacts (G-01), not topological repairs |
| `F-022` Tier A: no artifacts | **unaffected but narrower.** The sweep varied construction *parameters*; it never varied length source, and could not have caught G-01 or G-02 |
| circuity median 1.251 | **biased low.** Computed on chords; true value is higher wherever track curves (G-02/G-03) |
| `D-004` tolerance ≤ 1.5 km | **newly coupled** to length source — the admitted 1.0–1.5 km band is where the spine measure fails (G-02) |

None of this invalidates the `g05` sensitivity result, because that study asked a
different question. It does mean the sweep's factor list is incomplete, and
`length_source` should join it.

---

## Priority

1. **G-01** — size and flag the matching shortfall. Nothing else is worth refining while a fifth of the route km is suspect.
2. **G-02** — hybrid length with provenance. Highest ratio of correctness gained to work done; the data is already there.
3. **G-06 / G-04** — stop travel time and attribute granularity from overstating themselves. Cheap, and they protect Modules 2 and 3.
4. **G-08** — reverse geocoding, because Module 2 cannot proceed properly without it.
5. **G-05 / G-07** — derive with caveats; both are additive and low-risk.
6. **G-09 / G-10** — write down, do not implement.


## Update 2026-10-05 — graph v1.3

Gaps closed or reduced by v1.3 (see `03_graph_construction/graph_v1_3/VALIDATION_v1_3.md`):
states (9,088 of 9,095), lengths (7,541 edges measured/official; none below straight line),
connectivity (full: 18 → 3 components), missing stations (full: +488). Remaining gaps are
listed with owners in `graph_v1_3/audit/` and the VALIDATION report §5; the release blocker
(licence of `Railway_Network_.csv`) is unchanged.
