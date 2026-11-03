import csv
import json
import pathlib

def main():
    root = pathlib.Path("c:/Users/Sreehitha/OneDrive/Desktop/Major Project/Rail-Intel")
    work_dir = root / "03_graph_construction" / "graph_v2_0_open" / "work"
    results_dir = root / "audit_phase2b" / "results"
    
    # Check c2_report.json or c1_report.json
    c1_rep_file = work_dir / "c1_report.json"
    c2_rep_file = work_dir / "c2_report.json"
    
    c2_rep = json.load(open(c2_rep_file, encoding="utf-8")) if c2_rep_file.exists() else {}
    print("C2 report keys:", list(c2_rep.keys()))
    if "throats" in c2_rep:
        print("C2 report throats summary:", c2_rep["throats"])

    # Let's check open/edges.csv vs release/graph/edges.csv
    open_edges_file = root / "03_graph_construction" / "graph_v2_0_open" / "open" / "edges.csv"
    if open_edges_file.exists():
        with open(open_edges_file, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["edge_id"] == "v2.0:CSMT|JN:@72.836140,19.007082":
                    print("Open edges record for candidate:")
                    print(json.dumps(r, indent=2))
                    break

if __name__ == "__main__":
    main()
