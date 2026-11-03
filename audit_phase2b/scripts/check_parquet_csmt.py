import pathlib
import json

def main():
    root = pathlib.Path("c:/Users/Sreehitha/OneDrive/Desktop/Major Project/Rail-Intel")
    work_dir = root / "03_graph_construction" / "graph_v2_0_open" / "work"
    results_dir = root / "audit_phase2b" / "results"

    # Read network_vertices.parquet if possible, or pyarrow/parquet
    # Let's see if pyarrow is available
    try:
        import pyarrow.parquet as pq
        vertices = pq.read_table(work_dir / "network_vertices.parquet").to_pandas()
        edges = pq.read_table(work_dir / "network_edges.parquet").to_pandas()
        print(f"Network vertices loaded: {len(vertices)}, Network edges loaded: {len(edges)}")
        
        # Find vertices in South Mumbai
        sm_v = vertices[
            (vertices["lon"] >= 72.82) & (vertices["lon"] <= 72.85) &
            (vertices["lat"] >= 18.93) & (vertices["lat"] <= 18.97)
        ]
        print(f"Vertices between CSMT and Sandhurst Road: {len(sm_v)}")
        v_ids = set(sm_v["vertex"])
        
        # Edges between these vertices
        sm_e = edges[edges["a"].isin(v_ids) | edges["b"].isin(v_ids)]
        print(f"Edges touching these vertices: {len(sm_e)}")
        for _, r in sm_e.iterrows():
            print(f"  {r['a']} <-> {r['b']} | km: {r['km']} | kind: {r.get('kind')} | gauge: {r.get('gauge')}")
            
    except Exception as e:
        print(f"Parquet reading error: {e}")

if __name__ == "__main__":
    main()
