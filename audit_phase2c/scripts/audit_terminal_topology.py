import pyarrow.parquet as pq
import networkx as nx
import csv
import json
import math

def haversine(lon1, lat1, lon2, lat2):
    R = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))

work_dir = "03_graph_construction/graph_v2_0_open/work"

# Load station snaps
stations_meta = {
    "HWH": {"code": "HWH", "name": "Howrah Junction", "lon": 88.3428112, "lat": 22.5828709},
    "MAS": {"code": "MAS", "name": "Chennai Central", "lon": 80.2759622, "lat": 13.0824232},
    "SDAH": {"code": "SDAH", "name": "Sealdah", "lon": 88.3711047, "lat": 22.5679661},
    "MMCT": {"code": "MMCT", "name": "Mumbai Central", "lon": 72.8193152, "lat": 18.9695855}
}

with open(f"{work_dir}/station_snaps.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        c = row.get("code")
        if c in stations_meta:
            stations_meta[c]["snap_row"] = dict(row)

# Load network_vertices
v_table = pq.read_table(f"{work_dir}/network_vertices.parquet").to_pydict()
vertices = {}
for i, v in enumerate(v_table["vertex"]):
    vertices[v] = {
        "vertex": v,
        "lon": float(v_table["lon"][i]),
        "lat": float(v_table["lat"][i]),
        "osm_node": int(v_table["osm_node"][i]),
        "kind": str(v_table["kind"][i])
    }

# Load network_edges
e_table = pq.read_table(f"{work_dir}/network_edges.parquet").to_pydict()
G_c1 = nx.Graph()
for i in range(len(e_table["a"])):
    a = e_table["a"][i]
    b = e_table["b"][i]
    km = float(e_table["km"][i])
    G_c1.add_edge(a, b, km=km, chain=int(e_table["chain"][i]), kind=e_table["kind"][i], gauge=e_table["gauge"][i])

print(f"Total C1 vertices: {len(vertices)}, Total C1 edges: {G_c1.number_of_edges()}")

# For each target terminal, find nearby vertices (within 100m, and within 500m)
audit_results = {}

for code, info in stations_meta.items():
    st_lon, st_lat = info["lon"], info["lat"]
    snapped_v = info["snap_row"].get("vertex")
    snap_dist = float(info["snap_row"].get("snap_m", 0.0))

    # Find all vertices within 500m
    near_verts = []
    for v, vdata in vertices.items():
        d_m = haversine(st_lon, st_lat, vdata["lon"], vdata["lat"]) * 1000.0
        if d_m <= 500.0:
            deg = G_c1.degree(v) if G_c1.has_node(v) else 0
            near_verts.append({
                "vertex": v,
                "dist_to_station_m": round(d_m, 2),
                "lon": vdata["lon"],
                "lat": vdata["lat"],
                "osm_node": vdata["osm_node"],
                "kind": vdata["kind"],
                "degree_c1": deg,
                "is_snapped": (v == snapped_v)
            })

    near_verts.sort(key=lambda x: x["dist_to_station_m"])
    within_100m = [v for v in near_verts if v["dist_to_station_m"] <= 100.0]

    # Find edges incident to vertices within 500m
    near_v_set = set(v["vertex"] for v in near_verts)
    subgraph_edges = []
    for u, v, edata in G_c1.edges(near_v_set, data=True):
        subgraph_edges.append({
            "u": u,
            "v": v,
            "km": edata["km"],
            "chain": edata["chain"],
            "kind": edata["kind"],
            "gauge": edata["gauge"],
            "u_dist": next(x["dist_to_station_m"] for x in near_verts if x["vertex"] == u) if u in near_v_set else None,
            "v_dist": next(x["dist_to_station_m"] for x in near_verts if x["vertex"] == v) if v in near_v_set else None
        })

    audit_results[code] = {
        "station_info": info,
        "snapped_vertex": snapped_v,
        "snap_distance_m": snap_dist,
        "vertices_within_100m_count": len(within_100m),
        "vertices_within_100m": within_100m,
        "vertices_within_500m_count": len(near_verts),
        "subgraph_edges_count": len(subgraph_edges),
        "subgraph_edges": subgraph_edges
    }

    print(f"\n==========================================")
    print(f"Station {code} ({info['name']}):")
    print(f"  Snapped vertex: {snapped_v} (distance: {snap_dist} m)")
    print(f"  Vertices within 100m: {len(within_100m)}")
    for wv in within_100m:
        print(f"    - {wv['vertex']}: {wv['dist_to_station_m']} m, degree_c1={wv['degree_c1']}, osm_node={wv['osm_node']}, kind={wv['kind']}, is_snapped={wv['is_snapped']}")
    print(f"  Vertices within 500m: {len(near_verts)}")
    print(f"  Incident edges within 500m: {len(subgraph_edges)}")

with open("audit_phase2c/results/task2_terminal_c1_inspection.json", "w", encoding="utf-8") as f:
    json.dump(audit_results, f, indent=2)
