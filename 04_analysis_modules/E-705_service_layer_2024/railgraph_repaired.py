"""The repaired graph: v1.3 open plus the overrides G5 and G6 accepted.

One place assembles it, so every module downstream works on the same network and a
later gap can add its overrides here rather than in each caller.

    from railgraph_repaired import load_graph
    G, meta = load_graph(ROOT)

`G` is an undirected networkx graph; each edge carries `km`, `eid`, and `origin`
("v1.3", "G6" or "G5") so a result can be traced back to the repair that enabled it.

Pruning. G5 judged each candidate against the unrepaired graph, so its additions
interact: once one of them shortens a path, another can become a duplicate of a chain
that now works. `added_edge_audit.csv` lists the ones that turned out redundant, and
they are left out by default - keeping them would reintroduce the shortcut defect G5
was built to remove.
"""
from pathlib import Path

import networkx as nx
import pandas as pd

G5_DIR = "04_analysis_modules/E-703_trunk_wiring/out"
G6_DIR = "04_analysis_modules/E-704_missing_links/out"


def load_graph(root, with_repairs=True, g5_dir=None, g6_dir=None, prune=True,
               audit_file=None):
    root = Path(root)
    drop = set()
    if prune:
        af = Path(audit_file) if audit_file else (
            root / "04_analysis_modules/E-705_service_layer_2024/out/added_edge_audit.csv")
        if af.exists():
            a = pd.read_csv(af)
            drop = set(a.loc[a.verdict != "keep", "edge_id"])
    nodes = pd.read_csv(root / "03_graph_construction/graph_v1_3/open/nodes.csv")
    edges = pd.read_csv(root / "03_graph_construction/graph_v1_3/open/edges.csv")

    G = nx.Graph()
    for r in nodes.itertuples():
        G.add_node(r.node_id, name=r.node_name, lon=r.longitude, lat=r.latitude,
                   state=r.state, zone=r.zone_code)
    for r in edges.itertuples():
        if G.has_edge(r.from_node, r.to_node) and G[r.from_node][r.to_node]["km"] <= r.length_km:
            continue      # keep the shorter of parallel edges, as every module has
        G.add_edge(r.from_node, r.to_node, km=float(r.length_km), eid=r.edge_id,
                   origin="v1.3", tracks=r.n_tracks, gauge=r.gauge_code,
                   length_source=r.length_source)
    meta = dict(release="graph_v1_3/open", base_nodes=G.number_of_nodes(),
                base_edges=G.number_of_edges(), repairs_applied=with_repairs)
    if not with_repairs:
        return G, meta

    g5 = pd.read_csv(Path(g5_dir or (root / G5_DIR)) / "repairs_proposed.csv")
    removed = added5 = 0
    for r in g5.itertuples():
        if r.action == "remove_edge" and G.has_edge(r.a, r.b):
            G.remove_edge(r.a, r.b); removed += 1
        elif r.action == "add_edge" and not G.has_edge(r.a, r.b):
            if f"G5:{r.a}|{r.b}" in drop: continue
            G.add_edge(r.a, r.b, km=float(r.new), eid=f"G5:{r.a}|{r.b}", origin="G5",
                       tracks=None, gauge=None, length_source="official_adjacency")
            added5 += 1
    g6 = pd.read_csv(Path(g6_dir or (root / G6_DIR)) / "links_added.csv")
    added6 = 0
    for r in g6.itertuples():
        if not G.has_edge(r.a, r.b):
            if f"G6:{r.a}|{r.b}" in drop: continue
            G.add_edge(r.a, r.b, km=float(r.length_km), eid=f"G6:{r.a}|{r.b}", origin="G6",
                       tracks=None, gauge=None, length_source="official_adjacency_chord_floored")
            added6 += 1
    meta.update(g5_removed=removed, g5_added=added5, g6_added=added6,
                pruned_as_redundant=len(drop),
                nodes=G.number_of_nodes(), edges=G.number_of_edges(),
                components=nx.number_connected_components(G))
    return G, meta
