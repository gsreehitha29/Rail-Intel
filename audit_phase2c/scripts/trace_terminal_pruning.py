import pyarrow.parquet as pq
import networkx as nx
import csv
import json

work_dir = "03_graph_construction/graph_v2_0_open/work"

# Load station_snaps
stations = set()
vmap = {}
snap_lookup = {}
with open(f"{work_dir}/station_snaps.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        v = row.get("vertex")
        code = row.get("code")
        nid = row.get("node_id")
        if v and code:
            vmap[v] = code
            stations.add(code)
            snap_lookup[v] = dict(row)
        elif v and nid:
            node_name = f"OSM:{nid}"
            vmap[v] = node_name
            stations.add(node_name)
            snap_lookup[v] = dict(row)

# Load network_vertices
v_table = pq.read_table(f"{work_dir}/network_vertices.parquet").to_pydict()
verts = {v: {"lon": float(v_table["lon"][i]), "lat": float(v_table["lat"][i]), "osm_node": int(v_table["osm_node"][i]), "kind": str(v_table["kind"][i])}
         for i, v in enumerate(v_table["vertex"])}

# Load network_edges
table = pq.read_table(f"{work_dir}/network_edges.parquet")
edges = table.to_pydict()

G = nx.Graph()
G.add_nodes_from(set(vmap.values()))
edge_lookup = {}
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
    G.add_edge(a_mapped, b_mapped, km=km, raw_a=a, raw_b=b, chain=int(edges["chain"][i]), kind=edges["kind"][i])

# Trace prune(G, stations) step by step and record all deleted nodes/edges
pruned_history = {}
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
                "chain": ed.get("chain"), "kind": ed.get("kind")
            })
        pruned_history[n] = {
            "round": round_num,
            "degree_before_prune": G.degree(n),
            "neighbors": nbrs,
            "edges_dropped": dropped
        }
        G.remove_node(n)

print(f"Total nodes pruned nationwide: {len(pruned_history)} across {round_num} rounds.")

# Now analyze target terminals: HWH, MAS, SDAH, MMCT, CSMT
terminals_analysis = {}
target_data = [
    ("HWH", 88.3428112, 22.5828709),
    ("MAS", 80.2759622, 13.0824232),
    ("SDAH", 88.3711047, 22.5679661),
    ("MMCT", 72.8193152, 18.9695855),
    ("CSMT", 72.8357856, 18.9404925)
]

import math
def haversine(lon1, lat1, lon2, lat2):
    R = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))

for code, st_lon, st_lat in target_data:
    # 1. Check all vertices in C1 within 500m of station
    nearby_c1_verts = []
    for v, vinfo in verts.items():
        d_m = haversine(st_lon, st_lat, vinfo["lon"], vinfo["lat"]) * 1000.0
        if d_m <= 500.0:
            nearby_c1_verts.append((v, d_m, vinfo))
    
    nearby_c1_verts.sort(key=lambda x: x[1])

    # Check which of these were pruned
    pruned_nearby = []
    surviving_nearby = []
    for v, d_m, vinfo in nearby_c1_verts:
        mapped_name = vmap.get(v, v)
        if mapped_name in pruned_history:
            pruned_nearby.append({
                "vertex": v,
                "mapped_name": mapped_name,
                "dist_m": round(d_m, 2),
                "vinfo": vinfo,
                "prune_details": pruned_history[mapped_name]
            })
        else:
            surviving_nearby.append({
                "vertex": v,
                "mapped_name": mapped_name,
                "dist_m": round(d_m, 2),
                "vinfo": vinfo,
                "in_stations": mapped_name in stations,
                "degree_post_prune": G.degree(mapped_name) if G.has_node(mapped_name) else 0
            })

    terminals_analysis[code] = {
        "code": code,
        "lon": st_lon,
        "lat": st_lat,
        "total_c1_within_500m": len(nearby_c1_verts),
        "total_pruned_within_500m": len(pruned_nearby),
        "pruned_vertices": pruned_nearby,
        "surviving_vertices": surviving_nearby
    }

    print(f"\n==========================================")
    print(f"TERMINAL: {code}")
    print(f"  C1 vertices within 500m: {len(nearby_c1_verts)}")
    print(f"  Pruned vertices within 500m: {len(pruned_nearby)}")
    for p in pruned_nearby:
        ed = p["prune_details"]["edges_dropped"]
        tot_km = sum(e["km"] for e in ed)
        print(f"    - PRUNED: {p['vertex']} ({p['dist_m']} m) | kind: {p['vinfo']['kind']} | osm_node: {p['vinfo']['osm_node']} | dropped edges: {len(ed)}, km: {tot_km:.4f} km | chains: {[e['chain'] for e in ed]}")
    print(f"  Surviving vertices within 500m: {len(surviving_nearby)}")
    for s in surviving_nearby:
        print(f"    + SURVIVED: {s['vertex']} -> {s['mapped_name']} ({s['dist_m']} m) | in_stations: {s['in_stations']} | degree: {s['degree_post_prune']}")

with open("audit_phase2c/results/task4_5_terminals_prune_audit.json", "w", encoding="utf-8") as f:
    json.dump(terminals_analysis, f, indent=2)
