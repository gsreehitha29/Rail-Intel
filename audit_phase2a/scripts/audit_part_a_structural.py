import csv
import json
import math
import pathlib
import sys
from collections import Counter, defaultdict

import networkx as nx

R_EARTH_KM = 6371.0088

def haversine_km(lon1, lat1, lon2, lat2):
    try:
        p1_lon, p1_lat = float(lon1), float(lat1)
        p2_lon, p2_lat = float(lon2), float(lat2)
    except (ValueError, TypeError):
        return float("nan")

    if any(math.isnan(x) for x in (p1_lon, p1_lat, p2_lon, p2_lat)):
        return float("nan")

    phi1, phi2 = math.radians(p1_lat), math.radians(p2_lat)
    dphi = math.radians(p2_lat - p1_lat)
    dlam = math.radians(p2_lon - p1_lon)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    a = min(1.0, max(0.0, a))
    return 2.0 * R_EARTH_KM * math.asin(math.sqrt(a))

def read_csv_dicts(path: pathlib.Path):
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames

def write_csv_dicts(path: pathlib.Path, rows: list, fieldnames: list):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def audit_graph(graph_name: str, nodes_path: pathlib.Path, edges_path: pathlib.Path, anomalies_dir: pathlib.Path):
    print(f"\n=======================================================")
    print(f"Auditing {graph_name.upper()} Graph (Pure Python + NetworkX)...")
    print(f"Nodes: {nodes_path}")
    print(f"Edges: {edges_path}")
    print(f"=======================================================")

    raw_nodes, node_fields = read_csv_dicts(nodes_path)
    raw_edges, edge_fields = read_csv_dicts(edges_path)

    report = {
        "graph_name": graph_name,
        "nodes_file": str(nodes_path),
        "edges_file": str(edges_path),
        "node_columns": node_fields,
        "edge_columns": edge_fields,
        "counts": {
            "node_count": len(raw_nodes),
            "edge_count": len(raw_edges),
            "stations_count": sum(1 for n in raw_nodes if n.get("node_type") == "station"),
            "junctions_count": sum(1 for n in raw_nodes if n.get("node_type") == "junction"),
            "other_node_type_count": sum(1 for n in raw_nodes if n.get("node_type") not in ("station", "junction"))
        },
        "integrity": {},
        "coordinates": {},
        "lengths": {},
        "degrees": {},
        "components": {},
        "chord_comparisons": {}
    }

    # 1. Duplicate node IDs
    node_id_counts = Counter(n["node_id"] for n in raw_nodes)
    dup_node_ids = [n for n in raw_nodes if node_id_counts[n["node_id"]] > 1]
    report["integrity"]["duplicate_node_ids_count"] = len(dup_node_ids)
    if dup_node_ids:
        anom_file = anomalies_dir / f"{graph_name}_duplicate_node_ids.csv"
        write_csv_dicts(anom_file, dup_node_ids, node_fields)
        report["integrity"]["duplicate_node_ids_file"] = str(anom_file)

    # 2. Duplicate edge IDs
    edge_id_counts = Counter(e["edge_id"] for e in raw_edges)
    dup_edge_ids = [e for e in raw_edges if edge_id_counts[e["edge_id"]] > 1]
    report["integrity"]["duplicate_edge_ids_count"] = len(dup_edge_ids)
    if dup_edge_ids:
        anom_file = anomalies_dir / f"{graph_name}_duplicate_edge_ids.csv"
        write_csv_dicts(anom_file, dup_edge_ids, edge_fields)
        report["integrity"]["duplicate_edge_ids_file"] = str(anom_file)

    # 3. Missing edge endpoints
    node_id_set = set(node_id_counts.keys())
    missing_endpoints = []
    for e in raw_edges:
        u, v = e["from_node"], e["to_node"]
        if u not in node_id_set or v not in node_id_set:
            row = dict(e)
            row["u_missing"] = u not in node_id_set
            row["v_missing"] = v not in node_id_set
            missing_endpoints.append(row)
    report["integrity"]["missing_endpoints_edge_count"] = len(missing_endpoints)
    if missing_endpoints:
        anom_file = anomalies_dir / f"{graph_name}_missing_endpoints.csv"
        write_csv_dicts(anom_file, missing_endpoints, list(missing_endpoints[0].keys()))
        report["integrity"]["missing_endpoints_file"] = str(anom_file)

    # 4. Self-loops
    self_loops = [e for e in raw_edges if e["from_node"] == e["to_node"]]
    report["integrity"]["self_loops_count"] = len(self_loops)
    if self_loops:
        anom_file = anomalies_dir / f"{graph_name}_self_loops.csv"
        write_csv_dicts(anom_file, self_loops, edge_fields)
        report["integrity"]["self_loops_file"] = str(anom_file)

    # 5. Duplicate unordered endpoint pairs
    unordered_pair_counts = Counter()
    for e in raw_edges:
        u, v = e["from_node"], e["to_node"]
        pair = (min(u, v), max(u, v))
        unordered_pair_counts[pair] += 1
    dup_pairs = [e for e in raw_edges if unordered_pair_counts[(min(e["from_node"], e["to_node"]), max(e["from_node"], e["to_node"]))] > 1]
    report["integrity"]["duplicate_unordered_pairs_count"] = len(dup_pairs)
    if dup_pairs:
        anom_file = anomalies_dir / f"{graph_name}_duplicate_unordered_pairs.csv"
        write_csv_dicts(anom_file, dup_pairs, edge_fields)
        report["integrity"]["duplicate_unordered_pairs_file"] = str(anom_file)

    # 6. Edge ID versus endpoint consistency
    # Expected format: "v2.0:A|B" or "v2.0p:A|B" where A <= B
    prefix = "v2.0p:" if graph_name == "places" else "v2.0:"
    mismatched_edge_ids = []
    for e in raw_edges:
        u, v = e["from_node"], e["to_node"]
        expected = f"{prefix}{min(u, v)}|{max(u, v)}"
        if e["edge_id"] != expected:
            row = dict(e)
            row["expected_edge_id"] = expected
            mismatched_edge_ids.append(row)
    report["integrity"]["mismatched_edge_ids_count"] = len(mismatched_edge_ids)
    if mismatched_edge_ids:
        anom_file = anomalies_dir / f"{graph_name}_mismatched_edge_ids.csv"
        write_csv_dicts(anom_file, mismatched_edge_ids, list(mismatched_edge_ids[0].keys()))
        report["integrity"]["mismatched_edge_ids_file"] = str(anom_file)

    # 7. Coordinates check
    invalid_coords = []
    node_dict = {}
    for n in raw_nodes:
        nid = n["node_id"]
        node_dict[nid] = n
        try:
            lon = float(n["longitude"])
            lat = float(n["latitude"])
            if not (60.0 <= lon <= 105.0 and 5.0 <= lat <= 40.0):
                invalid_coords.append(n)
        except (ValueError, TypeError):
            invalid_coords.append(n)

    report["coordinates"]["invalid_or_missing_coords_count"] = len(invalid_coords)
    if invalid_coords:
        anom_file = anomalies_dir / f"{graph_name}_invalid_coords.csv"
        write_csv_dicts(anom_file, invalid_coords, node_fields)
        report["coordinates"]["invalid_coords_file"] = str(anom_file)

    # Check track coordinates if present
    if "track_lon" in node_fields and "track_lat" in node_fields:
        st_no_track = []
        large_snap = []
        max_snap_m = 0.0
        for n in raw_nodes:
            if n.get("node_type") == "station":
                t_lon = n.get("track_lon")
                t_lat = n.get("track_lat")
                if not t_lon or not t_lat:
                    st_no_track.append(n)
                else:
                    d_m = haversine_km(n["longitude"], n["latitude"], t_lon, t_lat) * 1000.0
                    if not math.isnan(d_m):
                        max_snap_m = max(max_snap_m, d_m)
                        if d_m > 150.0:
                            row = dict(n)
                            row["station_to_track_dist_m"] = round(d_m, 2)
                            large_snap.append(row)

        report["coordinates"]["stations_missing_track_coords_count"] = len(st_no_track)
        report["coordinates"]["stations_track_offset_over_150m_count"] = len(large_snap)
        report["coordinates"]["max_station_to_track_dist_m"] = round(max_snap_m, 2)

        if st_no_track:
            anom_file = anomalies_dir / f"{graph_name}_stations_missing_track_coords.csv"
            write_csv_dicts(anom_file, st_no_track, node_fields)
            report["coordinates"]["stations_missing_track_coords_file"] = str(anom_file)
        if large_snap:
            anom_file = anomalies_dir / f"{graph_name}_stations_track_offset_over_150m.csv"
            write_csv_dicts(anom_file, large_snap, list(large_snap[0].keys()))
            report["coordinates"]["stations_track_offset_over_150m_file"] = str(anom_file)

    # 8. Lengths validation
    invalid_lengths = []
    total_km = 0.0
    lengths = []
    for e in raw_edges:
        try:
            l_km = float(e["length_km"])
            if l_km <= 0 or math.isnan(l_km):
                invalid_lengths.append(e)
            else:
                total_km += l_km
                lengths.append(l_km)
        except (ValueError, TypeError):
            invalid_lengths.append(e)

    lengths.sort()
    n_len = len(lengths)
    report["lengths"]["invalid_or_zero_length_count"] = len(invalid_lengths)
    report["lengths"]["total_route_km"] = round(total_km, 2)
    report["lengths"]["min_length_km"] = lengths[0] if lengths else None
    report["lengths"]["max_length_km"] = lengths[-1] if lengths else None
    report["lengths"]["median_length_km"] = lengths[n_len // 2] if lengths else None
    report["lengths"]["mean_length_km"] = round(total_km / n_len, 4) if n_len else None

    if invalid_lengths:
        anom_file = anomalies_dir / f"{graph_name}_invalid_lengths.csv"
        write_csv_dicts(anom_file, invalid_lengths, edge_fields)
        report["lengths"]["invalid_lengths_file"] = str(anom_file)

    # 9. Degree recomputation versus stored degree
    G = nx.Graph()
    for n in raw_nodes:
        G.add_node(n["node_id"], **n)

    for e in raw_edges:
        u, v = e["from_node"], e["to_node"]
        l_km = float(e.get("length_km", 0.0)) if e.get("length_km") else 0.0
        G.add_edge(u, v, length_km=l_km, edge_id=e["edge_id"])

    recomputed_degrees = dict(G.degree())
    degree_mismatches = []
    for n in raw_nodes:
        stored_deg = int(n["degree"]) if n.get("degree") else None
        recomp_deg = recomputed_degrees[n["node_id"]]
        if stored_deg != recomp_deg:
            row = dict(n)
            row["stored_degree"] = stored_deg
            row["recomputed_degree"] = recomp_deg
            degree_mismatches.append(row)

    report["degrees"]["degree_mismatches_count"] = len(degree_mismatches)
    report["degrees"]["max_degree"] = max(recomputed_degrees.values()) if recomputed_degrees else 0
    report["degrees"]["mean_degree"] = round(sum(recomputed_degrees.values()) / len(recomputed_degrees), 4) if recomputed_degrees else 0.0
    report["degrees"]["degree_distribution"] = dict(sorted(Counter(recomputed_degrees.values()).items()))

    if degree_mismatches:
        anom_file = anomalies_dir / f"{graph_name}_degree_mismatches.csv"
        write_csv_dicts(anom_file, degree_mismatches, list(degree_mismatches[0].keys()))
        report["degrees"]["degree_mismatches_file"] = str(anom_file)

    # Isolated nodes (degree 0)
    isolated_nodes = [n for n in raw_nodes if recomputed_degrees[n["node_id"]] == 0]
    report["degrees"]["isolated_nodes_count"] = len(isolated_nodes)
    report["degrees"]["isolated_nodes_list"] = [
        {"node_id": n["node_id"], "node_type": n.get("node_type"), "node_name": n.get("node_name"), "station_code": n.get("station_code")}
        for n in isolated_nodes
    ]
    if isolated_nodes:
        anom_file = anomalies_dir / f"{graph_name}_isolated_nodes.csv"
        write_csv_dicts(anom_file, isolated_nodes, node_fields)
        report["degrees"]["isolated_nodes_file"] = str(anom_file)

    # Dead-end nodes (degree 1)
    degree_1_nodes = [n for n in raw_nodes if recomputed_degrees[n["node_id"]] == 1]
    deg1_junctions = [n for n in degree_1_nodes if n.get("node_type") == "junction"]
    report["degrees"]["degree_1_count"] = len(degree_1_nodes)
    report["degrees"]["degree_1_junctions_count"] = len(deg1_junctions)
    if deg1_junctions:
        anom_file = anomalies_dir / f"{graph_name}_degree_1_junctions.csv"
        write_csv_dicts(anom_file, deg1_junctions, node_fields)
        report["degrees"]["degree_1_junctions_file"] = str(anom_file)

    # Degree 2 non-station nodes (should have been spliced unless preserved)
    deg2_junctions = [n for n in raw_nodes if n.get("node_type") == "junction" and recomputed_degrees[n["node_id"]] == 2]
    report["degrees"]["degree_2_junctions_count"] = len(deg2_junctions)
    if deg2_junctions:
        anom_file = anomalies_dir / f"{graph_name}_degree_2_junctions.csv"
        write_csv_dicts(anom_file, deg2_junctions, node_fields)
        report["degrees"]["degree_2_junctions_file"] = str(anom_file)

    # 10. Connected components
    comps = list(nx.connected_components(G))
    comps.sort(key=len, reverse=True)
    comp_sizes = [len(c) for c in comps]
    report["components"]["num_components"] = len(comps)
    report["components"]["component_sizes"] = comp_sizes
    report["components"]["giant_component_nodes"] = comp_sizes[0] if comp_sizes else 0
    report["components"]["giant_component_share"] = round(comp_sizes[0] / len(raw_nodes), 6) if raw_nodes else 0.0

    # Components km
    comp_km = []
    for c in comps:
        subG = G.subgraph(c)
        total_sub_km = sum(d.get("length_km", 0.0) for _, _, d in subG.edges(data=True))
        comp_km.append(round(total_sub_km, 2))
    report["components"]["component_km"] = comp_km

    node_to_comp = {}
    for cid, c in enumerate(comps):
        for n in c:
            node_to_comp[n] = cid

    comp_id_mismatches = []
    in_giant_mismatches = []
    for n in raw_nodes:
        nid = n["node_id"]
        actual_cid = node_to_comp[nid]
        actual_in_giant = (actual_cid == 0)

        stored_cid = int(n["component_id"]) if n.get("component_id") is not None and n["component_id"] != "" else None
        stored_in_giant = (n.get("in_giant") == "True" or n.get("in_giant") is True)

        if stored_cid != actual_cid:
            row = dict(n)
            row["actual_component_id"] = actual_cid
            comp_id_mismatches.append(row)
        if stored_in_giant != actual_in_giant:
            row = dict(n)
            row["actual_in_giant"] = actual_in_giant
            in_giant_mismatches.append(row)

    report["components"]["comp_id_mismatch_count"] = len(comp_id_mismatches)
    report["components"]["in_giant_mismatch_count"] = len(in_giant_mismatches)

    # Summary of non-giant components
    non_giant_details = []
    for cid in range(1, len(comps)):
        comp_node_ids = comps[cid]
        comp_node_rows = [node_dict[nid] for nid in comp_node_ids]
        st_count = sum(1 for n in comp_node_rows if n.get("node_type") == "station")
        sched17_count = sum(1 for n in comp_node_rows if n.get("scheduled_2017") in ("True", True))
        non_giant_details.append({
            "component_id": cid,
            "total_nodes": len(comp_node_ids),
            "stations_count": st_count,
            "total_km": comp_km[cid],
            "scheduled_2017_nodes": sched17_count,
            "sample_nodes": [n["node_id"] for n in comp_node_rows[:5]]
        })
    report["components"]["non_giant_components_summary"] = non_giant_details

    # 11. Chord calculations & comparisons
    shorter_gt_0m = []
    shorter_gt_200m = []
    shorter_gt_300m = []
    shorter_track_gt_200m = []
    edges_gt_50km = []
    edges_gt_90km = []
    extreme_sinuosity = []
    near_zero_chord = []
    chord_discrepancies_gt_50m = []

    for e in raw_edges:
        u, v = e["from_node"], e["to_node"]
        n_u, n_v = node_dict.get(u), node_dict.get(v)
        if not n_u or not n_v:
            continue

        l_km = float(e.get("length_km", 0.0))
        c_km = haversine_km(n_u["longitude"], n_u["latitude"], n_v["longitude"], n_v["latitude"])

        # Check against stored length_chord_km if present
        if e.get("length_chord_km"):
            stored_chord = float(e["length_chord_km"])
            if abs(stored_chord - c_km) > 0.05:
                row = dict(e)
                row["recomputed_chord_km"] = round(c_km, 4)
                chord_discrepancies_gt_50m.append(row)

        diff_m = (c_km - l_km) * 1000.0
        if diff_m > 1.0:
            row = dict(e)
            row["chord_km"] = round(c_km, 4)
            row["diff_m"] = round(diff_m, 1)
            shorter_gt_0m.append(row)
            if diff_m > 200.0:
                shorter_gt_200m.append(row)
            if diff_m > 300.0:
                shorter_gt_300m.append(row)

        # Track chord comparison if available
        if n_u.get("track_lon") and n_v.get("track_lon"):
            tc_km = haversine_km(n_u["track_lon"], n_u["track_lat"], n_v["track_lon"], n_v["track_lat"])
            track_diff_m = (tc_km - l_km) * 1000.0
            if track_diff_m > 200.0:
                row = dict(e)
                row["track_chord_km"] = round(tc_km, 4)
                row["track_diff_m"] = round(track_diff_m, 1)
                shorter_track_gt_200m.append(row)

        if l_km > 50.0:
            row = dict(e)
            row["chord_km"] = round(c_km, 4)
            edges_gt_50km.append(row)
            if l_km > 90.0:
                edges_gt_90km.append(row)

        # Sinuosity
        if c_km > 0.001:
            ratio = l_km / c_km
            if ratio > 3.0 and l_km > 5.0:
                row = dict(e)
                row["chord_km"] = round(c_km, 4)
                row["sinuosity_ratio"] = round(ratio, 2)
                extreme_sinuosity.append(row)
        else:
            if l_km > 0.1:
                row = dict(e)
                row["chord_km"] = round(c_km, 4)
                near_zero_chord.append(row)

        if c_km < 0.05:
            row = dict(e)
            row["chord_km"] = round(c_km, 4)
            near_zero_chord.append(row)

    report["chord_comparisons"]["chord_recomputation_discrepancies_gt_50m"] = len(chord_discrepancies_gt_50m)
    report["chord_comparisons"]["length_shorter_than_station_chord_gt_0m"] = len(shorter_gt_0m)
    report["chord_comparisons"]["length_shorter_than_station_chord_gt_200m"] = len(shorter_gt_200m)
    report["chord_comparisons"]["length_shorter_than_station_chord_gt_300m"] = len(shorter_gt_300m)
    report["chord_comparisons"]["length_shorter_than_track_chord_gt_200m"] = len(shorter_track_gt_200m)
    report["chord_comparisons"]["edges_gt_50km_count"] = len(edges_gt_50km)
    report["chord_comparisons"]["edges_gt_90km_count"] = len(edges_gt_90km)
    report["chord_comparisons"]["extreme_sinuosity_gt_3x_and_5km_count"] = len(extreme_sinuosity)
    report["chord_comparisons"]["near_zero_chord_lt_50m_count"] = len(near_zero_chord)

    if shorter_gt_200m:
        anom_file = anomalies_dir / f"{graph_name}_shorter_than_station_chord_gt_200m.csv"
        write_csv_dicts(anom_file, shorter_gt_200m, list(shorter_gt_200m[0].keys()))
        report["chord_comparisons"]["shorter_than_chord_gt_200m_file"] = str(anom_file)

    if shorter_track_gt_200m:
        anom_file = anomalies_dir / f"{graph_name}_shorter_than_track_chord_gt_200m.csv"
        write_csv_dicts(anom_file, shorter_track_gt_200m, list(shorter_track_gt_200m[0].keys()))
        report["chord_comparisons"]["shorter_than_track_chord_gt_200m_file"] = str(anom_file)

    if edges_gt_50km:
        anom_file = anomalies_dir / f"{graph_name}_edges_gt_50km.csv"
        write_csv_dicts(anom_file, edges_gt_50km, list(edges_gt_50km[0].keys()))
        report["chord_comparisons"]["edges_gt_50km_file"] = str(anom_file)

    if extreme_sinuosity:
        anom_file = anomalies_dir / f"{graph_name}_extreme_sinuosity.csv"
        write_csv_dicts(anom_file, extreme_sinuosity, list(extreme_sinuosity[0].keys()))
        report["chord_comparisons"]["extreme_sinuosity_file"] = str(anom_file)

    if near_zero_chord:
        anom_file = anomalies_dir / f"{graph_name}_near_zero_chord_lt_50m.csv"
        write_csv_dicts(anom_file, near_zero_chord, list(near_zero_chord[0].keys()))
        report["chord_comparisons"]["near_zero_chord_file"] = str(anom_file)

    # 12. Structure: Bridges, Cut Vertices, Cycle Basis
    bridges = list(nx.bridges(G))
    cut_vertices = list(nx.articulation_points(G))
    cycles = nx.cycle_basis(G)

    report["structure"] = {
        "bridges_count": len(bridges),
        "cut_vertices_count": len(cut_vertices),
        "cycle_basis_count": len(cycles),
        "is_connected": nx.is_connected(G)
    }

    print(f"\n[DONE] Audit of {graph_name.upper()} complete.")
    print(f"Nodes: {report['counts']['node_count']} (Stations: {report['counts']['stations_count']}, Junctions: {report['counts']['junctions_count']})")
    print(f"Edges: {report['counts']['edge_count']}, Route km: {report['lengths']['total_route_km']}")
    print(f"Components: {report['components']['num_components']} (Giant share: {report['components']['giant_component_share']:.4%})")
    print(f"Degrees: Max={report['degrees']['max_degree']}, Mean={report['degrees']['mean_degree']}, Degree mismatches={report['degrees']['degree_mismatches_count']}")
    print(f"Isolated nodes (deg 0): {report['degrees']['isolated_nodes_count']}, Dead-end junctions (deg 1): {report['degrees']['degree_1_junctions_count']}, Deg-2 junctions: {report['degrees']['degree_2_junctions_count']}")
    print(f"Structure: Bridges={report['structure']['bridges_count']}, Cut vertices={report['structure']['cut_vertices_count']}, Cycles={report['structure']['cycle_basis_count']}")
    print(f"Integrity: Dup nodes={report['integrity']['duplicate_node_ids_count']}, Dup edges={report['integrity']['duplicate_edge_ids_count']}, Missing endpoints={report['integrity']['missing_endpoints_edge_count']}, Self-loops={report['integrity']['self_loops_count']}")
    print(f"Chord checks: Shorter than station chord > 200m: {report['chord_comparisons']['length_shorter_than_station_chord_gt_200m']}, Shorter than track chord > 200m: {report['chord_comparisons'].get('length_shorter_than_track_chord_gt_200m', 'N/A')}")
    print(f"Edges > 50km: {report['chord_comparisons']['edges_gt_50km_count']}, Edges > 90km: {report['chord_comparisons']['edges_gt_90km_count']}, Extreme sinuosity: {report['chord_comparisons']['extreme_sinuosity_gt_3x_and_5km_count']}")

    return report

def main():
    root = pathlib.Path(".")
    release_dir = root / "03_graph_construction" / "release" / "rail-intel-v2.0-open"
    anomalies_dir = root / "audit_phase2a" / "anomalies"
    results_dir = root / "audit_phase2a" / "results"

    phys_report = audit_graph(
        "physical",
        release_dir / "graph" / "nodes.csv",
        release_dir / "graph" / "edges.csv",
        anomalies_dir
    )

    places_report = audit_graph(
        "places",
        release_dir / "places" / "nodes.csv",
        release_dir / "places" / "edges.csv",
        anomalies_dir
    )

    combined = {
        "physical_graph": phys_report,
        "places_graph": places_report
    }

    out_json = results_dir / "part_a_structural_audit.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2)

    print(f"\nAll structural checks saved to {out_json}")

if __name__ == "__main__":
    main()
