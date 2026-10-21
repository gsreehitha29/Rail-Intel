"""Construction-choice sensitivity study -- the g05 novelty.

The question: **which downstream conclusions survive the choices made while
building the graph, and which are artifacts of them?**

[PAL26] asks this for the choice of *representation* of an already-built
network. This asks it for the *construction* -- placement tolerance, junction
stitching, node model, degree-2 dissolution, match confidence -- which is
upstream of representation.

Design (roadmap §g05): one-at-a-time around the shipped default for the full
battery, plus one targeted two-factor grid (tolerance x stitching) where F-001
and F-007 give prior reason to expect an interaction. Full factorial over the
nine factors is ~17,000 cells and infeasible.

Every conclusion gets a verdict: **robust** (moves less than its tolerance
band), **conditional** (moves materially but predictably), or **artifact**
(moves enough to change what a reader would conclude).
"""
from __future__ import annotations

import json
import time

import networkx as nx
import numpy as np
import pandas as pd

from . import config as C
from . import metrics as M
from .config import BuildSpec
from .build import load_graph
from .provenance import ProvenanceSpec, load_graph_v11

#: Sample size for betweenness inside the sweep. Justified by E-100's
#: convergence curve: k=1000 gives 98% top-50 overlap and Spearman 0.995
#: against exact, in 39s rather than 363s.
SWEEP_BC_K = 1000
SWEEP_PAIRS = 1500
TOPK = 50


# --------------------------------------------------------------------------- #
# the cell grid
# --------------------------------------------------------------------------- #

def one_at_a_time_cells() -> list[tuple[str, dict]]:
    """Default plus one deviation per factor.

    Tolerance has three levels, not five: F-008 showed `offset_km` is already
    capped at 2.0 km by s07, so 3.0 and infinity are provably identical to 2.0.
    """
    return [
        ("default", {}),
        # construction
        ("tolerance=1.0", {"offset_max_km": 1.0}),
        ("tolerance=2.0", {"offset_max_km": 2.0}),
        ("no_stitching", {"stitch_junctions": False}),
        ("node_model=station_only", {"node_model": "station_only"}),
        ("node_model=junction_only", {"node_model": "junction_only"}),
        ("match_conf=high_only", {"match_conf": ("high",)}),
        ("parallel=mean", {"parallel_policy": "mean"}),
        # representation
        ("dissolve_degree2", {"dissolve_degree2": True}),
        ("prune_degree1", {"prune_degree1": True}),
        ("merge_colocated", {"merge_colocated": True}),
        ("gauge_constrained", {"gauge_constrained": True}),
        ("view=core_v2", {"view": "core_v2"}),
        ("view=core_v4", {"view": "core_v4"}),
    ]


def derivation_cells() -> list[tuple[str, dict, dict]]:
    """W7 -- length *derivation* as a factor, which the sweep never varied.

    E-200's Tier A "no artifacts" verdict was computed over construction and
    representation parameters only, so it could not have detected G-01 or G-02
    (stated in E-200's own limitations). `length_mode='asis'` reproduces the
    v1.0 length and is the control that makes these cells comparable to the
    existing grid.

    Returned as (label, build_kw, provenance_kw) triples.
    """
    return [
        ("length=asis", {}, {"length_mode": "asis"}),
        ("length=hybrid", {}, {"length_mode": "hybrid"}),
        ("length=spine", {}, {"length_mode": "spine"}),
        ("length=chord", {}, {"length_mode": "chord"}),
        # the offset gate inside the hybrid is itself a choice
        ("length=hybrid_offset0.10", {}, {"length_mode": "hybrid",
                                          "offset_trust_km": 0.10}),
        ("length=hybrid_offset1.50", {}, {"length_mode": "hybrid",
                                          "offset_trust_km": 1.50}),
    ]


def derivation_interaction_cells() -> list[tuple[str, dict, dict]]:
    """tolerance x length_source -- the interaction D-026 names as required.

    F-028 couples them: the placement offset decides both which stations are
    placed at all and whether the spine measure between them is trustworthy.
    """
    out = []
    for tol in (1.0, 2.0):
        for mode in ("asis", "hybrid"):
            out.append((f"tol{tol}_length{mode}", {"offset_max_km": tol},
                        {"length_mode": mode}))
    return out


def interaction_cells() -> list[tuple[str, dict]]:
    """tolerance x stitching -- the interaction F-007 predicts."""
    out = []
    for tol in (1.0, 1.5, 2.0):
        for stitch in (True, False):
            out.append((f"tol{tol}_stitch{'ON' if stitch else 'OFF'}",
                        {"offset_max_km": tol, "stitch_junctions": stitch}))
    return out


# --------------------------------------------------------------------------- #
# per-cell measurement
# --------------------------------------------------------------------------- #

def corridor_criticality(G: nx.Graph, weight: str = "length_km",
                         k: int | None = 500) -> pd.Series:
    """Edge betweenness aggregated by corridor_id.

    F-017: node-level top-k is not k places -- in a near-tree, runs of adjacent
    degree-2 nodes carry identical betweenness, so top-200 nodes is 15
    localities. Corridor ids are also stable across sweep cells (they come from
    corridors.csv, not from the build), which node sets are not. So corridor
    criticality is both the honest measure and the comparable one.
    """
    eb = M.edge_betweenness(G, weight=weight, k=k, use_cache=False)
    eb = eb[eb.corridor_id.notna()]
    return eb.groupby("corridor_id").edge_betweenness.sum().sort_values(ascending=False)


def measure_cell(label: str, kw: dict, *, weight: str = "length_km",
                 bc_k: int = SWEEP_BC_K, ref_corridors: list | None = None,
                 ref_nodes: list | None = None,
                 prov_kw: dict | None = None) -> dict:
    """Full battery for one construction choice.

    `prov_kw` makes length derivation a factor (`W7`): when given, the v1.1
    provenance layer is applied with those parameters before the graph is
    built, and the cell's own tolerance governs spine eligibility.
    """
    t0 = time.time()
    spec = BuildSpec(label=label, **kw)
    if prov_kw is None:
        G = load_graph(spec, strict=False)
        prov = None
    else:
        prov = ProvenanceSpec(label=label, **prov_kw)
        G = load_graph_v11(spec, prov, strict=False)

    row: dict = {"cell": label, "spec_hash": spec.hash, "weight": weight}
    row.update({k: v for k, v in spec.to_dict().items() if k != "label"})
    row["length_mode"] = prov.length_mode if prov else "asis"
    row["offset_trust_km"] = prov.offset_trust_km if prov else None
    row["prov_hash"] = prov.hash if prov else None
    row = measure_graph(G, row, weight=weight, bc_k=bc_k,
                        ref_corridors=ref_corridors, ref_nodes=ref_nodes)
    row["secs"] = round(time.time() - t0, 1)
    return row


def measure_graph(G: nx.Graph, row: dict | None = None, *, weight: str = "length_km",
                  bc_k: int = SWEEP_BC_K, ref_corridors: list | None = None,
                  ref_nodes: list | None = None) -> dict:
    """The conclusion battery on an already-built graph.

    Split out of `measure_cell` so a graph that no `BuildSpec` produces -- the
    v1.2 repaired topology (`E-500`) -- is measured by exactly the same code as
    every sweep cell, and its verdicts are comparable.
    """
    row = dict(row or {})
    cs = M.cut_structure(G)
    row.update({k: cs[k] for k in
                ("n_nodes", "n_edges", "n_components", "giant_nodes",
                 "articulation_points", "bridges", "bridge_share",
                 "independent_cycles", "meshedness", "tree_likeness")})
    row["giant_share"] = cs["giant_nodes"] / cs["n_nodes"] if cs["n_nodes"] else np.nan
    row["route_km"] = float(sum(d["length_km"] for _, _, d in G.edges(data=True)))

    pp = M.path_profile(G, weight=weight, n_pairs=SWEEP_PAIRS)
    row.update({"mean_path": pp["mean_path"], "median_path": pp["median_path"],
                "mean_hops": pp["mean_hops"],
                "circuity_median": pp["circuity_median"]})

    # criticality rankings, node-level and corridor-level
    H = M.giant(G)
    bc = M.betweenness(H, weight=weight, k=min(bc_k, H.number_of_nodes() - 1),
                       use_cache=False)
    top_nodes = list(bc.nlargest(TOPK, "betweenness").node_id)
    row["top_nodes"] = top_nodes
    corr_rank = corridor_criticality(H, weight=weight)
    top_corr = list(corr_rank.head(TOPK).index)
    row["top_corridors"] = top_corr

    if ref_nodes is not None:
        row[f"top{TOPK}_node_overlap"] = len(set(top_nodes) & set(ref_nodes)) / TOPK
    if ref_corridors is not None:
        row[f"top{TOPK}_corridor_overlap"] = len(set(top_corr) & set(ref_corridors)) / TOPK

    # resilience: R per strategy, and which strategy is worst (F-011 ordering)
    rs = {}
    for strat in ("random", "degree", "betweenness"):
        df = M.percolation(G, strategy=strat, steps=30,
                           sample_k=min(400, max(50, H.number_of_nodes() // 10)))
        rs[strat] = float(df.R.iloc[0])
    row.update({f"R_{k}": v for k, v in rs.items()})
    row["worst_strategy"] = min(rs, key=rs.get)
    row["random_worse_than_betweenness"] = rs["random"] < rs["betweenness"]
    return row


# --------------------------------------------------------------------------- #
# tiers
# --------------------------------------------------------------------------- #

#: Which cells belong to which verdict tier. A single verdict over every cell is
#: uninformative, because some cells deliberately negate a decided operator
#: (`no_stitching` undoes `D-005`) and will of course break conclusions -- that
#: is what justified the operator. The tiers separate "choices still genuinely
#: open" from "choices already decided on evidence".
#:
#: Recorded here because `E-200` shipped `verdicts_tierA.csv` without any script
#: that regenerates it, so the project's headline robustness claim was not
#: reproducible by `make` (F-044). These definitions reproduce the published
#: Tier A numbers exactly; `E-401` asserts that.
TIER_A = (
    # the nine genuinely open construction and representation choices
    "default", "tolerance=1.0", "tolerance=2.0", "match_conf=high_only",
    "parallel=mean", "dissolve_degree2", "prune_degree1", "merge_colocated",
    "gauge_constrained",
)
#: Tier B adds the attributed-core views, which D-013 ships as flags precisely
#: because filtering on them damages redundancy (bridge share +122%).
TIER_B_ADDS = ("view=core_v2", "view=core_v4")
#: Tier C adds the cells that negate a decided operator outright.
TIER_C_ADDS = ("no_stitching", "node_model=station_only", "node_model=junction_only")


def tier_cells(tier: str, extra: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Cell labels belonging to `tier` ('A', 'B' or 'C'), plus any extras."""
    cells = TIER_A
    if tier in ("B", "C"):
        cells = cells + TIER_B_ADDS
    if tier == "C":
        cells = cells + TIER_C_ADDS
    return cells + tuple(extra)


def verdicts_for_tier(df: pd.DataFrame, tier: str,
                      extra: tuple[str, ...] = ()) -> pd.DataFrame:
    """Verdicts restricted to one tier's cells (plus `extra`, e.g. derivation cells)."""
    keep = set(tier_cells(tier, extra))
    sub = df[df.cell.astype(str).isin(keep)]
    return verdicts(sub)


# --------------------------------------------------------------------------- #
# verdicts
# --------------------------------------------------------------------------- #

#: Tolerance band per conclusion: how much movement still counts as "robust".
#: These are judgement calls and are stated so a reader can disagree with them
#: rather than having them buried in code.
BANDS = {
    "giant_share": 0.02,            # 2 percentage points
    "bridge_share": 0.02,
    "meshedness": 0.005,
    "mean_path": 0.10,              # relative: 10%
    "circuity_median": 0.05,        # relative
    "R_random": 0.20,               # relative
    "R_degree": 0.20,
    f"top{TOPK}_corridor_overlap": 0.20,   # 80% overlap counts as stable
}
RELATIVE = {"mean_path", "circuity_median", "R_random", "R_degree"}


def verdicts(df: pd.DataFrame) -> pd.DataFrame:
    """Per-conclusion robust / conditional / artifact verdict over the sweep."""
    d = df[df.cell == "default"].iloc[0]
    rows = []
    for conc, band in BANDS.items():
        if conc not in df.columns:
            continue
        vals = pd.to_numeric(df[conc], errors="coerce").dropna()
        if conc.endswith("overlap"):
            worst_val = vals.min()
            dev = 1.0 - worst_val
            worst_cell = df.loc[vals.idxmin(), "cell"]
            rng = f"{worst_val:.2f} worst overlap"
        else:
            base = float(d[conc])
            if conc in RELATIVE and base:
                devs = (vals - base).abs() / abs(base)
            else:
                devs = (vals - base).abs()
            dev = float(devs.max())
            worst_cell = df.loc[devs.idxmax(), "cell"]
            rng = f"{vals.min():.4g} to {vals.max():.4g} (default {base:.4g})"
        if dev <= band:
            v = "robust"
        elif dev <= 3 * band:
            v = "conditional"
        else:
            v = "artifact"
        rows.append({"conclusion": conc, "verdict": v, "max_deviation": dev,
                     "band": band, "relative": conc in RELATIVE,
                     "worst_cell": worst_cell, "range": rng})
    return pd.DataFrame(rows).sort_values(
        ["verdict", "max_deviation"], ascending=[True, False])


def sensitivity_damping(df: pd.DataFrame, factor_on: str, factor_off: str,
                        conclusions: list[str]) -> pd.DataFrame:
    """How much does one operator damp another factor's sensitivity? (F-007)"""
    on = df[df.cell.str.contains(factor_on)]
    off = df[df.cell.str.contains(factor_off)]
    rows = []
    for c in conclusions:
        if c not in df.columns:
            continue
        a = pd.to_numeric(on[c], errors="coerce").dropna()
        b = pd.to_numeric(off[c], errors="coerce").dropna()
        ra, rb = a.max() - a.min(), b.max() - b.min()
        rows.append({"conclusion": c, "range_with": float(ra),
                     "range_without": float(rb),
                     "damping_factor": float(rb / ra) if ra else np.inf})
    return pd.DataFrame(rows)
