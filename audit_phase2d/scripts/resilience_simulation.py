import csv
import json
import networkx as nx

release_dir = "03_graph_construction/release/rail-intel-v2.0-open/graph"

# Load baseline released graph
def load_graph():
    G = nx.Graph()
    with open(f"{release_dir}/nodes.csv", "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            G.add_node(row["node_id"], name=row["node_name"], state=row["state"], node_type=row["node_type"])
    with open(f"{release_dir}/edges.csv", "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            G.add_edge(row["from_node"], row["to_node"], km=float(row["length_km"]), eid=row["edge_id"], line_name=row.get("line_name"))
    return G

G_base = load_graph()
print(f"Baseline Graph: nodes={G_base.number_of_nodes()}, edges={G_base.number_of_edges()}")

# Baseline metrics
base_comps = sorted(nx.connected_components(G_base), key=len, reverse=True)
base_giant = base_comps[0]
base_bridges = list(nx.bridges(G_base))
base_articulation = list(nx.articulation_points(G_base))

print(f"Baseline Components: {len(base_comps)}, Giant Size: {len(base_giant)}")
print(f"Baseline Bridges: {len(base_bridges)}, Articulation Points: {len(base_articulation)}")

# Specific node degrees in baseline
terminals = ["CSMT", "HWH", "MAS", "MMCT", "SDAH"]
base_degrees = {t: G_base.degree(t) for t in terminals}
print("Baseline Terminal Degrees:", base_degrees)

# Specific OD paths in baseline
od_pairs = [
    ("CSMT", "MSD"),
    ("CSMT", "BY"),
    ("CSMT", "PR"),
    ("HWH", "TPKR"),
    ("HWH", "KGP"),
    ("MAS", "BBQ"),
    ("MAS", "TRL"),
    ("MMCT", "DDR"),
    ("MMCT", "BVI"),
    ("SDAH", "BLN")
]

def get_od_metrics(G):
    res = {}
    for u, v in od_pairs:
        if G.has_node(u) and G.has_node(v):
            if nx.has_path(G, u, v):
                p = nx.shortest_path(G, u, v, weight="km")
                d = nx.shortest_path_length(G, u, v, weight="km")
                res[f"{u}->{v}"] = {"has_path": True, "km": round(d, 4), "hops": len(p)-1, "path": p[:4] + ["..."] + p[-2:] if len(p) > 6 else p}
            else:
                res[f"{u}->{v}"] = {"has_path": False, "km": None, "hops": None}
        else:
            res[f"{u}->{v}"] = {"error": f"missing node u={G.has_node(u)}, v={G.has_node(v)}"}
    return res

base_od = get_od_metrics(G_base)
print("\n=== Baseline OD Paths ===")
print(json.dumps(base_od, indent=2))

# Scenario 1: Restore CSMT Slow Line (1.4163 km to MSD)
G_scen1 = G_base.copy()
G_scen1.add_edge("CSMT", "MSD", km=1.4163, eid="restored:CSMT-MSD", line_name="Central Railway Slow Line")

# Scenario 2: Restore HWH SER approach (to Tikiapara TPKR, 2.7 km)
G_scen2 = G_scen1.copy()
# In C1 chain 8315, Tikiapara TPKR connected to Howrah buffer stop n357842
G_scen2.add_edge("HWH", "TPKR", km=2.72, eid="restored:HWH-TPKR", line_name="South Eastern Railway Approach")

# Scenario 3: Restore MAS MMC Suburban approach (to Basin Bridge BBQ, 1.8 km)
G_scen3 = G_scen2.copy()
G_scen3.add_edge("MAS", "BBQ", km=1.82, eid="restored:MAS-BBQ", line_name="Chennai Suburban Moore Market Line")

# Compare resilience metrics for each scenario
scenarios = {
    "Baseline": G_base,
    "Scen1_CSMT_Restored": G_scen1,
    "Scen2_CSMT_HWH_Restored": G_scen2,
    "Scen3_All_3_Restored": G_scen3
}

scenario_metrics = {}
for sname, G_s in scenarios.items():
    bridges = list(nx.bridges(G_s))
    art = list(nx.articulation_points(G_s))
    od = get_od_metrics(G_s)
    
    # Check bridge status of terminal approach edges
    terminal_edge_bridges = {}
    for t in terminals:
        incident = list(G_s.edges(t))
        for u, v in incident:
            is_br = (u, v) in bridges or (v, u) in bridges
            terminal_edge_bridges[f"{u}-{v}"] = is_br

    scenario_metrics[sname] = {
        "nodes": G_s.number_of_nodes(),
        "edges": G_s.number_of_edges(),
        "bridges": len(bridges),
        "articulation_points": len(art),
        "terminal_edge_bridges": terminal_edge_bridges,
        "od_paths": od
    }

print("\n=== Scenario Comparison Summary ===")
for sname, sdata in scenario_metrics.items():
    print(f"\nScenario: {sname}")
    print(f"  Edges: {sdata['edges']}, Bridges: {sdata['bridges']} (Delta vs Base: {sdata['bridges'] - len(base_bridges)})")
    print(f"  Articulation Points: {sdata['articulation_points']} (Delta vs Base: {sdata['articulation_points'] - len(base_articulation)})")
    print("  Terminal Edge Bridge Status:")
    for e, is_br in sdata["terminal_edge_bridges"].items():
        print(f"    {e}: {'BRIDGE' if is_br else 'REDUNDANT (Loop)'}")

with open("audit_phase2d/results/task_c_d_resilience_simulation.json", "w", encoding="utf-8") as f:
    json.dump(scenario_metrics, f, indent=2)
