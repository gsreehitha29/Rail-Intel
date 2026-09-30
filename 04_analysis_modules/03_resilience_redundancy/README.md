# Redundancy & Resilience

**Owner:** Abrar (Network Intelligence / Domain Modules).

Node and edge removal, largest connected component decay, alternative paths, connectivity degradation, targeted versus random failure.

## Data

Build on graph v1 from `../../03_graph_construction/`, which is constructed
from `../../02_graph_inputs/graph_dataset/`. Do not start until graph v1 is
frozen — running against a moving graph makes results irreproducible.

## Which view this module uses

Use the **full topology view**, and say so in the writeup. This is the module the `core_v2`/`core_v4` filters would actively damage: filtering removes real alternative routes and pushes the bridge share from 14.6% past 30%, overstating fragility by about 2.5×. `parallel_differs` marks the 124 genuinely distinct parallel routes and `n_tracks` separates single-line corridors.

`../../docs/GRAPH_HANDOFF_V2.md` §4.9 has the full mapping of dataset
features to what each module needs, and §4.5 explains the two-view rule.

Put this module's notebooks, scripts and outputs in this folder.
