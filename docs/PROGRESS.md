# Progress log

> Append-only, newest last. One entry per working session: what was attempted,
> what the numbers were, what changed, what it unblocked. This is the raw
> material for the paper's methods section. Teammate-facing changes also go to
> `CHANGELOG.md`.

---

## 2026-10-03 — Phase 3 opened: roadmap and documentation apparatus (g00)

**Attempted.** Survey the literature for this theme, establish where the project
stands against prior art, produce a research-backed roadmap for graph
construction, and stand up the documentation apparatus the publication needs.

**Literature survey.** Nine sources, written up in `docs/LITERATURE.md` with a
gap analysis. The decisive finding is `F-006`: **every published graph of the
Indian railway network is timetable-derived** — Sen et al. 2003 (587 stations,
P-space), Ghosh et al., Bhatia et al. 2015 (809 stations, service O–D network).
None is geolocated or infrastructure-attributed, and none can be externally
validated, because the timetable is both their source and their only reference.
Our shipped dataset is 9,095 nodes — 15.5× Sen, 11.2× Bhatia — physical, and
cross-validatable because the timetable was never consumed as input.

Kurant & Thiran 2006 ("Trainspotting") is the methodological ancestor: it names
our physical layer *space-of-stations*, defines the physical/logical two-layer
model our `edges.csv` / `service_edges.csv` split already implements, and
predicts **exponential, not scale-free** degree distributions for rail
space-of-stations — a falsifiable check now scheduled as `E-102`. Critically it
goes timetable→physical by *removing* shortcuts; we go GIS→physical by *building
and stitching*. That inversion is claim C2.

Boeing 2025 supplies the validation protocol (stratified sampling, TP/TN/FP/FN
**per stratum**) and settles that retaining degree-2 nodes with a flag is
defensible. Karduni et al. 2016 is the publication template. UIC RailTopoModel
(IRS 30100) locates our graph at **meso–macro** aggregation level.

**Closest competitor identified:** Palk et al. 2026, *Networks*,
doi:10.1002/net.70021 — robustness across graph *representations*. Paywalled,
403s to automated retrieval. **Blocking for the C3 novelty claim.** Our intended
distinction is that we vary *construction*, upstream of representation.

**Measurement (`E-001`).** Two project documents disagreed on structural figures,
so all of them were recomputed independently from the shipped edge list rather
than trusting either. Results match `QA_REPORT.txt` exactly: 9,095 nodes, 9,689
edges, 18 components, giant 9,058 (99.6%), 1,338 articulation points, 1,412
bridges (14.6%), 612 independent cycles, degree mean 2.13 / max 7, 72,201 route
km, 581 parallel pairs / 124 differing, 249 co-located, 2,252 stitched edges,
115 dissolvable junctions.

`GRAPH_HANDOFF_V2.md` §4.3/§4.4/§4.7/§8 were the stale source (`F-003`) — six
regions corrected, with a figure-provenance banner added stating that the QA
report wins any future disagreement. Incidental finding `F-002`: `is_colocated`
records *flooring*, not shortness — edge `E000454` (AMPR–PGK) is 50 m long and
unflagged because it sits just above the 0.05 km floor. Raised as `D-021`.

**Changed.**
- New: `docs/PHASE3_GRAPH_ROADMAP.md` — the eight-stage `g00`–`g07` plan.
- New: `docs/LITERATURE.md`, `DECISIONS.md`, `FINDINGS.md`, `EXPERIMENTS.md`,
  `PAPER_OUTLINE.md`, `LIMITATIONS.md`, `PROGRESS.md`.
- `DECISIONS.md` seeded with 22 ADRs: 15 migrated from handoff §4.8, 6 open
  (`D-016`–`D-021`), 1 new accepted (`D-022`, NetworkX behind an isolating API).
- Corrected `docs/GRAPH_HANDOFF_V2.md` (6 regions).
- Pinned the Phase 3 environment in `requirements.txt`.

**Unblocked.** `g01` — builder, parameterised views, weight registry.

**Blocked on.** Palk et al. 2026 full text; venue confirmation; agreeing the
Phase 3 ownership split with Sreehitha.

---

## 2026-10-03 (later) — g01 complete: builder, views, weights

**Attempted.** Build `railgraph` — a strict loader, every construction choice as
a parameter, and a named weight registry — then prove it reproduces the shipped
dataset.

**Built.** `03_graph_construction/railgraph/`: `config.py` (`BuildSpec`, 12
parameters, stable spec hash, 14 shipped invariants), `build.py` (shipped and
rebuild paths, four representation transforms, `measure`, `assert_invariants`),
`weights.py` (4 named weights + `travel_time_coverage`), `__init__.py`.

**Key engineering decision (`D-023`).** `g05` needs `offset_km` and
`stitch_junctions` as live parameters, but `s09` holds them as module constants.
Rather than refactor shipped Phase 2 code, `railgraph` reimplements the
construction with every constant promoted to a `BuildSpec` field — and backs that
with `verify_rebuild_equivalence()`, which rebuilds at the default and compares
against `edges.csv`. **Result: 9,689 edges both sides, identical pair set, zero
length mismatches, worst delta 0.0.** The test fails the run loudly on any drift,
which is a stronger guarantee than a one-time reviewed refactor. Phase 2 is
untouched; `s10` still passes.

**`E-002` — 20 parameter cells.** Headline, `F-007`: **junction stitching damps
the placement-tolerance sensitivity of the giant-component share by 322×** —
0.23 pp stitched vs 74.61 pp unstitched; bridge-share sensitivity 0.79 pp vs
19.50 pp. The unstitched case is far worse than the v2 handoff recorded, because
it only tested two tolerance levels: at 1.0 km the unstitched graph collapses to a
**17.6% giant component in 137 components with 48.8% of edges as bridges**.

Three further findings, all verified by direct enumeration:

- `F-009` — **dissolving the 115 degree-2 junctions is not topology-preserving.**
  22 of 115 contractions land on an already-adjacent pair, destroying 22
  independent cycles (612→590, i.e. 3.6% of the network's redundancy). 20 are
  visible up front; 2 emerge during sequential contraction, so the operation is
  order-dependent. Worst case `JN::Khajjidoni`: direct edge 18.87 km, route via
  the junction 30.42 km — a real loop, silently merged. **This decides `D-017`:
  do not dissolve.** It is also a measured counterexample to the assumption that
  degree-2 smoothing is free, which `[BOE25]` relies on for street networks.
- `F-010` — **stricter match confidence increases the node count.** high-only
  gives 9,438 nodes vs 9,095, because rejecting a match splits one node into two
  (station plus a separate `JN::` topology point) rather than deleting anything.
  Operational junctions 474 → 823, bridge share 14.6% → 16.4%. "Stricter" is not
  "safer" — it manufactures 349 spurious topology points.
- `F-008` — **placement tolerance saturates at 2.0 km.** `offset_km` maxes at
  1.9989 because `s07` already caps at 2 km, so `tol=3.0` is provably identical
  to `tol=2.0`. The `g05` sweep's "∞" level is dropped as redundant.

**Fixed.** `_merge_colocated` rewritten from iterated pairwise contraction to
single-pass component relabelling: 24.2 s → 0.7 s, and the output *changed*
(8,884 → 8,856 nodes) because pairwise contraction handled chains of 3+
co-located stations order-dependently. The faster implementation is the correct
one.

**Unblocked.** `g03` metrics; `g02` can now decide `D-017` with evidence.

**Note for `g05`.** The sweep grid shrinks usefully: tolerance has 3 distinct
levels not 5 (`F-008`), and `parallel_policy='mean'` changes only total route km
by 181 km with identical topology, so it is a length-only factor.

---

## g02 and g05 — exports and the sensitivity sweep

`g02` (exports) and `g05` (sensitivity study) are done. `railgraph` now has
`io.py`, `metrics.py`, `validate.py`, `sensitivity.py` alongside `build.py`/
`config.py`/`weights.py`. Outputs landed:

- `experiments/E-100/` — metric baselines, bridge severance, percolation
  curves, communities, betweenness convergence. `F-011`–`F-021` written.
- `experiments/E-101/` — validation battery (`v1`–`v6`), the 202-edge audit
  frame for manual TP/FP/FN rating.
- `experiments/E-200/` — the construction-choice sensitivity sweep, 20 cells,
  three verdict tiers. `F-022`–`F-025` written.
- `graph_v1/` — GraphML, parquet, GeoJSON, and the content-hashed manifest.
  Round-trip verified (`E-007`); the one GeoJSON feature loss is `F-021`, not
  silent.

**Headline result (`F-022`).** Tiered verdicts on the sweep: against the nine
genuinely open construction/representation choices (Tier A), every main
conclusion is robust or conditional — **no artifacts**. Filtering to the
attributed-core views (Tier B, `D-013`) is where it breaks: fragility
overstates 2.2×, criticality ranking overlap drops to 0.34, path length and
circuity both inflate materially. That is the paper's sensitivity-study
result.

**Defect found by exporting, not by an internal check (`F-021`).** `JN::Khandala`
has no coordinate; its one stitched edge's length is an undefined haversine
that the pipeline's `clip(lower=0.05)` silently turns into `0.05 km,
is_colocated=True`. `VERIFICATION.txt`'s non-nullity check passes anyway.
Proposed as `D-024` — a `length_source` column — for Phase 2, not fixed here
(`D-023` keeps `railgraph` a read-only reimplementation of the frozen dataset).

**Unblocked.** `g06` (layout/visualization) and `g07` (freeze/release) can
start; the graph and its validation are both in a committable state.

**Still blocked.** `V4` (Sen/Bhatia reproduction) needs
`01_data_engineering/processed_data/cleaned_schedules.csv`; zone-level route-km
reconciliation (`E-102`) needs `reference_data/Table-19.2-Zone-wise.csv`. Both
are now reachable on-device; not yet run.
