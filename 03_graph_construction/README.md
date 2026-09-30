# 03 — Graph Construction

**Owner:** Sreehitha (Graph Engineering). This is the current phase.

The data half is finished. Node identity is resolved, vocabularies are
unified, edges are built and weighted, and the service layer is derived — so
this phase is about the graph object, its storage, its validation and its
visualisation, not about matching or cleaning.

## Build from

`../02_graph_inputs/graph_dataset/` — read its `README.md` first; it is the
data dictionary. `nodes.csv` and `edges.csv` load straight into NetworkX:

```python
import pandas as pd, networkx as nx

nodes = pd.read_csv("../02_graph_inputs/graph_dataset/nodes.csv")
edges = pd.read_csv("../02_graph_inputs/graph_dataset/edges.csv")

G = nx.Graph()
for r in nodes.itertuples():
    G.add_node(r.node_id, node_type=r.node_type, name=r.node_name,
               lon=r.longitude, lat=r.latitude, zone=r.zone_code, state=r.state)
for r in edges.itertuples():
    G.add_edge(r.from_node, r.to_node, km=r.length_km, gauge=r.gauge_code,
               tracks=r.n_tracks, speed=r.speed_kmph, load=r.service_load)
```

Expect **9,095 nodes, 9,689 edges, 99.6% in one connected component,
72,201 route km.** If your build does not reproduce those, compare against
`../02_graph_inputs/graph_dataset/QA_REPORT.txt` before going further.

## Read

- `../02_graph_inputs/graph_dataset/README.md` — the data dictionary
- `../docs/GRAPH_HANDOFF_V2.md` §4 — why the dataset is shaped this way,
  §4.8 the decision register, §4.9 what each downstream module needs
- `../CHANGELOG.md` — what changed and when
- `../docs/VALIDATION_REPORT.md` — closed, kept as provenance for how the
  preprocessing layer was checked

## What this phase owes the project

1. Graph v1 as a versioned, exportable artifact — GraphML plus parquet
   node/edge tables plus GeoJSON edge geometry (blueprint §13).
2. The four decisions still open in `../docs/GRAPH_HANDOFF_V2.md` §6.
3. Metrics infrastructure the Phase 4 modules call into.
4. Layout and visualisation.
5. A graph-level validation report, and graph v1 frozen before any
   downstream analysis runs against it.

Put this phase's code, notebooks and outputs in this folder. Do not hand-edit
anything in `graph_dataset/` — change the pipeline and re-run.
