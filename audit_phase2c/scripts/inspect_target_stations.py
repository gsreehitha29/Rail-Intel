import csv
import json

work_dir = "03_graph_construction/graph_v2_0_open/work"
release_dir = "03_graph_construction/release/rail-intel-v2.0-open/graph"

target_codes = ["HWH", "MAS", "SDAH", "BCT", "MMCT"]

# 1. Station snaps
station_snaps = []
with open(f"{work_dir}/station_snaps.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        c = row.get("code")
        name = row.get("name", "")
        if c in target_codes or any(k in name.upper() for k in ["HOWRAH", "SEALDAH", "CHENNAI CENTRAL", "MUMBAI CENTRAL"]):
            station_snaps.append(dict(row))

print("=== Station Snaps ===")
print(json.dumps(station_snaps, indent=2))

# 2. Released Nodes
released_nodes = []
with open(f"{release_dir}/nodes.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        node_id = row.get("node_id")
        name = row.get("name", "")
        if node_id in target_codes or any(node_id.startswith(f"{c}~") for c in target_codes) or any(k in name.upper() for k in ["HOWRAH", "SEALDAH", "CHENNAI CENTRAL", "MUMBAI CENTRAL"]):
            released_nodes.append(dict(row))

print("\n=== Released Nodes ===")
print(json.dumps(released_nodes, indent=2))

# 3. Incident edges in release
node_ids = set(r["node_id"] for r in released_nodes)
incident_edges = {n: [] for n in node_ids}
with open(f"{release_dir}/edges.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        u, v = row.get("a"), row.get("b")
        if u in node_ids:
            incident_edges[u].append(dict(row))
        if v in node_ids:
            incident_edges[v].append(dict(row))

print("\n=== Incident Edges in Released Graph ===")
for n, edges in incident_edges.items():
    print(f"\nNode {n} (Degree {len(edges)}):")
    for e in edges:
        other = e["b"] if e["a"] == n else e["a"]
        print(f"  -> {other} | km: {e['km']} | line: {e.get('line_name')} | joins: {e.get('joins')}")

with open("audit_phase2c/results/task1_released_stations.json", "w", encoding="utf-8") as f:
    json.dump({
        "station_snaps": station_snaps,
        "released_nodes": released_nodes,
        "incident_edges": incident_edges
    }, f, indent=2)
