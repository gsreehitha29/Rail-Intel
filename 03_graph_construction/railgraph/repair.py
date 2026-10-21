"""Graph v1.2 topology repair: remove edges that are provably the same track twice.

Background (`F-051`, `F-052`). G-01 -- "42.9% of declared stations never
matched" -- was described as a station-matching recall failure. Measured
against every in-repo station source it is not: 0 unplaced master stations lie
within 1.5 km of any deficit corridor's spine, 116 within 1.5 km of its raw
segment geometry (1.1% of the deficit), and none of the 75 master stations
missing from the graph lies on trusted track. The deficit is stations absent
from the data, which no code here can add.

What the gap *did* cause is fixable: stitching (`D-005`) joins a corridor's two
named ends whenever it has nothing better, and it does so even when (a) the
same corridor's station chain already connects them, or (b) the corridor has
almost no digitised track at all -- `C01457` "Bengaluru-Mysuru" has 1.36 km of
geometry for a 125.6 km edge, while the real line is in the graph as a 24-hop
chain via Mandya. Such an edge is a straight-line duplicate of a route that is
already represented, and in a path computation it is a shortcut.

An edge is removed only when BOTH hold:

  1. it is not supported by its own track: either a same-corridor station chain
     already joins its endpoints (kind `same_corridor_chain`), or its corridor
     has less than `support_max` of the edge's length in digitised geometry
     (kind `unsupported_geometry`); and
  2. an equivalent route already exists without it: the shortest remaining
     path has >= 2 hops and a length within the band (0.85-1.15x for
     same-corridor, where both lengths are measured; 0.85-1.30x for
     unsupported, where the edge is a chord and real track is longer).

Removal is sequential, longest edge first, re-testing on the current graph, so
two edges cannot each justify removing the other. Every removal is written out
with its evidence. Connectivity cannot change: condition 2 guarantees the
endpoints stay joined.
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd

SAME_BAND = (0.85, 1.15)
CROSS_BAND = (0.85, 1.30)
SUPPORT_MAX = 0.5
MIN_LEN_KM = 1.0


def geometry_support(edges: pd.DataFrame, corridors: pd.DataFrame) -> pd.Series:
    """Digitised track on the edge's corridor / the edge's length."""
    g = edges.corridor_id.map(corridors.set_index("corridor_id").geodesic_length_km)
    return g / edges.length_km


def _graph(edges: pd.DataFrame) -> nx.Graph:
    G = nx.Graph()
    for r in edges.itertuples(index=False):
        G.add_edge(r.from_node, r.to_node, km=float(r.length_km), eid=r.edge_id,
                   cid=r.corridor_id)
    return G


def find_removals(edges: pd.DataFrame, corridors: pd.DataFrame, *,
                  same_band=SAME_BAND, cross_band=CROSS_BAND,
                  support_max=SUPPORT_MAX, min_len_km=MIN_LEN_KM) -> pd.DataFrame:
    e = edges.copy()
    e["geometry_support"] = geometry_support(e, corridors)
    G = _graph(e)
    stitch = e[e.any_stitch.astype(bool)].sort_values("length_km", ascending=False)
    out = []
    for r in stitch.itertuples(index=False):
        u, v, L = r.from_node, r.to_node, float(r.length_km)
        if not G.has_edge(u, v):
            continue
        G.remove_edge(u, v)
        kind, alt, path = None, np.nan, []
        # (a) same corridor chain
        H = nx.Graph([(a, b, d) for a, b, d in G.edges(data=True) if d["cid"] == r.corridor_id])
        if u in H and v in H and nx.has_path(H, u, v):
            p = nx.dijkstra_path(H, u, v, weight="km")
            pl = nx.path_weight(H, p, "km")
            if len(p) - 1 >= 2 and same_band[0] <= pl / L <= same_band[1]:
                kind, alt, path = "same_corridor_chain", pl, p
        # (b) unsupported by its own geometry, equivalent route elsewhere
        if kind is None and r.geometry_support < support_max and L > min_len_km:
            try:
                p = nx.dijkstra_path(G, u, v, weight="km")
                pl = nx.path_weight(G, p, "km")
                if len(p) - 1 >= 2 and cross_band[0] <= pl / L <= cross_band[1]:
                    kind, alt, path = "unsupported_geometry", pl, p
            except nx.NetworkXNoPath:
                pass
        if kind is None:
            G.add_edge(u, v, km=L, eid=r.edge_id, cid=r.corridor_id)
            continue
        out.append({"edge_id": r.edge_id, "from_node": u, "to_node": v,
                    "corridor_id": r.corridor_id, "length_km": L, "kind": kind,
                    "geometry_support": float(r.geometry_support),
                    "alt_km": float(alt), "alt_ratio": float(alt / L),
                    "alt_hops": len(path) - 1,
                    "stations_bypassed": len(path) - 2,
                    "alt_path": " > ".join(path if len(path) <= 12 else path[:6] + ["..."] + path[-5:]),
                    "service_direct": int(r.service_direct) if pd.notna(r.service_direct) else 0})
    return pd.DataFrame(out)


def flag_columns(edges: pd.DataFrame, corridors: pd.DataFrame) -> pd.DataFrame:
    """Flags kept on every surviving edge so the residual is visible."""
    e = edges.copy()
    e["geometry_support"] = geometry_support(e, corridors)
    e["geometry_unsupported"] = (e.geometry_support < SUPPORT_MAX) & (e.length_km > MIN_LEN_KM)
    return e
