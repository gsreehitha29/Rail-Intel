"""Metrics infrastructure -- the API the four Phase 4 modules call into.

Three rules, all consequences of docs/PHASE3_GRAPH_ROADMAP.md §2:

1. **No implicit weight.** Every function that can be weighted takes `weight` by
   name from railgraph.weights. There is no silent default of distance.
2. **Tidy output with the config attached.** Every function returns a DataFrame
   (or a dict for scalars) carrying the spec hash and the weight it used, so a
   result can never be separated from how it was produced.
3. **Approximation is reported, never hidden.** Sampled betweenness returns its
   sample size and, where an exact baseline is cached, its measured rank
   correlation against exact.

Caching is keyed on (spec_hash, function, weight, params) and stored as parquet
under experiments/cache/. Exact weighted betweenness on the giant component
takes ~9 minutes, so it is computed once per frozen graph and reused.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Iterable, Sequence

import networkx as nx
import numpy as np
import pandas as pd

from . import config as C
from . import weights as W

CACHE = C.EXPERIMENTS / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

EARTH_RADIUS_KM = 6371.0088


# --------------------------------------------------------------------------- #
# plumbing
# --------------------------------------------------------------------------- #

def _key(G: nx.Graph, fn: str, **params) -> str:
    blob = json.dumps(
        {"spec": G.graph.get("spec_hash", "unknown"), "fn": fn,
         "n": G.number_of_nodes(), "m": G.number_of_edges(), "params": params},
        sort_keys=True, default=str).encode()
    return f"{fn}-{hashlib.sha256(blob).hexdigest()[:16]}"


def _cached(G: nx.Graph, fn: str, build, *, use_cache: bool = True, **params):
    path = CACHE / f"{_key(G, fn, **params)}.parquet"
    if use_cache and path.exists():
        return pd.read_parquet(path)
    out = build()
    if use_cache:
        try:
            out.to_parquet(path, index=False)
        except Exception:
            pass    # a cache miss is never a failure
    return out


def giant(G: nx.Graph) -> nx.Graph:
    """The largest connected component, as a copy."""
    if G.number_of_nodes() == 0:
        return G.copy()
    return G.subgraph(max(nx.connected_components(G), key=len)).copy()


def _wfun(G: nx.Graph, weight: str):
    """networkx takes either an attribute name or a callable; ours are callables."""
    if weight == "unit":
        return None                      # networkx fast path for unweighted
    return W.get(weight)


def _stamp(df: pd.DataFrame, G: nx.Graph, weight: str | None = None) -> pd.DataFrame:
    df = df.copy()
    df["spec_hash"] = G.graph.get("spec_hash", "unknown")
    df["dataset_version"] = G.graph.get("dataset_version", C.DATASET_VERSION)
    if weight is not None:
        df["weight"] = weight
    return df


# --------------------------------------------------------------------------- #
# local metrics
# --------------------------------------------------------------------------- #

def node_basics(G: nx.Graph) -> pd.DataFrame:
    """Degree, service strength, clustering, component membership. Cheap."""
    comp_id = {}
    for i, comp in enumerate(sorted(nx.connected_components(G), key=len, reverse=True)):
        for n in comp:
            comp_id[n] = i
    clust = nx.clustering(G)
    strength_load = {n: float(sum(G.edges[n, v].get("service_load") or 0.0
                                  for v in G.neighbors(n))) for n in G}
    strength_km = {n: float(sum(G.edges[n, v]["length_km"] for v in G.neighbors(n)))
                   for n in G}
    rows = []
    for n, d in G.nodes(data=True):
        rows.append({
            "node_id": n,
            "node_type": d.get("node_type"),
            "node_name": d.get("node_name"),
            "zone_code": d.get("zone_code"),
            "zone_source": d.get("zone_source"),
            "state": d.get("state"),
            "longitude": d.get("longitude"),
            "latitude": d.get("latitude"),
            "degree": G.degree(n),
            "strength_service_load": strength_load[n],
            "strength_km": strength_km[n],
            "clustering": clust[n],
            "component_id": comp_id[n],
            "in_giant": comp_id[n] == 0,
        })
    return _stamp(pd.DataFrame(rows), G)


# --------------------------------------------------------------------------- #
# centrality
# --------------------------------------------------------------------------- #

def betweenness(G: nx.Graph, weight: str = "length_km", *, k: int | None = None,
                seed: int = 42, use_cache: bool = True) -> pd.DataFrame:
    """Node betweenness. `k=None` is exact; an int samples k pivot nodes.

    Exact on the 9,058-node giant component costs ~9 minutes per weight, so the
    frozen default graph caches an exact run and sweep cells use k=500..1000.
    The returned frame always records which was used.
    """
    def build():
        t = time.time()
        bc = nx.betweenness_centrality(G, k=k, weight=_wfun(G, weight), seed=seed,
                                       normalized=True)
        df = pd.DataFrame({"node_id": list(bc), "betweenness": list(bc.values())})
        df["exact"] = k is None
        df["sample_k"] = -1 if k is None else k
        df["secs"] = round(time.time() - t, 2)
        return df
    return _stamp(_cached(G, "betweenness", build, use_cache=use_cache,
                          weight=weight, k=k, seed=seed), G, weight)


def edge_betweenness(G: nx.Graph, weight: str = "length_km", *, k: int | None = None,
                     seed: int = 42, use_cache: bool = True) -> pd.DataFrame:
    """Edge betweenness -- the corridor-criticality measure for Module 1."""
    def build():
        eb = nx.edge_betweenness_centrality(G, k=k, weight=_wfun(G, weight), seed=seed)
        rows = [{"from_node": min(u, v), "to_node": max(u, v),
                 "edge_betweenness": val,
                 "length_km": G.edges[u, v]["length_km"],
                 "service_load": G.edges[u, v].get("service_load"),
                 "corridor_id": G.edges[u, v].get("corridor_id"),
                 "any_stitch": bool(G.edges[u, v].get("any_stitch"))}
                for (u, v), val in eb.items()]
        df = pd.DataFrame(rows)
        df["exact"] = k is None
        df["sample_k"] = -1 if k is None else k
        return df
    return _stamp(_cached(G, "edge_betweenness", build, use_cache=use_cache,
                          weight=weight, k=k, seed=seed), G, weight)


def closeness(G: nx.Graph, weight: str = "length_km", *,
              use_cache: bool = True) -> pd.DataFrame:
    def build():
        cc = nx.closeness_centrality(G, distance=None if weight == "unit" else "length_km")
        return pd.DataFrame({"node_id": list(cc), "closeness": list(cc.values())})
    return _stamp(_cached(G, "closeness", build, use_cache=use_cache, weight=weight),
                  G, weight)


def pagerank(G: nx.Graph, weight: str = "service_load", *, alpha: float = 0.85,
             use_cache: bool = True) -> pd.DataFrame:
    """PageRank. Default weight is service load, not distance.

    On an undirected spatial graph PageRank is close to a degree ranking, so it
    is most informative weighted by traffic. D-010 note: using length as a
    PageRank weight is wrong in sign -- a longer edge is not a stronger link.
    """
    def build():
        attr = None
        if weight == "service_load":
            attr = "service_load"
            for _u, _v, d in G.edges(data=True):
                if d.get("service_load") is None or (isinstance(d.get("service_load"), float)
                                                     and np.isnan(d["service_load"])):
                    d["service_load"] = 0.0
        pr = nx.pagerank(G, alpha=alpha, weight=attr)
        return pd.DataFrame({"node_id": list(pr), "pagerank": list(pr.values())})
    return _stamp(_cached(G, "pagerank", build, use_cache=use_cache,
                          weight=weight, alpha=alpha), G, weight)


def betweenness_convergence(G: nx.Graph, weight: str = "length_km",
                            ks: Sequence[int] = (50, 100, 250, 500, 1000, 2000),
                            seed: int = 42, exact: pd.DataFrame | None = None,
                            top_k: int = 50) -> pd.DataFrame:
    """How large a betweenness sample is needed before the ranking stabilises?

    Roadmap §g03 requires that any sampled centrality reports its error rather
    than hiding it. This produces the convergence curve that justifies the
    sample size used in the sweep: Spearman and Kendall correlation against the
    exact run, plus top-k overlap, which is what Module 1 actually consumes.
    """
    from scipy.stats import kendalltau, spearmanr

    if exact is None:
        exact = betweenness(G, weight=weight, k=None)
    ex = exact.set_index("node_id")["betweenness"]
    ex_top = set(ex.nlargest(top_k).index)

    rows = []
    for k in ks:
        if k >= G.number_of_nodes():
            continue
        t = time.time()
        s = betweenness(G, weight=weight, k=k, seed=seed).set_index("node_id")["betweenness"]
        s = s.reindex(ex.index).fillna(0.0)
        rows.append({
            "sample_k": k,
            "secs": round(time.time() - t, 2),
            "spearman": float(spearmanr(ex.values, s.values).statistic),
            "kendall_tau": float(kendalltau(ex.values, s.values).statistic),
            f"top{top_k}_overlap": len(ex_top & set(s.nlargest(top_k).index)) / top_k,
            "max_abs_err": float(np.abs(ex.values - s.values).max()),
        })
    return _stamp(pd.DataFrame(rows), G, weight)


# --------------------------------------------------------------------------- #
# cuts and redundancy
# --------------------------------------------------------------------------- #

def cut_structure(G: nx.Graph) -> dict:
    """Articulation points, bridges, meshedness. The Module 3 primitives.

    Computed on the giant component, because articulation points and bridges are
    only defined per component and a global count silently mixes scales.
    """
    H = giant(G)
    aps = list(nx.articulation_points(H))
    brs = list(nx.bridges(H))
    n, m = H.number_of_nodes(), H.number_of_edges()
    mu = m - n + 1
    mu_max = 2 * n - 5 if n > 2 else 0          # planar maximum
    return {
        "spec_hash": G.graph.get("spec_hash"),
        "n_nodes": G.number_of_nodes(),
        "n_edges": G.number_of_edges(),
        "n_components": nx.number_connected_components(G),
        "giant_nodes": n,
        "giant_edges": m,
        "articulation_points": len(aps),
        "articulation_share": len(aps) / n if n else 0.0,
        "bridges": len(brs),
        "bridge_share": len(brs) / m if m else 0.0,
        "independent_cycles": mu,
        "meshedness": mu / mu_max if mu_max > 0 else 0.0,
        "tree_likeness": 1.0 - (mu / m) if m else 0.0,
    }


def bridge_severance(G: nx.Graph, top: int = 25) -> pd.DataFrame:
    """For each bridge, how many nodes are stranded if it is cut.

    This is what turns a topological bridge list into a ranked criticality
    statement, and with `service_load` it becomes the service-impact statement
    that D-015 makes possible ("this edge strands N trains").
    """
    H = giant(G)
    total = H.number_of_nodes()
    rows = []
    for u, v in nx.bridges(H):
        d = H.edges[u, v]
        H.remove_edge(u, v)
        comps = sorted((len(c) for c in nx.connected_components(H)), reverse=True)
        H.add_edge(u, v, **d)
        stranded = comps[1] if len(comps) > 1 else 0
        rows.append({
            "from_node": min(u, v), "to_node": max(u, v),
            "nodes_stranded": stranded,
            "stranded_share": stranded / total,
            "length_km": d["length_km"],
            "service_load": d.get("service_load"),
            "corridor_id": d.get("corridor_id"),
            "any_stitch": bool(d.get("any_stitch")),
            "n_tracks": d.get("n_tracks"),
        })
    df = pd.DataFrame(rows).sort_values("nodes_stranded", ascending=False)
    return _stamp(df.head(top) if top else df, G)


# --------------------------------------------------------------------------- #
# paths, circuity
# --------------------------------------------------------------------------- #

def _haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(lambda a: np.radians(np.asarray(a, dtype=float)),
                                 (lon1, lat1, lon2, lat2))
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def path_profile(G: nx.Graph, weight: str = "length_km", *, n_pairs: int = 4000,
                 seed: int = 42) -> dict:
    """Mean shortest path and circuity, from a random sample of node pairs.

    All-pairs on 9,058 nodes is 41M paths, so this samples. Circuity -- network
    distance over great-circle distance -- is the standard rail accessibility
    measure (Zhao et al. 2019) and needs no population data, which keeps
    Module 2 inside the blueprint's scope.
    """
    H = giant(G)
    nodes = [n for n, d in H.nodes(data=True)
             if d.get("longitude") is not None and not pd.isna(d.get("longitude"))]
    rng = np.random.default_rng(seed)
    wf = _wfun(H, weight)

    net, crow, hops = [], [], []
    srcs = rng.choice(len(nodes), size=min(n_pairs, len(nodes)), replace=False)
    for i in srcs:
        s = nodes[i]
        t = nodes[rng.integers(len(nodes))]
        if s == t:
            continue
        try:
            dist = nx.shortest_path_length(H, s, t, weight=wf)
            hop = nx.shortest_path_length(H, s, t)
        except nx.NetworkXNoPath:
            continue
        gc = float(_haversine(H.nodes[s]["longitude"], H.nodes[s]["latitude"],
                              H.nodes[t]["longitude"], H.nodes[t]["latitude"]))
        net.append(dist); crow.append(gc); hops.append(hop)

    net_a, crow_a = np.array(net), np.array(crow)
    out = {
        "spec_hash": G.graph.get("spec_hash"),
        "weight": weight,
        "n_pairs_sampled": len(net),
        "mean_path": float(net_a.mean()) if len(net_a) else np.nan,
        "median_path": float(np.median(net_a)) if len(net_a) else np.nan,
        "mean_hops": float(np.mean(hops)) if hops else np.nan,
    }
    # Circuity is network distance over great-circle distance, so it is only
    # defined when the weight IS distance. Under any other weight the ratio has
    # no units and is reported as missing rather than as a number.
    if weight != "length_km":
        out.update({"circuity_mean": np.nan, "circuity_median": np.nan,
                    "circuity_p90": np.nan, "circuity_n": 0})
        return out
    ok = crow_a > 1.0            # meaningless at separations below a kilometre
    circ = net_a[ok] / crow_a[ok]
    out.update({
        "circuity_mean": float(circ.mean()) if circ.size else np.nan,
        "circuity_median": float(np.median(circ)) if circ.size else np.nan,
        "circuity_p90": float(np.percentile(circ, 90)) if circ.size > 1 else np.nan,
        "circuity_n": int(circ.size),
    })
    return out


# --------------------------------------------------------------------------- #
# communities
# --------------------------------------------------------------------------- #

def communities(G: nx.Graph, method: str = "louvain", *, weight: str | None = None,
                seed: int = 42, resolution: float = 1.0) -> pd.DataFrame:
    """Community partition. `method` in {louvain, infomap, label_prop, greedy}.

    Roadmap §1.4: modularity maximisation has a known resolution limit and
    degenerate near-optima, so Module 1 must run at least two methodologically
    different algorithms -- Louvain (modularity) and Infomap (flow) -- and
    validate against `zone_code` as an independent label. Never cluster on zone.
    """
    H = giant(G)
    attr = None
    if weight == "service_load":
        attr = "service_load"
        for _u, _v, d in H.edges(data=True):
            v = d.get("service_load")
            d["service_load"] = 0.0 if v is None or (isinstance(v, float) and np.isnan(v)) else float(v)
    elif weight == "inverse_length":
        attr = "_w"
        for _u, _v, d in H.edges(data=True):
            d["_w"] = 1.0 / max(float(d["length_km"]), 0.05)

    if method == "louvain":
        parts = nx.community.louvain_communities(H, weight=attr, seed=seed,
                                                 resolution=resolution)
    elif method == "label_prop":
        parts = list(nx.community.asyn_lpa_communities(H, weight=attr, seed=seed))
    elif method == "greedy":
        parts = nx.community.greedy_modularity_communities(H, weight=attr,
                                                           resolution=resolution)
    elif method == "infomap":
        import infomap as _im
        idx = {n: i for i, n in enumerate(H.nodes)}
        rev = {i: n for n, i in idx.items()}
        im = _im.Infomap(silent=True, seed=seed, two_level=True)
        for u, v, d in H.edges(data=True):
            im.add_link(idx[u], idx[v], float(d.get(attr, 1.0)) if attr else 1.0)
        im.run()
        groups: dict[int, list] = {}
        for node in im.tree:
            if node.is_leaf:
                groups.setdefault(node.module_id, []).append(rev[node.node_id])
        parts = list(groups.values())
    else:
        raise ValueError(f"unknown method {method!r}")

    rows = []
    for cid, members in enumerate(sorted(parts, key=len, reverse=True)):
        for n in members:
            rows.append({"node_id": n, "community": cid,
                         "community_size": len(members)})
    df = pd.DataFrame(rows)
    df["method"] = method
    df["modularity"] = nx.community.modularity(H, parts, weight=attr,
                                               resolution=resolution)
    df["n_communities"] = len(parts)
    return _stamp(df, G, weight or "unit")


def community_vs_zone(G: nx.Graph, part: pd.DataFrame) -> dict:
    """Agreement between a detected partition and the railway-zone labels.

    Zone is an independent administrative label, not a construction input, so
    agreement is external corroboration that the detected structure is real.
    Restricted to nodes whose zone is *stated* rather than corridor-inferred --
    inferred zone is partly derived from the same corridors that made the edges,
    so including it would leak.
    """
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

    nb = node_basics(G)[["node_id", "zone_code", "zone_source"]]
    m = part.merge(nb, on="node_id", how="inner")
    stated = m[(m.zone_source == "station_master") & m.zone_code.notna()]
    allz = m[m.zone_code.notna()]

    def score(df):
        if len(df) < 10:
            return {"n": len(df), "nmi": np.nan, "ari": np.nan}
        return {"n": len(df),
                "nmi": float(normalized_mutual_info_score(df.zone_code, df.community)),
                "ari": float(adjusted_rand_score(df.zone_code, df.community))}

    return {
        "spec_hash": G.graph.get("spec_hash"),
        "method": part["method"].iloc[0] if len(part) else None,
        "n_communities": int(part["n_communities"].iloc[0]) if len(part) else 0,
        "modularity": float(part["modularity"].iloc[0]) if len(part) else np.nan,
        "stated_zone_only": score(stated),
        "all_zone_incl_inferred": score(allz),
    }


# --------------------------------------------------------------------------- #
# resilience
# --------------------------------------------------------------------------- #

def percolation(G: nx.Graph, strategy: str = "random", *, weight: str = "length_km",
                steps: int = 40, seed: int = 42, recompute: bool = False,
                sample_k: int = 500) -> pd.DataFrame:
    """Node-removal percolation curve, with the robustness measure R.

    Follows Bhatia et al. 2015 for the Indian case: the reported quantity is the
    State of Critical Functionality, SCF = (nodes in giant) / (initial nodes).
    R is the normalised area under that curve (Schneider et al.), which makes
    attack sequences comparable by one number instead of by eyeballing curves.

    `strategy` in {random, degree, betweenness, service_load}.
    `recompute=True` re-ranks after every removal batch (adaptive attack), which
    is stronger but costs a centrality run per step.
    """
    H = giant(G)
    n0 = H.number_of_nodes()
    rng = np.random.default_rng(seed)

    def rank(graph) -> list:
        if strategy == "random":
            order = list(graph.nodes)
            rng.shuffle(order)
            return order
        if strategy == "degree":
            return [n for n, _ in sorted(graph.degree, key=lambda x: -x[1])]
        if strategy == "service_load":
            s = {n: sum(graph.edges[n, v].get("service_load") or 0.0
                        for v in graph.neighbors(n)) for n in graph}
            return sorted(s, key=lambda n: -s[n])
        if strategy == "betweenness":
            k = None if graph.number_of_nodes() <= 1200 else min(sample_k, graph.number_of_nodes() - 1)
            bc = nx.betweenness_centrality(graph, k=k, weight=_wfun(graph, weight), seed=seed)
            return sorted(bc, key=lambda n: -bc[n])
        raise ValueError(f"unknown strategy {strategy!r}")

    work = H.copy()
    order = rank(work)
    per_step = max(1, n0 // steps)
    rows = [{"removed": 0, "removed_frac": 0.0, "giant_nodes": n0, "scf": 1.0}]
    removed = 0
    while removed < n0 - 1 and work.number_of_nodes() > 1:
        batch = order[:per_step] if not recompute else rank(work)[:per_step]
        batch = [n for n in batch if n in work][:per_step]
        if not batch:
            break
        work.remove_nodes_from(batch)
        removed += len(batch)
        if not recompute:
            order = order[len(batch):]
        comps = list(nx.connected_components(work)) if work.number_of_nodes() else []
        g = max((len(c) for c in comps), default=0)
        rows.append({"removed": removed, "removed_frac": removed / n0,
                     "giant_nodes": g, "scf": g / n0})

    df = pd.DataFrame(rows)
    df["strategy"] = strategy
    df["adaptive"] = recompute
    # R = normalised area under the SCF curve (Schneider et al.)
    df["R"] = float(np.trapezoid(df.scf.values, df.removed_frac.values))
    return _stamp(df, G, weight)


# --------------------------------------------------------------------------- #
# service layer
# --------------------------------------------------------------------------- #

def service_edges() -> pd.DataFrame:
    """The shipped service layer (L2): frequency and observed run-time per pair."""
    return pd.read_csv(C.DATASET / "service_edges.csv")


def service_graph(G: nx.Graph, *, weight: str = "runtime_min_median") -> nx.Graph:
    """Service graph on the physical node set, weighted by observed run-time.

    D-009: the service layer keeps direction in the source, but for accessibility
    the undirected projection is what Module 2 wants. Only pairs whose endpoints
    both exist as physical nodes are kept, and that fraction is recorded on the
    graph so a result can state its coverage.
    """
    se = service_edges()
    keep = se[se.from_station.isin(G) & se.to_station.isin(G)]
    S = nx.Graph()
    S.add_nodes_from(G.nodes(data=True))
    for r in keep.itertuples():
        w = getattr(r, weight, np.nan)
        if pd.isna(w):
            continue
        if S.has_edge(r.from_station, r.to_station):
            if w < S.edges[r.from_station, r.to_station]["minutes"]:
                S.edges[r.from_station, r.to_station]["minutes"] = float(w)
            continue
        S.add_edge(r.from_station, r.to_station, minutes=float(w),
                   n_trains=int(r.n_trains), physical_hops=r.physical_hops)
    S.graph.update({"spec_hash": G.graph.get("spec_hash"),
                    "service_pairs_total": len(se),
                    "service_pairs_used": S.number_of_edges(),
                    "coverage": S.number_of_edges() / len(se) if len(se) else 0.0})
    return S


def space_p(min_trains: int = 1, *, max_rows: int | None = None) -> pd.DataFrame:
    """The transfer (space-P) graph, derived on demand.

    D-014: materialising this would be roughly 16 million rows, so it is never
    shipped. This builds it from the service layer for a bounded query rather
    than in full -- callers wanting transfer-count accessibility should build it
    per origin, not globally.
    """
    raise NotImplementedError(
        "space_p is derived per-origin by Module 2 from cleaned_schedules.csv; "
        "see docs/GRAPH_HANDOFF_V2.md §4.8 (D-014). A global materialisation is "
        "~16M rows and is deliberately not provided here.")


# --------------------------------------------------------------------------- #
# one-call summary
# --------------------------------------------------------------------------- #

def summarise(G: nx.Graph, *, weight: str = "length_km", bc_k: int | None = 500,
              n_pairs: int = 2000) -> dict:
    """The scalar battery one sweep cell needs. Fast enough to run ~30 times."""
    out = cut_structure(G)
    out.update({f"path_{k}": v for k, v in
                path_profile(G, weight=weight, n_pairs=n_pairs).items()
                if k not in ("spec_hash", "weight")})
    bc = betweenness(G, weight=weight, k=bc_k, use_cache=True)
    out["bc_top50"] = list(bc.nlargest(50, "betweenness").node_id)
    out["bc_sample_k"] = bc_k if bc_k else -1
    deg = np.array([d for _, d in G.degree()])
    out.update({"degree_mean": float(deg.mean()), "degree_max": int(deg.max()),
                "degree2_share": float((deg == 2).mean()),
                "route_km": float(sum(d["length_km"] for _, _, d in G.edges(data=True))),
                "weight": weight})
    return out
