"""E-718 - E-709's severance criticality, rerun on v2.x-open (remediation Step 9).

Same metrics as E-709 (stable class, D-055): bridges, cut points, exposure of daily train
movements to bridges, load concentration and the detour cost of the busiest sections. Three
changes, each forced by v2:
  1. no duplicate-pair contraction: v2 has no known same-place duplicates (V2-25 closed);
  2. "stations severed" counts station nodes only, because the v2 physical graph also holds
     junction nodes, which E-709's node count would inflate;
  3. two views (D-066): `physical` (with 2024 trains per day, for exposure and load) and
     `places` (structure only; places sections carry no service).

    python sever_v2.py <version: v2_0_open | v2_1_open> <stage: structure | exposure | load | corridors>
Writes out/<version>/.
"""
from __future__ import annotations
import json, sys
from collections import defaultdict
from pathlib import Path
import networkx as nx
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARTIFACT_KM, ARTIFACT_SEVERED = 1.0, 1      # E-709's intra-station artifact rule


def graph(ver, view):
    g = ROOT / "03_graph_construction" / f"graph_{ver}" / "open"
    if view == "places": g = g / "places"
    n = pd.read_csv(g / "nodes.csv", low_memory=False); e = pd.read_csv(g / "edges.csv")
    tpd, dist = {}, {}
    if view == "physical":
        es = pd.read_csv(ROOT / "03_graph_construction" / f"service_layer_{ver}" / "open" / "edge_service.csv")
        tpd = dict(zip(es.edge_id, es.trains_per_day)); dist = dict(zip(es.edge_id, es.distinct_trains))
    G = nx.Graph()
    for r in n.itertuples():
        G.add_node(r.node_id, name=r.node_name, state=r.state, station=r.node_type == "station")
    for r in e.itertuples():
        G.add_edge(r.from_node, r.to_node, km=float(r.length_km), eid=r.edge_id,
                   tpd=float(tpd.get(r.edge_id, 0.0)), distinct=int(dist.get(r.edge_id, 0)))
    return G.subgraph(max(nx.connected_components(G), key=len)).copy()


def nst(H, nodes):
    return sum(1 for x in nodes if H.nodes[x]["station"])


def structure(H, view):
    tot_st = nst(H, H)
    brs = []
    for u, v in nx.bridges(H):
        d = H[u][v]; H.remove_edge(u, v)
        c = nx.node_connected_component(H, u); H.add_edge(u, v, **d)
        s = nst(H, c)
        brs.append(dict(view=view, kind="bridge", eid=d["eid"], a=u, b=v, a_name=H.nodes[u]["name"], b_name=H.nodes[v]["name"],
                        km=round(d["km"], 3), trains_per_day=round(d["tpd"], 2), distinct_trains=d["distinct"],
                        stations_severed=min(s, tot_st - s), nodes_severed=min(len(c), H.number_of_nodes() - len(c)),
                        state=H.nodes[u]["state"]))
    aps = []
    for a in list(nx.articulation_points(H)):
        attrs, inc = dict(H.nodes[a]), [(x, dict(H[a][x])) for x in H[a]]
        H.remove_node(a)
        comps = sorted(nx.connected_components(H), key=len, reverse=True)
        H.add_node(a, **attrs)
        for x, d in inc: H.add_edge(a, x, **d)
        sev = [nst(H, c) for c in comps[1:]]
        aps.append(dict(view=view, kind="cut_point", node=a, name=attrs["name"], is_station=attrs["station"], degree=len(inc),
                        stations_severed=sum(sev), fragments=len(comps), largest_severed=max(sev) if sev else 0,
                        trains_per_day_incident=round(sum(d["tpd"] for _, d in inc), 2), state=attrs["state"]))
    br, ap = pd.DataFrame(brs), pd.DataFrame(aps)
    return dict(view=view, nodes=H.number_of_nodes(), stations=tot_st, edges=H.number_of_edges(),
                bridges=len(br), cut_points=len(ap), station_cut_points=int(ap.is_station.sum()),
                bridge_share_of_edges=round(len(br) / H.number_of_edges(), 4),
                bridges_carrying_traffic=int((br.trains_per_day > 0).sum()),
                km_on_bridges=round(float(br.km.sum()), 1),
                share_km_on_bridges=round(float(br.km.sum()) / sum(d["km"] for *_, d in H.edges(data=True)), 4)), br, ap


def exposure(H, ver, out):
    """Share of daily train movements whose route crosses a bridge (E-709's measure).
    A simple path crosses a bridge exactly when the bridge separates its two ends, so the bridges a
    movement crosses are the edges on the path between its ends in the bridge tree (2-edge-connected
    components joined by bridges). Same result as E-709's shortest-path test, in seconds."""
    p = pd.read_csv(ROOT / "03_graph_construction" / f"service_layer_{ver}" / "open" / "service_edges_directed.csv",
                    usecols=["from_station", "to_station", "trains_per_day"])
    p = p[p.from_station.isin(H) & p.to_station.isin(H) & (p.from_station != p.to_station)]
    p = p.groupby(["from_station", "to_station"], as_index=False).trains_per_day.sum()
    brs = list(nx.bridges(H))
    K = H.copy(); K.remove_edges_from(brs)
    comp = {}
    for i, c in enumerate(nx.connected_components(K)):
        for x in c: comp[x] = i
    T = nx.Graph()
    T.add_nodes_from(set(comp.values()))
    for u, v in brs: T.add_edge(comp[u], comp[v], br=frozenset((u, v)))
    per, tot, cross, rows = defaultdict(float), 0.0, 0.0, []
    for o, grp in p.groupby("from_station"):
        tp = nx.single_source_shortest_path(T, comp[o])
        for r in grp.itertuples():
            w = float(r.trains_per_day); tot += w
            path = tp[comp[r.to_station]]
            hit = {T[path[i]][path[i + 1]]["br"] for i in range(len(path) - 1)}
            if hit:
                cross += w
                for e in hit: per[e] += w
                rows.append(dict(origin=o, dest=r.to_station, trains_per_day=round(w, 3), bridges_crossed=len(hit)))
    pd.DataFrame(rows).to_csv(out / "exposed_service_pairs.csv", index=False)
    pb = pd.DataFrame([dict(a=sorted(k)[0], b=sorted(k)[1], trains_per_day_dependent=round(v, 2)) for k, v in per.items()])
    pb.sort_values("trains_per_day_dependent", ascending=False).to_csv(out / "bridge_dependency.csv", index=False)
    return dict(pairs_routed=len(p), pairs_unroutable=0, movements_per_day=round(tot, 1),
                movements_crossing_a_bridge=round(cross, 1), share_exposed=round(cross / tot, 4),
                bridges_with_dependent_traffic=len(pb))


def load(H, out):
    e = pd.DataFrame([dict(a=u, b=v, eid=d["eid"], km=round(d["km"], 3), trains_per_day=round(d["tpd"], 2),
                           a_name=H.nodes[u]["name"], b_name=H.nodes[v]["name"]) for u, v, d in H.edges(data=True)])
    e = e.sort_values("trains_per_day", ascending=False).reset_index(drop=True)
    s = e.trains_per_day.values; tot = s.sum()
    conc = {f"top_{k}pct_share": round(float(s[:max(1, int(len(s) * k / 100))].sum() / tot), 4) for k in (1, 5, 10, 25)}
    brset = {frozenset(x) for x in nx.bridges(H)}; det = []
    for r in e.head(100).itertuples():
        if frozenset((r.a, r.b)) in brset:
            det.append(dict(eid=r.eid, a_name=r.a_name, b_name=r.b_name, trains_per_day=r.trains_per_day, km=r.km,
                            detour_km=None, detour_factor=None, severs=True)); continue
        d = H[r.a][r.b]; H.remove_edge(r.a, r.b)
        try: alt = nx.dijkstra_path_length(H, r.a, r.b, weight="km")
        except nx.NetworkXNoPath: alt = None
        H.add_edge(r.a, r.b, **d)
        det.append(dict(eid=r.eid, a_name=r.a_name, b_name=r.b_name, trains_per_day=r.trains_per_day, km=r.km,
                        detour_km=round(alt - r.km, 2) if alt else None,
                        detour_factor=round(alt / r.km, 2) if alt and r.km else None, severs=False))
    dt = pd.DataFrame(det); dt.to_csv(out / "top_load_detour.csv", index=False); e.to_csv(out / "edge_load_ranked.csv", index=False)
    nb = dt[~dt.severs].dropna(subset=["detour_factor"])
    return dict(sections=len(e), trains_per_day_total=round(float(tot), 1), median_trains_per_day=round(float(e.trains_per_day.median()), 2),
                sections_with_no_service=int((e.trains_per_day == 0).sum()), concentration=conc,
                top100_that_sever=int(dt.severs.sum()), top100_median_detour_factor=round(float(nb.detour_factor.median()), 2),
                top100_detour_over_3x=int((nb.detour_factor > 3).sum()),
                top100_median_detour_km=round(float(nb.detour_km.median()), 1))


def corridors(out):
    br = pd.read_csv(out / "bridges.csv"); br = br[br.view == "physical"].copy()
    dep = pd.read_csv(out / "bridge_dependency.csv")
    dm = {frozenset((r.a, r.b)): r.trains_per_day_dependent for r in dep.itertuples()}
    br["trains_per_day_dependent"] = [dm.get(frozenset((a, b)), 0.0) for a, b in zip(br.a, br.b)]
    br["artifact"] = (br.km < ARTIFACT_KM) & (br.stations_severed == ARTIFACT_SEVERED)
    art, real = br[br.artifact], br[~br.artifact]
    art.sort_values("trains_per_day", ascending=False).to_csv(out / "intra_station_artifacts.csv", index=False)
    B = nx.Graph()
    for r in real.itertuples():
        B.add_edge(r.a, r.b, km=r.km, tpd=r.trains_per_day, dep=r.trains_per_day_dependent, severed=r.stations_severed, eid=r.eid,
                   an=r.a_name, bn=r.b_name, st=r.state)
    rows = []
    for comp in nx.connected_components(B):
        S = B.subgraph(comp); ed = [d for *_, d in S.edges(data=True)]
        ends = [n for n in S if S.degree(n) == 1]
        rows.append(dict(sections=S.number_of_edges(), km=round(sum(x["km"] for x in ed), 1),
                         max_stations_severed=max(x["severed"] for x in ed), max_trains_per_day=round(max(x["tpd"] for x in ed), 2),
                         max_dependent_trains_per_day=round(max(x["dep"] for x in ed), 2),
                         weakest_section_eid=max(ed, key=lambda x: x["severed"])["eid"],
                         endpoints=" | ".join(sorted(str(n) for n in ends)[:4]),
                         states=", ".join(sorted({str(x["st"]) for x in ed if pd.notna(x["st"])})[:3])))
    co = pd.DataFrame(rows).sort_values(["max_stations_severed", "max_dependent_trains_per_day"], ascending=False).reset_index(drop=True)
    co.insert(0, "corridor_id", [f"SC{i:04d}" for i in range(len(co))])
    co.to_csv(out / "severance_corridors.csv", index=False)
    ap = pd.read_csv(out / "cut_points.csv"); ap = ap[ap.view == "physical"]
    jn = ap[(ap.degree >= 3) & (ap.stations_severed > 1)].sort_values(["stations_severed", "trains_per_day_incident"], ascending=False)
    jn.to_csv(out / "junction_cut_points.csv", index=False)
    return dict(bridges_total=len(br), intra_station_artifacts=int(br.artifact.sum()), real_bridges=len(real),
                severance_corridors=len(co), corridors_with_traffic=int((co.max_trains_per_day > 0).sum()),
                corridors_severing_over_50=int((co.max_stations_severed > 50).sum()),
                corridors_severing_over_200=int((co.max_stations_severed > 200).sum()),
                longest_chain_sections=int(co.sections.max()), junction_cut_points=len(jn),
                junction_cut_points_over_50=int((jn.stations_severed > 50).sum()),
                worst_corridors=co.head(5)[["corridor_id", "sections", "km", "max_stations_severed", "max_dependent_trains_per_day", "endpoints", "states"]].to_dict("records"))


def main():
    ver, stage = sys.argv[1], sys.argv[2]
    out = HERE / "out" / ver; out.mkdir(parents=True, exist_ok=True)
    rp = out / "E-718_report.json"
    rpt = json.loads(rp.read_text()) if rp.exists() else dict(release=f"graph_{ver}/open")
    if stage == "structure":
        res, brs, aps = {}, [], []
        for view in ("physical", "places"):
            r, b, a = structure(graph(ver, view), view); res[view] = r; brs.append(b); aps.append(a)
        pd.concat(brs).to_csv(out / "bridges.csv", index=False); pd.concat(aps).to_csv(out / "cut_points.csv", index=False)
        rpt["structure"] = res
    elif stage == "exposure": rpt["exposure"] = exposure(graph(ver, "physical"), ver, out)
    elif stage == "load": rpt["load"] = load(graph(ver, "physical"), out)
    elif stage == "corridors": rpt["corridors"] = corridors(out)
    rp.write_text(json.dumps(rpt, indent=1, default=str))
    print(json.dumps(rpt.get(stage), indent=1, default=str)[:2500])


if __name__ == "__main__":
    main()
