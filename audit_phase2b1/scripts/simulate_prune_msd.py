import pandas as pd
import csv
import pathlib
import networkx as nx
import pyarrow.parquet as pq

def main():
    root = pathlib.Path("c:/Users/Sreehitha/OneDrive/Desktop/Major Project/Rail-Intel")
    work_dir = root / "03_graph_construction" / "graph_v2_0_open" / "work"

    E = pq.read_table(work_dir / "network_edges.parquet").to_pandas()
    snaps = list(csv.DictReader(open(work_dir / "station_snaps.csv", encoding="utf-8")))

    kept_snaps = [r for r in snaps if r.get("vertex") and r.get("review_metro") != "True"]
    vmap = {}
    stations = set()
    for r in kept_snaps:
        code = r.get("code") or ("OSM:" + r["node_id"])
        vmap[r["vertex"]] = code
        stations.add(code)

    snaps_csmt = next(r["vertex"] for r in snaps if r.get("code") == "CSMT")
    snaps_msd = next(r["vertex"] for r in snaps if r.get("code") == "MSD")

    print(f"Total stations in vmap: {len(stations)}")
    print(f"CSMT mapped from vertex {snaps_csmt} -> {vmap.get(snaps_csmt)}")
    print(f"MSD mapped from vertex {snaps_msd} -> {vmap.get(snaps_msd)}")

    # 1. Step: vertex_graph
    G = nx.Graph()
    G.add_nodes_from(set(vmap.values()))
    
    edge_msd_south_found = False
    for i, (a, b, km) in enumerate(zip(E.a.values, E.b.values, E.km.values)):
        orig_a, orig_b = a, b
        a, b = vmap.get(a, a), vmap.get(b, b)
        if a == b: continue
        if (orig_a == "n128794" and orig_b == "s3558085") or (orig_b == "n128794" and orig_a == "s3558085"):
            edge_msd_south_found = True
            print(f"In vertex_graph: edge n128794 <-> s3558085 becomes {a} <-> {b} (km={km:.4f})")
        if G.has_edge(a, b) and G[a][b]["km"] <= km: continue
        G.add_edge(a, b, km=float(km), rows=(i,), via=frozenset())

    print(f"Edge n128794 <-> MSD in G after vertex_graph: {G.has_edge('n128794', 'MSD')}")
    if G.has_edge('n128794', 'MSD'):
        print(f"  Degree of n128794 in G: {G.degree('n128794')}")
        print(f"  n128794 in stations: {'n128794' in stations}")

    # 2. Step: prune(G, stations)
    d1 = [n for n, d in G.degree() if d <= 1 and n not in stations]
    print(f"\nBefore prune: total nodes in G={len(G)}, degree <= 1 non-stations={len(d1)}")
    print(f"Is n128794 in d1? {'n128794' in d1}")
    
    # Run one round of prune
    G.remove_nodes_from(d1)
    print(f"After prune: is n128794 in G? {'n128794' in G}")
    print(f"After prune: MSD neighbors: {[nbr for nbr in G.neighbors('MSD')]}")

if __name__ == "__main__":
    main()
