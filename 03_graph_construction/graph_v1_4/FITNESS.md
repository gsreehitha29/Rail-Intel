# Graph v1.4 — FINAL

**Status: frozen.** This release is the project's dataset. It is not changed again
except under the stop rule in §5.

Finalising is a *decision*, not a milestone that arrives on its own. This file records
the decision, the evidence that it is a safe one, and — more usefully — which
conclusions this graph can carry and which it never will.

## 1. Why this is final rather than finished

The repair queue regenerates. Every audit of this graph has produced a new list of
defects, and every pass of repairs has produced the next list. That is not a sign the
work is failing; it is a property of the inputs. The physical graph is derived from
OSM-lineage GIS segments, which have no complete station register, no authoritative
code column and no canonical geometry. No amount of repair converts that into a
complete register. The queue is therefore infinite, and "fix the remaining gaps"
is not a terminating instruction.

So the question is not *is the graph clean* but *which claims are already safe*. That
is measurable, and it has been measured.

## 2. The evidence that finalising is safe now

Repairs were applied to v1.3 and the structural results recompared (E-707):

| | v1.3 raw | v1.4 repaired | of which already present in v1.3 |
|---|---|---|---|
| articulation points | 1,380 | 1,173 | **1,173 — all of them** |
| bridges | 1,480 | 1,256 | **1,256 — all of them** |
| top-50 by betweenness | — | 50 | 35 |

Cut points and bridges are **nested**: one round of repair removed 207 false cut
points and created *none*. This is not luck, it is mechanism. 129 of the 137
overrides add an edge, and adding an edge can only ever destroy a cut point, never
create one. The 8 removals are all shortcuts whose endpoints remain joined by a
train-attested alternate path (see `OVERRIDES.csv`), so they cannot create one either.
Further repair of the same kind can only shrink these sets again.

**Therefore a claim of the form "this station is a cut point" is already safe**: it
survives further repair, because the set only ever loses members. A claim of the form
"these are the ten most critical stations" is **not** safe — 15 of the top 50 moved
under one round of repair, and would move again.

That asymmetry is the finalisation criterion, and it is the thing worth taking from
the last several weeks of bug-hunting. The bug-hunting was not treading water; it was
establishing which class of result this dataset can bear.

## 3. Claims this graph supports

Verified against two references never used in construction (2024 timetable: 95.69% of
train route lengths within 5%, median error 0.72%; IIT KGP IRN distances: 82.68%
within 5%).

- Connectivity and reachability between any two of the 9,095 stations.
- Shortest physical route distance, to ~1% on the median pair.
- **Cut points and bridges** — single stations and sections whose loss disconnects
  the network. Stable by §2.
- Corridor- and region-level load, using `trains_per_day` from the service layer
  (16,703 directed pairs). Counting distinct trains instead overstates daily traffic
  2.03× overall and re-orders 49 of the 100 busiest sections, so the weighted figure
  is the only valid one.
- Detour / circuity, and the cost of losing a named section.
- Observed section runtimes from the 2024 delay data. Declared speeds in the source
  are unusable and must not be used.

## 4. Claims this graph will not support

Not "not yet" — these need data that does not exist in any source held, and would not
be produced by more repair.

| Claim | Blocked by | Size of the problem |
|---|---|---|
| node-level criticality *ranking* (top-10 stations) | incomplete station coverage; duplicate nodes | 228 stations absent; 82 node pairs are one real station split in two, which understates exactly the junctions a ranking is about |
| absolute path kilometres | lower-bound lengths | 25.3% of network km is a straight-line floor, not a measurement |
| capacity, congestion, delay propagation as a *mechanism* | no capacity, no signalling, no turn restrictions, undirected | structural — not in scope for a space-of-stations graph |
| anything involving freight | passenger trains only | the 2024 dataset has no freight |
| exact centrality values | all of the above | report ranks and classes, never values |

## 5. The stop rule

v1.4 is amended **only** when an analysis produces a result that is demonstrably
wrong *because of* the graph, shown on a named, reproducible case. A newly discovered
defect is not sufficient grounds. Defects found from here are recorded in §6 as
properties of the dataset, not as a backlog.

If an amendment is ever justified it is a new version (v1.5) with its own gates and
manifest; v1.4's files are never edited in place.

## 6. Known permanent properties

Closed, with measured impact. These are **not** pending work.

- **82 duplicate node pairs** — one station held as two nodes. Understates junction
  criticality. Merging needs a station register we do not have; merging on name or
  distance was tested and produced false merges.
- **228 absent stations**, 39 unresolvable codes — listed in
  `station_code_crosswalk.csv`. Joins must go through `load_resolver()`, which returns
  `None` for these rather than silently dropping them.
- **25.3% lower-bound lengths**; 823 further length disagreements deferred.
  Every edge carries `length_is_lower_bound`; any km total must report it.
- **17 fragments** outside the giant component (0.41% of nodes).
- **71 OSM code collisions** in the deferred coordinate queue, which is why that queue
  was never applied — one entry would have moved Tuglakabad to Kerala.
- **Source licence unresolved** — v1.4 inherits v1.3's untraced base source.
  Internal analysis only until traced.

## 7. How to use it

```python
import sys; sys.path.insert(0, "03_graph_construction")
from railgraph.release import load_graph, load_service, load_resolver, release_info
```

`release_info()` returns the version, the gate results and the caveats. Analysis
modules read the release — never the construction outputs, never a re-run of repairs.
