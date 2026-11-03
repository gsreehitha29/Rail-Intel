import csv
import json
import pathlib

def main():
    root = pathlib.Path(__file__).resolve().parents[2]
    work_dir = root / "03_graph_construction" / "graph_v2_0_open" / "work"
    release_dir = root / "03_graph_construction" / "release" / "rail-intel-v2.0-open"
    results_dir = root / "audit_phase2b" / "results"

    nodes = {n["node_id"]: n for n in csv.DictReader(open(release_dir / "graph" / "nodes.csv", encoding="utf-8"))}
    edges = list(csv.DictReader(open(release_dir / "graph" / "edges.csv", encoding="utf-8")))

    # Find candidate edge in edges.csv
    candidate_id = "v2.0:CSMT|JN:@72.836140,19.007082"
    cand_edge = next(e for e in edges if e["edge_id"] == candidate_id)
    print("Candidate edge properties:")
    print(json.dumps(cand_edge, indent=2))

    # All edges incident to JN:@72.836140,19.007082
    jn_cand = "JN:@72.836140,19.007082"
    jn_edges = [e for e in edges if jn_cand in (e["from_node"], e["to_node"])]
    print(f"\nAll edges incident to {jn_cand}:")
    for e in jn_edges:
        other = e["to_node"] if e["from_node"] == jn_cand else e["from_node"]
        print(f"  -> {other} ({nodes.get(other, {}).get('node_name', '')}), len={e['length_km']} km, joins='{e['joins']}', line='{e['line_name']}'")

if __name__ == "__main__":
    main()
