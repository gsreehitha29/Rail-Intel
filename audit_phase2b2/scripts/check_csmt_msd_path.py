import pyarrow.parquet as pq
import networkx as nx
import json

work_dir = "03_graph_construction/graph_v2_0_open/work"
edges_table = pq.read_table(f"{work_dir}/network_edges.parquet")
edges = edges_table.to_pydict()

G = nx.Graph()
for i in range(len(edges["a"])):
    G.add_edge(edges["a"][i], edges["b"][i], km=float(edges["km"][i]), chain=int(edges["chain"][i]), kind=edges["kind"][i])

print(f"Total nodes in Stage C1 network: {G.number_of_nodes()}, edges: {G.number_of_edges()}")

# Check if n128794 and n289147 are connected in G
has_path = nx.has_path(G, "n128794", "n289147")
print(f"Is there a path between n128794 and n289147 in Stage C1 network? {has_path}")

if has_path:
    path = nx.shortest_path(G, "n128794", "n289147", weight="km")
    length = nx.shortest_path_length(G, "n128794", "n289147", weight="km")
    print(f"Shortest path length: {length:.4f} km, hops: {len(path)-1}")
    print("Path hops:")
    for u, v in zip(path[:-1], path[1:]):
        edata = G[u][v]
        print(f"  {u} -> {v} ({edata['km']:.4f} km, chain {edata['chain']}, {edata['kind']})")
else:
    print("n128794 and n289147 are in DIFFERENT components in Stage C1 network!")

# Also check distance between them
import math
def haversine(lon1, lat1, lon2, lat2):
    R = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))

verts_table = pq.read_table(f"{work_dir}/network_vertices.parquet").to_pydict()
v_dict = {}
for i, v in enumerate(verts_table["vertex"]):
    if v in ["n128794", "n289147"]:
        v_dict[v] = (verts_table["lon"][i], verts_table["lat"][i])

dist_m = haversine(v_dict["n128794"][0], v_dict["n128794"][1], v_dict["n289147"][0], v_dict["n289147"][1]) * 1000
print(f"Straight line distance between n128794 and n289147: {dist_m:.2f} meters")

with open("audit_phase2b2/results/task6_path_check.json", "w", encoding="utf-8") as f:
    json.dump({
        "has_path": has_path,
        "path_length_km": length if has_path else None,
        "straight_line_m": dist_m,
        "path": path if has_path else None
    }, f, indent=2)
