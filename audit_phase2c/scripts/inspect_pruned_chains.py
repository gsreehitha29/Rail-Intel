import pyarrow.parquet as pq
import networkx as nx
import csv
import json

work_dir = "03_graph_construction/graph_v2_0_open/work"

# Load pruned history from previous run
with open("audit_phase2c/results/task4_5_terminals_prune_audit.json", "r", encoding="utf-8") as f:
    term_audit = json.load(f)

# Load network_edges to trace where pruned chains go
edges_table = pq.read_table(f"{work_dir}/network_edges.parquet").to_pydict()
chain_edges = {}
for i in range(len(edges_table["chain"])):
    c = int(edges_table["chain"][i])
    chain_edges.setdefault(c, []).append({
        "a": edges_table["a"][i],
        "b": edges_table["b"][i],
        "km": float(edges_table["km"][i]),
        "kind": edges_table["kind"][i],
        "gauge": edges_table["gauge"][i]
    })

# Load station_snaps to see which stations are on these chains
snaps_by_vertex = {}
with open(f"{work_dir}/station_snaps.csv", "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        v = row.get("vertex")
        if v:
            snaps_by_vertex[v] = dict(row)

# Detailed inspection of pruned chains for each terminal
detailed_pruned_chains = {}

for code, data in term_audit.items():
    detailed_pruned_chains[code] = []
    seen_chains = set()
    for p in data["pruned_vertices"]:
        for ed in p["prune_details"]["edges_dropped"]:
            cid = ed.get("chain")
            if cid and cid not in seen_chains:
                seen_chains.add(cid)
                cedges = chain_edges.get(cid, [])
                total_chain_km = sum(e["km"] for e in cedges)
                
                # Check all vertices in this chain
                cverts = set()
                for e in cedges:
                    cverts.add(e["a"])
                    cverts.add(e["b"])
                
                # Check if any station snapped to any vertex in this chain
                stations_on_chain = [snaps_by_vertex[cv]["code"] for cv in cverts if cv in snaps_by_vertex and snaps_by_vertex[cv].get("code")]
                
                detailed_pruned_chains[code].append({
                    "chain_id": cid,
                    "initiating_pruned_vertex": p["vertex"],
                    "dist_from_terminal_m": p["dist_m"],
                    "total_chain_km": round(total_chain_km, 4),
                    "edge_count": len(cedges),
                    "first_edge": cedges[0] if cedges else None,
                    "last_edge": cedges[-1] if cedges else None,
                    "stations_on_chain": stations_on_chain
                })

print("=== Detailed Inspection of Pruned Chains at Terminals ===")
for code, chains in detailed_pruned_chains.items():
    print(f"\nTerminal: {code} ({len(chains)} distinct pruned chains)")
    for ch in chains:
        print(f"  Chain {ch['chain_id']}: {ch['total_chain_km']} km (from vertex {ch['initiating_pruned_vertex']}, {ch['dist_from_terminal_m']}m) | Stations on chain: {ch['stations_on_chain']}")

# Also inspect BCT specifically
print("\n=== Special Search for BCT in Station Snaps & Raw Station Data ===")
with open(f"{work_dir}/station_snaps.csv", "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row.get("code") == "BCT" or "BCT" in row.get("ref", "") or "Mumbai Central" in row.get("name", ""):
            print(dict(row))

with open("audit_phase2c/results/task6_pruned_chains_detail.json", "w", encoding="utf-8") as f:
    json.dump(detailed_pruned_chains, f, indent=2)
