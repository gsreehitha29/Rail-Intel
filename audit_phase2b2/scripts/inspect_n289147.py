import pyarrow.parquet as pq
import json

work_dir = "03_graph_construction/graph_v2_0_open/work"
edges_table = pq.read_table(f"{work_dir}/network_edges.parquet")
edges = edges_table.to_pydict()

n289147_edges = []
for i in range(len(edges["a"])):
    if edges["a"][i] == "n289147" or edges["b"][i] == "n289147":
        n289147_edges.append({
            "a": edges["a"][i],
            "b": edges["b"][i],
            "km": float(edges["km"][i]),
            "chain": int(edges["chain"][i]),
            "kind": edges["kind"][i],
            "gauge": edges["gauge"][i]
        })

print("=== All edges incident to n289147 ===")
print(json.dumps(n289147_edges, indent=2))
