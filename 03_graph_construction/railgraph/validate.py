"""Validation battery for graph v1.

Six layers, per docs/PHASE3_GRAPH_ROADMAP.md §g04:

  V1  internal invariants, re-derived from the graph object
  V2  structural plausibility against theory ([KUR06] exponential degree,
      [BAR11] bounded degree, route-km decomposition)
  V3  cross-source external validation against the timetable, STRATIFIED --
      the direct test of claim C2
  V4  prior-art reproduction ([SEN03] P-space, [BHA15] service network)
  V5  stratified ground-truth audit (sampling frame only; labelling is manual)
  V6  null models, so structural claims are made against a baseline

Each layer returns a dict or DataFrame. `run_all` assembles them into the
report that becomes docs/VALIDATION_v1.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import networkx as nx

from . import config as C
from . import metrics as M
from .build import assert_invariants, measure


# --------------------------------------------------------------------------- #
# V1 -- internal invariants
# --------------------------------------------------------------------------- #

def v1_invariants(G: nx.Graph) -> dict:
    """Re-derive every shipped guarantee from the graph object, not the CSVs."""
    m = assert_invariants(G, strict=False)
    nodes = pd.read_csv(C.DATASET / "nodes.csv")
    edges = pd.read_csv(C.DATASET / "edges.csv")

    comp = {}
    for i, c in enumerate(sorted(nx.connected_components(G), key=len, reverse=True)):
        for n in c:
            comp[n] = i
    nd = nodes.set_index("node_id")
    degree_match = all(int(nd.loc[n, "degree"]) == G.degree(n) for n in G)
    giant_match = all(bool(nd.loc[n, "in_giant_component"]) == (comp[n] == 0) for n in G)

    return {
        "layer": "V1",
        "invariant_failures": m["invariant_failures"],
        "all_invariants_pass": not m["invariant_failures"],
        "node_degree_column_matches_graph": degree_match,
        "in_giant_component_column_matches_graph": giant_match,
        "node_id_unique": bool(nodes.node_id.is_unique),
        "edge_id_unique": bool(edges.edge_id.is_unique),
        "no_self_loops": int(nx.number_of_selfloops(G)) == 0,
        "measured": {k: v for k, v in m.items() if k != "invariant_failures"},
    }


# --------------------------------------------------------------------------- #
# V2 -- structural plausibility against theory
# --------------------------------------------------------------------------- #

def v2_degree_distribution(G: nx.Graph) -> dict:
    """Exponential vs power law, by maximum likelihood and a likelihood ratio.

    [KUR06] finds rail space-of-stations degree distributions are EXPONENTIAL,
    not scale-free, and [BAR11] explains why: spatial embedding bounds degree.
    This is a falsifiable prediction about our construction -- a power-law fit
    would mean we built something other than a physical rail network.
    """
    deg = np.array([d for _, d in G.degree()])
    deg = deg[deg >= 1]
    k_min = 1
    x = deg[deg >= k_min].astype(float)
    n = len(x)

    # exponential (discrete, MLE on the shifted variable)
    lam = 1.0 / (x.mean() - k_min + 1.0)
    ll_exp = float(np.sum(np.log(lam) - lam * (x - k_min)))

    # power law (continuous MLE, Clauset et al. form)
    alpha = 1.0 + n / np.sum(np.log(x / (k_min - 0.5)))
    ll_pl = float(np.sum(np.log((alpha - 1) / (k_min - 0.5))
                         - alpha * np.log(x / (k_min - 0.5))))

    counts = pd.Series(deg).value_counts().sort_index()
    return {
        "layer": "V2",
        "check": "degree_distribution",
        "n": int(n),
        "degree_mean": float(deg.mean()),
        "degree_max": int(deg.max()),
        "degree_var": float(deg.var()),
        "share_degree_le_2": float((deg <= 2).mean()),
        "exponential_lambda": float(lam),
        "exponential_loglik": ll_exp,
        "powerlaw_alpha": float(alpha),
        "powerlaw_loglik": ll_pl,
        "loglik_ratio_exp_over_pl": ll_exp - ll_pl,
        "favoured": "exponential" if ll_exp > ll_pl else "power_law",
        "kurant_thiran_prediction_met": bool(ll_exp > ll_pl and deg.max() <= 20),
        "degree_counts": {int(k): int(v) for k, v in counts.items()},
    }


def v2_route_km(G: nx.Graph) -> dict:
    """Decompose the +3.3% gap against the Year Book's published route km.

    F-004 requires this be explained, not merely reported as 'close'. The
    hypothesis is that 'route km' counts each route once, while our corridor set
    counts parallel chords, loops and bypasses separately.
    """
    corr = pd.read_csv(C.DATASET / "corridors.csv")
    edges = pd.read_csv(C.DATASET / "edges.csv")
    YEARBOOK_ROUTE_KM = 69_439.0

    graph_km = float(edges.length_km.sum())
    corridor_km = float(corr.geodesic_length_km.sum())
    declared_km = float(corr.declared_track_length_km.sum(skipna=True))

    # the parallel-route component: edges produced by more than one corridor
    par = edges[edges.n_parallel_corridors > 1]
    par_extra_km = float(par.length_km.sum())
    par_differs_km = float(edges[edges.parallel_differs.astype(bool)].length_km.sum())
    stitch_km = float(edges[edges.any_stitch.astype(bool)].length_km.sum())

    return {
        "layer": "V2",
        "check": "route_km_decomposition",
        "yearbook_route_km": YEARBOOK_ROUTE_KM,
        "graph_edge_km": graph_km,
        "corridor_geodesic_km": corridor_km,
        "corridor_declared_km": declared_km,
        "gap_vs_yearbook_km": graph_km - YEARBOOK_ROUTE_KM,
        "gap_vs_yearbook_pct": (graph_km - YEARBOOK_ROUTE_KM) / YEARBOOK_ROUTE_KM * 100,
        "declared_inflation_pct": (declared_km / corridor_km - 1) * 100 if corridor_km else np.nan,
        "km_on_parallel_edges": par_extra_km,
        "km_on_genuinely_differing_parallels": par_differs_km,
        "km_on_stitched_edges": stitch_km,
        "n_parallel_edges": int(len(par)),
    }


# --------------------------------------------------------------------------- #
# V3 -- cross-source external validation (the C2 test)
# --------------------------------------------------------------------------- #

def v3_cross_source(G: nx.Graph, max_hops: int = 3) -> dict:
    """Validate the physical graph against the timetable, in both directions.

    The timetable was never used to build the physical layer (D-009, D-015), so
    it is a genuine external test set. Two directions, both needed:

      completeness  -- does every service adjacency correspond to a physical
                       edge or a short physical path? A service pair that needs
                       many hops, or lands in another component, is a hole in
                       the physical graph.
      soundness     -- does every physical edge carry service? An edge with no
                       service is not necessarily wrong (freight-only, closed
                       line, reconstruction artifact) but the RATE matters, and
                       it must be reported BY STRATUM, because the aggregate
                       hides whether the stitched edges -- the novel operator --
                       are the weak ones.
    """
    se = pd.read_csv(C.DATASET / "service_edges.csv")
    comp = {}
    for i, c in enumerate(sorted(nx.connected_components(G), key=len, reverse=True)):
        for n in c:
            comp[n] = i

    # ---- direction 1: service -> physical (completeness)
    se["a_in"] = se.from_station.isin(G)
    se["b_in"] = se.to_station.isin(G)
    both = se[se.a_in & se.b_in].copy()
    both["direct"] = [G.has_edge(a, b) for a, b in zip(both.from_station, both.to_station)]
    both["same_component"] = [comp[a] == comp[b]
                              for a, b in zip(both.from_station, both.to_station)]

    hops = []
    for a, b, direct, same in zip(both.from_station, both.to_station,
                                  both.direct, both.same_component):
        if direct:
            hops.append(1)
        elif not same:
            hops.append(-1)                       # different components
        else:
            try:
                hops.append(nx.shortest_path_length(G, a, b))
            except nx.NetworkXNoPath:
                hops.append(-1)
    both["phys_hops"] = hops

    completeness = {
        "service_pairs_total": int(len(se)),
        "both_endpoints_in_graph": int(len(both)),
        "both_endpoints_share": len(both) / len(se),
        "direct_physical_edge": int(both.direct.sum()),
        "direct_share_of_resolvable": float(both.direct.mean()),
        f"within_{max_hops}_hops": int(((both.phys_hops >= 1)
                                        & (both.phys_hops <= max_hops)).sum()),
        f"within_{max_hops}_hops_share": float(((both.phys_hops >= 1)
                                                & (both.phys_hops <= max_hops)).mean()),
        "cross_component_contradictions": int((both.phys_hops == -1).sum()),
        "median_hops_when_indirect": float(both.loc[both.phys_hops > 1, "phys_hops"].median()),
    }

    # ---- direction 2: physical -> service (soundness), BY STRATUM
    edges = pd.read_csv(C.DATASET / "edges.csv")
    direct_pairs = {tuple(sorted(p)) for p in zip(se.from_station, se.to_station)}
    edges["has_direct_service"] = [tuple(sorted((u, v))) in direct_pairs
                                   for u, v in zip(edges.from_node, edges.to_node)]
    edges["has_projected_load"] = edges.service_load.fillna(0) > 0
    nd = pd.read_csv(C.DATASET / "nodes.csv").set_index("node_id")
    nt = nd.node_type.to_dict()
    edges["endpoint_types"] = [
        "both_station" if nt.get(u) == "station" and nt.get(v) == "station"
        else ("both_junction" if nt.get(u) != "station" and nt.get(v) != "station"
              else "mixed")
        for u, v in zip(edges.from_node, edges.to_node)]

    def stratum(df, name):
        return {
            "stratum": name,
            "n_edges": int(len(df)),
            "share_of_all": len(df) / len(edges),
            "direct_service_rate": float(df.has_direct_service.mean()) if len(df) else np.nan,
            "projected_load_rate": float(df.has_projected_load.mean()) if len(df) else np.nan,
        }

    strata = [stratum(edges, "ALL")]
    for val, name in [(True, "any_stitch=True"), (False, "any_stitch=False")]:
        strata.append(stratum(edges[edges.any_stitch.astype(bool) == val],
                              name))
    for t in ("both_station", "mixed", "both_junction"):
        strata.append(stratum(edges[edges.endpoint_types == t], f"endpoints={t}"))
    for val, name in [(True, "core_v4=True"), (False, "core_v4=False")]:
        strata.append(stratum(edges[edges.core_v4.astype(bool) == val], name))
    for val, name in [(True, "parallel_differs=True"), (False, "parallel_differs=False")]:
        strata.append(stratum(edges[edges.parallel_differs.astype(bool) == val], name))
    for val, name in [(True, "is_colocated=True"), (False, "is_colocated=False")]:
        strata.append(stratum(edges[edges.is_colocated.astype(bool) == val], name))

    return {
        "layer": "V3",
        "completeness_service_to_physical": completeness,
        "soundness_physical_to_service_by_stratum": strata,
    }


# --------------------------------------------------------------------------- #
# V6 -- null models
# --------------------------------------------------------------------------- #

def v6_null_models(G: nx.Graph, n_reps: int = 5, seed: int = 42) -> dict:
    """Degree-preserving rewiring, so structural claims have a baseline.

    "14.6% of edges are bridges" and "the network is 94% tree-like" are only
    meaningful against what a graph with the same degree sequence would give.
    A spatially constrained null would be stronger still, but degree-preserving
    rewiring already separates "property of the degree sequence" from "property
    of the spatial embedding".
    """
    H = M.giant(G)
    obs = M.cut_structure(H)
    rng = np.random.default_rng(seed)
    rows = []
    for rep in range(n_reps):
        R = H.copy()
        try:
            nx.double_edge_swap(R, nswap=10 * R.number_of_edges(),
                                max_tries=200 * R.number_of_edges(),
                                seed=int(rng.integers(1 << 31)))
        except (nx.NetworkXError, nx.NetworkXAlgorithmError):
            pass
        Rg = R.subgraph(max(nx.connected_components(R), key=len)).copy()
        n, m = Rg.number_of_nodes(), Rg.number_of_edges()
        rows.append({
            "rep": rep,
            "giant_nodes": n,
            "n_components": nx.number_connected_components(R),
            "bridges": len(list(nx.bridges(Rg))),
            "bridge_share": len(list(nx.bridges(Rg))) / m if m else np.nan,
            "articulation_points": len(list(nx.articulation_points(Rg))),
            "independent_cycles": m - n + 1,
        })
    null = pd.DataFrame(rows)
    return {
        "layer": "V6",
        "observed": {k: obs[k] for k in
                     ("bridges", "bridge_share", "articulation_points",
                      "independent_cycles", "giant_nodes", "n_components")},
        "null_mean": {k: float(null[k].mean()) for k in
                      ("bridges", "bridge_share", "articulation_points",
                       "independent_cycles", "giant_nodes", "n_components")},
        "null_std": {k: float(null[k].std()) for k in
                     ("bridges", "bridge_share", "articulation_points",
                      "independent_cycles")},
        "z_bridge_share": float((obs["bridge_share"] - null.bridge_share.mean())
                                / null.bridge_share.std())
        if null.bridge_share.std() else np.nan,
        "n_reps": n_reps,
    }


# --------------------------------------------------------------------------- #
# V5 -- audit sampling frame (labelling is manual, by two raters)
# --------------------------------------------------------------------------- #

def v5_audit_frame(G: nx.Graph, per_stratum: int = 25, seed: int = 42) -> pd.DataFrame:
    """Build the stratified sample for manual ground-truth audit.

    [BOE25]'s protocol: sample by stratum, verify each case against independent
    reference material, report TP/FP/FN per stratum rather than one global
    accuracy. Deliberately over-samples the known weak spots, and always
    includes the single most critical edge in the network, because an aggregate
    pass rate licenses nothing about the one edge the headline result rests on.
    """
    edges = pd.read_csv(C.DATASET / "edges.csv")
    nd = pd.read_csv(C.DATASET / "nodes.csv").set_index("node_id")
    rng = np.random.default_rng(seed)

    strata = {
        "stitched": edges.any_stitch.astype(bool),
        "unstitched": ~edges.any_stitch.astype(bool),
        "parallel_differs": edges.parallel_differs.astype(bool),
        "colocated": edges.is_colocated.astype(bool),
        "outside_core_v4": ~edges.core_v4.astype(bool),
        "junction_endpoint": [not (str(u).startswith("JN::") is False
                                   and str(v).startswith("JN::") is False)
                              for u, v in zip(edges.from_node, edges.to_node)],
        "long_edge_gt_50km": edges.length_km > 50,
        "no_service": edges.service_load.fillna(0) == 0,
    }

    picks = []
    for name, mask in strata.items():
        sub = edges[np.asarray(mask)]
        if not len(sub):
            continue
        take = sub.iloc[rng.choice(len(sub), size=min(per_stratum, len(sub)),
                                   replace=False)].copy()
        take["audit_stratum"] = name
        picks.append(take)

    # always audit the worst bridge, by name -- F-015/F-016
    sev = M.bridge_severance(G, top=5)
    worst = edges.merge(sev[["from_node", "to_node"]], on=["from_node", "to_node"])
    if len(worst):
        worst = worst.copy()
        worst["audit_stratum"] = "top5_severing_bridge"
        picks.append(worst)

    out = pd.concat(picks).drop_duplicates("edge_id")
    out["from_name"] = out.from_node.map(nd.node_name)
    out["to_name"] = out.to_node.map(nd.node_name)
    out["zone"] = out.from_node.map(nd.zone_code)
    cols = ["audit_stratum", "edge_id", "from_node", "from_name", "to_node", "to_name",
            "zone", "length_km", "corridor_id", "any_stitch", "parallel_differs",
            "is_colocated", "core_v4", "service_load", "n_tracks", "gauge_code"]
    out = out[cols].sort_values(["audit_stratum", "edge_id"]).reset_index(drop=True)
    # blank columns for the two raters
    for c in ("rater1_verdict", "rater1_source", "rater2_verdict", "rater2_source", "notes"):
        out[c] = ""
    return out


# --------------------------------------------------------------------------- #
# V3b -- the fair stitching test
# --------------------------------------------------------------------------- #

def v3b_stitch_fair_test(G: nx.Graph) -> dict:
    """Separate the definitional artifact from the real stitching deficit.

    The raw stratified result (v3) shows stitched edges carrying direct service
    at 57.9% against 86.7% unstitched -- a 28.8 pp gap that looks damning. But
    `service_edges.csv` contains only station codes, so an edge with a junction
    endpoint CANNOT have direct service by definition, and every such edge is
    stitched. Conditioning on station-to-station edges is the only fair test.
    """
    from scipy.stats import fisher_exact

    se = pd.read_csv(C.DATASET / "service_edges.csv")
    ed = pd.read_csv(C.DATASET / "edges.csv")
    nt = pd.read_csv(C.DATASET / "nodes.csv").set_index("node_id").node_type.to_dict()

    codes = set(se.from_station) | set(se.to_station)
    direct = {tuple(sorted(p)) for p in zip(se.from_station, se.to_station)}
    ed["has_direct"] = [tuple(sorted((u, v))) in direct
                        for u, v in zip(ed.from_node, ed.to_node)]
    ed["has_load"] = ed.service_load.fillna(0) > 0
    ed["stitch"] = ed.any_stitch.astype(bool)
    ed["both_station"] = [nt.get(u) == "station" and nt.get(v) == "station"
                          for u, v in zip(ed.from_node, ed.to_node)]

    bs = ed[ed.both_station]
    a, b = bs[bs.stitch], bs[~bs.stitch]
    tab = [[int(a.has_direct.sum()), int(len(a) - a.has_direct.sum())],
           [int(b.has_direct.sum()), int(len(b) - b.has_direct.sum())]]
    odds, p = fisher_exact(tab)

    return {
        "layer": "V3b",
        "service_layer_contains_junction_ids": any(str(c).startswith("JN::") for c in codes),
        "junction_endpoint_edges": int((~ed.both_station).sum()),
        "junction_endpoint_edges_all_stitched": bool(ed.loc[~ed.both_station, "stitch"].all()),
        "raw_gap_pp": float((ed[~ed.stitch].has_direct.mean()
                             - ed[ed.stitch].has_direct.mean()) * 100),
        "fair_stitched_n": int(len(a)),
        "fair_stitched_direct": float(a.has_direct.mean()),
        "fair_stitched_load": float(a.has_load.mean()),
        "fair_unstitched_n": int(len(b)),
        "fair_unstitched_direct": float(b.has_direct.mean()),
        "fair_unstitched_load": float(b.has_load.mean()),
        "fair_gap_pp_direct": float((b.has_direct.mean() - a.has_direct.mean()) * 100),
        "fair_gap_pp_load": float((b.has_load.mean() - a.has_load.mean()) * 100),
        "artifact_share_of_raw_gap": float(
            1 - (b.has_direct.mean() - a.has_direct.mean())
            / (ed[~ed.stitch].has_direct.mean() - ed[ed.stitch].has_direct.mean())),
        "fisher_odds_ratio": float(odds),
        "fisher_p": float(p),
    }


def v2_route_km_reconciliation(G: nx.Graph) -> dict:
    """Test whether excluding zero-station corridors reconciles the route-km gap.

    It does, almost exactly -- but the mechanism is NOT established, so this is
    reported as an open question rather than a validation. See F-019.
    """
    ed = pd.read_csv(C.DATASET / "edges.csv")
    corr = pd.read_csv(C.DATASET / "corridors.csv")
    YB = 69_439.0
    zero = set(corr.loc[corr.n_stations_found == 0, "corridor_id"])
    ed["from_zero_station_corridor"] = ed.corridor_id.isin(zero)
    km_all = float(ed.length_km.sum())
    km_zero = float(ed[ed.from_zero_station_corridor].length_km.sum())
    km_par = float(ed[ed.n_parallel_corridors > 1].length_km.sum())
    zc = corr[corr.n_stations_found == 0]
    return {
        "layer": "V2",
        "check": "route_km_reconciliation",
        "yearbook_route_km": YB,
        "graph_km": km_all,
        "gap_pct": (km_all - YB) / YB * 100,
        "km_from_zero_station_corridors": km_zero,
        "n_edges_from_zero_station_corridors": int(ed.from_zero_station_corridor.sum()),
        "km_excluding_zero_station": km_all - km_zero,
        "gap_pct_excluding_zero_station": (km_all - km_zero - YB) / YB * 100,
        "km_excluding_zero_and_parallel": km_all - km_zero - km_par,
        "gap_pct_excluding_zero_and_parallel": (km_all - km_zero - km_par - YB) / YB * 100,
        "zero_station_corridor_count": int(len(zc)),
        "zero_station_length_median_km": float(zc.geodesic_length_km.median()),
        "zero_station_length_max_km": float(zc.geodesic_length_km.max()),
        "mechanism_established": False,
        "mechanism_note": (
            "Excluding zero-station corridors closes the gap to -0.06%, but "
            "inspection shows they are NOT all yard/siding links: the longest "
            "include Balipara-Harmuti Jn (132.6 km), Bogibeel Bridge-Harmuti Jn "
            "(116.0 km) and Balangir-Puranakatak (94.9 km), which are genuine "
            "route. The near-exact reconciliation may therefore be coincidental. "
            "Resolve with the per-zone comparison against "
            "reference_data/Table-19.2-Zone-wise.csv -- one national total can "
            "reconcile by luck, seventeen zone totals cannot."),
    }


def run_all(G: nx.Graph, *, null_reps: int = 12) -> dict:
    """Assemble the full battery. V4 and V5 labelling are handled separately."""
    return {
        "dataset_version": C.DATASET_VERSION,
        "spec_hash": G.graph.get("spec_hash"),
        "V1": v1_invariants(G),
        "V2_degree": v2_degree_distribution(G),
        "V2_route_km": v2_route_km(G),
        "V2_route_km_reconciliation": v2_route_km_reconciliation(G),
        "V3": v3_cross_source(G),
        "V3b": v3b_stitch_fair_test(G),
        "V6": v6_null_models(G, n_reps=null_reps),
    }
