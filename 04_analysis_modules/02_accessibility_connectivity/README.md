# Accessibility & Service Connectivity

**Owner:** Abrar (Network Intelligence / Domain Modules).

Service frequency, reachable destinations, direct versus indirect connectivity, shortest travel paths, station accessibility profiles.

## Data

Build on graph v1 from `../../03_graph_construction/`, which is constructed
from `../../02_graph_inputs/graph_dataset/`. Do not start until graph v1 is
frozen — running against a moving graph makes results irreproducible.

## Which view this module uses

Needs `service_edges.csv`: `runtime_min_median` for genuinely time-weighted shortest paths and `n_trains` for frequency. Derive the space-P transfer graph on the fly from the schedules — it is not shipped because it would be roughly 16 million rows.

`../../docs/GRAPH_HANDOFF_V2.md` §4.9 has the full mapping of dataset
features to what each module needs, and §4.5 explains the two-view rule.

Put this module's notebooks, scripts and outputs in this folder.
