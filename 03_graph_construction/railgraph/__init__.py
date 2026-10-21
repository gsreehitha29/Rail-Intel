"""Rail-Intell Phase 3 — graph construction.

    from railgraph import BuildSpec, load_graph
    G = load_graph()                                   # shipped default, invariant-checked
    H = load_graph(BuildSpec(stitch_junctions=False))   # a sensitivity cell

See docs/PHASE3_GRAPH_ROADMAP.md for the stage plan and docs/DECISIONS.md for
why each default is what it is.
"""
from .config import BuildSpec, SHIPPED_INVARIANTS, DATASET_VERSION
from .build import (
    load_graph, rebuild_tables, shipped_tables, to_graph,
    measure, assert_invariants, InvariantError, verify_rebuild_equivalence,
)
from . import weights
from .provenance import ProvenanceSpec, enrich as enrich_v11, summarise as summarise_v11

__all__ = [
    "BuildSpec", "SHIPPED_INVARIANTS", "DATASET_VERSION",
    "load_graph", "rebuild_tables", "shipped_tables", "to_graph",
    "measure", "assert_invariants", "InvariantError",
    "verify_rebuild_equivalence", "weights",
    "ProvenanceSpec", "enrich_v11", "summarise_v11",
]
