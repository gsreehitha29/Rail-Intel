import csv
import json
import pathlib

def main():
    root = pathlib.Path(".")
    release_dir = root / "03_graph_construction" / "release" / "rail-intel-v2.0-open"
    results_dir = root / "audit_phase2b" / "results"
    
    edges = list(csv.DictReader(open(release_dir / "graph" / "edges.csv", encoding="utf-8")))
    nodes = {n["node_id"]: n for n in csv.DictReader(open(release_dir / "graph" / "nodes.csv", encoding="utf-8"))}

    stations_to_check = [
        "CSMT", "MSD", "SNRD", "BY", "CHG", "CRD", "PR", "DR",
        "DKRD", "RRD", "CTGN", "SVE", "VDLR"
    ]
    
    report = {}

    for st in stations_to_check:
        inc = [e for e in edges if st in (e["from_node"], e["to_node"])]
        n = nodes.get(st, {})
        st_data = {
            "node_id": st,
            "node_name": n.get("node_name"),
            "degree": n.get("degree"),
            "coords": [float(n.get("longitude", 0)), float(n.get("latitude", 0))],
            "incident_edges": []
        }
        for e in inc:
            other = e["to_node"] if e["from_node"] == st else e["from_node"]
            st_data["incident_edges"].append({
                "neighbor_id": other,
                "neighbor_name": nodes.get(other, {}).get("node_name", ""),
                "neighbor_type": nodes.get(other, {}).get("node_type", ""),
                "length_km": float(e["length_km"]),
                "chord_km": float(e.get("length_chord_km", 0)),
                "joins": e.get("joins", ""),
                "line_name": e.get("line_name", ""),
                "trains_2017": int(e.get("trains_2017", 0))
            })
        report[st] = st_data
        
    out_file = results_dir / "south_mumbai_stations_details.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    for st, d in report.items():
        print(f"Station: {st} ({d['node_name']}) | Deg: {d['degree']} | Coords: {d['coords']}")
        for inc in d["incident_edges"]:
            print(f"   -> {inc['neighbor_id']} ({inc['neighbor_name']}), {inc['length_km']} km, joins='{inc['joins']}', line='{inc['line_name']}', trains={inc['trains_2017']}")

if __name__ == "__main__":
    main()
