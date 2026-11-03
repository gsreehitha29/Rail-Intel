import csv
import json
import pathlib

def main():
    root = pathlib.Path("c:/Users/Sreehitha/OneDrive/Desktop/Major Project/Rail-Intel")
    work_dir = root / "03_graph_construction" / "graph_v2_0_open" / "work"
    results_dir = root / "audit_phase2b" / "results"

    throats = list(csv.DictReader(open(work_dir / "c2_throat_links.csv", encoding="utf-8")))
    print(f"Total c2_throat_links: {len(throats)}")
    
    # Check fields in c2_throat_links.csv
    if throats:
        print("Fields in c2_throat_links:", list(throats[0].keys()))

if __name__ == "__main__":
    main()
