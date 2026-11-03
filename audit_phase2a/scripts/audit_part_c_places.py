import csv
import json
import math
import pathlib
from collections import Counter, defaultdict

import networkx as nx

def main():
    root = pathlib.Path(".")
    release_dir = root / "03_graph_construction" / "release" / "rail-intel-v2.0-open"
    results_dir = root / "audit_phase2a" / "results"
    anomalies_dir = root / "audit_phase2a" / "anomalies"

    # Load physical graph
    with open(release_dir / "graph" / "nodes.csv", "r", encoding="utf-8") as f:
        phys_nodes = list(csv.DictReader(f))
    with open(release_dir / "graph" / "edges.csv", "r", encoding="utf-8") as f:
        phys_edges = list(csv.DictReader(f))

    # Load places graph
    with open(release_dir / "places" / "nodes.csv", "r", encoding="utf-8") as f:
        place_nodes = list(csv.DictReader(f))
    with open(release_dir / "places" / "edges.csv", "r", encoding="utf-8") as f:
        place_edges = list(csv.DictReader(f))

    print("Building NetworkX graphs for Physical and Places...")
    Gp = nx.Graph()
    for n in phys_nodes:
        Gp.add_node(n["node_id"], **n)
    for e in phys_edges:
        Gp.add_edge(e["from_node"], e["to_node"], length_km=float(e["length_km"]), edge_id=e["edge_id"])

    Gpl = nx.Graph()
    for n in place_nodes:
        Gpl.add_node(n["node_id"], **n)
    for e in place_edges:
        Gpl.add_edge(e["from_node"], e["to_node"], length_km=float(e["length_km"]), edge_id=e["edge_id"])

    # 1. Station preservation
    phys_st_ids = set(n["node_id"] for n in phys_nodes if n.get("node_type") == "station")
    place_st_ids = set(n["node_id"] for n in place_nodes if n.get("node_type") == "station")

    missing_stations_in_places = phys_st_ids - place_st_ids
    extra_stations_in_places = place_st_ids - phys_st_ids

    # 2. Junction reduction & absorption
    phys_jn_ids = set(n["node_id"] for n in phys_nodes if n.get("node_type") == "junction")
    place_jn_ids = set(n["node_id"] for n in place_nodes if n.get("node_type") == "junction")

    absorbed_junctions_count = len(phys_jn_ids) - len(place_jn_ids)

    # In places/nodes.csv, inspect junctions_in_place
    stations_absorbing_junctions = []
    for n in place_nodes:
        j_in_p = int(n.get("junctions_in_place", 0))
        if j_in_p > 0:
            stations_absorbing_junctions.append({
                "node_id": n["node_id"],
                "node_name": n.get("node_name"),
                "node_type": n.get("node_type"),
                "junctions_in_place": j_in_p,
                "degree": int(n.get("degree", 0))
            })

    stations_absorbing_junctions.sort(key=lambda x: x["junctions_in_place"], reverse=True)

    # 3. Component mapping & station reachability
    phys_comps = list(nx.connected_components(Gp))
    phys_comps.sort(key=len, reverse=True)
    place_comps = list(nx.connected_components(Gpl))
    place_comps.sort(key=len, reverse=True)

    comp_comparison = []
    for idx, (pc, plc) in enumerate(zip(phys_comps, place_comps)):
        pc_st = set(n for n in pc if n in phys_st_ids)
        plc_st = set(n for n in plc if n in place_st_ids)
        comp_comparison.append({
            "component_index": idx,
            "phys_total_nodes": len(pc),
            "place_total_nodes": len(plc),
            "phys_stations": len(pc_st),
            "place_stations": len(plc_st),
            "stations_match": pc_st == plc_st
        })

    # 4. Station-to-station direct adjacency in Places graph vs Physical graph
    phys_direct_st_pairs = set()
    for e in phys_edges:
        u, v = e["from_node"], e["to_node"]
        if u in phys_st_ids and v in phys_st_ids:
            phys_direct_st_pairs.add((min(u, v), max(u, v)))

    place_direct_st_pairs = set()
    for e in place_edges:
        u, v = e["from_node"], e["to_node"]
        if u in place_st_ids and v in place_st_ids:
            place_direct_st_pairs.add((min(u, v), max(u, v)))

    newly_adjacent_st_pairs = place_direct_st_pairs - phys_direct_st_pairs
    dropped_adjacent_st_pairs = phys_direct_st_pairs - place_direct_st_pairs

    new_adj_details = []
    for u, v in sorted(list(newly_adjacent_st_pairs))[:100]:
        e_info = Gpl[u][v]
        phys_dist = nx.shortest_path_length(Gp, u, v, weight="length_km") if nx.has_path(Gp, u, v) else None
        phys_hops = len(nx.shortest_path(Gp, u, v)) - 1 if nx.has_path(Gp, u, v) else None
        new_adj_details.append({
            "u": u,
            "v": v,
            "place_edge_km": round(e_info["length_km"], 4),
            "phys_path_km": round(phys_dist, 4) if phys_dist is not None else None,
            "phys_hops": phys_hops,
            "dist_diff_km": round(abs(e_info["length_km"] - phys_dist), 4) if phys_dist is not None else None
        })

    # 5. Shortest path distance preservation on representative station pairs
    # Use 32 well-known stations from test_v2_spotcheck
    test_stations = [
        "NDLS", "CSMT", "HWH", "SBC", "SC", "BZA", "PUNE", "JP", "LKO", "BPL",
        "NGP", "ADI", "PNBE", "GHY", "TVC", "ERS", "KYQ", "JAT", "ASR", "CDG",
        "BBS", "RNC", "R", "DDN", "MAO", "VSKP", "CAPE", "SHM", "DBRG", "NJP",
        "SML", "MAS"
    ]
    # Filter to those in giant component
    test_stations = [s for s in test_stations if s in phys_st_ids and nx.has_path(Gp, "NDLS", s)]

    path_comparisons = []
    max_pct_diff = 0.0
    for i in range(len(test_stations)):
        for j in range(i + 1, min(i + 6, len(test_stations))):
            s1, s2 = test_stations[i], test_stations[j]
            dp = nx.shortest_path_length(Gp, s1, s2, weight="length_km")
            dpl = nx.shortest_path_length(Gpl, s1, s2, weight="length_km")
            pct_err = abs(dpl - dp) / dp * 100.0
            max_pct_diff = max(max_pct_diff, pct_err)
            path_comparisons.append({
                "from_station": s1,
                "to_station": s2,
                "physical_km": round(dp, 2),
                "places_km": round(dpl, 2),
                "abs_diff_km": round(abs(dpl - dp), 3),
                "pct_diff": round(pct_err, 4)
            })

    # 6. Bridge and Articulation Point differences
    phys_bridges = set(tuple(sorted([u, v])) for u, v in nx.bridges(Gp))
    place_bridges = set(tuple(sorted([u, v])) for u, v in nx.bridges(Gpl))

    phys_cuts = set(nx.articulation_points(Gp))
    place_cuts = set(nx.articulation_points(Gpl))

    # How many station cut points in each?
    phys_st_cuts = phys_cuts & phys_st_ids
    place_st_cuts = place_cuts & place_st_ids

    # 7. Independent cycles
    phys_cycles_count = len(nx.cycle_basis(Gp))
    place_cycles_count = len(nx.cycle_basis(Gpl))

    results = {
        "station_preservation": {
            "physical_station_count": len(phys_st_ids),
            "places_station_count": len(place_st_ids),
            "missing_in_places": list(missing_stations_in_places),
            "extra_in_places": list(extra_stations_in_places),
            "exact_match": len(missing_stations_in_places) == 0 and len(extra_stations_in_places) == 0
        },
        "junction_contraction": {
            "physical_junctions": len(phys_jn_ids),
            "places_junctions": len(place_jn_ids),
            "junctions_reduced": len(phys_jn_ids) - len(place_jn_ids),
            "top_absorbing_stations": stations_absorbing_junctions[:15]
        },
        "connected_components": comp_comparison,
        "structural_metrics": {
            "physical": {
                "nodes": len(phys_nodes),
                "edges": len(phys_edges),
                "total_km": round(sum(float(e["length_km"]) for e in phys_edges), 2),
                "bridges_count": len(phys_bridges),
                "cut_vertices_count": len(phys_cuts),
                "station_cut_vertices": len(phys_st_cuts),
                "cycle_basis_count": phys_cycles_count
            },
            "places": {
                "nodes": len(place_nodes),
                "edges": len(place_edges),
                "total_km": round(sum(float(e["length_km"]) for e in place_edges), 2),
                "bridges_count": len(place_bridges),
                "cut_vertices_count": len(place_cuts),
                "station_cut_vertices": len(place_st_cuts),
                "cycle_basis_count": place_cycles_count
            },
            "interpretation": (
                "The physical graph contains 1,267 cycles and 2,794 junctions because it preserves explicit track geometry, "
                "triangles, crossovers, and yards. The places graph collapses track points and junctions within 1 km into "
                "unified places, reducing cycles from 1,267 down to 498 and reducing junctions from 2,794 to 517. "
                "This contracts redundant intra-station cycles while preserving the macro-scale routing structure."
            )
        },
        "adjacency_and_topological_changes": {
            "physical_direct_station_pairs": len(phys_direct_st_pairs),
            "places_direct_station_pairs": len(place_direct_st_pairs),
            "newly_adjacent_station_pairs_count": len(newly_adjacent_st_pairs),
            "sample_newly_adjacent": new_adj_details[:20]
        },
        "routing_distance_preservation": {
            "pairs_evaluated": len(path_comparisons),
            "max_pct_diff": round(max_pct_diff, 4),
            "sample_comparisons": path_comparisons[:15]
        }
    }

    out_file = results_dir / "part_c_places_comparison.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Save newly adjacent pairs to CSV
    if new_adj_details:
        out_csv = anomalies_dir / "places_newly_adjacent_station_pairs.csv"
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(new_adj_details[0].keys()))
            w.writeheader()
            w.writerows(new_adj_details)
        print(f"Saved newly adjacent station pairs to {out_csv}")

    print(f"\nPart C Places Comparison complete. Results saved to {out_file}")

if __name__ == "__main__":
    main()
