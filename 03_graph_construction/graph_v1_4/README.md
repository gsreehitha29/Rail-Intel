# graph v1.4 — FINAL

The repaired, frozen railway graph. Supersedes v1.3 open for analysis.

**Frozen.** What this graph can and cannot carry, and the rule for changing it:
[`FITNESS.md`](FITNESS.md). Amendments are a new version, never an edit in place
(D-055). The engineering contract is `docs/STABILITY.md`, enforced by `make test`.

**9095 stations · 9759 sections · 74,849.7 km · built by `make v14`**

## Use it

```python
import sys; sys.path.insert(0, "03_graph_construction")
from railgraph.release import load_graph, load_service, load_resolver, release_info

G    = load_graph()        # networkx graph
svc  = load_service()      # directed service pairs, with trains_per_day
code = load_resolver()     # station code from any dataset -> graph node
release_info()             # version, gates, caveats
```

Load it this way rather than reading the CSVs, so every module works on the same network.

## What is here

| Path | Contents |
| --- | --- |
| `open/nodes.csv` `.parquet` | 9095 stations |
| `open/edges.csv` `.parquet` | 9759 sections, each with `origin` saying which release or repair put it there |
| `open/rail_graph_v1_4_open.graphml` | the same graph for Gephi, igraph and the like |
| `OVERRIDES.csv` | every repair decision, including the 42 rejected, each with its evidence |
| `station_code_crosswalk.csv` | 68 renamed codes resolved, 228 stations recorded as absent |
| `gates.json` · `VALIDATION_v1_4.md` | what this build was checked against |
| `graph_v1_4.manifest.json` | SHA-256 of every input and output |
| `../service_layer_v1_4/open/` | 16703 directed pairs, hourly departures, per-section loads, per-train frequency |

## How it is built

`make v14` runs five stages and takes about a minute. The repairs themselves are *derived*
by E-702 to E-706, which read the evidence and write decision tables; this build *applies*
those decisions and is deterministic. Re-running on unchanged inputs reproduces every
output hash, which the manifest records.

The split is deliberate. Deciding what to repair needs judgement and evidence, and should
be reviewable row by row. Applying the decisions should not need either.

## Before you use it

Read `VALIDATION_v1_4.md`. The short version: topology is sound and validated against
trains the graph was never built from; distance is three-quarters sound; declared speed
should not be used at all.
