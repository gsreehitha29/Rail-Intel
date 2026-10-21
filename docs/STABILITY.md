# Stability contract — what downstream code may rely on

Graph release **v1.4**, frozen under D-055. This is the promise the test suite enforces;
`tests/` is its executable form. If a test in `tests/test_release.py` fails, this
contract has been broken.

## Guaranteed for the lifetime of v1.4

**The entry point.** `railgraph.release` is the only supported way in. Its four
functions keep their names and signatures:

```python
load_graph(root=None, release="v1_4", variant="open", weight="km")
load_service(root=None, release="v1_4", variant="open", what="edges")
load_resolver(root=None, release="v1_4")
release_info(root=None, release="v1_4")
```

Reading `graph_v1_4/open/*.csv` directly is permitted but unsupported: those paths are
stable, their parsing is your problem.

**Node identity.** `node_id` is stable. A node is never renumbered, re-pointed at a
different place, or reused for a different station. The 82 known duplicate pairs stay
as they are — contract this yourself if your analysis needs it (E-709 shows how).

**Edge identity.** `edge_id` is stable and unique. An edge's endpoints never change.

**Schema.** Columns are append-only. No column is removed, renamed, or has its units or
meaning changed. New columns may appear at the end, so select by name, never position.

**Counts.** 9,095 nodes, 9,759 edges, 74,849.7 km, 18 components, giant share 0.9959.
These do not move within v1.4.

**The gates.** All nine pass, and `gates.json` keeps its structure. A release where any
gate fails is never published.

**Canonical format.** CSV. Parquet is a convenience copy and is *not* byte-reproducible
across machines, because Arrow embeds its writer version. Compare CSVs, hash CSVs, cite
CSVs.

## Explicitly not guaranteed

- **Parquet bytes** — see above.
- **Row order** in any file. Sort if you depend on order.
- **Anything in `04_analysis_modules/*/out/`** — analysis outputs are regenerable and may
  change when a module is improved. Only the release itself is frozen.
- **The derivation modules** (E-702…E-706). They produce `OVERRIDES.csv`; their internals
  are free to change as long as the overrides they emit are unchanged.
- **Non-giant components.** The 17 fragments may be connected by a future release.

## What may *not* be relied on scientifically

Separate from the engineering contract, and set by D-055. The release supports
connectivity, reachability, route distance, cut points, bridges, and corridor load via
`trains_per_day`. It does **not** support node-level criticality ranking, absolute path
kilometres, capacity or congestion as a mechanism, freight, or exact centrality values.
`release_info()["caveats"]` returns the short form. Build on the first list; cite the
second as a limitation.

## How v1.4 changes

It does not. Under D-055 an amendment is a **new release** — v1.5, its own directory, its
own gates, its own manifest — never an edit in place. v1.4's files stay byte-identical
once published.

Grounds for v1.5 are narrow: an analysis result demonstrably wrong *because of* the
graph, on a named reproducible case. Discovering a defect is not grounds; defects are
recorded as properties in `graph_v1_4/FITNESS.md` §6.

## When a test fails

A failure is a fork, not a chore:

1. **A bug** — something edited a frozen file by hand, or a derivation module changed its
   output without a new release. Fix the cause, not the test.
2. **A deliberate new release** — then `golden.json` is regenerated *as part of* cutting
   v1.5, alongside a `DECISIONS.md` entry recording what moved and why.

Editing `golden.json` to make a red test green, with no decision record, destroys the
only mechanism that tells you the dataset has drifted.

## Running it

```
make test          # or: pytest -q
```

`tests/golden.json` is generated from the release and reviewed, not hand-typed. The
E-709 finding tests skip cleanly if `make sever` has not been run.
