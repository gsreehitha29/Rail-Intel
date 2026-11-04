import csv
import json
import pathlib
import math
import networkx as nx
import pyarrow.parquet as pq

def haversine_km(lon1, lat1, lon2, lat2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    return 2.0 * 6371.0088 * math.asin(math.sqrt(min(1.0, max(0.0, a))))

def main():
    root = pathlib.Path(__file__).resolve().parents[2]
    release_dir = root / "03_graph_construction" / "release" / "rail-intel-v2.0-open"
    work_dir = root / "03_graph_construction" / "graph_v2_0_open" / "work"
    results_dir = root / "audit_phase2b1" / "results"
    artifacts_dir = root / "audit_phase2b1" / "artifacts"

    # ==========================================
    # TASK 1: RELEASED TOPOLOGY & SERVICE LAYER
    # ==========================================
    print("--- TASK 1: Released Topology Verification ---")
    nodes_raw = list(csv.DictReader(open(release_dir / "graph" / "nodes.csv", encoding="utf-8")))
    edges_raw = list(csv.DictReader(open(release_dir / "graph" / "edges.csv", encoding="utf-8")))
    nodes = {n["node_id"]: n for n in nodes_raw}
    
    csmt_node = nodes["CSMT"]
    msd_node = nodes["MSD"]
    
    csmt_edges = [e for e in edges_raw if "CSMT" in (e["from_node"], e["to_node"])]
    msd_edges = [e for e in edges_raw if "MSD" in (e["from_node"], e["to_node"])]
    
    # Build NetworkX graph
    G = nx.Graph()
    for n in nodes_raw:
        G.add_node(n["node_id"], **n)
    for e in edges_raw:
        d = dict(e)
        d["length_km"] = float(d["length_km"])
        G.add_edge(d["from_node"], d["to_node"], **d)
        
    shortest_path = nx.shortest_path(G, "CSMT", "MSD", weight="length_km")
    shortest_path_km = nx.shortest_path_length(G, "CSMT", "MSD", weight="length_km")
    chord_csmt_msd = haversine_km(
        float(csmt_node["longitude"]), float(csmt_node["latitude"]),
        float(msd_node["longitude"]), float(msd_node["latitude"])
    )
    
    # Service layer records for CSMT <-> MSD
    service_pairs = list(csv.DictReader(open(release_dir / "service_2017" / "station_pairs.csv", encoding="utf-8")))
    csmt_msd_service = [r for r in service_pairs if (r["from_station"] == "CSMT" and r["to_station"] == "MSD") or (r["from_station"] == "MSD" and r["to_station"] == "CSMT")]
    
    task1_data = {
        "csmt_node": csmt_node,
        "msd_node": msd_node,
        "csmt_incident_edges": csmt_edges,
        "msd_incident_edges": msd_edges,
        "shortest_path": shortest_path,
        "shortest_path_km": round(shortest_path_km, 4),
        "chord_km": round(chord_csmt_msd, 4),
        "detour_ratio": round(shortest_path_km / chord_csmt_msd, 2),
        "hops": len(shortest_path) - 1,
        "path_breakdown": [
            {
                "step": i + 1,
                "from": shortest_path[i],
                "to": shortest_path[i+1],
                "edge_id": G[shortest_path[i]][shortest_path[i+1]]["edge_id"],
                "length_km": G[shortest_path[i]][shortest_path[i+1]]["length_km"],
                "line_name": G[shortest_path[i]][shortest_path[i+1]]["line_name"],
                "joins": G[shortest_path[i]][shortest_path[i+1]]["joins"]
            }
            for i in range(len(shortest_path) - 1)
        ],
        "service_layer_records": csmt_msd_service
    }
    
    with open(results_dir / "task1_released_topology.json", "w", encoding="utf-8") as f:
        json.dump(task1_data, f, indent=2)
        
    print(f"CSMT incident edges: {len(csmt_edges)}, MSD incident edges: {len(msd_edges)}")
    print(f"CSMT-MSD path: {shortest_path_km:.2f} km across {len(shortest_path)-1} hops (chord {chord_csmt_msd:.2f} km, detour {task1_data['detour_ratio']}x)")
    for s in csmt_msd_service:
        print(f"Service pair: {s['from_station']} -> {s['to_station']}, n_trains: {s['n_trains_2017']}, path_km: {s['path_km']}, sections: {s['path_sections']}")

    # ==========================================
    # TASK 2 & 3: INTERMEDIATE PIPELINE ARTIFACTS
    # ==========================================
    print("\n--- TASK 2 & 3: Tracing Pipeline Artifacts (Parquet & Work files) ---")
    
    # 1. network_vertices.parquet
    vertices_table = pq.read_table(work_dir / "network_vertices.parquet")
    edges_table = pq.read_table(work_dir / "network_edges.parquet")
    
    print(f"Total network_vertices: {vertices_table.num_rows}, Total network_edges: {edges_table.num_rows}")
    print(f"Vertex columns: {vertices_table.column_names}")
    print(f"Edge columns: {edges_table.column_names}")
    
    # Filter vertices in CSMT-MSD corridor: lat 18.935 to 18.960, lon 72.830 to 72.845
    v_df = vertices_table.to_pandas()
    e_df = edges_table.to_pandas()
    
    corridor_v = v_df[
        (v_df["lat"] >= 18.935) & (v_df["lat"] <= 18.960) &
        (v_df["lon"] >= 72.830) & (v_df["lon"] <= 72.845)
    ]
    corridor_v_set = set(corridor_v["vertex"])
    print(f"Vertices in CSMT-MSD corridor: {len(corridor_v)}")
    
    # Edges touching these vertices
    corridor_e = e_df[e_df["a"].isin(corridor_v_set) | e_df["b"].isin(corridor_v_set)]
    print(f"Edges in CSMT-MSD corridor: {len(corridor_e)}")
    
    corridor_v.to_csv(artifacts_dir / "corridor_network_vertices.csv", index=False)
    corridor_e.to_csv(artifacts_dir / "corridor_network_edges.csv", index=False)
    
    # Station snap records for CSMT and MSD
    snaps = list(csv.DictReader(open(work_dir / "station_snaps.csv", encoding="utf-8")))
    csmt_snap = next(r for r in snaps if r.get("code") == "CSMT")
    msd_snap = next(r for r in snaps if r.get("code") == "MSD")
    
    print(f"CSMT snap: vertex={csmt_snap.get('vertex')}, osm_node={csmt_snap.get('node_id')}, snap_m={csmt_snap.get('snap_m')}")
    print(f"MSD snap: vertex={msd_snap.get('vertex')}, osm_node={msd_snap.get('node_id')}, snap_m={msd_snap.get('snap_m')}")
    
    task2_data = {
        "corridor_vertices_count": len(corridor_v),
        "corridor_edges_count": len(corridor_e),
        "csmt_snap": csmt_snap,
        "msd_snap": msd_snap,
        "edge_kinds": corridor_e["kind"].value_counts().to_dict() if "kind" in corridor_e else {},
        "edge_gauges": corridor_e["gauge"].value_counts().to_dict() if "gauge" in corridor_e else {},
        "sample_corridor_edges": corridor_e.head(20).to_dict(orient="records")
    }
    
    with open(results_dir / "task2_pipeline_tracing.json", "w", encoding="utf-8") as f:
        json.dump(task2_data, f, indent=2)

if __name__ == "__main__":
    main()
