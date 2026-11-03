import csv
import json
import pathlib
import networkx as nx

def main():
    root = pathlib.Path("c:/Users/Sreehitha/OneDrive/Desktop/Major Project\Rail-Intel")
    release_dir = root / "03_graph_construction" / "release" / "rail-intel-v2.0-open"
    results_dir = root / "audit_phase2b" / "results"
    
    nodes = {n["node_id"]: n for n in csv.DictReader(open(release_dir / "graph" / "nodes.csv", encoding="utf-8"))}
    edges = list(csv.DictReader(open(release_dir / "graph" / "edges.csv", encoding="utf-8")))

    G = nx.Graph()
    for e in edges:
        d = dict(e)
        d["length_km"] = float(d["length_km"])
        G.add_edge(d["from_node"], d["to_node"], **d)

    # Subgraph for South Mumbai approach:
    # Starting from CSMT and Masjid, explore up to Dadar and Vadala Road
    seeds = ["CSMT", "MSD", "SNRD", "DKRD"]
    local_nodes = set(seeds)
    for _ in range(5):
        next_nodes = set()
        for u in local_nodes:
            for v in G.neighbors(u):
                # keep south of Kurla (lat <= 19.07)
                if float(nodes[v]["latitude"]) <= 19.07:
                    next_nodes.add(v)
        local_nodes.update(next_nodes)

    subG = G.subgraph(local_nodes)
    
    local_nodes_list = []
    for nid in sorted(local_nodes):
        n = nodes[nid]
        local_nodes_list.append({
            "node_id": nid,
            "node_type": n["node_type"],
            "node_name": n["node_name"],
            "station_code": n["station_code"],
            "lon": float(n["longitude"]),
            "lat": float(n["latitude"]),
            "degree_full_graph": int(n["degree"]),
            "degree_local_subgraph": subG.degree(nid)
        })

    local_edges_list = []
    for u, v in subG.edges():
        e = subG[u][v]
        local_edges_list.append({
            "edge_id": e["edge_id"],
            "from_node": u,
            "to_node": v,
            "from_name": nodes[u]["node_name"] or nodes[u]["node_id"],
            "to_name": nodes[v]["node_name"] or nodes[v]["node_id"],
            "length_km": e["length_km"],
            "chord_km": float(e.get("length_chord_km", 0)),
            "line_name": e.get("line_name", ""),
            "joins": e.get("joins", ""),
            "scheduled_2017": e.get("scheduled_2017", ""),
            "trains_2017": int(e.get("trains_2017", 0))
        })

    # Generate Mermaid diagram
    mermaid_lines = ["graph TD"]
    for e in sorted(local_edges_list, key=lambda x: x["length_km"], reverse=True):
        u_label = f"{nodes[e['from_node']]['node_name']} ({e['from_node']})" if nodes[e['from_node']]['node_name'] else e['from_node']
        v_label = f"{nodes[e['to_node']]['node_name']} ({e['to_node']})" if nodes[e['to_node']]['node_name'] else e['to_node']
        
        # Clean labels for mermaid
        u_id = e['from_node'].replace(":", "_").replace("@", "_").replace(",", "_").replace(".", "_")
        v_id = e['to_node'].replace(":", "_").replace("@", "_").replace(",", "_").replace(".", "_")
        
        edge_label = f"{e['length_km']} km"
        if e['joins']:
            edge_label += f" [{e['joins']}]"
        if e['trains_2017'] > 0:
            edge_label += f" ({e['trains_2017']} trains)"
            
        mermaid_lines.append(f'    {u_id}["{u_label}"] ---|"{edge_label}"| {v_id}["{v_label}"]')

    out = {
        "local_nodes": local_nodes_list,
        "local_edges": local_edges_list,
        "mermaid_diagram": "\n".join(mermaid_lines)
    }

    out_json = results_dir / "csmt_local_topology_subgraph.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    out_mmd = results_dir / "csmt_local_topology.mmd"
    with open(out_mmd, "w", encoding="utf-8") as f:
        f.write("\n".join(mermaid_lines))

    print(f"Subgraphs saved. Nodes: {len(local_nodes_list)}, Edges: {len(local_edges_list)}")

if __name__ == "__main__":
    main()
