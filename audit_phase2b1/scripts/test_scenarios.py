import csv
import json
import pathlib
import networkx as nx

def main():
    root = pathlib.Path(__file__).resolve().parents[2]
    release_dir = root / "03_graph_construction" / "release" / "rail-intel-v2.0-open"
    results_dir = root / "audit_phase2b1" / "results"
    artifacts_dir = root / "audit_phase2b1" / "artifacts"

    nodes_raw = list(csv.DictReader(open(release_dir / "graph" / "nodes.csv", encoding="utf-8")))
    edges_raw = list(csv.DictReader(open(release_dir / "graph" / "edges.csv", encoding="utf-8")))
    nodes = {n["node_id"]: n for n in nodes_raw}

    # Build Baseline Graph (Scenario 0)
    G0 = nx.Graph()
    for n in nodes_raw:
        G0.add_node(n["node_id"], **n)
    for e in edges_raw:
        d = dict(e)
        d["length_km"] = float(d["length_km"])
        G0.add_edge(d["from_node"], d["to_node"], **d)

    # Build Scenario 1: Baseline + Direct CSMT-MSD edge (1.4163 km, exact chain 4365 length)
    G1 = G0.copy()
    G1.add_edge("CSMT", "MSD", length_km=1.4163, edge_id="test:CSMT|MSD", line_name="Central Railway (Slow)", joins="pruned_restoration")

    candidate_edge = ("CSMT", "JN:@72.836140,19.007082")

    test_pairs = [
        ("CSMT", "MSD", "Masjid"),
        ("CSMT", "SNRD", "Sandhurst Road"),
        ("CSMT", "BY", "Byculla"),
        ("CSMT", "CHG", "Chinchpokli"),
        ("CSMT", "CRD", "Currey Road"),
        ("CSMT", "PR", "Parel"),
        ("CSMT", "DR", "Dadar"),
        ("CSMT", "TNA", "Thane"),
        ("CSMT", "KYN", "Kalyan Jn"),
        ("CSMT", "PNVL", "Panvel (Harbour Line)")
    ]

    scenarios_summary = []
    for s_name, G_curr in [("Scenario 0 (Baseline Release)", G0), ("Scenario 1 (Restored CSMT-MSD 1.4163 km)", G1)]:
        bridges = set(tuple(sorted([u, v])) for u, v in nx.bridges(G_curr))
        cand_is_bridge = tuple(sorted(candidate_edge)) in bridges
        csmt_deg = G_curr.degree("CSMT")
        msd_deg = G_curr.degree("MSD")
        cycle_count = len(nx.cycle_basis(G_curr))
        cut_points = len(list(nx.articulation_points(G_curr)))
        
        pair_results = []
        for u, v, v_name in test_pairs:
            if nx.has_path(G_curr, u, v):
                p = nx.shortest_path(G_curr, u, v, weight="length_km")
                l = nx.shortest_path_length(G_curr, u, v, weight="length_km")
                pair_results.append({
                    "target": v,
                    "target_name": v_name,
                    "length_km": round(l, 4),
                    "hops": len(p) - 1,
                    "path": p
                })
        
        # Check the cycle that candidate_edge belongs to in G1
        cand_cycle = None
        if not cand_is_bridge and s_name.startswith("Scenario 1"):
            # Find simple cycle containing candidate edge
            # Temporarily remove candidate edge, find path between endpoints
            G_temp = G_curr.copy()
            G_temp.remove_edge(*candidate_edge)
            alt_path = nx.shortest_path(G_temp, candidate_edge[0], candidate_edge[1], weight="length_km")
            cand_cycle = [candidate_edge[0]] + alt_path
            cand_cycle_km = nx.shortest_path_length(G_temp, candidate_edge[0], candidate_edge[1], weight="length_km") + 7.7844
            
        scenarios_summary.append({
            "scenario": s_name,
            "csmt_degree": csmt_deg,
            "msd_degree": msd_deg,
            "candidate_is_bridge": cand_is_bridge,
            "total_bridges": len(bridges),
            "total_cut_points": cut_points,
            "total_cycles": cycle_count,
            "candidate_cycle_length_km": round(cand_cycle_km, 4) if cand_cycle else None,
            "candidate_cycle_path": cand_cycle if cand_cycle else None,
            "routing_results": pair_results
        })

    with open(results_dir / "scenario_evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(scenarios_summary, f, indent=2)

    # Print summary comparison table
    print("=== SCENARIO COMPARISON TABLE ===")
    print(f"{'Metric':<35} | {'Baseline (Release v2.0)':<25} | {'Scenario 1 (Restored Edge)':<25}")
    print("-" * 90)
    print(f"{'CSMT Degree':<35} | {scenarios_summary[0]['csmt_degree']:<25} | {scenarios_summary[1]['csmt_degree']:<25}")
    print(f"{'MSD Degree':<35} | {scenarios_summary[0]['msd_degree']:<25} | {scenarios_summary[1]['msd_degree']:<25}")
    print(f"{'Candidate Edge is Bridge?':<35} | {str(scenarios_summary[0]['candidate_is_bridge']):<25} | {str(scenarios_summary[1]['candidate_is_bridge']):<25}")
    print(f"{'Total Bridges in Graph':<35} | {scenarios_summary[0]['total_bridges']:<25} | {scenarios_summary[1]['total_bridges']:<25}")
    print(f"{'Total Articulation Points':<35} | {scenarios_summary[0]['total_cut_points']:<25} | {scenarios_summary[1]['total_cut_points']:<25}")
    print(f"{'Total Independent Cycles':<35} | {scenarios_summary[0]['total_cycles']:<25} | {scenarios_summary[1]['total_cycles']:<25}")
    
    print("\n=== ROUTING DISTANCES COMPARISON ===")
    print(f"{'OD Pair':<30} | {'Baseline km (hops)':<25} | {'Scenario 1 km (hops)':<25} | {'Delta km'}")
    print("-" * 90)
    for r0, r1 in zip(scenarios_summary[0]["routing_results"], scenarios_summary[1]["routing_results"]):
        d0_str = f"{r0['length_km']:.2f} km ({r0['hops']} hops)"
        d1_str = f"{r1['length_km']:.2f} km ({r1['hops']} hops)"
        delta = r1['length_km'] - r0['length_km']
        print(f"{r0['target'] + ' (' + r0['target_name'] + ')':<30} | {d0_str:<25} | {d1_str:<25} | {delta:+.2f} km")

if __name__ == "__main__":
    main()
