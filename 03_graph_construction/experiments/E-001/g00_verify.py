"""Independently recompute the contested figures from the shipped edge list."""
import pandas as pd, networkx as nx, numpy as np
from pathlib import Path

D = Path.home()/"mnt/Rail-Intell/02_graph_inputs/graph_dataset"
nodes = pd.read_csv(D/"nodes.csv")
edges = pd.read_csv(D/"edges.csv")
seq   = pd.read_csv(D/"station_sequences.csv")

G = nx.Graph()
G.add_nodes_from(nodes.node_id)
for r in edges.itertuples():
    G.add_edge(r.from_node, r.to_node, km=r.length_km)

print(f"nodes            {G.number_of_nodes():,}")
print(f"edges            {G.number_of_edges():,}")
comps = sorted(nx.connected_components(G), key=len, reverse=True)
print(f"components       {len(comps)}")
giant = G.subgraph(comps[0])
print(f"giant            {giant.number_of_nodes():,} ({giant.number_of_nodes()/G.number_of_nodes()*100:.1f}%)")
print(f"giant edges      {giant.number_of_edges():,}")

ap = list(nx.articulation_points(giant))
br = list(nx.bridges(giant))
print(f"articulation pts {len(ap):,}   <- handoff 4.7 says 1,341 / 4.9 says 1,338")
print(f"bridges          {len(br):,}   <- handoff 4.7 says 1,432 / 4.9 says 1,412")
print(f"bridge share     {len(br)/giant.number_of_edges()*100:.1f}%")
mu = giant.number_of_edges() - giant.number_of_nodes() + 1
print(f"indep cycles     {mu:,}   <- docs say 612")
deg = np.array([d for _, d in G.degree()])
print(f"degree mean/max  {deg.mean():.2f} / {deg.max()}   <- QA says 2.13 / 7")
print(f"deg==2 share     {(deg==2).mean()*100:.1f}%   <- docs say 83%")
print(f"route km         {edges.length_km.sum():,.0f}   <- docs say 72,201")

print(f"\nparallel: n_parallel_corridors>1  {(edges.n_parallel_corridors>1).sum():,}   <- 4.3 says 397, QA says 581")
print(f"parallel: parallel_differs        {edges.parallel_differs.sum():,}   <- 4.3 says 98, QA says 124")
print(f"colocated (is_colocated)          {edges.is_colocated.sum():,}   <- 4.3 says 183, README says 249")
print(f"edges len<=0.051                  {(edges.length_km<=0.051).sum():,}")
print(f"any_stitch                        {edges.any_stitch.sum():,}")
print(f"\nseq rows {len(seq):,}  used_for_edges {seq.used_for_edges.sum():,}  offset>1.5 {(seq.offset_km>1.5).sum():,}")
print(f"nodes: station {(nodes.node_type=='station').sum():,}  op_junction {(nodes.node_type=='operational_junction').sum():,}  dissolvable {nodes.is_dissolvable.sum():,}")
