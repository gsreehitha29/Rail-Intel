import pandas as pd
import networkx as nx
import math
import json

def haversine_m(lon1, lat1, lon2, lat2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    return 2.0 * 6371008.8 * math.asin(math.sqrt(min(1.0, max(0.0, a))))

def main():
    edges = pd.read_csv('audit_phase2b1/artifacts/corridor_network_edges.csv')
    vertices = pd.read_csv('audit_phase2b1/artifacts/corridor_network_vertices.csv').set_index('vertex')

    G = nx.Graph()
    for _, r in edges.iterrows():
        G.add_edge(r['a'], r['b'], km=r['km'], kind=r['kind'], chain=r['chain'])

    v_csmt = 'n289147'
    v_msd = 's3558085'

    comps = list(nx.connected_components(G))
    c_csmt = next(c for c in comps if v_csmt in c)
    c_msd = next(c for c in comps if v_msd in c)

    print(f"CSMT component nodes: {len(c_csmt)}, MSD component nodes: {len(c_msd)}")

    # Details of MSD component nodes:
    msd_nodes_data = []
    for v in c_msd:
        if v in vertices.index:
            row = vertices.loc[v]
            msd_nodes_data.append({
                "vertex": v,
                "lon": float(row["lon"]),
                "lat": float(row["lat"]),
                "osm_node": row["osm_node"],
                "kind": row["kind"]
            })
    msd_nodes_data.sort(key=lambda x: x["lat"])

    print("\n--- MSD Component Nodes (sorted South to North) ---")
    for d in msd_nodes_data:
        print(f"  {d['vertex']} | osm_node: {d['osm_node']} | ({d['lon']:.5f}, {d['lat']:.5f}) | kind: {d['kind']}")

    # Find closest pair of vertices between c_csmt and c_msd
    min_dist = float("inf")
    closest_pair = None
    for u in c_csmt:
        if u not in vertices.index: continue
        r_u = vertices.loc[u]
        for v in c_msd:
            if v not in vertices.index: continue
            r_v = vertices.loc[v]
            d = haversine_m(r_u["lon"], r_u["lat"], r_v["lon"], r_v["lat"])
            if d < min_dist:
                min_dist = d
                closest_pair = (u, v, r_u, r_v)

    u, v, r_u, r_v = closest_pair
    print(f"\n--- Closest Gap between CSMT and MSD components in Stage C1 ---")
    print(f"Distance: {min_dist:.2f} meters")
    print(f"CSMT component side: vertex {u} at ({r_u['lon']:.5f}, {r_u['lat']:.5f}), osm_node: {r_u['osm_node']}")
    print(f"MSD component side:  vertex {v} at ({r_v['lon']:.5f}, {r_v['lat']:.5f}), osm_node: {r_v['osm_node']}")

    # Check edges touching the southern-most node of MSD component
    southern_msd = msd_nodes_data[0]
    print(f"\nSouthern-most node of MSD component: {southern_msd['vertex']} at lat {southern_msd['lat']}")
    edges_touching_south = edges[(edges['a'] == southern_msd['vertex']) | (edges['b'] == southern_msd['vertex'])]
    print("Edges touching southern-most MSD node:")
    for _, r in edges_touching_south.iterrows():
        print(f"  {r['a']} <-> {r['b']} | km: {r['km']} | kind: {r['kind']} | chain: {r['chain']}")

    out = {
        "msd_component_nodes": msd_nodes_data,
        "min_gap_meters": round(min_dist, 2),
        "closest_pair": {
            "csmt_vertex": u,
            "csmt_coords": [float(r_u["lon"]), float(r_u["lat"])],
            "csmt_osm_node": str(r_u["osm_node"]),
            "msd_vertex": v,
            "msd_coords": [float(r_v["lon"]), float(r_v["lat"])],
            "msd_osm_node": str(r_v["osm_node"])
        }
    }
    with open('audit_phase2b1/results/corridor_gap_analysis.json', 'w') as f:
        json.dump(out, f, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))

if __name__ == "__main__":
    main()
