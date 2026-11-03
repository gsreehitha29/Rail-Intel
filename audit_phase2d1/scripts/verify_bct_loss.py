import json
import csv
import pandas as pd

release_dir = "03_graph_construction/release/rail-intel-v2.0-open"

# 1. Inspect station_code_crosswalk.csv
crosswalk_path = f"{release_dir}/graph/station_code_crosswalk.csv"
cw_entries = []
with open(crosswalk_path, "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if "BCT" in row.values() or "MMCT" in row.values():
            cw_entries.append(dict(row))

print("=== Crosswalk entries for BCT / MMCT ===")
print(cw_entries)

# 2. Check nodes.csv for MMCT and BCT
nodes_path = f"{release_dir}/graph/nodes.csv"
bct_nodes = []
with open(nodes_path, "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row["node_id"] in ["BCT", "MMCT"] or row.get("station_code") in ["BCT", "MMCT"]:
            bct_nodes.append(dict(row))

print("\n=== Nodes entries for BCT / MMCT ===")
print(json.dumps(bct_nodes, indent=2))

# 3. Check edges.csv incident to MMCT
edges_path = f"{release_dir}/graph/edges.csv"
mmct_edges = []
with open(edges_path, "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row["from_node"] in ["BCT", "MMCT"] or row["to_node"] in ["BCT", "MMCT"]:
            mmct_edges.append(dict(row))

print("\n=== Incident Edges for MMCT in release ===")
print(json.dumps(mmct_edges, indent=2))

# 4. Check 2017 service layer: station_pairs.csv
sp_path = f"{release_dir}/service_2017/station_pairs.csv"
sp_bct = []
with open(sp_path, "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row["from_station"] in ["BCT", "MMCT"] or row["to_station"] in ["BCT", "MMCT"]:
            sp_bct.append(dict(row))

print(f"\n=== station_pairs.csv records for BCT / MMCT: {len(sp_bct)} ===")

# 5. Check E-702 crosswalk reference
e702_path = "04_analysis_modules/E-702_station_code_crosswalk/out/crosswalk.csv"
try:
    e702_df = pd.read_csv(e702_path)
    e702_bct = e702_df[e702_df.code.isin(["BCT", "MMCT"]) | e702_df.graph_node.isin(["BCT", "MMCT"])].to_dict(orient="records")
    print(f"\n=== E-702 module crosswalk records ({len(e702_bct)}) ===")
    print(json.dumps(e702_bct, indent=2))
except Exception as e:
    print(f"Error reading E-702 crosswalk: {e}")

with open("audit_phase2d1/results/task10_bct_verification.json", "w", encoding="utf-8") as f:
    json.dump({
        "crosswalk_entries": cw_entries,
        "nodes": bct_nodes,
        "incident_edges": mmct_edges,
        "station_pairs_count": len(sp_bct),
        "e702_records": e702_bct if 'e702_bct' in locals() else []
    }, f, indent=2)
