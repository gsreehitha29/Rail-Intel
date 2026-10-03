"""Build the Rail-Intell physical graph, with every construction choice as a
parameter.

Two paths:

  shipped  -- read graph_dataset/{nodes,edges}.csv directly. Fast, and the
              authoritative default. Used whenever the spec does not change any
              construction parameter.
  rebuild  -- re-derive nodes and edges from station_sequences + nodes_junctions
              + corridors under a different spec. This is what makes the g05
              sensitivity sweep possible.

The rebuild path is a faithful reimplementation of s09_graph_dataset.py's
build_nodes / build_edges / finalise_edges, *not* a call into it: the shipped
pipeline is left untouched (project principle -- do not modify Phase 2 code to
serve Phase 3). The safety net for that choice is verify_rebuild_equivalence(),
which rebuilds at the shipped default and asserts the result is identical to
edges.csv. If the reimplementation ever drifts, that test fails loudly. See
D-023.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import networkx as nx

from . import config as C
from .config import BuildSpec

EARTH_RADIUS_KM = 6371.0088  # matches 02_graph_inputs/pipeline/config.py


def haversine_km(lon1, lat1, lon2, lat2):
    """Vectorised great-circle distance in km (WGS84 sphere).

    Identical to the pipeline's implementation, including the earth radius.
    """
    lon1, lat1, lon2, lat2 = map(
        lambda a: np.radians(np.asarray(a, dtype=float)), (lon1, lat1, lon2, lat2)
    )
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


# --------------------------------------------------------------------------- #
# sources
# --------------------------------------------------------------------------- #

def shipped_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """The authoritative shipped node and edge tables."""
    return (pd.read_csv(C.DATASET / "nodes.csv"),
            pd.read_csv(C.DATASET / "edges.csv"))


def _rebuild_sources() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Inputs the rebuild path needs.

    Note this spans both Phase 2 output folders: the dataset for sequences,
    corridors and the station master, and graph_inputs for the junction
    identity table, which the dataset does not re-export.
    """
    seq = pd.read_csv(C.DATASET / "station_sequences.csv")
    corr = pd.read_csv(C.DATASET / "corridors.csv")
    stations = pd.read_csv(C.DATASET / "stations.csv")
    junctions = pd.read_csv(C.INPUTS / "nodes_junctions.csv")
    return seq, corr, stations, junctions


# --------------------------------------------------------------------------- #
# rebuild (parameterised reimplementation of s09)
# --------------------------------------------------------------------------- #

def _junction_map(junctions: pd.DataFrame, spec: BuildSpec) -> tuple[dict, list]:
    """canonical junction name -> node id, plus the rows that stayed junctions.

    A junction resolves to its station code when a confident match exists,
    otherwise to a typed JN:: node (D-001). Under node_model='station_only' the
    unmatched junctions get no node at all, which is what fragments the graph.
    """
    conf = junctions.match_confidence.isin(spec.match_conf) & junctions.station_code.notna()
    jmap: dict[str, str | None] = {}
    jrows = []
    for r in junctions.itertuples():
        name = r.canonical_junction_name
        if name in jmap:
            continue
        if conf.loc[r.Index]:
            jmap[name] = str(r.station_code).strip()
        elif spec.node_model == "station_only":
            jmap[name] = None
        else:
            jmap[name] = "JN::" + str(name)
            jrows.append(r)
    return jmap, jrows


def _build_edge_records(seq, corr, jmap, spec: BuildSpec) -> pd.DataFrame:
    """Corridor chains, optionally stitched at their junction endpoints."""
    placed = seq[seq.offset_km <= spec.offset_max_km].sort_values(
        ["corridor_id", "measure_km"])
    recs = []
    for cid, g in placed.groupby("corridor_id", sort=True):
        stn = list(g.station_code)
        meas = list(g.measure_km)
        offs = list(g.offset_km)
        if spec.stitch_junctions:
            a = jmap.get(g.corridor_a.iloc[0])
            b = jmap.get(g.corridor_b.iloc[0])
            codes = [a] + stn + [b]
            meas = [np.nan] + meas + [np.nan]
            offs = [np.nan] + offs + [np.nan]
        else:
            codes = stn
        # drop empties and collapse immediate repeats
        keep = [i for i, c in enumerate(codes) if c and (i == 0 or c != codes[i - 1])]
        codes = [codes[i] for i in keep]
        meas = [meas[i] for i in keep]
        offs = [offs[i] for i in keep]
        for i in range(len(codes) - 1):
            u, v = codes[i], codes[i + 1]
            if u == v:
                continue
            d = meas[i + 1] - meas[i]
            recs.append({"corridor_id": cid, "u": u, "v": v, "length_km": d,
                         "is_stitch": bool(np.isnan(d)),
                         "offset_u": offs[i], "offset_v": offs[i + 1]})

    if spec.stitch_junctions:
        # corridors with no placed station still connect their two junctions
        have = set(placed.corridor_id)
        for r in corr.itertuples():
            if r.corridor_id in have:
                continue
            a, b = jmap.get(r.corridor_a), jmap.get(r.corridor_b)
            if a and b and a != b:
                recs.append({"corridor_id": r.corridor_id, "u": a, "v": b,
                             "length_km": r.geodesic_length_km, "is_stitch": True,
                             "offset_u": np.nan, "offset_v": np.nan})

    e = pd.DataFrame(recs)
    return e[e.u != e.v].copy()


def _finalise(e: pd.DataFrame, corr: pd.DataFrame, pos: pd.DataFrame,
              spec: BuildSpec) -> pd.DataFrame:
    """Collapse to a simple undirected edge list and attach corridor attributes."""
    need = e.length_km.isna()
    if need.any():
        lu = pos.reindex(e.loc[need, "u"]).to_numpy()
        lv = pos.reindex(e.loc[need, "v"]).to_numpy()
        e.loc[need, "length_km"] = haversine_km(lu[:, 0], lu[:, 1], lv[:, 0], lv[:, 1])
    e["length_km"] = e.length_km.astype(float)
    e["key"] = [tuple(sorted(p)) for p in zip(e.u, e.v)]

    length_agg = {"shortest": "min", "mean": "mean", "multigraph": "min"}[spec.parallel_policy]
    agg = e.groupby("key").agg(
        length_km=("length_km", length_agg),
        length_km_max=("length_km", "max"),
        length_km_min=("length_km", "min"),
        n_parallel_corridors=("corridor_id", "nunique"),
        corridor_id=("corridor_id", "first"),
        any_stitch=("is_stitch", "any"),
        offset_max=("offset_u", "max"),
    ).reset_index()
    agg["from_node"] = [k[0] for k in agg.key]
    agg["to_node"] = [k[1] for k in agg.key]
    agg = agg.drop(columns=["key"])

    cmap = corr.set_index("corridor_id")
    a = cmap.reindex(agg.corridor_id)
    for src, dst in [("gauge_code", "gauge_code"), ("gauge_name", "gauge_name"),
                     ("zone_code", "zone_code"), ("zone_name", "zone_name"),
                     ("speed_kmph", "speed_kmph"), ("no_of_lanes", "n_tracks"),
                     ("bridge_present", "bridge_present"),
                     ("tunnel_present", "tunnel_present"),
                     ("reconstruction_status", "reconstruction_status"),
                     ("attr_complete", "attr_complete"), ("recon_clean", "recon_clean"),
                     ("core_v2", "core_v2"), ("core_v4", "core_v4")]:
        agg[dst] = a[src].to_numpy()

    # F-002 / D-021: is_colocated records that the raw length was BELOW the
    # floor, not that the stations are close. Preserved as-is for fidelity with
    # the shipped column; length_below_floor is the unambiguous name and
    # is_short_edge is the question most callers actually mean.
    agg["is_colocated"] = agg.length_km < spec.min_edge_km
    agg["length_below_floor"] = agg.is_colocated
    agg["is_short_edge"] = agg.length_km < 0.1
    agg["length_km"] = agg.length_km.clip(lower=spec.min_edge_km)
    agg["parallel_differs"] = (agg.length_km_max - agg.length_km_min).abs() > 1.0
    agg = agg.sort_values(["from_node", "to_node"]).reset_index(drop=True)
    agg["edge_id"] = ["E" + str(i).zfill(6) for i in range(1, len(agg) + 1)]
    agg["dataset_version"] = C.DATASET_VERSION
    return agg


def _junction_only_tables(corr: pd.DataFrame, junctions: pd.DataFrame):
    """The 2,029-node corridor-endpoint graph (D-001 'junction-only' option)."""
    j = junctions.drop_duplicates("canonical_junction_name")
    nodes = pd.DataFrame({
        "node_id": "JN::" + j.canonical_junction_name.astype(str),
        "node_type": "operational_junction",
        "station_code": j.station_code.values,
        "node_name": j.canonical_junction_name.values,
        "longitude": j.longitude.values, "latitude": j.latitude.values,
        "zone_code": None, "zone_name": None, "state": None, "in_scope": True,
        "junction_class": j.junction_class.values,
        "match_confidence": j.match_confidence.values,
        "dataset_version": C.DATASET_VERSION,
    })
    c = corr[corr.corridor_a != corr.corridor_b]
    edges = pd.DataFrame({
        "from_node": "JN::" + c.corridor_a.astype(str),
        "to_node": "JN::" + c.corridor_b.astype(str),
        "length_km": c.geodesic_length_km.values,
        "corridor_id": c.corridor_id.values,
        "gauge_code": c.gauge_code.values, "zone_code": c.zone_code.values,
        "speed_kmph": c.speed_kmph.values, "n_tracks": c.no_of_lanes.values,
        "any_stitch": False, "core_v2": c.core_v2.values, "core_v4": c.core_v4.values,
    })
    edges["key"] = [tuple(sorted(p)) for p in zip(edges.from_node, edges.to_node)]
    edges = edges.drop_duplicates("key").drop(columns=["key"]).reset_index(drop=True)
    edges["edge_id"] = ["E" + str(i).zfill(6) for i in range(1, len(edges) + 1)]
    edges["is_colocated"] = False
    edges["parallel_differs"] = False
    edges["n_parallel_corridors"] = 1
    return nodes, edges


def rebuild_tables(spec: BuildSpec) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Re-derive node and edge tables under `spec`."""
    seq, corr, stations, junctions = _rebuild_sources()

    if spec.node_model == "junction_only":
        return _junction_only_tables(corr, junctions)

    jmap, jrows = _junction_map(junctions, spec)
    placed = seq[seq.offset_km <= spec.offset_max_km]
    ncorr = placed.groupby("station_code").corridor_id.nunique()
    smeta = stations.set_index("station_code")

    station_codes = set(placed.station_code) | {
        v for v in jmap.values() if v and not v.startswith("JN::")}
    rows = []
    for code in sorted(station_codes):
        m = smeta.loc[code] if code in smeta.index else None
        rows.append({
            "node_id": code, "node_type": "station", "station_code": code,
            "node_name": m.station_name if m is not None else None,
            "longitude": m.longitude if m is not None else np.nan,
            "latitude": m.latitude if m is not None else np.nan,
            "zone_code": m.zone_code if m is not None else None,
            "zone_name": m.zone_name if m is not None else None,
            "state": m.state if m is not None else None,
            "in_scope": bool(m.in_scope) if m is not None else True,
            "junction_class": None, "match_confidence": None,
            "spatial_gap_km": np.nan,
            "n_corridors": int(ncorr.get(code, 0)),
            "coordinate_shared": bool(m.coordinate_shared) if m is not None else False,
        })
    for r in jrows:
        rows.append({
            "node_id": "JN::" + str(r.canonical_junction_name),
            "node_type": "operational_junction", "station_code": None,
            "node_name": r.canonical_junction_name,
            "longitude": r.longitude, "latitude": r.latitude,
            "zone_code": None, "zone_name": None, "state": None, "in_scope": True,
            "junction_class": r.junction_class,
            "match_confidence": r.match_confidence,
            "spatial_gap_km": r.spatial_gap_km,
            "n_corridors": int(r.corridor_degree) if pd.notna(r.corridor_degree) else 0,
            "coordinate_shared": False,
        })
    nodes = pd.DataFrame(rows).drop_duplicates("node_id").reset_index(drop=True)
    nodes["dataset_version"] = C.DATASET_VERSION

    pos = nodes.set_index("node_id")[["longitude", "latitude"]]
    e = _build_edge_records(seq, corr, jmap, spec)
    edges = _finalise(e, corr, pos, spec)

    # drop nodes no edge touches, then recompute the structural columns
    touched = set(edges.from_node) | set(edges.to_node)
    nodes = nodes[nodes.node_id.isin(touched)].reset_index(drop=True)
    return nodes, edges


# --------------------------------------------------------------------------- #
# graph assembly and representation views
# --------------------------------------------------------------------------- #

_VIEW_COL = {"topology": None, "attr_complete": "attr_complete",
             "core_v2": "core_v2", "core_v4": "core_v4"}


def _apply_view(edges: pd.DataFrame, spec: BuildSpec) -> pd.DataFrame:
    col = _VIEW_COL[spec.view]
    if col is None:
        return edges
    if col not in edges.columns:
        raise KeyError(f"view {spec.view!r} needs column {col!r}")
    flag = edges[col]
    if flag.dtype == object:
        flag = flag.astype(str).str.lower().isin({"true", "1", "yes"})
    return edges[flag.fillna(False).astype(bool)]


def _dissolve_degree2(G: nx.Graph) -> nx.Graph:
    """Contract degree-2 operational junctions by path contraction (D-002/D-017).

    Merges the two incident edges and sums their lengths -- the standard
    degree-2 smoothing of primal street-network graphs (Boeing 2025, Porta et
    al.). Only nodes that are operational junctions AND degree 2 are touched, so
    no station identity is ever destroyed. Where the two neighbours are already
    adjacent, contraction would create a parallel edge; the shorter is kept and
    the fact recorded on the surviving edge.
    """
    H = G.copy()
    targets = [n for n, d in H.nodes(data=True)
               if d.get("node_type") == "operational_junction" and H.degree(n) == 2]
    dissolved = 0
    for n in targets:
        if n not in H or H.degree(n) != 2:
            continue
        (a, ea), (b, eb) = [(nb, H.edges[n, nb]) for nb in H.neighbors(n)]
        if a == b:
            continue
        new_len = float(ea["length_km"]) + float(eb["length_km"])
        attrs = dict(ea)
        attrs["length_km"] = new_len
        attrs["dissolved_via"] = n
        attrs["any_stitch"] = bool(ea.get("any_stitch")) or bool(eb.get("any_stitch"))
        if H.has_edge(a, b):
            if new_len < float(H.edges[a, b]["length_km"]):
                H.edges[a, b].update(attrs)
            H.edges[a, b]["n_parallel_corridors"] = \
                int(H.edges[a, b].get("n_parallel_corridors", 1)) + 1
        else:
            H.add_edge(a, b, **attrs)
        H.remove_node(n)
        dissolved += 1
    H.graph["dissolved_degree2"] = dissolved
    return H


def _prune_degree1_junctions(G: nx.Graph) -> nx.Graph:
    """Drop degree-1 operational junctions (line ends carrying no station)."""
    H = G.copy()
    victims = [n for n, d in H.nodes(data=True)
               if d.get("node_type") == "operational_junction" and H.degree(n) == 1]
    H.remove_nodes_from(victims)
    H.graph["pruned_degree1"] = len(victims)
    return H


def _merge_colocated(G: nx.Graph, threshold_km: float = 0.05) -> nx.Graph:
    """Merge station groups joined by sub-threshold edges into one node each.

    Boeing 2025 argues for topological rather than geometric consolidation, and
    this is topological by construction: it merges only across an existing edge,
    so stations that are spatially close but not connected are never merged.

    Implemented as one pass -- take the connected components of the short-edge
    subgraph and relabel each to a deterministic survivor -- rather than
    iterated pairwise contraction. Pairwise contraction is O(n) graph copies and
    also order-dependent on chains of three or more co-located stations; the
    component approach is neither.
    """
    short = [(u, v) for u, v, d in G.edges(data=True)
             if bool(d.get("length_below_floor"))
             or (bool(d.get("is_colocated")) and float(d["length_km"]) <= threshold_km)]
    if not short:
        H = G.copy()
        H.graph["merged_colocated"] = 0
        return H

    S = nx.Graph()
    S.add_edges_from(short)
    mapping, groups = {}, 0
    for comp in nx.connected_components(S):
        if len(comp) < 2:
            continue
        survivor = sorted(comp)[0]           # deterministic
        for n in comp:
            mapping[n] = survivor
        groups += 1

    H = nx.relabel_nodes(G, mapping, copy=True)
    H.remove_edges_from(nx.selfloop_edges(H))
    # record what was folded into each survivor, for provenance
    folded: dict[str, list] = {}
    for src, dst in mapping.items():
        if src != dst:
            folded.setdefault(dst, []).append(src)
    for dst, members in folded.items():
        if dst in H:
            H.nodes[dst]["merged_nodes"] = sorted(members)
    H.graph["merged_colocated"] = groups
    H.graph["merged_nodes_removed"] = sum(len(v) for v in folded.values())
    return H


def _gauge_constrain(G: nx.Graph) -> nx.Graph:
    """Keep only the dominant-gauge subgraph (D-011).

    Gauge is a traversability constraint, so a shortest path crossing a gauge
    break is a modelling error. This is an opt-in routing mode, never the
    default: 60 non-Broad-Gauge corridors are real track and dropping them from
    the stored graph would be the silent-deletion failure D-013 warns about.
    """
    H = G.copy()
    bad = [(u, v) for u, v, d in H.edges(data=True)
           if d.get("gauge_code") not in (None, "BG") and pd.notna(d.get("gauge_code"))]
    H.remove_edges_from(bad)
    H.remove_nodes_from([n for n in list(H.nodes) if H.degree(n) == 0])
    H.graph["gauge_removed_edges"] = len(bad)
    return H


_NODE_ATTRS = ("node_type", "station_code", "node_name", "longitude", "latitude",
               "zone_code", "zone_name", "zone_source", "state", "in_scope",
               "junction_class", "match_confidence", "spatial_gap_km",
               "n_corridors", "coordinate_shared", "is_dissolvable")
_EDGE_ATTRS = ("edge_id", "length_km", "corridor_id", "gauge_code", "gauge_name",
               "zone_code", "zone_name", "speed_kmph", "n_tracks",
               "bridge_present", "tunnel_present", "n_parallel_corridors",
               "parallel_differs", "is_colocated", "length_below_floor",
               "is_short_edge", "any_stitch", "reconstruction_status",
               "attr_complete", "recon_clean", "core_v2", "core_v4",
               "service_direct", "service_load")


def to_graph(nodes: pd.DataFrame, edges: pd.DataFrame, spec: BuildSpec) -> nx.Graph:
    """Assemble a NetworkX graph and apply the representation parameters."""
    edges = _apply_view(edges, spec)
    G = nx.Graph()
    ncols = [c for c in _NODE_ATTRS if c in nodes.columns]
    for r in nodes.itertuples(index=False):
        d = {c: getattr(r, c) for c in ncols}
        G.add_node(r.node_id, **d)
    ecols = [c for c in _EDGE_ATTRS if c in edges.columns]
    for r in edges.itertuples(index=False):
        d = {c: getattr(r, c) for c in ecols}
        G.add_edge(r.from_node, r.to_node, **d)

    # a view can orphan nodes; drop them before the structural steps
    G.remove_nodes_from([n for n in list(G.nodes) if G.degree(n) == 0])

    if spec.merge_colocated:
        G = _merge_colocated(G)
    if spec.prune_degree1:
        G = _prune_degree1_junctions(G)
    if spec.dissolve_degree2:
        G = _dissolve_degree2(G)
    if spec.gauge_constrained:
        G = _gauge_constrain(G)
    if spec.giant_only:
        giant = max(nx.connected_components(G), key=len)
        G = G.subgraph(giant).copy()

    G.graph.update({"spec": spec.to_dict(), "spec_hash": spec.hash,
                    "dataset_version": C.DATASET_VERSION})
    return G


# --------------------------------------------------------------------------- #
# invariants
# --------------------------------------------------------------------------- #

class InvariantError(AssertionError):
    """Raised when a graph built at the shipped default does not match it."""


def measure(G: nx.Graph) -> dict:
    """The structural summary used for invariant checks and sweep cells."""
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    giant = G.subgraph(comps[0]) if comps else G
    deg = np.array([d for _, d in G.degree()]) if G.number_of_nodes() else np.array([0])
    types = nx.get_node_attributes(G, "node_type")
    stitch = nx.get_edge_attributes(G, "any_stitch")
    return {
        "n_nodes": G.number_of_nodes(),
        "n_edges": G.number_of_edges(),
        "n_components": len(comps),
        "giant_nodes": giant.number_of_nodes(),
        "giant_edges": giant.number_of_edges(),
        "giant_share": giant.number_of_nodes() / G.number_of_nodes() if G.number_of_nodes() else 0.0,
        "articulation_points": len(list(nx.articulation_points(giant))),
        "bridges": len(list(nx.bridges(giant))),
        "independent_cycles": giant.number_of_edges() - giant.number_of_nodes() + 1,
        "degree_mean": float(deg.mean()),
        "degree_max": int(deg.max()),
        "degree2_share": float((deg == 2).mean()),
        "route_km": float(sum(d["length_km"] for _, _, d in G.edges(data=True))),
        "n_station_nodes": sum(1 for v in types.values() if v == "station"),
        "n_junction_nodes": sum(1 for v in types.values() if v == "operational_junction"),
        "n_stitched_edges": int(sum(1 for v in stitch.values() if bool(v))),
    }


def assert_invariants(G: nx.Graph, strict: bool = True) -> dict:
    """Check a default-spec graph against the shipped invariants."""
    m = measure(G)
    failures = []
    for k, want in C.SHIPPED_INVARIANTS.items():
        if k == "n_dissolvable":
            got = sum(1 for n, d in G.nodes(data=True)
                      if d.get("node_type") == "operational_junction" and G.degree(n) == 2)
        else:
            got = m.get(k)
        if got is None:
            continue
        ok = abs(got - want) <= 1.0 if k == "route_km" else got == want
        if not ok:
            failures.append(f"  {k}: expected {want:,} got {got:,}")
    if failures and strict:
        raise InvariantError(
            "graph does not match the shipped dataset:\n" + "\n".join(failures))
    m["invariant_failures"] = failures
    return m


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #

def load_graph(spec: BuildSpec | None = None, *, strict: bool = True) -> nx.Graph:
    """Build the graph described by `spec` (shipped default when None).

    At the shipped default the graph is checked against SHIPPED_INVARIANTS and
    raises InvariantError on any mismatch -- the g01 contract is that a silent
    disagreement with graph_dataset/ is impossible.
    """
    spec = spec or BuildSpec(label="shipped default")
    if spec.needs_rebuild:
        nodes, edges = rebuild_tables(spec)
    else:
        nodes, edges = shipped_tables()
    G = to_graph(nodes, edges, spec)
    if spec.is_shipped_default:
        assert_invariants(G, strict=strict)
    return G


def verify_rebuild_equivalence() -> dict:
    """Rebuild at the shipped default and compare against edges.csv.

    The safety net for reimplementing s09 rather than calling it (D-023). Both
    tables are reduced to a canonical (from, to, rounded length) form, because
    edge_id ordering is an artifact of row order, not of topology.
    """
    _, shipped = shipped_tables()
    nodes_r, rebuilt = rebuild_tables(BuildSpec(offset_max_km=1.5000001))  # force rebuild path

    def canon(df):
        k = pd.DataFrame({
            "a": np.minimum(df.from_node, df.to_node),
            "b": np.maximum(df.from_node, df.to_node),
            "km": df.length_km.round(6),
        })
        return k.sort_values(["a", "b"]).reset_index(drop=True)

    cs, cr = canon(shipped), canon(rebuilt)
    pairs_s = set(zip(cs.a, cs.b))
    pairs_r = set(zip(cr.a, cr.b))
    merged = cs.merge(cr, on=["a", "b"], how="inner", suffixes=("_s", "_r"))
    len_mismatch = merged[(merged.km_s - merged.km_r).abs() > 1e-6]
    return {
        "shipped_edges": len(cs),
        "rebuilt_edges": len(cr),
        "identical_pair_set": pairs_s == pairs_r,
        "only_in_shipped": sorted(pairs_s - pairs_r)[:20],
        "only_in_rebuilt": sorted(pairs_r - pairs_s)[:20],
        "n_only_in_shipped": len(pairs_s - pairs_r),
        "n_only_in_rebuilt": len(pairs_r - pairs_s),
        "length_mismatches": len(len_mismatch),
        "worst_length_delta": float((merged.km_s - merged.km_r).abs().max()) if len(merged) else 0.0,
        "equivalent": bool(pairs_s == pairs_r and len(len_mismatch) == 0),
    }
