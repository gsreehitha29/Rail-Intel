"""E-709 - national severance criticality on graph v1.4.

Only stable-class metrics (D-055): cut points, bridges, connectivity and
trains-per-day load. No betweenness, no node-level centrality ranking.

Two views of the network:
  raw    - the release as shipped
  merged - the 82 known same-place duplicate node pairs contracted into one node,
           because a station held as two nodes manufactures a bridge between its
           own halves and makes both halves look like cut points.
The merged view is the headline; the raw view is reported so the size of that
artifact class is visible.

    python sever.py <staged root> <out dir> [stage ...]
stages: structure | exposure | load
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import networkx as nx
import pandas as pd


def read(root: Path):
    g = root / "03_graph_construction" / "graph_v1_4"
    s = root / "03_graph_construction" / "service_layer_v1_4" / "open"
    nodes = pd.read_csv(g / "open" / "nodes.csv")
    edges = pd.read_csv(g / "open" / "edges.csv")
    edge_svc = pd.read_csv(s / "edge_service.csv")
    pairs = pd.read_csv(s / "service_edges_directed.csv")
    dup = pd.read_csv(root / "04_analysis_modules" / "E-705_service_layer_2024"
                      / "out" / "duplicate_node_pairs.csv")
    return nodes, edges, edge_svc, pairs, dup


def build(nodes, edges, edge_svc):
    tpd = dict(zip(edge_svc.edge_id, edge_svc.trains_per_day))
    dist = dict(zip(edge_svc.edge_id, edge_svc.distinct_trains))
    G = nx.Graph()
    for r in nodes.itertuples():
        G.add_node(r.node_id, name=r.node_name, state=r.state, zone=r.zone_code,
                   lon=r.longitude, lat=r.latitude)
    for r in edges.itertuples():
        G.add_edge(r.from_node, r.to_node, km=float(r.length_km), eid=r.edge_id,
                   tpd=float(tpd.get(r.edge_id, 0.0)),
                   distinct=int(dist.get(r.edge_id, 0)),
                   lower_bound=bool(r.length_is_lower_bound))
    return G


def contract(G, dup):
    """Contract each same-place duplicate pair. Returns (graph, node -> rep map)."""
    same = dup[dup.same_place.astype(str).str.lower() == "true"]
    uf = {}

    def find(x):
        uf.setdefault(x, x)
        while uf[x] != x:
            uf[x] = uf[uf[x]]
            x = uf[x]
        return x

    for r in same.itertuples():
        if r.a not in G or r.b not in G:
            continue
        ra, rb = find(r.a), find(r.b)
        if ra != rb:
            uf[rb] = ra
    rep = {n: find(n) if n in uf else n for n in G.nodes}

    M = nx.Graph()
    for n in G.nodes:
        r = rep[n]
        if r not in M:
            M.add_node(r, **G.nodes[r])
    for u, v, d in G.edges(data=True):
        ru, rv = rep[u], rep[v]
        if ru == rv:
            continue                       # the within-station link disappears
        if M.has_edge(ru, rv):             # parallel after contraction: keep shorter,
            e = M[ru][rv]                  # sum the traffic
            e["tpd"] += d["tpd"]
            e["distinct"] += d["distinct"]
            if d["km"] < e["km"]:
                e["km"], e["eid"] = d["km"], d["eid"]
        else:
            M.add_edge(ru, rv, **dict(d))
    return M, rep


def giant(G):
    return G.subgraph(max(nx.connected_components(G), key=len)).copy()


def structure(G, label, nodes_name):
    """Bridges and cut points, each with what it severs and what it carries."""
    H = giant(G)
    out = {}

    brs = []
    for u, v in nx.bridges(H):
        d = H[u][v]
        H.remove_edge(u, v)
        comp = nx.node_connected_component(H, u)
        H.add_edge(u, v, **d)
        small = min(len(comp), H.number_of_nodes() - len(comp))
        brs.append(dict(view=label, kind="bridge", eid=d["eid"], a=u, b=v,
                        a_name=nodes_name.get(u, u), b_name=nodes_name.get(v, v),
                        km=round(d["km"], 3), trains_per_day=round(d["tpd"], 2),
                        distinct_trains=d["distinct"], stations_severed=small,
                        state=H.nodes[u].get("state"), zone=H.nodes[u].get("zone")))
    br = pd.DataFrame(brs)

    aps = []
    for a in nx.articulation_points(H):
        inc = [H[a][n] for n in H[a]]
        H2 = H.copy()
        H2.remove_node(a)
        comps = sorted((len(c) for c in nx.connected_components(H2)), reverse=True)
        aps.append(dict(view=label, kind="cut_point", node=a,
                        name=nodes_name.get(a, a), degree=H.degree(a),
                        stations_severed=sum(comps[1:]), fragments=len(comps),
                        largest_severed=comps[1] if len(comps) > 1 else 0,
                        trains_per_day_incident=round(sum(e["tpd"] for e in inc), 2),
                        state=H.nodes[a].get("state"), zone=H.nodes[a].get("zone")))
    ap = pd.DataFrame(aps)

    out.update(view=label, nodes=H.number_of_nodes(), edges=H.number_of_edges(),
               bridges=len(br), cut_points=len(ap),
               bridge_share_of_edges=round(len(br) / H.number_of_edges(), 4),
               cut_point_share_of_nodes=round(len(ap) / H.number_of_nodes(), 4),
               bridges_carrying_traffic=int((br.trains_per_day > 0).sum()) if len(br) else 0,
               km_on_bridges=round(float(br.km.sum()), 1) if len(br) else 0.0)
    return out, br, ap


def exposure(G, pairs, rep, out_dir):
    """Share of daily train movements whose shortest path crosses a bridge.

    A movement over a bridge has no alternative route at all: if that section is
    lost the service cannot run, it can only be cancelled.
    """
    H = giant(G)
    brset = {frozenset((u, v)) for u, v in nx.bridges(H)}

    p = pairs.copy()
    p["o"] = p.from_station.map(lambda x: rep.get(x, x))
    p["d"] = p.to_station.map(lambda x: rep.get(x, x))
    p = p[(p.o.isin(H)) & (p.d.isin(H)) & (p.o != p.d)]
    p = p.groupby(["o", "d"], as_index=False).trains_per_day.sum()

    per_bridge = defaultdict(float)
    tot = cross = 0.0
    nx_pairs = unroutable = 0
    rows = []
    for o, grp in p.groupby("o"):
        try:
            _, paths = nx.single_source_dijkstra(H, o, weight="km")
        except nx.NetworkXNoPath:
            unroutable += len(grp)
            continue
        for r in grp.itertuples():
            path = paths.get(r.d)
            w = float(r.trains_per_day)
            tot += w
            if path is None:
                unroutable += 1
                continue
            nx_pairs += 1
            hit = [frozenset((path[i], path[i + 1])) for i in range(len(path) - 1)]
            hit = [e for e in hit if e in brset]
            if hit:
                cross += w
                for e in set(hit):
                    per_bridge[e] += w
                rows.append(dict(origin=o, dest=r.d, trains_per_day=round(w, 3),
                                 bridges_crossed=len(set(hit))))
    pd.DataFrame(rows).to_csv(out_dir / "exposed_service_pairs.csv", index=False)
    pb = pd.DataFrame([dict(a=sorted(k)[0], b=sorted(k)[1],
                            trains_per_day_dependent=round(v, 2))
                       for k, v in per_bridge.items()])
    pb = pb.sort_values("trains_per_day_dependent", ascending=False)
    pb.to_csv(out_dir / "bridge_dependency.csv", index=False)
    return dict(pairs_routed=nx_pairs, pairs_unroutable=unroutable,
                movements_per_day=round(tot, 1),
                movements_crossing_a_bridge=round(cross, 1),
                share_exposed=round(cross / tot, 4) if tot else None,
                bridges_with_dependent_traffic=len(pb))


def load(G, out_dir):
    """Load concentration, and the detour cost of losing the busiest sections."""
    H = giant(G)
    e = pd.DataFrame([dict(a=u, b=v, eid=d["eid"], km=round(d["km"], 3),
                           trains_per_day=round(d["tpd"], 2),
                           a_name=H.nodes[u].get("name"), b_name=H.nodes[v].get("name"),
                           state=H.nodes[u].get("state"), zone=H.nodes[u].get("zone"))
                      for u, v, d in H.edges(data=True)])
    e = e.sort_values("trains_per_day", ascending=False).reset_index(drop=True)

    s = e.trains_per_day.sort_values(ascending=False).values
    tot = s.sum()
    conc = {f"top_{k}pct_share": round(float(s[:max(1, int(len(s) * k / 100))].sum() / tot), 4)
            for k in (1, 5, 10, 25)}

    brset = {frozenset((u, v)) for u, v in nx.bridges(H)}
    det = []
    for r in e.head(100).itertuples():
        key = frozenset((r.a, r.b))
        if key in brset:
            det.append(dict(eid=r.eid, a=r.a, b=r.b, a_name=r.a_name, b_name=r.b_name,
                            trains_per_day=r.trains_per_day, km=r.km,
                            detour_km=None, detour_factor=None, severs=True))
            continue
        d = H[r.a][r.b]
        H.remove_edge(r.a, r.b)
        try:
            alt = nx.dijkstra_path_length(H, r.a, r.b, weight="km")
        except nx.NetworkXNoPath:
            alt = None
        H.add_edge(r.a, r.b, **d)
        det.append(dict(eid=r.eid, a=r.a, b=r.b, a_name=r.a_name, b_name=r.b_name,
                        trains_per_day=r.trains_per_day, km=r.km,
                        detour_km=round(alt - r.km, 2) if alt else None,
                        detour_factor=round(alt / r.km, 2) if alt and r.km else None,
                        severs=False))
    dt = pd.DataFrame(det)
    dt.to_csv(out_dir / "top_load_detour.csv", index=False)
    e.to_csv(out_dir / "edge_load_ranked.csv", index=False)

    nb = dt[~dt.severs].dropna(subset=["detour_factor"])
    return dict(sections=len(e), trains_per_day_total=round(float(tot), 1),
                median_trains_per_day=round(float(e.trains_per_day.median()), 2),
                sections_with_no_service=int((e.trains_per_day == 0).sum()),
                concentration=conc,
                top100_that_sever=int(dt.severs.sum()),
                top100_median_detour_factor=round(float(nb.detour_factor.median()), 2)
                if len(nb) else None,
                top100_detour_over_3x=int((nb.detour_factor > 3).sum()) if len(nb) else 0)


def main():
    root = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    want = sys.argv[3:] or ["structure", "exposure", "load"]

    nodes, edges, edge_svc, pairs, dup = read(root)
    G = build(nodes, edges, edge_svc)
    M, rep = contract(G, dup)
    names = dict(zip(nodes.node_id, nodes.node_name))
    rep_out = pd.DataFrame([dict(node=k, representative=v) for k, v in rep.items() if k != v])
    rep_out.to_csv(out / "contracted_nodes.csv", index=False)

    rpt = dict(release="graph_v1_4/open", contracted_pairs=len(rep_out),
               raw_nodes=G.number_of_nodes(), raw_edges=G.number_of_edges(),
               merged_nodes=M.number_of_nodes(), merged_edges=M.number_of_edges())

    if "structure" in want:
        r_raw, br_raw, ap_raw = structure(G, "raw", names)
        r_m, br_m, ap_m = structure(M, "merged", names)
        pd.concat([br_raw, br_m]).to_csv(out / "bridges.csv", index=False)
        pd.concat([ap_raw, ap_m]).to_csv(out / "cut_points.csv", index=False)
        rpt["structure"] = dict(raw=r_raw, merged=r_m, artifact_bridges=r_raw["bridges"] - r_m["bridges"],
                                artifact_cut_points=r_raw["cut_points"] - r_m["cut_points"])
    if "exposure" in want:
        rpt["exposure"] = exposure(M, pairs, rep, out)
    if "load" in want:
        rpt["load"] = load(M, out)

    (out / "E-709_report.json").write_text(json.dumps(rpt, indent=1, default=str))
    print(json.dumps(rpt, indent=1, default=str))


if __name__ == "__main__":
    main()
