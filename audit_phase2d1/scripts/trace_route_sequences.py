import csv
import json
import networkx as nx

release_dir = "03_graph_construction/release/rail-intel-v2.0-open/graph"

# Load graph with edge attributes
G_base = nx.Graph()
with open(f"{release_dir}/nodes.csv", "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        G_base.add_node(row["node_id"], name=row["node_name"], state=row["state"], node_type=row["node_type"])
with open(f"{release_dir}/edges.csv", "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        G_base.add_edge(row["from_node"], row["to_node"], km=float(row["length_km"]), eid=row["edge_id"],
                        line_name=row.get("line_name"), chord_km=float(row["length_chord_km"]))

# Route edge sequences helper
def get_route_edges(G, u, v):
    node_path = nx.shortest_path(G, u, v, weight="km")
    total_km = nx.shortest_path_length(G, u, v, weight="km")
    edge_seq = []
    for a, b in zip(node_path[:-1], node_path[1:]):
        edata = G[a][b]
        edge_seq.append({
            "from_node": a,
            "to_node": b,
            "edge_id": edata["eid"],
            "length_km": edata["km"],
            "line_name": edata.get("line_name", "")
        })
    return {
        "from": u,
        "to": v,
        "total_km": round(total_km, 4),
        "hops": len(edge_seq),
        "node_sequence": node_path,
        "edge_sequence": edge_seq
    }

routes = {}

# 1. CSMT -> MSD
routes["CSMT_MSD_baseline"] = get_route_edges(G_base, "CSMT", "MSD")

G_scen_csmt = G_base.copy()
G_scen_csmt.add_edge("CSMT", "MSD", km=1.4163, eid="restored:CSMT-MSD", line_name="Central Railway Slow Line")
routes["CSMT_MSD_scenario"] = get_route_edges(G_scen_csmt, "CSMT", "MSD")

# 2. HWH -> TPKR
routes["HWH_TPKR_baseline"] = get_route_edges(G_base, "HWH", "TPKR")

G_scen_hwh = G_base.copy()
G_scen_hwh.add_edge("HWH", "TPKR", km=2.72, eid="restored:HWH-TPKR", line_name="South Eastern Railway Approach")
routes["HWH_TPKR_scenario"] = get_route_edges(G_scen_hwh, "HWH", "TPKR")

# 3. MAS -> BBQ
routes["MAS_BBQ_baseline"] = get_route_edges(G_base, "MAS", "BBQ")

G_scen_mas = G_base.copy()
G_scen_mas.add_edge("MAS", "BBQ", km=1.82, eid="restored:MAS-BBQ", line_name="Chennai Suburban Moore Market Line")
routes["MAS_BBQ_scenario"] = get_route_edges(G_scen_mas, "MAS", "BBQ")

print("=== Edge Sequences for Baseline vs Scenario Routes ===")
for rname, rinfo in routes.items():
    print(f"\n--- {rname} ---")
    print(f"Total km: {rinfo['total_km']} km | Hops: {rinfo['hops']}")
    print("Edge Sequence:")
    for i, e in enumerate(rinfo["edge_sequence"]):
        print(f"  {i+1}. {e['from_node']} -> {e['to_node']} | {e['length_km']} km | {e['edge_id']} | {e['line_name']}")

with open("audit_phase2d1/results/task7_route_edge_sequences.json", "w", encoding="utf-8") as f:
    json.dump(routes, f, indent=2)
