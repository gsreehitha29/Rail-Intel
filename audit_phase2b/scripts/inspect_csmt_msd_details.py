import csv
import json
import pathlib

def main():
    root = pathlib.Path("c:/Users/Sreehitha/OneDrive/Desktop/Major Project/Rail-Intel")
    work_dir = root / "03_graph_construction" / "graph_v2_0_open" / "work"
    release_dir = root / "03_graph_construction" / "release" / "rail-intel-v2.0-open"
    results_dir = root / "audit_phase2b" / "results"

    nodes = {n["node_id"]: n for n in csv.DictReader(open(release_dir / "graph" / "nodes.csv", encoding="utf-8"))}
    edges = list(csv.DictReader(open(release_dir / "graph" / "edges.csv", encoding="utf-8")))

    csmt = nodes["CSMT"]
    msd = nodes["MSD"]
    snrd = nodes["SNRD"]
    by = nodes["BY"]
    chg = nodes["CHG"]
    crd = nodes["CRD"]
    pr = nodes["PR"]

    print("=== Station Coordinates & Track Coordinates ===")
    for st in [csmt, msd, snrd, by, chg, crd, pr]:
        print(f"{st['node_id']} ({st['node_name']}):")
        print(f"  Station coords: ({st['longitude']}, {st['latitude']})")
        print(f"  Track coords:   ({st['track_lon']}, {st['track_lat']})")
        print(f"  OSM Node ID:    {st['osm_node_id']}")
        print(f"  Degree:         {st['degree']}")

    # Let's inspect edges connected to JN:@72.838157,18.955373 (the junction right north of Masjid)
    jn_msd = "JN:@72.838157,18.955373"
    print(f"\nEdges connected to {jn_msd}:")
    for e in edges:
        if jn_msd in (e["from_node"], e["to_node"]):
            other = e["to_node"] if e["from_node"] == jn_msd else e["from_node"]
            print(f"  -> {other} ({nodes.get(other, {}).get('node_name', '')}), {e['length_km']} km, line='{e['line_name']}'")

if __name__ == "__main__":
    main()
