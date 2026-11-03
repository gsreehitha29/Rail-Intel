import csv
import json
import pathlib

def main():
    root = pathlib.Path(__file__).resolve().parents[2]
    release_dir = root / "03_graph_construction" / "release" / "rail-intel-v2.0-open"
    results_dir = root / "audit_phase2b" / "results"
    artifacts_dir = root / "audit_phase2b" / "artifacts"
    
    nodes = {n["node_id"]: n for n in csv.DictReader(open(release_dir / "graph" / "nodes.csv", encoding="utf-8"))}
    edges = list(csv.DictReader(open(release_dir / "graph" / "edges.csv", encoding="utf-8")))

    candidate_id = "v2.0:CSMT|JN:@72.836140,19.007082"
    cand_edge = next(e for e in edges if e["edge_id"] == candidate_id)

    # 1. Candidate edge table
    cand_table = [{
        "attribute": k,
        "value": v
    } for k, v in cand_edge.items()]
    
    with open(artifacts_dir / "candidate_edge_attributes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["attribute", "value"])
        w.writeheader()
        w.writerows(cand_table)

    # 2. Endpoints table
    u_cand = "CSMT"
    v_cand = "JN:@72.836140,19.007082"
    endpoints_table = [
        nodes[u_cand],
        nodes[v_cand]
    ]
    with open(artifacts_dir / "candidate_endpoints.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(nodes[u_cand].keys()))
        w.writeheader()
        w.writerows(endpoints_table)

    # 3. Incident edges at endpoints
    incident_edges = [e for e in edges if u_cand in (e["from_node"], e["to_node"]) or v_cand in (e["from_node"], e["to_node"])]
    with open(artifacts_dir / "incident_edges.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(incident_edges[0].keys()))
        w.writeheader()
        w.writerows(incident_edges)

    # 4. Local South Mumbai stations and connectivity table
    local_st_ids = ["CSMT", "MSD", "SNRD", "BY", "CHG", "CRD", "PR", "DR", "DKRD", "RRD", "CTGN", "SVE", "VDLR"]
    local_st_rows = [nodes[sid] for sid in local_st_ids if sid in nodes]
    with open(artifacts_dir / "south_mumbai_stations.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(local_st_rows[0].keys()))
        w.writeheader()
        w.writerows(local_st_rows)

    # 5. Routing impact table
    routing_impact = [
        {"od_pair": "CSMT -> MSD (Masjid)", "graph_km": 14.21, "chord_km": 1.34, "hops": 8, "detour_ratio": 10.64, "trains_2017": 172, "status": "Severe Detour (14 km vs 1.3 km)"},
        {"od_pair": "CSMT -> SNRD (Sandhurst Road)", "graph_km": 13.20, "chord_km": 2.30, "hops": 6, "detour_ratio": 5.73, "trains_2017": 0, "status": "Severe Detour"},
        {"od_pair": "CSMT -> BY (Byculla)", "graph_km": 11.23, "chord_km": 4.03, "hops": 5, "detour_ratio": 2.79, "trains_2017": 48, "status": "Detour via Parel"},
        {"od_pair": "CSMT -> CHG (Chinchpokli)", "graph_km": 10.06, "chord_km": 5.20, "hops": 3, "detour_ratio": 1.93, "trains_2017": 0, "status": "Detour via Parel"},
        {"od_pair": "CSMT -> CRD (Currey Road)", "graph_km": 9.32, "chord_km": 5.93, "hops": 3, "detour_ratio": 1.57, "trains_2017": 0, "status": "Detour via Parel"},
        {"od_pair": "CSMT -> PR (Parel)", "graph_km": 8.10, "chord_km": 7.67, "hops": 2, "detour_ratio": 1.06, "trains_2017": 0, "status": "Direct Fast Line Corridor"},
        {"od_pair": "CSMT -> DR (Dadar)", "graph_km": 9.17, "chord_km": 8.58, "hops": 4, "detour_ratio": 1.07, "trains_2017": 49, "status": "Accurate Fast Line Alignment"},
        {"od_pair": "CSMT -> TNA (Thane)", "graph_km": 33.56, "chord_km": 31.06, "hops": 17, "detour_ratio": 1.08, "trains_2017": 1, "status": "Accurate Mainline Path"},
        {"od_pair": "CSMT -> KYN (Kalyan Jn)", "graph_km": 51.73, "chord_km": 45.16, "hops": 39, "detour_ratio": 1.15, "trains_2017": 5, "status": "Accurate Mainline Path"}
    ]
    with open(artifacts_dir / "routing_impact_table.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(routing_impact[0].keys()))
        w.writeheader()
        w.writerows(routing_impact)

    print("Phase 2B artifact tables successfully created in audit_phase2b/artifacts/")

if __name__ == "__main__":
    main()
