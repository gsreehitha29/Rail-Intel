import pyarrow.parquet as pq
import csv
import json

work_dir = "03_graph_construction/graph_v2_0_open/work"

# 1. Read network_vertices.parquet
table = pq.read_table(f"{work_dir}/network_vertices.parquet")
df_verts = table.to_pydict()

target_vertices = ["n128794", "n289147", "s3558085"]
results = {}

for i, v in enumerate(df_verts["vertex"]):
    if v in target_vertices:
        results[v] = {
            "vertex": v,
            "lon": float(df_verts["lon"][i]),
            "lat": float(df_verts["lat"][i]),
            "osm_node": int(df_verts["osm_node"][i]),
            "kind": str(df_verts["kind"][i])
        }

print("=== Target Vertices in network_vertices.parquet ===")
print(json.dumps(results, indent=2))

# 2. Inspect station_snaps.csv for CSMT and MSD
print("\n=== Station Snaps for CSMT and MSD ===")
snaps = []
with open(f"{work_dir}/station_snaps.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get("code") in ["CSMT", "MSD"] or "Chhatrapati Shivaji" in row.get("name", "") or row.get("name") == "Masjid":
            print(dict(row))
            snaps.append(dict(row))

# 3. Inspect chain 4365 in network_edges.parquet
print("\n=== Chain 4365 in network_edges.parquet ===")
edges_table = pq.read_table(f"{work_dir}/network_edges.parquet")
edges = edges_table.to_pydict()
chain_4365_edges = []
all_n128794_edges = []
for i, c in enumerate(edges["chain"]):
    if c == 4365 or edges["a"][i] == "n128794" or edges["b"][i] == "n128794":
        edge_data = {
            "a": edges["a"][i],
            "b": edges["b"][i],
            "km": float(edges["km"][i]),
            "chain": int(edges["chain"][i]),
            "kind": edges["kind"][i],
            "gauge": edges["gauge"][i]
        }
        if c == 4365:
            chain_4365_edges.append(edge_data)
        if edges["a"][i] == "n128794" or edges["b"][i] == "n128794":
            all_n128794_edges.append(edge_data)

print("Chain 4365:")
print(json.dumps(chain_4365_edges, indent=2))
print("All edges incident to n128794:")
print(json.dumps(all_n128794_edges, indent=2))

# Save results to audit_phase2b2/results/task2_3_identifiers.json
with open("audit_phase2b2/results/task2_3_identifiers.json", "w", encoding="utf-8") as f:
    json.dump({
        "target_vertices": results,
        "snaps": snaps,
        "chain_4365_edges": chain_4365_edges,
        "all_n128794_edges": all_n128794_edges
    }, f, indent=2)
