import pandas as pd
import csv
import pathlib
import networkx as nx
import pyarrow.parquet as pq

def main():
    root = pathlib.Path(__file__).resolve().parents[2]
    work_dir = root / "03_graph_construction" / "graph_v2_0_open" / "work"
    results_dir = root / "audit_phase2b1" / "results"

    # 1. Load network edges and vertices
    E = pq.read_table(work_dir / "network_edges.parquet").to_pandas()
    V = pq.read_table(work_dir / "network_vertices.parquet").to_pandas().set_index("vertex")
    
    # 2. Load station snaps
    snaps = list(csv.DictReader(open(work_dir / "station_snaps.csv", encoding="utf-8")))
    
    # Filter snaps for CSMT and MSD
    csmt_snap = next(r for r in snaps if r.get("code") == "CSMT")
    msd_snap = next(r for r in snaps if r.get("code") == "MSD")
    
    print(f"CSMT snap record: vertex={csmt_snap['vertex']}, osm_node={csmt_snap['node_id']}, code={csmt_snap['code']}")
    print(f"MSD snap record:  vertex={msd_snap['vertex']}, osm_node={msd_snap['node_id']}, code={msd_snap['code']}")

    # 3. Check all edges in E touching the MSD vertex s3558085
    msd_v = msd_snap["vertex"]
    e_msd = E[(E["a"] == msd_v) | (E["b"] == msd_v)]
    print(f"\nEdges in network_edges.parquet touching MSD vertex ({msd_v}): {len(e_msd)}")
    for _, r in e_msd.iterrows():
        other = r["b"] if r["a"] == msd_v else r["a"]
        other_row = V.loc[other] if other in V.index else None
        coords = f"({other_row['lon']:.5f}, {other_row['lat']:.5f})" if other_row is not None else "unknown"
        print(f"  {r['a']} <-> {r['b']} | km: {r['km']:.4f} | chain: {r['chain']} | other coords: {coords}")

    # Check edges touching the southern endpoint of chain 4365: n128794
    south_v = "n128794"
    e_south = E[(E["a"] == south_v) | (E["b"] == south_v)]
    print(f"\nEdges touching southern vertex {south_v}: {len(e_south)}")
    for _, r in e_south.iterrows():
        print(f"  {r['a']} <-> {r['b']} | km: {r['km']:.4f} | chain: {r['chain']}")

    # What is the distance between n128794 and CSMT vertex n289147?
    v_csmt = csmt_snap["vertex"]
    r_csmt = V.loc[v_csmt]
    r_south = V.loc[south_v]
    import math
    phi1, phi2 = math.radians(r_csmt["lat"]), math.radians(r_south["lat"])
    dphi = math.radians(r_south["lat"] - r_csmt["lat"])
    dlam = math.radians(r_south["lon"] - r_csmt["lon"])
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    dist_m = 2.0 * 6371008.8 * math.asin(math.sqrt(min(1.0, max(0.0, a))))
    print(f"\nDistance between CSMT snapped vertex ({v_csmt}) and southern track vertex ({south_v}): {dist_m:.2f} meters!")

    # Check other CSMT-area vertices in V:
    csmt_area_v = V[(V["lat"] >= 18.939) & (V["lat"] <= 18.942) & (V["lon"] >= 72.834) & (V["lon"] <= 72.837)]
    print(f"\nVertices in CSMT station throat area (lat 18.939-18.942, lon 72.834-72.837): {len(csmt_area_v)}")
    for v_id, r in csmt_area_v.iterrows():
        edges_touching = E[(E["a"] == v_id) | (E["b"] == v_id)]
        print(f"  Vertex {v_id} | ({r['lon']:.5f}, {r['lat']:.5f}) | osm_node: {r['osm_node']} | kind: {r['kind']} | degree_in_E: {len(edges_touching)}")
        for _, er in edges_touching.iterrows():
            print(f"     -> to {er['b'] if er['a'] == v_id else er['a']} | km: {er['km']:.4f} | chain: {er['chain']}")

if __name__ == "__main__":
    main()
