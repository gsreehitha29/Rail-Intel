import csv
import json
import pathlib

def main():
    root = pathlib.Path(".")
    release_dir = root / "03_graph_construction" / "release" / "rail-intel-v2.0-open"
    work_dir = root / "03_graph_construction" / "graph_v2_0_open" / "work"
    results_dir = root / "audit_phase2b" / "results"
    
    # 1. Check throat_links in release provenance
    throat_links_file = release_dir / "provenance" / "throat_links.csv"
    throats = list(csv.DictReader(open(throat_links_file, encoding="utf-8")))
    
    csmt_throats = []
    for t in throats:
        # Check if vertex or osm mentions CSMT or related coordinates
        if "CSMT" in (t.get("vertex_a"), t.get("vertex_b")):
            csmt_throats.append(t)
            
    print(f"Total throats in provenance: {len(throats)}")
    print(f"Throats mentioning CSMT directly: {len(csmt_throats)}")
    for t in csmt_throats:
        print("  Direct CSMT throat:", t)
        
    # 2. Check station snaps for Mumbai stations
    snaps_file = work_dir / "station_snaps.csv"
    mumbai_codes = ["CSMT", "MSD", "SNRD", "BY", "CHG", "CRD", "PR", "DKRD"]
    mumbai_snaps = {}
    if snaps_file.exists():
        with open(snaps_file, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("code") in mumbai_codes:
                    mumbai_snaps[r["code"]] = r
                    print(f"Snap: {r['code']} -> vertex: {r.get('vertex')}, snapped: {r.get('snapped')}, dist_m: {r.get('snap_m')}")
                    
    # 3. Check c2_throat_links.csv in work dir
    work_throats_file = work_dir / "c2_throat_links.csv"
    work_throats = []
    if work_throats_file.exists():
        with open(work_throats_file, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if "CSMT" in (r.get("vertex_a"), r.get("vertex_b")) or "CSMT" in r.get("reason", ""):
                    work_throats.append(r)
        print(f"Work throats touching CSMT: {len(work_throats)}")
        for r in work_throats:
            print("  Work throat:", r)

    out_data = {
        "release_throats_csmt": csmt_throats,
        "mumbai_station_snaps": mumbai_snaps,
        "work_throats_csmt": work_throats
    }
    
    out_file = results_dir / "csmt_provenance_tracing.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

if __name__ == "__main__":
    main()
