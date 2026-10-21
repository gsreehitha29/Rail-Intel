"""E-403 -- topology case inspection (Phase 3 plan item 5).

Inspects, without changing the topology, the three kinds of case the Phase 3
plan names: isolated components, high-degree nodes, and the `is_dissolvable`
junctions. Reads the shipped `nodes.csv` / `edges.csv` only.

The question D-020 left open -- are the 17 small components real isolated
lines or residual data gaps? -- is answered by measurement: for each one, the
great-circle distance to the nearest giant-component node, and whether any
Phase 2 corridor connects it to the giant. Thresholds are stated and varied,
not chosen.

Run: python 03_graph_construction/experiments/E-403_topology_cases/run.py
"""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DS = REPO / "02_graph_inputs" / "graph_dataset"
R = 6371.0088


def hav(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def main() -> int:
    n = pd.read_csv(DS / "nodes.csv"); e = pd.read_csv(DS / "edges.csv")
    cor = pd.read_csv(DS / "corridors.csv").set_index("corridor_id")
    G = nx.from_pandas_edgelist(e, "from_node", "to_node", edge_attr=["edge_id", "length_km", "corridor_id", "gauge_code"])
    ni = n.set_index("node_id")
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    giant, small = comps[0], comps[1:]
    gn = ni.loc[list(giant)].dropna(subset=["longitude"])

    # ---------------- isolated components ----------------
    rows = []
    for i, c in enumerate(small, 1):
        sub = G.subgraph(c)
        best = (np.inf, None, None)
        for node in c:
            lon, lat = ni.loc[node, ["longitude", "latitude"]]
            if pd.isna(lon):
                continue
            d = hav(lon, lat, gn.longitude.to_numpy(), gn.latitude.to_numpy())
            j = int(np.argmin(d))
            if d[j] < best[0]:
                best = (float(d[j]), node, gn.index[j])
        cids = sorted({d["corridor_id"] for *_, d in sub.edges(data=True)})
        rows.append({
            "component": i, "n_nodes": len(c), "n_edges": sub.number_of_edges(),
            "nodes": "; ".join(f"{x} ({ni.loc[x,'node_type'][:4]}) {ni.loc[x,'node_name']}" for x in sorted(c)),
            "node_types": ",".join(sorted({ni.loc[x, 'node_type'] for x in c})),
            "route_km": round(sum(d["length_km"] for *_, d in sub.edges(data=True)), 2),
            "corridors": ",".join(cids),
            "gauge": ",".join(sorted({str(d["gauge_code"]) for *_, d in sub.edges(data=True)})),
            "zone": ",".join(sorted({str(ni.loc[x, 'zone_code']) for x in c})),
            "nearest_giant_node": best[2], "nearest_giant_name": ni.loc[best[2], "node_name"] if best[2] else None,
            "gap_to_giant_km": round(best[0], 3) if np.isfinite(best[0]) else None,
            "corridor_declared_stations": int(cor.loc[cids, "declared_no_of_stations"].fillna(0).sum()),
            "corridor_stations_found": int(cor.loc[cids, "n_stations_found"].fillna(0).sum()),
        })
    comp_df = pd.DataFrame(rows)
    gaps = comp_df.gap_to_giant_km.dropna()
    thresholds = {f"within_{t}km": int((gaps <= t).sum()) for t in (1, 2, 5, 10, 25)}
    comp_df["declared_minus_found"] = comp_df.corridor_declared_stations - comp_df.corridor_stations_found
    comp_df.to_csv(HERE / "small_components.csv", index=False)

    # baselines -- without these a small gap or a deficit means nothing:
    #   (1) how common is a station deficit across ALL corridors?
    #   (2) how far is an ordinary giant node from its nearest OTHER giant node?
    dec = pd.to_numeric(cor.declared_no_of_stations, errors="coerce")
    fnd = pd.to_numeric(cor.n_stations_found, errors="coerce")
    deficit_share_all = float(((dec - fnd) > 0).sum() / ((dec - fnd).notna()).sum())
    lon, lat = gn.longitude.to_numpy(), gn.latitude.to_numpy()
    nn = np.empty(len(gn))
    for s0 in range(0, len(gn), 500):
        D = hav(lon[s0:s0 + 500, None], lat[s0:s0 + 500, None], lon[None, :], lat[None, :])
        D[np.arange(D.shape[0]), np.arange(s0, s0 + D.shape[0])] = np.inf
        nn[s0:s0 + 500] = D.min(axis=1)
    baseline = {"corridors_with_station_deficit_share_all": round(deficit_share_all, 4),
                "giant_node_nearest_other_node_km": {
                    "p25": round(float(np.quantile(nn, .25)), 3),
                    "median": round(float(np.median(nn)), 3),
                    "p75": round(float(np.quantile(nn, .75)), 3),
                    "p95": round(float(np.quantile(nn, .95)), 3)},
                "small_components_gap_km_median": round(float(gaps.median()), 3),
                "small_gap_le_giant_node_p95": int((gaps <= np.quantile(nn, .95)).sum())}

    # ---------------- high-degree nodes ----------------
    deg = pd.Series(dict(G.degree()))
    hd = n[n.degree >= 6].copy()
    hd["strength_km"] = hd.node_id.map(lambda x: sum(d["length_km"] for *_, d in G.edges(x, data=True)))
    hd["distinct_corridors"] = hd.node_id.map(lambda x: len({d["corridor_id"] for *_, d in G.edges(x, data=True)}))
    hd["gauges"] = hd.node_id.map(lambda x: ",".join(sorted({str(d["gauge_code"]) for *_, d in G.edges(x, data=True)})))
    hd = hd.sort_values(["degree", "strength_km"], ascending=False)[
        ["node_id", "node_name", "node_type", "degree", "distinct_corridors", "gauges", "zone_code", "state", "strength_km"]]
    hd.to_csv(HERE / "high_degree_nodes.csv", index=False)
    dist = n.degree.value_counts().sort_index()
    top_share = float(deg.sort_values(ascending=False).head(int(len(deg) * 0.01)).sum() / deg.sum())

    # ---------------- dissolvable junctions ----------------
    d2 = n[n.is_dissolvable].node_id.tolist()
    drows = []
    for x in d2:
        nb = list(G.neighbors(x))
        if len(nb) != 2:
            drows.append({"node_id": x, "anomaly": f"degree {len(nb)}"}); continue
        a, b = nb
        ea, eb = G.edges[x, a], G.edges[x, b]
        drows.append({
            "node_id": x, "node_name": ni.loc[x, "node_name"], "junction_class": ni.loc[x, "junction_class"],
            "neighbour_a": a, "neighbour_b": b,
            "same_corridor": ea["corridor_id"] == eb["corridor_id"],
            "same_gauge": ea["gauge_code"] == eb["gauge_code"],
            "merged_km": round(ea["length_km"] + eb["length_km"], 3),
            "would_duplicate_existing_edge": bool(G.has_edge(a, b)),
            "neighbours_in_giant": bool(a in giant and b in giant),
        })
    dd = pd.DataFrame(drows)
    dd.to_csv(HERE / "dissolvable_junctions.csv", index=False)
    diss = {
        "n": len(dd), "all_degree_2": bool(dd.get("anomaly", pd.Series(dtype=object)).isna().all()),
        "all_operational_junctions": bool(ni.loc[d2, "node_type"].eq("operational_junction").all()),
        "same_corridor_both_sides": int(dd.same_corridor.sum()),
        "same_gauge_both_sides": int(dd.same_gauge.sum()),
        "would_create_duplicate_edge": int(dd.would_duplicate_existing_edge.sum()),
        "junction_class": dd.junction_class.value_counts(dropna=False).to_dict(),
        "merged_km_median": float(dd.merged_km.median()),
    }

    # ---------------- articulation / bridge context for the small cases ----------------
    rep = {
        "experiment": "E-403", "title": "topology case inspection (read-only)",
        "components": {
            "n_components": len(comps), "giant_nodes": len(giant),
            "small_components": len(small),
            "small_component_sizes": sorted([len(c) for c in small], reverse=True),
            "small_nodes_total": int(sum(len(c) for c in small)),
            "small_route_km_total": round(float(comp_df.route_km.sum()), 2),
            "small_node_types": {k: int(v) for k, v in
                                 n[n.node_id.isin(set().union(*small))].node_type.value_counts().items()},
            "gap_to_giant_km": {"min": float(gaps.min()), "median": float(gaps.median()), "max": float(gaps.max())},
            "count_within_threshold": thresholds,
            "no_coordinate": int(comp_df.gap_to_giant_km.isna().sum()),
            "corridors_with_declared_station_deficit": int((comp_df.declared_minus_found > 0).sum()),
        },
        "baselines": baseline,
        "high_degree": {"degree_distribution": {int(k): int(v) for k, v in dist.items()},
                        "mean": round(float(n.degree.mean()), 3), "max": int(n.degree.max()),
                        "n_deg_ge_6": int(len(hd)), "n_deg_7": int((n.degree == 7).sum()),
                        "top_1pct_degree_share_of_endpoints": round(top_share, 4),
                        "hd_node_types": hd.node_type.value_counts().to_dict(),
                        "names_deg7": hd[hd.degree == 7].node_name.tolist()},
        "dissolvable": diss,
    }
    (HERE / "E-403_report.json").write_text(json.dumps(rep, indent=2, default=str))
    print(json.dumps(rep, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
