# Network Expansion & What-If

**Owner:** Abrar (Network Intelligence / Domain Modules).

Candidate station pairs, before/after shortest paths, component reduction, accessibility and redundancy improvement, scenario comparison.

## Data

Build on graph v1 from `../../03_graph_construction/`, which is constructed
from `../../02_graph_inputs/graph_dataset/`. Do not start until graph v1 is
frozen — running against a moving graph makes results irreproducible.

## Which view this module uses

Candidate edges come from the data, not from imagination: the 607 service pairs with an endpoint missing from the graph, the 40 junctions whose name match was rejected on a spatial conflict, and the low-redundancy regions Module 3 surfaces. Use `length_km` between candidate endpoints as the cost proxy.

`../../docs/GRAPH_HANDOFF_V2.md` §4.9 has the full mapping of dataset
features to what each module needs, and §4.5 explains the two-view rule.

Put this module's notebooks, scripts and outputs in this folder.
