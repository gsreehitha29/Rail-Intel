"""Paths, build specification, and the shipped invariants.

A BuildSpec captures every construction and representation choice as data, so a
graph is fully described by (dataset version, spec). That is what makes the g05
sensitivity sweep possible: each cell is one spec.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATASET = REPO / "02_graph_inputs" / "graph_dataset"
INPUTS = REPO / "02_graph_inputs" / "graph_inputs"
EXPERIMENTS = REPO / "03_graph_construction" / "experiments"
RELEASE = REPO / "03_graph_construction" / "graph_v1"

DATASET_VERSION = "v1.0"

#: Invariants the shipped dataset must satisfy. Asserted by build.load_graph()
#: whenever the spec is the shipped default. s10_verify_dataset.py checks the
#: files; this checks the graph object built from them.
SHIPPED_INVARIANTS = {
    "n_nodes": 9095,
    "n_edges": 9689,
    "n_components": 18,
    "giant_nodes": 9058,
    "giant_edges": 9669,
    "articulation_points": 1338,
    "bridges": 1412,
    "independent_cycles": 612,
    "degree_max": 7,
    "route_km": 72201.0,       # rounded; compared at 1 km tolerance
    "n_station_nodes": 8621,
    "n_junction_nodes": 474,
    "n_dissolvable": 115,
    "n_stitched_edges": 2252,
}

VALID_NODE_MODELS = ("hybrid", "station_only", "junction_only")
VALID_VIEWS = ("topology", "attr_complete", "core_v2", "core_v4")
VALID_PARALLEL = ("shortest", "mean", "multigraph")


@dataclass(frozen=True)
class BuildSpec:
    """Every construction choice, with the shipped default as its default value.

    Construction parameters (require a rebuild from station_sequences):
        offset_max_km     placement tolerance, D-004
        stitch_junctions  attach chains to junction endpoints, D-005
        node_model        hybrid | station_only | junction_only, D-001
        match_conf        accepted station-match confidence classes, D-003
        min_edge_km       floor for co-located stations, D-007
        parallel_policy   shortest | mean | multigraph, D-006

    Representation parameters (applied to an already-built edge list):
        view              topology | attr_complete | core_v2 | core_v4, D-013
        dissolve_degree2  contract the 115 dissolvable junctions, D-002/D-017
        prune_degree1     drop degree-1 operational junctions (line ends)
        merge_colocated   merge co-located station pairs into one node
        gauge_constrained keep only the dominant gauge component, D-011
        giant_only        restrict to the giant component, D-020
    """

    # construction
    offset_max_km: float = 1.5
    stitch_junctions: bool = True
    node_model: str = "hybrid"
    match_conf: tuple[str, ...] = ("high", "medium")
    min_edge_km: float = 0.05
    parallel_policy: str = "shortest"
    # representation
    view: str = "topology"
    dissolve_degree2: bool = False
    prune_degree1: bool = False
    merge_colocated: bool = False
    gauge_constrained: bool = False
    giant_only: bool = False
    # bookkeeping
    label: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        if self.node_model not in VALID_NODE_MODELS:
            raise ValueError(f"node_model must be one of {VALID_NODE_MODELS}")
        if self.view not in VALID_VIEWS:
            raise ValueError(f"view must be one of {VALID_VIEWS}")
        if self.parallel_policy not in VALID_PARALLEL:
            raise ValueError(f"parallel_policy must be one of {VALID_PARALLEL}")
        if self.offset_max_km <= 0:
            raise ValueError("offset_max_km must be positive")

    @property
    def is_shipped_default(self) -> bool:
        """True when this spec is exactly the one that produced graph_dataset/."""
        d = asdict(self)
        d.pop("label")
        return d == {
            "offset_max_km": 1.5, "stitch_junctions": True, "node_model": "hybrid",
            "match_conf": ("high", "medium"), "min_edge_km": 0.05,
            "parallel_policy": "shortest", "view": "topology",
            "dissolve_degree2": False, "prune_degree1": False,
            "merge_colocated": False, "gauge_constrained": False,
            "giant_only": False,
        }

    @property
    def needs_rebuild(self) -> bool:
        """True when the shipped edges.csv cannot be used as-is."""
        return not (
            self.offset_max_km == 1.5
            and self.stitch_junctions
            and self.node_model == "hybrid"
            and tuple(self.match_conf) == ("high", "medium")
            and self.min_edge_km == 0.05
            and self.parallel_policy == "shortest"
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["match_conf"] = list(self.match_conf)
        d["dataset_version"] = DATASET_VERSION
        return d

    @property
    def hash(self) -> str:
        """Stable 12-char hash of the spec, for experiment keys and caching."""
        d = self.to_dict()
        d.pop("label", None)
        blob = json.dumps(d, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:12]

    def __str__(self) -> str:
        return self.label or f"spec:{self.hash}"
