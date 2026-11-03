import csv
import json
import pathlib
import networkx as nx

def main():
    root = pathlib.Path(".")
    release_dir = root / "03_graph_construction" / "release" / "rail-intel-v2.0-open"
    results_dir = root / "audit_phase2b" / "results"
    
    nodes_file = release_dir / "graph" / "nodes.csv"
    edges_file = release_dir / "graph" / "edges.csv"
    
    with open(nodes_file, "r", encoding="utf-8") as f:
        nodes = list(csv.DictReader(f))
    with open(edges_file, "r", encoding="utf-8") as f:
        edges = list(csv.DictReader(f))
        
    node_dict = {n["node_id"]: n for n in nodes}
    
    # 1. South Mumbai bounding box: lat 18.92 to 19.06, lon 72.80 to 72.88
    south_mumbai_nodes = [
        n for n in nodes 
        if 72.80 <= float(n["longitude"]) <= 72.88 and 18.92 <= float(n["latitude"]) <= 19.06
    ]
    south_mumbai_node_ids = set(n["node_id"] for n in south_mumbai_nodes)
    
    # Edges touching South Mumbai nodes
    south_mumbai_edges = [
        e for e in edges
        if e["from_node"] in south_mumbai_node_ids or e["to_node"] in south_mumbai_node_ids
    ]
    
    # 2. Check stations in South Mumbai
    stations = [n for n in south_mumbai_nodes if n["node_type"] == "station"]
    junctions = [n for n in south_mumbai_nodes if n["node_type"] == "junction"]
    
    # Check specifically for CSMT, Churchgate, Masjid, Byculla, Sandhurst Road, Parel, Dadar
    target_names = ["CSMT", "CCG", "MSD", "SNRD", "BY", "CHG", "CRD", "PR", "DR", "DDR", "VDLR", "CLA"]
    target_stations = [n for n in nodes if n.get("station_code") in target_names or n["node_id"] in target_names]
    
    # 3. Check graph traversal starting from CSMT
    G = nx.Graph()
    for n in nodes:
        G.add_node(n["node_id"], **n)
    for e in edges:
        d = dict(e)
        d["length_km"] = float(d["length_km"])
        G.add_edge(d["from_node"], d["to_node"], **d)
        
    # BFS up to 6 hops from CSMT
    bfs_tree_edges = []
    visited = { "CSMT": 0 }
    queue = ["CSMT"]
    while queue:
        curr = queue.pop(0)
        curr_dist = visited[curr]
        if curr_dist >= 6:
            continue
        for nbr in G.neighbors(curr):
            if nbr not in visited:
                visited[nbr] = curr_dist + 1
                queue.append(nbr)
                edge_data = G[curr][nbr]
                bfs_tree_edges.append({
                    "hop": curr_dist + 1,
                    "from": curr,
                    "to": nbr,
                    "edge_id": edge_data["edge_id"],
                    "length_km": edge_data["length_km"],
                    "line_name": edge_data.get("line_name", ""),
                    "joins": edge_data.get("joins", ""),
                    "trains_2017": edge_data.get("trains_2017", 0),
                    "to_node_type": node_dict[nbr]["node_type"],
                    "to_node_name": node_dict[nbr].get("node_name", "")
                })

    out = {
        "south_mumbai_nodes_count": len(south_mumbai_nodes),
        "south_mumbai_stations_count": len(stations),
        "south_mumbai_junctions_count": len(junctions),
        "stations": [
            {
                "node_id": n["node_id"],
                "node_name": n["node_name"],
                "station_code": n["station_code"],
                "lon": float(n["longitude"]),
                "lat": float(n["latitude"]),
                "degree": int(n["degree"])
            }
            for n in sorted(stations, key=lambda x: float(x["latitude"]))
        ],
        "junctions": [
            {
                "node_id": n["node_id"],
                "lon": float(n["longitude"]),
                "lat": float(n["latitude"]),
                "degree": int(n["degree"])
            }
            for n in sorted(junctions, key=lambda x: float(x["latitude"]))
        ],
        "bfs_from_csmt_up_to_6_hops": bfs_tree_edges,
        "known_mumbai_targets": [
            {
                "node_id": n["node_id"],
                "station_code": n["station_code"],
                "node_name": n["node_name"],
                "degree": int(n["degree"]),
                "lon": float(n["longitude"]),
                "lat": float(n["latitude"])
            }
            for n in target_stations
        ]
    }
    
    out_file = results_dir / "south_mumbai_network_trace.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
        
    print(f"South Mumbai trace saved to {out_file}")
    print(f"Stations in South Mumbai: {[s['node_id'] for s in out['stations']]}")
    print("\nBFS from CSMT (first 8 hops/branches):")
    for b in bfs_tree_edges[:10]:
        print(f"  Hop {b['hop']}: {b['from']} -> {b['to']} ({b['to_node_type']}: {b['to_node_name']}), {b['length_km']} km, joins='{b['joins']}', line='{b['line_name']}'")

if __name__ == "__main__":
    main()
