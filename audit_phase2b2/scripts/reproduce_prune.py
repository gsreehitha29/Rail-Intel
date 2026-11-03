import pyarrow.parquet as pq
import networkx as nx
import csv
import json

work_dir = "03_graph_construction/graph_v2_0_open/work"

# Load station_snaps
stations = set()
vmap = {}
with open(f"{work_dir}/station_snaps.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        v = row.get("vertex")
        code = row.get("code")
        if v and code:
            vmap[v] = code
            stations.add(code)
        elif v and row.get("node_id"):
            vmap[v] = f"OSM:{row['node_id']}"
            stations.add(f"OSM:{row['node_id']}")

# Load network_edges
table = pq.read_table(f"{work_dir}/network_edges.parquet")
edges = table.to_pydict()

G = nx.Graph()
G.add_nodes_from(set(vmap.values()))
for i in range(len(edges["a"])):
    a = edges["a"][i]
    b = edges["b"][i]
    km = float(edges["km"][i])
    a_mapped = vmap.get(a, a)
    b_mapped = vmap.get(b, b)
    if a_mapped == b_mapped:
        continue
    if G.has_edge(a_mapped, b_mapped) and G[a_mapped][b_mapped]["km"] <= km:
        continue
    G.add_edge(a_mapped, b_mapped, km=km, raw_a=a, raw_b=b, chain=int(edges["chain"][i]), kind=edges["kind"][i])

print(f"Graph before prune: nodes={G.number_of_nodes()}, edges={G.number_of_edges()}")

# Check status of n128794, CSMT, MSD
print(f"Is 'n128794' in G? {G.has_node('n128794')}")
print(f"Degree of 'n128794': {G.degree('n128794') if G.has_node('n128794') else 'N/A'}")
if G.has_node('n128794'):
    print(f"Neighbors of 'n128794': {list(G.neighbors('n128794'))}")
print(f"Is 'n128794' in stations? {'n128794' in stations}")
print(f"Is 'CSMT' in G? {G.has_node('CSMT')}, degree={G.degree('CSMT') if G.has_node('CSMT') else 'N/A'}")
print(f"Is 'MSD' in G? {G.has_node('MSD')}, degree={G.degree('MSD') if G.has_node('MSD') else 'N/A'}")

# Simulate prune(G, stations) step-by-step
pruned_records = []
round_num = 0
while True:
    d1 = [n for n, d in G.degree() if d <= 1 and n not in stations]
    if not d1:
        break
    round_num += 1
    for n in d1:
        neighbors = list(G.neighbors(n))
        edges_dropped = []
        for nbr in neighbors:
            edata = G[n][nbr]
            edges_dropped.append({
                "u": n,
                "v": nbr,
                "km": edata["km"],
                "chain": edata.get("chain"),
                "kind": edata.get("kind"),
                "raw_a": edata.get("raw_a"),
                "raw_b": edata.get("raw_b")
            })
        if n == "n128794" or "MSD" in neighbors or "CSMT" in neighbors:
            pruned_records.append({
                "round": round_num,
                "node": n,
                "degree": G.degree(n),
                "in_stations": n in stations,
                "edges_dropped": edges_dropped
            })
        G.remove_node(n)

print(f"\nPrune completed in {round_num} rounds.")
print(f"Special pruned records around CSMT/MSD:")
print(json.dumps(pruned_records, indent=2))

with open("audit_phase2b2/results/task4_prune_reproduction.json", "w", encoding="utf-8") as f:
    json.dump({
        "pruned_records": pruned_records,
        "round_completed": round_num
    }, f, indent=2)
