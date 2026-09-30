# Network Structure & Criticality

**Owner:** Abrar (Network Intelligence / Domain Modules).

Degree and weighted degree, betweenness, closeness, PageRank, communities, articulation points and bridges, critical corridors and structural bottlenecks.

## Data

Build on graph v1 from `../../03_graph_construction/`, which is constructed
from `../../02_graph_inputs/graph_dataset/`. Do not start until graph v1 is
frozen — running against a moving graph makes results irreproducible.

## Which view this module uses

Use the **full topology view** — all 9,689 edges. `service_load` on each edge gives traffic-weighted betweenness, which is what separates a real bottleneck (high betweenness *and* high load) from a reconstruction artifact. Baselines to check against: 1,338 articulation points, 1,412 bridges.

`../../docs/GRAPH_HANDOFF_V2.md` §4.9 has the full mapping of dataset
features to what each module needs, and §4.5 explains the two-view rule.

Put this module's notebooks, scripts and outputs in this folder.
