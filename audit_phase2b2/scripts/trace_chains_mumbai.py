import pyarrow.parquet as pq
import json

work_dir = "03_graph_construction/graph_v2_0_open/work"
table = pq.read_table(f"{work_dir}/network_edges.parquet")
edges = table.to_pydict()
verts_table = pq.read_table(f"{work_dir}/network_vertices.parquet").to_pydict()
v_coords = {v: (verts_table["lon"][i], verts_table["lat"][i]) for i, v in enumerate(verts_table["vertex"])}

# Find all edges in the South Mumbai corridor (lat between 18.93 and 19.01, lon between 72.82 and 72.85)
corridor_edges = []
for i in range(len(edges["a"])):
    a = edges["a"][i]
    b = edges["b"][i]
    if a in v_coords and b in v_coords:
        ca = v_coords[a]
        cb = v_coords[b]
        if (18.93 <= ca[1] <= 19.01 and 72.82 <= ca[0] <= 72.85) or (18.93 <= cb[1] <= 19.01 and 72.82 <= cb[0] <= 72.85):
            corridor_edges.append({
                "a": a, "b": b,
                "km": float(edges["km"][i]),
                "chain": int(edges["chain"][i]),
                "kind": edges["kind"][i],
                "lat_a": ca[1], "lon_a": ca[0],
                "lat_b": cb[1], "lon_b": cb[0]
            })

print(f"Total corridor edges in Stage C1: {len(corridor_edges)}")

# Chains in this corridor
chains = set(e["chain"] for e in corridor_edges)
print(f"Chains present in South Mumbai corridor: {chains}")

# Trace chain 8563 (incident to n289147, CSMT snap)
c_8563 = [e for e in corridor_edges if e["chain"] == 8563]
print(f"Chain 8563 edges: {len(c_8563)}")
for e in c_8563:
    print(f"  {e['a']} -> {e['b']}, km={e['km']:.4f}, kind={e['kind']}")

# Trace chain 7820, 7819, 7821 (which connect to n289068)
c_fast = [e for e in corridor_edges if e["chain"] in [7819, 7820, 7821]]
print(f"Fast line chain edges (7819, 7820, 7821): {len(c_fast)}")
for e in c_fast:
    print(f"  chain {e['chain']}: {e['a']} -> {e['b']}, km={e['km']:.4f}, kind={e['kind']}")

with open("audit_phase2b2/results/corridor_edges_south_mumbai.json", "w", encoding="utf-8") as f:
    json.dump({
        "corridor_edges_count": len(corridor_edges),
        "chains": list(chains),
        "c_8563": c_8563,
        "c_fast": c_fast
    }, f, indent=2)
