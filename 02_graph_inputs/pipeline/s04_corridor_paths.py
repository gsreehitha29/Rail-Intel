"""
Stage 04 — Corridor path (spine) reconstruction.

This is the stage that addresses validation gap #3: "can corridor geometry
actually be walked end-to-end so that stations can be ordered along it?"

Method
------
For each corridor, build a LOCAL micro-graph from its own segments only:

    nodes = segment endpoints, snapped together within SNAP_TOLERANCE_M
    edges = segments, weighted by true geodesic length

then extract the corridor's "spine" = the longest end-to-end path through its
largest connected component, found by the double-sweep (two Dijkstra passes)
method. Everything not on the spine is a spur (siding, yard lead, branch).

Why local and not global: the earlier EDA measured endpoint degree GLOBALLY
across all 118k segments, so a corridor whose ends connect to NEIGHBOURING
corridors showed "0 boundary endpoints" and was counted as malformed. That is
normal, healthy network connectivity, not a defect. Measuring inside each
corridor answers the question that actually matters for station ordering.

Outputs
-------
graph_inputs/corridor_paths.csv        per-corridor reconstruction metrics
pipeline/cache/corridor_spines.parquet spine geometry (WKB) for stage 05
"""

from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely import wkb as shapely_wkb
from shapely.geometry import LineString

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CACHE_DIR, GRAPH_INPUT_VERSION, OUT_DIR, banner, to_local_xy  # noqa: E402

SNAP_TOLERANCE_M = 10.0  # endpoints within this distance are treated as one node


def snap_nodes(points_xy: np.ndarray, tol_km: float) -> np.ndarray:
    """Cluster 2-D points within tol_km using a KD-tree + union-find."""
    n = len(points_xy)
    parent = np.arange(n)

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)

    tree = cKDTree(points_xy)
    for i, j in tree.query_pairs(tol_km):
        union(i, j)
    return np.array([find(i) for i in range(n)])


def double_sweep(G: nx.Graph, nodes: list):
    """Return (u, v, path) for the longest shortest-path in a connected graph."""
    start = nodes[0]
    d1 = nx.single_source_dijkstra_path_length(G, start, weight="w")
    u = max(d1, key=d1.get)
    d2, p2 = nx.single_source_dijkstra(G, u, weight="w")
    v = max(d2, key=d2.get)
    return u, v, p2[v], d2[v]


def main() -> None:
    banner("STAGE 04 — CORRIDOR PATH (SPINE) RECONSTRUCTION")

    seg = pd.read_parquet(CACHE_DIR / "segments_geometry.parquet")
    seg = seg[(seg["corridor_a"] != "") & (seg["corridor_b"] != "")].copy()
    corridors = pd.read_csv(OUT_DIR / "corridors.csv")
    key_to_id = dict(
        zip(zip(corridors["corridor_a"], corridors["corridor_b"]), corridors["corridor_id"])
    )
    print(f"Segments with valid endpoints: {len(seg):,}")
    print(f"Corridors to reconstruct     : {len(corridors):,}")
    print(f"Endpoint snap tolerance      : {SNAP_TOLERANCE_M:.0f} m")
    print()

    tol_km = SNAP_TOLERANCE_M / 1000.0
    results = []
    spines = []

    for gi, (key, grp) in enumerate(seg.groupby(["corridor_a", "corridor_b"], sort=True)):
        corridor_id = key_to_id.get(key)
        if corridor_id is None:
            continue

        grp = grp.reset_index(drop=True)
        n_seg = len(grp)
        total_len = float(grp["length_km"].sum())

        # --- snap endpoints into micro-graph nodes -----------------------
        lons = np.concatenate([grp["start_lon"].values, grp["end_lon"].values])
        lats = np.concatenate([grp["start_lat"].values, grp["end_lat"].values])
        x, y = to_local_xy(lons, lats)
        labels = snap_nodes(np.column_stack([x, y]), tol_km)
        start_node = labels[:n_seg]
        end_node = labels[n_seg:]
        n_raw_endpoints = len(np.unique(np.concatenate([
            np.round(np.column_stack([x[:n_seg], y[:n_seg]]), 6).view([('', float)] * 2).ravel()
            if False else start_node, end_node])))

        # --- build micro-graph -------------------------------------------
        G = nx.Graph()
        n_parallel = 0
        n_degenerate = 0
        for i in range(n_seg):
            u, v = int(start_node[i]), int(end_node[i])
            w = float(grp.at[i, "length_km"])
            if u == v:
                n_degenerate += 1
                continue
            if G.has_edge(u, v):
                n_parallel += 1
                if w < G[u][v]["w"]:
                    G[u][v].update(w=w, seg=i)
            else:
                G.add_edge(u, v, w=w, seg=i)

        if G.number_of_edges() == 0:
            results.append(dict(
                corridor_id=corridor_id, corridor_a=key[0], corridor_b=key[1],
                status="degenerate_no_edges", n_segments=n_seg, n_nodes=0,
                n_components=0, n_terminals=0, total_length_km=total_len,
                spine_length_km=0.0, spine_coverage=0.0, spine_n_segments=0,
                spur_length_km=0.0, n_parallel_segments=n_parallel,
                n_degenerate_segments=n_degenerate, main_component_share=0.0,
            ))
            continue

        comps = list(nx.connected_components(G))
        comp_lengths = [
            sum(G[u][v]["w"] for u, v in G.subgraph(c).edges()) for c in comps
        ]
        main_idx = int(np.argmax(comp_lengths))
        main_nodes = list(comps[main_idx])
        Gm = G.subgraph(main_nodes).copy()
        main_len = comp_lengths[main_idx]

        n_terminals = sum(1 for n in Gm.nodes if Gm.degree(n) == 1)

        u, v, path_nodes, spine_len = double_sweep(Gm, main_nodes)

        # --- classify -----------------------------------------------------
        coverage = spine_len / total_len if total_len > 0 else 0.0
        if len(comps) > 1:
            status = "fragmented"
        elif n_terminals == 0:
            status = "loop"
        elif coverage >= 0.995:
            status = "clean_path"
        else:
            status = "path_with_spurs"

        # --- build ordered spine geometry ---------------------------------
        coords: list = []
        spine_segments = 0
        for a_node, b_node in zip(path_nodes[:-1], path_nodes[1:]):
            si = Gm[a_node][b_node]["seg"]
            line = shapely_wkb.loads(grp.at[si, "wkb"])
            c = list(line.coords)
            # orient the segment so it continues from the current endpoint
            if int(start_node[si]) != a_node:
                c = c[::-1]
            if coords and coords[-1] == c[0]:
                coords.extend(c[1:])
            else:
                coords.extend(c)
            spine_segments += 1

        if len(coords) >= 2:
            spines.append({
                "corridor_id": corridor_id,
                "wkb": shapely_wkb.dumps(LineString(coords)),
                "n_coords": len(coords),
            })

        results.append(dict(
            corridor_id=corridor_id, corridor_a=key[0], corridor_b=key[1],
            status=status, n_segments=n_seg, n_nodes=Gm.number_of_nodes(),
            n_components=len(comps), n_terminals=n_terminals,
            total_length_km=total_len, spine_length_km=float(spine_len),
            spine_coverage=float(coverage), spine_n_segments=spine_segments,
            spur_length_km=float(max(total_len - spine_len, 0.0)),
            n_parallel_segments=n_parallel, n_degenerate_segments=n_degenerate,
            main_component_share=float(main_len / total_len) if total_len else 0.0,
        ))

        if (gi + 1) % 500 == 0:
            print(f"  ... {gi + 1:,} corridors processed")

    res = pd.DataFrame(results)
    res["snap_tolerance_m"] = SNAP_TOLERANCE_M
    res["graph_input_version"] = GRAPH_INPUT_VERSION

    print()
    print(f"Corridors reconstructed: {len(res):,}")
    print()
    print("RECONSTRUCTION STATUS:")
    for status, n in res["status"].value_counts().items():
        print(f"  {status:<22} {n:>6,}  ({n/len(res)*100:5.1f}%)")
    print()
    usable = res[res["status"].isin(["clean_path", "path_with_spurs", "fragmented", "loop"])]
    print(f"Corridors with a usable ordered spine: {len(usable):,} "
          f"({len(usable)/len(res)*100:.1f}%)")
    print()
    print("SPINE COVERAGE (spine length / total corridor geometry length):")
    for lo, hi in [(0.99, 1.01), (0.95, 0.99), (0.80, 0.95), (0.50, 0.80), (0.0, 0.50)]:
        n = int(((res["spine_coverage"] >= lo) & (res["spine_coverage"] < hi)).sum())
        print(f"  {lo:.2f}-{hi:.2f}: {n:>6,}")
    print()
    print(f"Total spine length   : {res['spine_length_km'].sum():,.0f} km")
    print(f"Total spur length    : {res['spur_length_km'].sum():,.0f} km")
    print(f"Corridors fragmented : {int((res['n_components']>1).sum()):,} "
          f"(median main-component share {res.loc[res['n_components']>1,'main_component_share'].median():.3f})")

    res.to_csv(OUT_DIR / "corridor_paths.csv", index=False)
    pd.DataFrame(spines).to_parquet(CACHE_DIR / "corridor_spines.parquet", index=False)
    print()
    print(f"WROTE {OUT_DIR / 'corridor_paths.csv'}")
    print(f"WROTE {CACHE_DIR / 'corridor_spines.parquet'}  ({len(spines):,} spines)")


if __name__ == "__main__":
    main()
