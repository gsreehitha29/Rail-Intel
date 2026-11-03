import csv
import json

release_dir = "03_graph_construction/release/rail-intel-v2.0-open/graph"
target_nodes = ["HWH", "MAS", "MMCT", "SDAH", "BCT", "CSMT"]

incident_edges = {n: [] for n in target_nodes}
with open(f"{release_dir}/edges.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        u, v = row.get("from_node"), row.get("to_node")
        if u in incident_edges:
            incident_edges[u].append(dict(row))
        if v in incident_edges:
            incident_edges[v].append(dict(row))

for n, edges in incident_edges.items():
    print(f"\nStation {n} (Degree {len(edges)}):")
    for e in edges:
        other = e["to_node"] if e["from_node"] == n else e["from_node"]
        print(f"  Edge: {e['edge_id']}")
        print(f"    Connects to: {other}")
        print(f"    Length: {e['length_km']} km (chord: {e['length_chord_km']} km)")
        print(f"    Line name: {e.get('line_name')}")
        print(f"    Joins: {e.get('joins')}")
        print(f"    Trains 2017: {e.get('trains_2017')}")

with open("audit_phase2c/results/task1_incident_edges_corrected.json", "w", encoding="utf-8") as f:
    json.dump(incident_edges, f, indent=2)
