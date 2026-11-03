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
    
    candidate_id = "v2.0:CSMT|JN:@72.836140,19.007082"
    u_cand = "CSMT"
    v_cand = "JN:@72.836140,19.007082"
    
    candidate_edge = next((e for e in edges if e["edge_id"] == candidate_id), None)
    if not candidate_edge:
        print(f"FATAL: Candidate edge {candidate_id} NOT found!")
        return

    # 1. Incident edges
    csmt_incident = [e for e in edges if u_cand in (e["from_node"], e["to_node"])]
    jn_incident = [e for e in edges if v_cand in (e["from_node"], e["to_node"])]
    
    # 2. Build full graph G
    G = nx.Graph()
    for n in nodes:
        G.add_node(n["node_id"], **n)
    for e in edges:
        d = dict(e)
        d["length_km"] = float(d["length_km"])
        G.add_edge(d["from_node"], d["to_node"], **d)
        
    # Check bridge status
    is_bridge = (u_cand, v_cand) in nx.bridges(G) or (v_cand, u_cand) in nx.bridges(G)
    
    # Check degree
    deg_csmt = G.degree(u_cand)
    deg_jn = G.degree(v_cand)
    
    # Local subgraph around CSMT and JN (4 hops)
    sub_nodes = set([u_cand, v_cand])
    for _ in range(4):
        next_layer = set()
        for node in sub_nodes:
            next_layer.update(G.neighbors(node))
        sub_nodes.update(next_layer)
        
    subG = G.subgraph(sub_nodes)
    sub_edges = [dict(G[u][v], from_node=u, to_node=v) for u, v in subG.edges()]
    sub_nodes_data = [node_dict[n] for n in sub_nodes]
    
    # Check what happens if candidate edge is removed
    G_rem = G.copy()
    G_rem.remove_edge(u_cand, v_cand)
    
    comps_rem = list(nx.connected_components(G_rem))
    comps_rem.sort(key=len, reverse=True)
    
    # Find which component CSMT is in
    csmt_comp = next(c for c in comps_rem if u_cand in c)
    jn_comp = next(c for c in comps_rem if v_cand in c)
    is_disconnected = (u_cand not in jn_comp)
    
    # Reachable stations from CSMT before and after
    st_ids = set(n["node_id"] for n in nodes if n["node_type"] == "station")
    
    # In original G
    orig_comp = next(c for c in nx.connected_components(G) if u_cand in c)
    reachable_st_before = len(orig_comp & st_ids)
    reachable_st_after = len(csmt_comp & st_ids)
    
    output = {
        "candidate_edge": candidate_edge,
        "endpoint_u": node_dict.get(u_cand),
        "endpoint_v": node_dict.get(v_cand),
        "csmt_degree": deg_csmt,
        "jn_degree": deg_jn,
        "csmt_incident_edges": csmt_incident,
        "jn_incident_edges": jn_incident,
        "structural_analysis": {
            "is_bridge": is_bridge,
            "has_alternate_path_without_candidate": nx.has_path(G_rem, u_cand, v_cand),
            "shortest_path_without_candidate": list(nx.shortest_path(G_rem, u_cand, v_cand)) if nx.has_path(G_rem, u_cand, v_cand) else None,
            "shortest_path_km_without_candidate": nx.shortest_path_length(G_rem, u_cand, v_cand, weight="length_km") if nx.has_path(G_rem, u_cand, v_cand) else None,
            "csmt_component_size_after_removal": len(csmt_comp),
            "csmt_component_stations_after_removal": list(csmt_comp & st_ids),
            "reachable_stations_before": reachable_st_before,
            "reachable_stations_after": reachable_st_after,
            "stations_lost": reachable_st_before - reachable_st_after
        },
        "local_network": {
            "subgraph_nodes_count": len(sub_nodes),
            "subgraph_edges_count": len(sub_edges),
            "subgraph_stations": [node_dict[n] for n in sub_nodes if node_dict[n]["node_type"] == "station"],
            "subgraph_junctions": [node_dict[n] for n in sub_nodes if node_dict[n]["node_type"] == "junction"]
        }
    }
    
    out_json = results_dir / "csmt_edge_structural_data.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
        
    print(f"Results written to {out_json}")
    print(f"Candidate Edge: {candidate_id}")
    print(f"Length: {candidate_edge['length_km']} km, Chord: {candidate_edge['length_chord_km']} km")
    print(f"CSMT Degree: {deg_csmt}, Incident edges count: {len(csmt_incident)}")
    for e in csmt_incident:
        print(f"  CSMT incident: {e['edge_id']} -> to {e['to_node'] if e['from_node'] == 'CSMT' else e['from_node']}, len: {e['length_km']}, joins: '{e['joins']}', line: '{e['line_name']}'")
    print(f"JN Degree: {deg_jn}, Incident edges count: {len(jn_incident)}")
    for e in jn_incident:
        print(f"  JN incident: {e['edge_id']} -> to {e['to_node'] if e['from_node'] == v_cand else e['from_node']}, len: {e['length_km']}, joins: '{e['joins']}', line: '{e['line_name']}'")
    print(f"Is Bridge in G: {is_bridge}")
    print(f"CSMT component size after removal: {len(csmt_comp)} nodes, stations: {list(csmt_comp & st_ids)}")
    print(f"Alternate path between CSMT and JN exists: {nx.has_path(G_rem, u_cand, v_cand)}")

if __name__ == "__main__":
    main()
