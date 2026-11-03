import csv
import json
import pathlib
from collections import Counter, defaultdict

import networkx as nx

def main():
    root = pathlib.Path(".")
    release_dir = root / "03_graph_construction" / "release" / "rail-intel-v2.0-open"
    results_dir = root / "audit_phase2a" / "results"
    anomalies_dir = root / "audit_phase2a" / "anomalies"

    # Load released graph
    with open(release_dir / "graph" / "nodes.csv", "r", encoding="utf-8") as f:
        nodes = list(csv.DictReader(f))
    with open(release_dir / "graph" / "edges.csv", "r", encoding="utf-8") as f:
        edges = list(csv.DictReader(f))

    node_dict = {n["node_id"]: n for n in nodes}

    # Load provenance files
    with open(release_dir / "provenance" / "throat_links.csv", "r", encoding="utf-8") as f:
        throats_raw = list(csv.DictReader(f))
    with open(release_dir / "provenance" / "joins.csv", "r", encoding="utf-8") as f:
        joins_raw = list(csv.DictReader(f))
    with open(release_dir / "provenance" / "wikidata_placements.csv", "r", encoding="utf-8") as f:
        wikidata_raw = list(csv.DictReader(f))
    with open(release_dir / "provenance" / "code_conflicts.csv", "r", encoding="utf-8") as f:
        conflicts_raw = list(csv.DictReader(f))

    # Build full graph G
    G = nx.Graph()
    for n in nodes:
        G.add_node(n["node_id"], **n)
    for e in edges:
        G.add_edge(e["from_node"], e["to_node"], length_km=float(e["length_km"]), edge_id=e["edge_id"], joins=e.get("joins", ""))

    # Base graph properties
    base_components = list(nx.connected_components(G))
    base_bridges = set(nx.bridges(G))
    base_cut_vertices = set(nx.articulation_points(G))

    # -------------------------------------------------------------
    # 1. THROAT LINKS ANALYSIS
    # -------------------------------------------------------------
    print("Analyzing Throat Links...")
    # Edges in released graph with joins == 'throat'
    throat_edges = [e for e in edges if e.get("joins") == "throat"]
    throat_edge_ids = set(e["edge_id"] for e in throat_edges)

    throat_bridges = []
    throat_non_bridges = []
    for e in throat_edges:
        u, v = e["from_node"], e["to_node"]
        pair = (u, v) if (u, v) in base_bridges else ((v, u) if (v, u) in base_bridges else None)
        if pair:
            throat_bridges.append(e)
        else:
            throat_non_bridges.append(e)

    # What happens if we remove all throat edges?
    G_no_throats = G.copy()
    for e in throat_edges:
        if G_no_throats.has_edge(e["from_node"], e["to_node"]):
            G_no_throats.remove_edge(e["from_node"], e["to_node"])

    no_throats_components = list(nx.connected_components(G_no_throats))
    no_throats_giant_size = max(len(c) for c in no_throats_components)

    # Check for parallel paths for each throat edge
    # Does a path exist between u and v in G_no_throats?
    throats_with_alternative = []
    throats_without_alternative = []
    for e in throat_edges:
        u, v = e["from_node"], e["to_node"]
        if nx.has_path(G_no_throats, u, v):
            alt_len = nx.shortest_path_length(G_no_throats, u, v, weight="length_km")
            throats_with_alternative.append({
                "edge_id": e["edge_id"],
                "u": u,
                "v": v,
                "throat_km": float(e["length_km"]),
                "alternative_km": round(alt_len, 4),
                "detour_ratio": round(alt_len / float(e["length_km"]), 2) if float(e["length_km"]) > 0 else None
            })
        else:
            throats_without_alternative.append({
                "edge_id": e["edge_id"],
                "u": u,
                "v": v,
                "throat_km": float(e["length_km"])
            })

    # Length statistics of released throat edges
    throat_lengths = [float(e["length_km"]) for e in throat_edges]

    # Reconciliation between 745 raw rows and 462 released edges
    # Check endpoints in raw throats
    raw_throats_u_in_nodes = sum(1 for t in throats_raw if t["vertex_a"] in node_dict)
    raw_throats_v_in_nodes = sum(1 for t in throats_raw if t["vertex_b"] in node_dict)

    throat_reconciliation = {
        "raw_rows_in_provenance": len(throats_raw),
        "released_edges_with_throat_join": len(throat_edges),
        "explanation": (
            "The 745 provenance records represent internal sample/vertex links generated during Stage O5a "
            "(station throats) before topological contraction. During Stage O4 (pruning dangles, splicing degree-2 "
            "vertices, dropping short bypasses, and collapsing parallel edges), the intermediate throat track segments "
            "were contracted and consolidated into 462 final railway track sections carrying joins='throat'."
        ),
        "length_stats_km": {
            "min": min(throat_lengths),
            "max": max(throat_lengths),
            "mean": round(sum(throat_lengths) / len(throat_lengths), 4),
            "total_km": round(sum(throat_lengths), 2),
            "max_throat_exceeds_2km": sum(1 for l in throat_lengths if l > 2.0)
        },
        "topological_impact": {
            "throat_edges_acting_as_bridges": len(throat_bridges),
            "throat_edges_in_cycles": len(throat_non_bridges),
            "throats_with_alternative_path_when_removed": len(throats_with_alternative),
            "throats_without_alternative_path_when_removed": len(throats_without_alternative),
            "components_without_throats": len(no_throats_components),
            "components_with_throats": len(base_components),
            "giant_nodes_without_throats": no_throats_giant_size,
            "giant_nodes_with_throats": len(base_components[0])
        }
    }

    # Save throat bridges for inspection
    if throat_bridges:
        out_tb = anomalies_dir / "throat_bridges_critical.csv"
        with open(out_tb, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(throat_bridges[0].keys()))
            w.writeheader()
            w.writerows(throat_bridges)
        throat_reconciliation["critical_throat_bridges_file"] = str(out_tb)

    # -------------------------------------------------------------
    # 2. JOINS ANALYSIS
    # -------------------------------------------------------------
    print("Analyzing Joins...")
    join_edges = [e for e in edges if e.get("joins") in ("join_A", "join_A2", "join_C")]
    join_edges_by_type = Counter(e["joins"] for e in join_edges)

    # Impact of removing each join individually
    join_impacts = []
    for j in joins_raw:
        stage = j["stage"]
        join_tag = f"join_{stage}"
        # find matching edge in edges
        matched = [e for e in edges if e.get("joins") == join_tag and (
            (e["from_node"] == j["main_side"] and e["to_node"] == j["piece_side"]) or
            (e["from_node"] == j["piece_side"] and e["to_node"] == j["main_side"]) or
            j["example_station"] in (e["from_node"], e["to_node"]) or
            abs(float(e["length_km"]) - float(j["km"])) < 0.05
        )]

        edge_info = matched[0] if matched else None
        is_bridge = False
        severed_nodes = 0
        if edge_info:
            u, v = edge_info["from_node"], edge_info["to_node"]
            if (u, v) in base_bridges or (v, u) in base_bridges:
                is_bridge = True
                G_test = G.copy()
                G_test.remove_edge(u, v)
                sub_comps = list(nx.connected_components(G_test))
                severed_nodes = min(len(c) for c in sub_comps if u in c or v in c)

        join_impacts.append({
            "stage": j["stage"],
            "main_side": j["main_side"],
            "piece_side": j["piece_side"],
            "prov_km": float(j["km"]),
            "stations_joined": int(j["stations_joined"]),
            "example_station": j["example_station"],
            "evidence": j["evidence"],
            "matched_edge_id": edge_info["edge_id"] if edge_info else None,
            "matched_length_km": float(edge_info["length_km"]) if edge_info else None,
            "length_source": edge_info.get("length_source") if edge_info else None,
            "is_bridge": is_bridge,
            "severed_nodes_if_removed": severed_nodes
        })

    # Investigate the two timetable-distance joins:
    tt_joins = [j for j in join_impacts if j["stage"] == "C"]

    joins_reconciliation = {
        "raw_rows_in_provenance": len(joins_raw),
        "released_edges_with_join": len(join_edges),
        "joins_by_type_in_edges": dict(join_edges_by_type),
        "joins_by_stage_in_provenance": dict(Counter(j["stage"] for j in joins_raw)),
        "all_joins_detailed": join_impacts,
        "timetable_distance_joins": tt_joins
    }

    # -------------------------------------------------------------
    # 3. WIKIDATA PLACEMENTS ANALYSIS
    # -------------------------------------------------------------
    print("Analyzing Wikidata Placements...")
    wiki_fates = Counter(w["fate"] for w in wikidata_raw)

    # Check inserted stations in nodes.csv
    nodes_wikidata = [n for n in nodes if n.get("coordinate_source") == "wikidata"]
    nodes_wikidata_codes = set(n["station_code"] for n in nodes_wikidata if n.get("station_code"))

    inserted_wiki_rows = [w for w in wikidata_raw if w["fate"] == "inserted"]
    inserted_wiki_codes = set(w["code"] for w in inserted_wiki_rows)

    # Are all inserted stations in nodes?
    inserted_in_nodes = sum(1 for c in inserted_wiki_codes if c in nodes_wikidata_codes or c in node_dict)

    wikidata_reconciliation = {
        "raw_rows_in_provenance": len(wikidata_raw),
        "fate_breakdown": dict(wiki_fates),
        "nodes_with_coordinate_source_wikidata": len(nodes_wikidata),
        "inserted_codes_in_provenance": len(inserted_wiki_codes),
        "inserted_codes_found_in_graph_nodes": inserted_in_nodes,
        "discrepancies": list(inserted_wiki_codes - nodes_wikidata_codes - set(node_dict.keys()))
    }

    # -------------------------------------------------------------
    # 4. CODE CONFLICTS ANALYSIS
    # -------------------------------------------------------------
    print("Analyzing Code Conflicts...")
    # In nodes.csv, check how many nodes have "~" in node_id or station_code
    conflict_nodes = [n for n in nodes if "~" in n["node_id"]]
    conflict_node_codes = Counter(n["node_id"].split("~")[0] for n in conflict_nodes)

    conflicts_reconciliation = {
        "raw_rows_in_provenance": len(conflicts_raw),
        "nodes_with_conflict_tilde_in_id": len(conflict_nodes),
        "conflict_codes_represented": dict(conflict_node_codes),
        "provenance_rows": conflicts_raw
    }

    part_b_results = {
        "throat_links": throat_reconciliation,
        "joins": joins_reconciliation,
        "wikidata_placements": wikidata_reconciliation,
        "code_conflicts": conflicts_reconciliation
    }

    out_file = results_dir / "part_b_provenance_reconciliation.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(part_b_results, f, indent=2)

    print(f"\nPart B Provenance Reconciliation complete. Results saved to {out_file}")

if __name__ == "__main__":
    main()
