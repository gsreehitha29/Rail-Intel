# E-713 — dataset closure profile and manual audit pack

Full profile of graph v1.4 for closing the dataset, and the samples for a manual audit.
The closure audit document is built from `out/profile.json`; every figure in it is here.

    python profile.py <root> out          # ~1 min; deterministic (seed 20261015)

## What it found that the gates and tests did not

1. **`degree` in `nodes.csv` is stale on 255 nodes** — the nodes touched by v1.4's edge
   repairs. The build recomputed the graph but not the column. `load_graph()` is right.
2. **The 129 repair-added sections carry no attributes** — no gauge, zone, tracks, corridor,
   speed, service or `official_km`; 1,578.6 km.
3. **All 90 sections shorter than their own straight line are repair additions.** The length
   is an official consecutive-stop distance; an endpoint's coordinates are wrong, by up to
   169 km (e.g. Barasat–Kazipara, 3.0 km between stations 135 km apart).
4. **No override has a reviewer, review date or source URL** — 179 of 179.

Also: per-section length agreement with the timetable is 51.0% within 5% (route-level is
0.72% median error, because section errors partly cancel); the "confirmed by official" label
corresponds to roughly a 25% tolerance; Kollam Jn (151 trains/day) is absent; 29 crosswalk
rows marked for review were never reviewed; 6 sections carry a standard-gauge label.

## The audit pack — `out/audit_pack/`

Each CSV has blank `verdict` and `note` columns, and map links where position matters.

| File | Rows | What to check | Priority |
|---|---|---|---|
| `G_edges_below_straight_line.csv` | 93 | wrong length, or wrong coordinates? | **1 — decides defect 3** |
| `K_overrides_sample_25.csv` | 25 | does the evidence support the action? | **1 — signs off the decision trail** |
| `A_fragments_all.csv` | 17 | genuinely isolated, or a missing link? | **1** |
| `B_nodes_sample_50.csv` | 50 | random nodes by role: right place, name, state, zone? | **2 — gives a positional error rate** |
| `C_edges_sample_by_length_source.csv` | 64 | random sections per length source: right length within ~5%? | **2 — gives a length error rate per source** |
| `D_edges_longest_30.csv` | 30 | is there really no station in between? | 3 |
| `E_edges_shortest_30.csv` | 30 | two stations, or one held twice? | 3 |
| `F_edges_disagree_with_official_30.csv` | 30 | our length or the timetable's? | 3 |
| `H_nodes_missing_attributes.csv` | 105 | find the value or confirm it cannot be found | 3 |
| `I_nodes_shared_names.csv` | 143 | same station twice, or different places? | 4 |
| `J_service_implausible_speeds.csv` | 178 | bad runtime or bad path length? | 4 |
