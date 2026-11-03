import csv
import json
import networkx as nx

release_dir = "03_graph_construction/release/rail-intel-v2.0-open/graph"

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
bridges_base = set(tuple(sorted((u, v))) for u, v in nx.bridges(G_base))
print(f"Base bridges: {len(bridges_base)}")

# Scenarios
# Scen 1: CSMT - MSD
G1 = G_base.copy()
G1.add_edge("CSMT", "MSD", km=1.4163, eid="restored:CSMT-MSD", line_name="Central Railway Slow Line")
bridges_g1 = set(tuple(sorted((u, v))) for u, v in nx.bridges(G1))

diff_g1 = bridges_base - bridges_g1
print(f"\nScenario 1: Bridges eliminated by adding CSMT-MSD ({len(diff_g1)} bridges):")
for u, v in sorted(diff_g1):
    edata = G_base[u][v]
    print(f"  - {u} <-> {v} | eid: {edata['eid']} | km: {edata['km']} | line: {edata.get('line_name')}")

# Scen 2: HWH - TPKR
G2 = G1.copy()
G2.add_edge("HWH", "TPKR", km=2.72, eid="restored:HWH-TPKR", line_name="South Eastern Railway Approach")
bridges_g2 = set(tuple(sorted((u, v))) for u, v in nx.bridges(G2))

diff_g2 = bridges_g1 - bridges_g2
print(f"\nScenario 2: Bridges eliminated by adding HWH-TPKR ({len(diff_g2)} bridges):")
for u, v in sorted(diff_g2):
    edata = G_base[u][v]
    print(f"  - {u} <-> {v} | eid: {edata['eid']} | km: {edata['km']} | line: {edata.get('line_name')}")

# Scen 3: MAS - BBQ
G3 = G2.copy()
G3.add_edge("MAS", "BBQ", km=1.82, eid="restored:MAS-BBQ", line_name="Chennai Suburban Moore Market Line")
bridges_g3 = set(tuple(sorted((u, v))) for u, v in nx.bridges(G3))

diff_g3 = bridges_g2 - bridges_g3
print(f"\nScenario 3: Bridges eliminated by adding MAS-BBQ ({len(diff_g3)} bridges):")
for u, v in sorted(diff_g3):
    edata = G_base[u][v]
    print(f"  - {u} <-> {v} | eid: {edata['eid']} | km: {edata['km']} | line: {edata.get('line_name')}")

total_eliminated = bridges_base - bridges_g3
print(f"\nTotal bridges eliminated across all 3 scenarios: {len(total_eliminated)}")

# Save to JSON
with open("audit_phase2d1/results/task5_bridge_elimination_trace.json", "w", encoding="utf-8") as f:
    json.dump({
        "baseline_bridges_count": len(bridges_base),
        "scen1_eliminated": [list(x) for x in sorted(diff_g1)],
        "scen2_eliminated": [list(x) for x in sorted(diff_g2)],
        "scen3_eliminated": [list(x) for x in sorted(diff_g3)],
        "total_eliminated": [list(x) for x in sorted(total_eliminated)]
    }, f, indent=2)
