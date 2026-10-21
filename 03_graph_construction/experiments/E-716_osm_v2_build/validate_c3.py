"""E-716 milestone C3 - validate v2.0-open against v1.4.1 and the outside references.

    python validate_c3.py [repo root]

1  the E-708 gates (G1-G9), rerun on v2.0 through the v1.4 loaders
2  section lengths against timetable distances: the E-715 sample of 423 pairs, and every
   v1.4 section with an official distance whose two stations are both in v2.0
3  the stable class by station code: bridges, cut points, the stations each bridge
   severs; on the whole graph and on the served network (edges with a 2024 train)
4  every cut-point difference on the served network sorted into a named cause

Writes graph_v2_0_open/work/c3_report.json and c3_*.csv. Nothing is built or changed.
"""
import json, sys, time
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
# C3a is the roadmap's gate. C3b reuses v1.4's own thresholds. C3c names the two retrodictive
# cases; its 0.8 overlap was set at checkpoint CP1, after measuring. C3d is a reporting rule,
# not a quality bar: every difference written down with a cause; "other" goes to the register.
RETRODICTIVE = {"Siliguri corridor (Barsoi-Makuria)": "BOE|MFA", "Lumding-Badarpur hill section": "HTL|MYD"}
GATE = dict(retrodictive_overlap=0.8)


def load(G3, ver, served=False, places=False):
    """A graph by station code. For v2.0 the stable class is read on the places view (D-066),
    the station-level form comparable with v1.4; lengths always on the physical graph."""
    if places:
        sys.path.insert(0, str(HERE)); import osm_build as ob
        n = pd.read_csv(G3 / f"graph_{ver}/open/nodes.csv")
        if not served:
            pn = pd.read_csv(G3 / f"graph_{ver}/open/places/nodes.csv"); pe = pd.read_csv(G3 / f"graph_{ver}/open/places/edges.csv")
            G = nx.Graph(); G.add_nodes_from(pn.node_id)
            G.add_weighted_edges_from(zip(pe.from_node, pe.to_node, pe.length_km), weight="km")
        else:
            G, _, _, _ = load(G3, ver, True)
            for u, v, d in G.edges(data=True): d.update(rows=(), via=frozenset())
            stations = set(n.node_id[n.node_type == "station"])
            ob.o4_places(G, stations, 1.0)
        code = {r.node_id: str(r.station_code).upper() for r in n.itertuples() if pd.notna(r.station_code) and r.node_id in G}
        return G, n, None, code
    n = pd.read_csv(G3 / f"graph_{ver}/open/nodes.csv"); e = pd.read_csv(G3 / f"graph_{ver}/open/edges.csv")
    if served:
        es = pd.read_csv(G3 / f"service_layer_{ver}/open/edge_service.csv")
        e = e[e.edge_id.isin(set(es.edge_id[es.trains_per_day > 0]))]
    G = nx.Graph(); G.add_nodes_from(n.node_id)
    G.add_weighted_edges_from(zip(e.from_node, e.to_node, e.length_km), weight="km")
    code = {r.node_id: str(r.station_code).upper() for r in n.itertuples() if pd.notna(r.station_code)}
    return G, n, e, code


def e708_gates(root):
    sys.path.insert(0, str(root / "03_graph_construction/experiments/E-708_v1_4_build"))
    import v14
    old = v14.SLUG
    try:
        v14.SLUG = "v2_0_open"
        return v14.stage_gates(root, root / "03_graph_construction/graph_v2_0_open")
    finally:
        v14.SLUG = old


def lengths(G3):
    G, n2, e2, _ = load(G3, "v2_0_open")
    cw = pd.read_csv(G3 / "graph_v2_0_open/station_code_crosswalk.csv")
    ids = set(n2.node_id); al = dict(zip(cw.code, cw.graph_node))
    res = lambda c: c if c in ids else al.get(c)
    n14 = pd.read_csv(G3 / "graph_v1_4_1/open/nodes.csv"); e14 = pd.read_csv(G3 / "graph_v1_4_1/open/edges.csv")
    code = dict(zip(n14.node_id, n14.station_code.str.upper()))
    cache = {}
    def sp(a, b):
        a, b = res(a), res(b)
        if a is None or b is None or a == b: return np.nan
        if a not in cache: cache[a] = nx.single_source_dijkstra_path_length(G, a, cutoff=300, weight="km")
        return cache[a].get(b, np.nan)
    def score(df, col):
        e = (df[col] / df.official_km - 1).abs()
        tol = ((df[col] - df.official_km).abs() <= (0.05 * df.official_km).clip(lower=1.0))
        return dict(n=int(e.notna().sum()), within_5pct=round(float((e <= .05).mean()), 4),
                    within_1km_or_5pct=round(float(tol.mean()), 4), median_err=round(float(e.median()), 4))
    off = e14[e14.official_km.notna() & (e14.official_km > 0) & (e14.origin == "graph_v1_3/open")].copy()
    off["ca"] = off.from_node.map(code); off["cb"] = off.to_node.map(code)
    off = off.dropna(subset=["ca", "cb"])
    off["v2_km"] = [sp(a, b) for a, b in zip(off.ca, off.cb)]
    both = off[off.v2_km.notna()]; lb = both.length_is_lower_bound.astype(bool)
    p = pd.read_csv(HERE / "e715_pairs.csv"); p["v2_km"] = [sp(a, b) for a, b in zip(p.ca, p.cb)]
    pb = p[p.v2_km.notna()]
    rep = dict(e715_pairs=dict(pairs=int(len(p)), comparable=int(len(pb)), v2=score(pb, "v2_km"), v141=score(pb, "length_km")),
               v14_official_sections=dict(sections=int(len(off)), comparable=int(len(both)), v2=score(both, "v2_km"),
                                          v141=score(both, "length_km"),
                                          on_v141_floor_sections=dict(n=int(lb.sum()), v2=score(both[lb], "v2_km"),
                                                                      v141=score(both[lb], "length_km"))))
    return rep, both


def analyse(G, code):
    H = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    rows = []
    for u, v in nx.bridges(H):
        km = H[u][v]["km"]; H.remove_edge(u, v); side = nx.node_connected_component(H, u); H.add_edge(u, v, km=km)
        if len(side) > H.number_of_nodes() / 2: side = set(H) - side
        rows.append(dict(u=u, v=v, km=km, severed_codes=frozenset(code[x] for x in side if x in code)))
    return H, pd.DataFrame(rows), set(nx.articulation_points(H))


def stable(G3, served):
    G1, n1, _, c1 = load(G3, "v1_4_1", served); G2, n2, _, c2 = load(G3, "v2_0_open", served, places=True)
    cw = pd.read_csv(G3 / "graph_v2_0_open/station_code_crosswalk.csv"); al = dict(zip(cw.code, cw.graph_node))
    H1, B1, A1 = analyse(G1, c1); H2, B2, A2 = analyse(G2, c2)
    common = ({c for c in c1.values()}) & ({c for c in c2.values()} | set(al))
    rep = dict(common_station_codes=len(common))
    for tag, H, B, A, code in (("v141", H1, B1, A1, c1), ("v2", H2, B2, A2, c2)):
        km = sum(d["km"] for *_, d in H.edges(data=True))
        rep[tag] = dict(nodes=H.number_of_nodes(), edges=H.number_of_edges(), bridges=len(B),
                        share_km_on_bridges=round(float(B.km.sum()) / km, 4), cut_points=len(A),
                        cycles=H.number_of_edges() - H.number_of_nodes() + 1)
    cp1 = {c1[a] for a in A1 if a in c1} & common
    cp2 = {c2[a] for a in A2 if a in c2}
    for a in A2:
        if a not in c2: cp2 |= {c2[y] for y in G2[a] if y in c2}
    cp2 &= common
    rep["cut_point_stations"] = dict(v141=len(cp1), v2=len(cp2), both=len(cp1 & cp2),
                                     jaccard=round(len(cp1 & cp2) / len(cp1 | cp2), 4))
    big = B1[B1.severed_codes.map(len) >= 20].drop_duplicates("severed_codes")
    m = []
    for r in big.itertuples():
        a = set(r.severed_codes) & common
        if not a: continue
        bj, bn = 0.0, 0
        for s in B2.severed_codes:
            b = set(s) & common
            if b:
                j = len(a & b) / len(a | b)
                if j > bj: bj, bn = j, len(s)
        m.append(dict(v141_bridge=f"{r.u}|{r.v}", v141_severed=len(r.severed_codes), v2_severed=bn, jaccard=round(bj, 3)))
    M = pd.DataFrame(m).sort_values("v141_severed", ascending=False)
    rep["large_severances"] = dict(n=len(M), matched_jaccard_ge_0_8=int((M.jaccard >= 0.8).sum()),
                                   median_jaccard=round(float(M.jaccard.median()), 3))
    return rep, M, dict(G1=G1, G2=G2, H1=H1, H2=H2, cp1=cp1, cp2=cp2, common=common, c1=c1, c2=c2, al=al)


def classify(x):
    G1, G2, cp1, cp2, common, c1, c2, al = (x[k] for k in ("H1", "H2", "cp1", "cp2", "common", "c1", "c2", "al"))
    inv1 = {v: k for k, v in c1.items()}; inv2 = {v: k for k, v in c2.items()}
    node2 = lambda c: inv2.get(c) or (al.get(c) if al.get(c) in G2 else None)
    def why(Gx, nx_, ny_, Gy):
        if nx_ is None or nx_ not in Gx: return "absent from the other graph's network"
        if Gx.degree(nx_) == 1: return "a terminus in the other graph; the line continues past it here"
        nb = sorted(Gx[nx_]); H = Gx.copy(); H.remove_node(nx_); best = None
        for i in range(len(nb)):
            for j in range(i + 1, len(nb)):
                try:
                    L = nx.shortest_path_length(H, nb[i], nb[j], weight="km") + Gx[nx_][nb[i]]["km"] + Gx[nx_][nb[j]]["km"]
                    best = L if best is None else min(best, L)
                except nx.NetworkXNoPath: pass
        if best is None: return "other"
        return ("on a loop of at most 10 km in the other graph" if best <= 10 else
                "on a longer loop in the other graph: a route one graph has and the other lacks")
    rows = []
    for c in sorted(common):
        a, b = inv1.get(c), node2(c)
        if a not in G1 or b not in G2: continue
        if (c in cp1) == (c in cp2): continue
        if c in cp1: rows.append(dict(code=c, cut_point_in="v1.4.1 only", cause=why(G2, b, a, G1)))
        else: rows.append(dict(code=c, cut_point_in="v2.0 only", cause=why(G1, a, b, G2)))
    R = pd.DataFrame(rows, columns=["code", "cut_point_in", "cause"])
    n_common = sum(1 for c in common if inv1.get(c) in G1 and node2(c) in G2)
    return dict(stations_in_both=n_common, agree=n_common - len(R), agreement=round(1 - len(R) / n_common, 4),
                by_cause={f"{k[0]} | {k[1]}": int(v) for k, v in R.groupby(["cut_point_in", "cause"]).size().items()}), R


def main():
    t0 = time.time()
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[2]
    G3 = root / "03_graph_construction"; work = G3 / "graph_v2_0_open/work"
    v141 = json.loads((G3 / "graph_v1_4_1/gates.json").read_text())
    g = e708_gates(root)
    L, sections = lengths(G3)
    S_all, M_all, _ = stable(G3, False)
    S_srv, M_srv, x = stable(G3, True)
    K, R = classify(x)
    gates = {"C3a_lengths_not_worse_on_e715_pairs":
                 L["e715_pairs"]["v2"]["within_5pct"] >= L["e715_pairs"]["v141"]["within_5pct"]
                 and L["e715_pairs"]["v2"]["median_err"] <= L["e715_pairs"]["v141"]["median_err"],
             "C3b_e708_gates_all_pass_on_v2": bool(g["all_passed"]),
             "C3c_retrodictive_cases_reproduced_on_served_network":
                 all(float(M_srv.loc[M_srv.v141_bridge.isin([b, "|".join(reversed(b.split("|")))]), "jaccard"].max()) >= GATE["retrodictive_overlap"]
                     for b in RETRODICTIVE.values()),
             "C3d_every_served_cut_point_difference_recorded_with_a_cause": bool(R.cause.notna().all())}
    retro = {k: M_srv.loc[M_srv.v141_bridge.isin([b, "|".join(reversed(b.split("|")))])].to_dict("records") for k, b in RETRODICTIVE.items()}
    rep = dict(milestone="C3", e708_gates=dict(v2=g["measured"], v141=v141["measured"], v2_passed=g["gates"]),
               lengths=L, stable_all=S_all, stable_served=S_srv, retrodictive=retro, served_cut_point_differences=K,
               gate=dict(thresholds=GATE, passed=gates, all_passed=all(gates.values())), seconds=round(time.time() - t0, 1))
    (work / "c3_report.json").write_text(json.dumps(rep, indent=1, default=str))
    M_all.to_csv(work / "c3_large_severances_all.csv", index=False)
    M_srv.to_csv(work / "c3_large_severances_served.csv", index=False)
    R.to_csv(work / "c3_cut_point_differences.csv", index=False)
    sections.to_csv(work / "c3_section_lengths.csv", index=False)
    print(json.dumps(rep, indent=1, default=str))


if __name__ == "__main__":
    main()
