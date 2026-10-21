# E-705 — gap G15: the 2024 service layer

**The gap.** The shipped service layer is built from the 2017 timetable, so every service-weighted result described 2017 trains running on current track, and 267 sections that carry trains today showed none.

**Status: filled and verified.** A directed, timed service layer built from the September 2024 routes, on the repaired graph. It matches the Sept 2024 delay data train-for-train, which the 2017 layer never could.

This only became possible after the earlier gaps: G1's crosswalk resolves the renamed codes the 2024 data uses, and G5/G6 put the track under the trains. **Every one of the 16,703 station pairs has both ends in the graph** — against 94.4% for the 2017 layer.

## What it contains

| File | Contents |
|---|---|
| `service_edges_directed_2024.csv` | 16,703 ordered station pairs: train counts, observed runtimes (median, p10, p90), train types, and how the pair sits on the track — direct edge, path km, hops, implied speed |
| `service_hourly_2024.csv` | departures by hour of day, per ordered pair |
| `edge_service_2024.csv` | per physical edge: 2024 trains, 2017 trains, and which repair (if any) created the edge |
| `edges_newly_served_2024.csv` / `edges_no_longer_served_2024.csv` | what changed against 2017 |

3,889 trains, 85,055 stops. 1,195 stops remain unmapped — exactly G1's residual, the stations the graph genuinely lacks.

## Verification

**Runtimes agree with the independently built 2017 layer.** On 1,974 pairs both layers cover, the median difference is **2.0 minutes**, with 89% inside 10 minutes. The two are built from different timetables by different code, so this is real evidence the layer is assembled correctly.

Scheduled runtimes are a **median 9.1% longer in 2024 than 2017** on the same pairs. That is schedule padding, and it bears directly on the punctuality objective: some of the headline on-time figure is bought by slackening the timetable.

**Speeds are sensible.** Median implied speed 57.0 km/h against 54.0 for 2017 — the 2024 set is express-heavy, so a little faster. 1.3% of pairs fall outside 10–130 km/h and are left for review.

**The repairs carry trains.** 109 of 129 repaired edges (85%) carry 2024 traffic, led by Barkhera–Budni (261 trains) and Panch Pipila–Thandla Rd (226).

## It complements the 2017 layer; it does not replace it

| | 2017 layer | 2024 layer |
|---|---|---|
| trains | 5,208 | 3,889 |
| directed pairs | 19,865 | 16,703 |
| pairs that are a single physical edge | 77.0% | 28.5% |
| median hops per pair | 1 | 3 |
| edges carrying trains | 8,753 | 8,411 |

The 2024 dataset is express-heavy, so consecutive stops sit further apart and fewer are single edges. That is a different train population, not lower accuracy. Only 5,413 pairs appear in both.

**Use the 2024 layer** for anything joined to the Sept 2024 delays, and for current routes — 397 edges (6,529 km) carry trains in 2024 and none in 2017. **Use the 2017 layer** for breadth of stopping coverage. Together they cover 9,150 edges. Edge loads correlate at Spearman 0.851, so neither contradicts the other.

**Do not read `edges_no_longer_served` as line closures.** 739 edges lost service only because the 2024 dataset omits the local and passenger trains that serve them.

## A correction this work forced on G5

Auditing the added edges turned up a flaw in G5: it judged every candidate against the *unrepaired* graph, so its additions interact. Once one addition shortened a path, another could become a duplicate of a chain that now worked. Ratnagiri–Thivim was added at 193 km alongside an existing 192.67 km chain on the same alignment — buying nothing but a way to skip every Konkan Railway station between them.

**42 added edges (2,114 km) were pruned as redundant**, re-tested with each edge removed so it could not vouch for itself. The measures barely move (route error ±0.0001, off-spine detour +663 km) because both metrics reward shortcuts by construction. The case for pruning is correctness, not score: a duplicate edge makes a line look redundant when it is not, which would corrupt exactly the criticality analysis this project exists for. `added_edge_audit.csv` records every decision, and `railgraph_repaired.py` applies the pruning for all later work.

## New finding: duplicated stations

82 edges shorter than 600 m join two nodes that are the same station under different names, and they carry 7,243 trains — Allahabad Jn / Allahabad City, Katni Murwara / Katni, Jabalpur twice, Sabarmati Jn twice, Ujjain Jn twice, Dhaulpur twice. Allahabad Jn and Prayagraj Junction are also separate nodes 145 m apart, now joined by an edge carrying 514 trains, because G1 mapped the renamed code to one and the old code holds the other.

This matters for criticality: removing a duplicated junction leaves its twin standing, so the junction looks far less critical than it is. The list is in `out/duplicate_node_pairs.csv` and belongs to the duplicates gap (audit list 10).

## Files

- `railgraph_repaired.py` — assembles v1.3 + G5 + G6 with pruning; every later module should load the graph through this
- `build_service_2024.py` — builds the layer. `python build_service_2024.py <root> out`
- `verify.py` — runtimes, speeds, coverage, repairs. `python verify.py <root> out out`
- `audit_added_edges.py` — the redundancy audit. `python audit_added_edges.py <root> out`
- `verify_pruned.py` — measures raw, full and pruned repair sets
