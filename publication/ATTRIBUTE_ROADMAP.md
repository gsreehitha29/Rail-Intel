# Attribute roadmap — what to add, what to refuse, and why

**Status:** proposed · **Evidence:** `E-300` · **Companion to:** `GAP_ANALYSIS.md`

Each candidate attribute is specified the same way, so that a reviewer can check
it and a downstream module can trust it:

- **source** — the file it comes from
- **granularity** — the level at which the value was *observed*, not stored
- **derivation** — exactly how it is computed
- **validation** — the independent check it must pass before shipping
- **verdict** — ship / ship-with-caveat / refuse
- **consumer** — which module actually needs it

An attribute with no validation plan does not get built. An attribute whose
granularity is coarser than the edge gets a `*_granularity` marker or it does not
ship.

---

## A. Length and geometry

### A1 · `length_km` → hybrid, with `length_source`  — **ship**

| | |
|---|---|
| source | `station_sequences.measure_km` (along-spine), station coordinates (chord) |
| granularity | **edge** — genuinely per-edge, both components |
| derivation | `spine = |Δmeasure_km|`; `chord = haversine(a, b)`. Use `spine` when `max(offset_a, offset_b) < 0.25 km` **and** `spine ≥ chord`; else `chord`. |
| validation | (a) no edge shorter than its own chord; (b) corridor sinuosity ranking must still place all four mountain railways in the top 1% (`E-300` part 3); (c) total route km re-reconciled against `Table-19.2-Zone-wise.csv` per zone |
| verdict | **ship** |
| consumer | all four modules — this is the weight almost everything uses |

`length_source ∈ {spine, chord_fallback_offset, chord_fallback_collapse, floored, undefined}`.
This **supersedes `D-024`**, which proposed a narrower `length_source` covering
only the floored/undefined case (`F-021`). The same column now carries the much
larger chord-vs-spine distinction as well. One column, one concept: *how do we
know this length?*

Expected effect: +2.88% on total route km in aggregate, concentrated — 17.7% of
edges move by more than 5%, and circuity rises wherever track curves.

### A2 · `sinuosity` (edge and corridor)  — **ship**

| | |
|---|---|
| source | derived from A1 |
| granularity | edge (ratio), corridor (aggregate) |
| derivation | `spine_km / chord_km`, defined only where `length_source = spine` |
| validation | already passed — recovers all four UNESCO mountain railways in the top 6 of 871 corridors with no terrain input |
| verdict | **ship** |
| consumer | Module 2 (circuity, detour factor), Module 4 (realistic new-line cost) |

This is a genuinely new attribute for this literature. Terrain difficulty is
normally brought in from a DEM; here it falls out of the construction geometry
and validates against an independent ground truth. Worth a figure in the paper.

---

## B. Infrastructure

### B1 · `bridge_count`, `bridged_m`, `bridge_density_per_km` — **ship with caveat**

| | |
|---|---|
| source | `Railway_Network_.csv` `bridge_yn` + `st_lengthshape`, via the segment→edge map |
| granularity | **segment** — the only true segment-level attribute in the source |
| derivation | per edge: count of `bridge_yn = Y` segments in its span; sum of their `st_lengthshape`; divide by edge length for density |
| validation | **done, and it demoted the attribute.** Capture rate 0.316 vs Rajya Sabha Q.371; Spearman 0.703; range 0.006 (NFR) → 0.638 (WR) |
| verdict | **ship with a hard caveat** |
| consumer | Module 3 (structural vulnerability) |

**Mandatory restriction, carried in the column description and the datasheet:**
not valid as an absolute count and **not comparable across zones**. Usable only
as a relative density within a zone or within a corridor. A `bridge_capture_zone`
companion column should carry that zone's capture rate so a user cannot
accidentally compare across zones without seeing it.

If this restriction cannot be enforced in the downstream module, **do not ship
it** — a zone-correlated bias in a resilience result is worse than no attribute.

### B2 · `tunnel_count`, `tunnelled_m` — **ship**

Same derivation; 576 tunnel segments (0.48%). No official per-zone tunnel count
exists in the repo to validate against, so it ships as **unvalidated** and
labelled so. Low volume, low risk, genuinely informative in NFR/KR/NR hill
sections — and it should correlate with A2 sinuosity, which is itself a
consistency check worth running.

### B3 · `electrified` — **refuse**

| | |
|---|---|
| source | `zone_electrification_2021.csv` |
| granularity | **zone** (17 rows) |
| verdict | **refuse** |

Writing a zone ratio onto every edge in that zone manufactures precision: the
column would contain no information beyond `zone_code`, which the edge already
has, while presenting itself as a physical property of the track. A module could
then "find" that electrification predicts an outcome when it has rediscovered the
zone. Legitimate use is as a **validation target** at zone level. See `D-032`.

To actually get electrification, an external per-section source is required
(IR electrification status by section, or OpenStreetMap `railway=rail` +
`electrified=*`). Recorded as a known external dependency, not attempted now.

---

## C. Provenance and honesty columns

These add no new information. They stop existing information from overstating
itself, which `E-300` shows is the dominant failure mode.

### C1 · `*_granularity` markers — **ship**

Per attribute, one of `segment` / `corridor` / `zone` / `inferred`. From `E-300`
part 1: `gauge_code`, `speed_kmph`, `n_tracks`, `zone_code` are all `corridor`;
only bridge/tunnel derivations are `segment`. → `D-027`.

### C2 · `*_conflict` propagation — **ship**

Carry `speed_kmph_conflict`, `gauge_conflict`, `no_of_lanes_conflict`,
`railway_zone_conflict` from `corridors.csv` onto the edges of those 200
corridors (8.78%). Pure join, no new data. → `D-030`.

### C3 · `speed_is_fallback` — **ship**

True on the 35.6% of edges where `speed_kmph` was absent and `weights.py`
substituted 50 km/h. Any travel-time result must report its coverage. → `D-029`.

### C4 · `station_match_deficit`, `suspect_long_edge` — **ship**

`station_match_deficit = declared_no_of_stations − n_stations_found` for the
edge's corridor. `suspect_long_edge = (deficit ≥ 3) AND (length_km > 10)` —
766 edges, 24.5% of route km. This is the G-01 flag, and it is the single most
important column to add: it lets every downstream module report results with and
without the suspect fifth of the network. → `D-025`.

---

## D. Node attributes

### D1 · `state`, `district` by reverse geocoding — **ship**

| | |
|---|---|
| source | node coordinates (100% present) + external admin boundaries (GADM / Natural Earth) |
| granularity | node |
| derivation | point-in-polygon |
| validation | agreement with the 48.29% of nodes that already carry a state; disagreements inspected, not silently overwritten |
| verdict | **ship** |
| consumer | Module 2 (accessibility, regional equity) — currently blocked |

The only new external dependency the project should take on. It raises coverage
from 45.8% to ~100% and makes it uniform rather than inherited.

### D2 · `is_interchange`, `n_corridors` — **ship**

Already derivable in-repo (`station_n_corridors` exists in `station_sequences`).
A station where ≥2 corridors meet is functionally different from a wayside halt,
and no current node attribute expresses that beyond raw degree.

### D3 · `service_direct` / `service_load` renaming — **ship**

Rename to `service_observed` and `service_projected`, or add a datasheet note.
They differ on 36.5% of edges and on 1,031 edges `direct = 0` while `load > 0`.
One is observation, the other inference; the names do not say so.

---

## E. Refused, with reasons

| Candidate | Source | Why refused |
|---|---|---|
| `electrified` | zone aggregate | manufactures precision (B3, `D-032`) |
| gauge from `gauge_history` | national, per year | national time series; the per-corridor `gauge_code` is already better |
| passenger / freight volume | `datafile.csv`, zone × gauge, 2009–11 | zone-level and fifteen years stale |
| `tracklength` as edge length | corridor constant | corridor total, not edge length (G-04) |
| `noofstations` as a node count | corridor constant | a declaration, not a measurement — use it only as the G-01 recall target |

---

## Sequencing

Nothing here requires touching the frozen Phase 2 dataset except where noted.
`railgraph` reimplements construction (`D-023`), so A1, A2, C1–C4 can all be
derived in Phase 3 from the existing shipped inputs.

| Step | Work | Touches Phase 2? |
|---|---|---|
| 1 | C4 — the G-01 defect flag | no |
| 2 | A1 + A2 — hybrid length and sinuosity | no |
| 3 | C1–C3 — granularity, conflict, fallback markers | no |
| 4 | D1 — reverse geocoding | no (new external input) |
| 5 | B1 + B2 — bridge/tunnel derivation | needs the segment→edge map from the pipeline cache |
| 6 | Phase 2 recall work on G-01 | **yes** — Bhuvanesh's call, separate release |

Steps 1–3 should land together as graph **v1.1**, with the `g05` sweep re-run
with `length_source` added as a factor. That re-run is the point at which we
learn whether the Tier A "no artifacts" verdict survives a construction choice
the sweep has never varied.
