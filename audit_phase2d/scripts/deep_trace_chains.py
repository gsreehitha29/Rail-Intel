import pyarrow.parquet as pq
import networkx as nx
import csv
import json

work_dir = "03_graph_construction/graph_v2_0_open/work"
release_dir = "03_graph_construction/release/rail-intel-v2.0-open/graph"

target_chains = {
    "CSMT_4365": 4365,
    "HWH_8315": 8315,
    "HWH_7959": 7959,
    "MAS_25": 25,
    "MAS_26": 26,
    "MMCT_630": 630,
    "MMCT_804": 804,
    "MMCT_3929": 3929,
    "MMCT_806": 806,
    "SDAH_3867": 3867
}

# 1. Load station_snaps
stations = set()
vmap = {}
snap_rows = {}
with open(f"{work_dir}/station_snaps.csv", "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        v = row.get("vertex")
        code = row.get("code")
        nid = row.get("node_id")
        if v and code:
            vmap[v] = code
            stations.add(code)
            snap_rows[v] = dict(row)
        elif v and nid:
            node_name = f"OSM:{nid}"
            vmap[v] = node_name
            stations.add(node_name)
            snap_rows[v] = dict(row)

# 2. Load network_vertices
v_table = pq.read_table(f"{work_dir}/network_vertices.parquet").to_pydict()
verts = {v: {"lon": float(v_table["lon"][i]), "lat": float(v_table["lat"][i]), "osm_node": int(v_table["osm_node"][i]), "kind": str(v_table["kind"][i])}
         for i, v in enumerate(v_table["vertex"])}

# 3. Load network_edges
table = pq.read_table(f"{work_dir}/network_edges.parquet")
edges = table.to_pydict()

# Group edges by chain
chain_edges_map = {}
for i in range(len(edges["chain"])):
    c = int(edges["chain"][i])
    chain_edges_map.setdefault(c, []).append({
        "index": i,
        "a": edges["a"][i],
        "b": edges["b"][i],
        "km": float(edges["km"][i]),
        "kind": edges["kind"][i],
        "gauge": edges["gauge"][i]
    })

# Build Stage C1 graph G
G = nx.Graph()
G.add_nodes_from(set(vmap.values()))
for i in range(len(edges["a"])):
    a = edges["a"][i]
    b = edges["b"][i]
    km = float(edges["km"][i])
    a_mapped = vmap.get(a, a)
    b_mapped = vmap.get(b, b)
    if a_mapped == b_mapped:
        continue
    if G.has_edge(a_mapped, b_mapped) and G[a_mapped][b_mapped]["km"] <= km:
        continue
    G.add_edge(a_mapped, b_mapped, km=km, raw_a=a, raw_b=b, chain=int(edges["chain"][i]), kind=edges["kind"][i], edge_idx=i)

# Simulate prune(G, stations) step-by-step recording which edges/nodes of target chains get dropped
pruned_records = {}
round_num = 0
while True:
    d1 = [n for n, d in G.degree() if d <= 1 and n not in stations]
    if not d1:
        break
    round_num += 1
    for n in d1:
        nbrs = list(G.neighbors(n))
        dropped = []
        for nbr in nbrs:
            ed = G[n][nbr]
            dropped.append({
                "u": n, "v": nbr, "km": ed["km"],
                "raw_a": ed.get("raw_a"), "raw_b": ed.get("raw_b"),
                "chain": ed.get("chain"), "kind": ed.get("kind"),
                "edge_idx": ed.get("edge_idx")
            })
        pruned_records[n] = {
            "round": round_num,
            "degree": G.degree(n),
            "neighbors": nbrs,
            "edges_dropped": dropped
        }
        G.remove_node(n)

# 4. Load released edges to see what survived into the release
released_edges = []
with open(f"{release_dir}/edges.csv", "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        released_edges.append(dict(row))

# Analysis per target chain
chain_audit = {}
for name, cid in target_chains.items():
    cedges = chain_edges_map.get(cid, [])
    tot_km = sum(e["km"] for e in cedges)
    
    # Vertices involved in this chain
    c_verts = set()
    for e in cedges:
        c_verts.add(e["a"])
        c_verts.add(e["b"])
        
    mapped_verts = {v: vmap.get(v, v) for v in c_verts}
    
    # Track stations on this chain
    stations_on_chain = {v: snap_rows[v]["code"] for v in c_verts if v in snap_rows and snap_rows[v].get("code")}
    
    # Find which edges and vertices of this chain were pruned
    pruned_nodes_in_chain = {}
    pruned_edges_in_chain = []
    for v, mv in mapped_verts.items():
        if mv in pruned_records:
            pruned_nodes_in_chain[v] = pruned_records[mv]
            for ed in pruned_records[mv]["edges_dropped"]:
                if ed.get("chain") == cid:
                    pruned_edges_in_chain.append(ed)
                    
    pruned_km = sum(e["km"] for e in pruned_edges_in_chain)
    survived_km = tot_km - pruned_km
    
    chain_audit[name] = {
        "chain_id": cid,
        "total_edges_c1": len(cedges),
        "total_km_c1": round(tot_km, 4),
        "total_vertices_c1": len(c_verts),
        "stations_on_chain": stations_on_chain,
        "pruned_vertices_count": len(pruned_nodes_in_chain),
        "pruned_edges_count": len(pruned_edges_in_chain),
        "pruned_km": round(pruned_km, 4),
        "survived_km": round(survived_km, 4),
        "pruned_nodes_details": pruned_nodes_in_chain,
        "pruned_edges_details": pruned_edges_in_chain,
        "all_c1_edges": cedges
    }
    
    print(f"\n==========================================")
    print(f"CHAIN: {name} (ID: {cid})")
    print(f"  C1 Length: {tot_km:.4f} km | Edges: {len(cedges)} | Vertices: {len(c_verts)}")
    print(f"  Stations on Chain: {list(stations_on_chain.values())}")
    print(f"  Pruned Vertices: {len(pruned_nodes_in_chain)} | Pruned Edges: {len(pruned_edges_in_chain)}")
    print(f"  Pruned Length: {pruned_km:.4f} km | Survived Length: {survived_km:.4f} km")
    if pruned_edges_in_chain:
        print("  Pruned Edges Sample:")
        for pe in pruned_edges_in_chain:
            print(f"    - {pe['raw_a']} <-> {pe['raw_b']} ({pe['km']:.4f} km, {pe['kind']}) in round {pruned_nodes_in_chain.get(pe['u'], {}).get('round')}")

with open("audit_phase2d/results/task_a_deep_chain_trace.json", "w", encoding="utf-8") as f:
    json.dump(chain_audit, f, indent=2)
