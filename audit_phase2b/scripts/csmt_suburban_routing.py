import csv
import json
import pathlib
import networkx as nx

def main():
    root = pathlib.Path(".")
    release_dir = root / "03_graph_construction" / "release" / "rail-intel-v2.0-open"
    results_dir = root / "audit_phase2b" / "results"
    
    edges = list(csv.DictReader(open(release_dir / "graph" / "edges.csv", encoding="utf-8")))
    nodes = {n["node_id"]: n for n in csv.DictReader(open(release_dir / "graph" / "nodes.csv", encoding="utf-8"))}

    G = nx.Graph()
    for e in edges:
        d = dict(e)
        d["length_km"] = float(d["length_km"])
        G.add_edge(d["from_node"], d["to_node"], **d)

    targets = ["MSD", "SNRD", "BY", "CHG", "CRD", "PR", "DR", "KYN", "TNA"]
    
    paths_data = {}
    for tgt in targets:
        if nx.has_path(G, "CSMT", tgt):
            path = nx.shortest_path(G, "CSMT", tgt, weight="length_km")
            length = nx.shortest_path_length(G, "CSMT", tgt, weight="length_km")
            # compute straight line chord
            p1 = [float(nodes["CSMT"]["longitude"]), float(nodes["CSMT"]["latitude"])]
            p2 = [float(nodes[tgt]["longitude"]), float(nodes[tgt]["latitude"])]
            # haversine
            import math
            phi1, phi2 = math.radians(p1[1]), math.radians(p2[1])
            dphi = math.radians(p2[1] - p1[1])
            dlam = math.radians(p2[0] - p1[0])
            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
            chord = 2 * 6371.0088 * math.asin(math.sqrt(min(1.0, max(0.0, a))))
            
            paths_data[tgt] = {
                "target_name": nodes[tgt]["node_name"],
                "path_nodes": path,
                "path_length_km": round(length, 2),
                "chord_km": round(chord, 2),
                "hops": len(path) - 1,
                "detour_ratio": round(length / chord, 2) if chord > 0 else None
            }
            print(f"CSMT -> {tgt} ({nodes[tgt]['node_name']}): {round(length, 2)} km (chord {round(chord, 2)} km, {len(path)-1} hops, detour {round(length/chord, 2)}x)")
            print(f"   Path: {' -> '.join(path)}")

    out_file = results_dir / "csmt_suburban_routing_paths.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(paths_data, f, indent=2)

if __name__ == "__main__":
    main()
