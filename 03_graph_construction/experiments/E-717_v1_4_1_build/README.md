# E-717 — graph v1.4.1 build

`make v141` (≈1 min) writes `03_graph_construction/graph_v1_4_1/` and
`service_layer_v1_4_1/`. It is a **working build**, not a release, until milestone A3 freezes it
(adds the docs and manifest stages). v1.4 is never touched (D-055).

| Milestone | What it adds | Status |
|---|---|---|
| A1 | I-01 derived node columns recomputed; I-02 attributes on the 129 repair sections; `overrides_applied`, `service_direct`, `service_load` retired | done 2026-10-19 |
| A3 | I-03 coordinate fixes and I-05 sign-off as new OVERRIDES.csv rows; split-sample check; freeze | waits on the Tier 1 audit (A2) |

New edge columns: `repair_attrs_inferred`, `repair_attrs_unresolved` — on repair sections only,
naming which of gauge, zone, tracks and corridor were taken from neighbouring sections and which
could not be (the neighbours at the two ends did not agree on one value).

Tests: `tests/test_v1_4_1.py` (skipped until the build exists). Results: `docs/EXPERIMENTS.md`.
