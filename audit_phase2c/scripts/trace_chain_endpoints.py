import pyarrow.parquet as pq
import csv
import json

work_dir = "03_graph_construction/graph_v2_0_open/work"
release_dir = "03_graph_construction/release/rail-intel-v2.0-open/graph"

# Vertices table
v_table = pq.read_table(f"{work_dir}/network_vertices.parquet").to_pydict()
verts = {v: (float(v_table["lon"][i]), float(v_table["lat"][i]), int(v_table["osm_node"][i]), str(v_table["kind"][i]))
         for i, v in enumerate(v_table["vertex"])}

# Edges table
edges_table = pq.read_table(f"{work_dir}/network_edges.parquet").to_pydict()

target_chains = {
    "HWH": [7959, 8315, 13110, 7972, 928],
    "MAS": [26, 25, 5729, 5269, 144],
    "SDAH": [3867, 4199, 4201],
    "MMCT": [3929, 806, 630, 804]
}

chain_details = {}

for term, cids in target_chains.items():
    chain_details[term] = {}
    for cid in cids:
        c_edges = []
        for i in range(len(edges_table["chain"])):
            if int(edges_table["chain"][i]) == cid:
                a, b = edges_table["a"][i], edges_table["b"][i]
                c_edges.append({
                    "a": a, "b": b,
                    "km": float(edges_table["km"][i]),
                    "kind": edges_table["kind"][i],
                    "coord_a": verts.get(a),
                    "coord_b": verts.get(b)
                })
        
        tot_km = sum(e["km"] for e in c_edges)
        chain_details[term][cid] = {
            "total_km": round(tot_km, 4),
            "edge_count": len(c_edges),
            "start_vertex": c_edges[0]["a"] if c_edges else None,
            "end_vertex": c_edges[-1]["b"] if c_edges else None,
            "start_coords": c_edges[0]["coord_a"] if c_edges else None,
            "end_coords": c_edges[-1]["coord_b"] if c_edges else None,
            "edges_summary": c_edges[:3] + (c_edges[-3:] if len(c_edges) > 3 else [])
        }

print("=== Chain Trace Summary ===")
for term, cdata in chain_details.items():
    print(f"\nTerminal: {term}")
    for cid, det in cdata.items():
        print(f"  Chain {cid}: {det['total_km']} km, {det['edge_count']} edges")
        print(f"    Start: {det['start_vertex']} at {det['start_coords']}")
        print(f"    End: {det['end_vertex']} at {det['end_coords']}")

with open("audit_phase2c/results/task6_chain_trace_details.json", "w", encoding="utf-8") as f:
    json.dump(chain_details, f, indent=2)
