"""E-716 milestone C2 - OpenStreetMap stages O3b, O5, O4 and O6, with their gate.

    python run_c2.py [repo root]

Runs C1 in memory, then:
  O3b  timetable codes OSM has no station for: aliases and Wikidata placements
  O5   joins the pieces to the main network, each join on stated evidence
  O4   contracts the track to a station-level graph
  O6   the 2024 service layer on it (E-708's stage, unchanged)

O5 runs before O4 so that a join lands at its true point on the track.
Writes graph_v2_0_open/open/ (nodes, edges, crosswalk), service_layer_v2_0_open/open/,
and graph_v2_0_open/work/c2_*.  A working build, not a release.
"""
import json, sys, time
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import osm_build as ob                                                # noqa: E402
import run_c1                                                         # noqa: E402

# D-063 - read from measured distributions, see the decision
STATION_MERGE_KM = 2.0     # same code within this = one station (35 of 48 repeated codes; the rest are > 5 km)
ALIAS_M = 300.0            # Wikidata point this close to an OSM station = the same station, other code
THROAT_MAX_KM = 2.0        # yard/station track a join or throat may use (largest fragment join seen: 1.45 km)
SHORT_GAP_KM = 0.5         # P2 pass 1: a construction/disused way this short inside a line may be a throat
SEARCH_KM = 50.0           # how far along track a join is searched for
SHARE_M = 100.0         # = SNAP_M: a piece's track end this close to a main-network station
BYPASS = (3.0, 1.2, 0.2)
PLACE_KM = 1.0             # D-066: the places view: track points within 1 km along the track are one place
THROAT_TEST = (1.3, 0.5)   # D-065: a throat is added if kept track between its ends is > 1.3 x it + 0.5 km
GAUGE = {"1676": "BG", "1000": "MG", "762": "NG", "610": "NG", "1435": "SG", "1067": "NG",
         "1000;1676": "BG/MG", "610;1676": "BG/NG"}
BUILD_TIMETABLES = ("2017",)   # D-068: the build reads open timetables only; 2024 validates
GATE = dict(min_station_share_in_main=0.995, counted_over="stations with a 2024 train (D-064)")


CACHE = Path.home() / ".cache" / "rail-intel" / "c1.pkl"


def c1_cached(root: Path, stage: str):
    """C1 in memory, or from a cache outside the repo so the build can run in two steps
    on a machine that limits how long one command may take."""
    import pickle
    if stage == "rest" and CACHE.exists():
        with open(CACHE, "rb") as f:
            o = pickle.load(f)
        o["P"] = np.c_[ob.lcc(o["LL"][:, 0], o["LL"][:, 1])]
        o["key"] = ob.make_key(o["C"], o["paths"])
        return o
    o = run_c1.c1(root)
    if stage == "c1":
        # V2-15: keep only what the later steps read, so the build fits a 4 GB machine
        keep = ("W", "S", "refs", "xy", "keep", "reason", "nodes", "seg", "cid", "paths", "C", "LL", "E", "St", "r1", "r2", "r2c", "r3")
        slim = {k: o[k] for k in keep}
        slim["W"] = slim["W"].drop(columns=["node_refs", "wkb"])
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE, "wb") as f:
            pickle.dump(slim, f, protocol=5)
    return o


JOINS = CACHE.with_name("joins.pkl")


def build(root: Path, stage: str = "all"):
    """stage: all (one process) | c1 | joins | graph. joins and graph read the caches the
    previous step wrote, so each step fits a 3-minute, 4 GB machine (V2-15)."""
    import pickle
    t0 = time.time()
    o = c1_cached(root, "c1" if stage == "c1" else ("rest" if stage in ("joins", "graph", "rest") else "all"))
    if stage == "c1":
        return None
    if stage == "graph" and JOINS.exists():
        with open(JOINS, "rb") as f:
            j = pickle.load(f)
        return contract_step(o, j, t0)
    St = o["St"]
    inside = ob.in_india(St.lon.values, St.lat.values,
                         root / "external_data/india_outline_soi_datameet/india-soi.geojson")
    pairs_raw = ob.timetable_pairs(root, BUILD_TIMETABLES)
    tt_codes = set(pairs_raw.a) | set(pairs_raw.b)
    # D-068: Wikidata (P5696, CC0) also lists Indian Railways codes no 2017 train uses; such a
    # code may go to an uncoded OSM station of the same name, but is not placed on its own
    wcodes = pd.read_csv(root / "external_data/wikidata_stations.csv", usecols=["code"]).code.dropna().str.strip()
    wd_codes = set(wcodes[wcodes.str.match(ob.CODE_RE)])
    nbrs = {}
    for a_, b_ in zip(pairs_raw.a, pairs_raw.b):
        nbrs.setdefault(a_, set()).add(b_); nbrs.setdefault(b_, set()).add(a_)
    s, conflicts, same_point = ob.station_nodes(St, tt_codes, STATION_MERGE_KM, inside, neighbours=nbrs)
    k = s[s.kept]
    vm = dict(zip(k.vertex, k.graph_node))
    stations = set(k.graph_node)
    G = ob.vertex_graph(o["E"], vm)
    sp = ob.Splitter(G, o["E"], vm, o["LL"])
    rep = dict(stations=dict(osm_snapped=int(St.vertex.notna().sum()), outside_india=int((~inside[St.vertex.notna().to_numpy()]).sum()),
                             metro_review_dropped=int((s.review_metro & ~s.kept & s.in_india).sum()),
                             kept=int(s.kept.sum()), nodes=len(stations), code_conflicts=len(conflicts),
                             same_track_point_aliases=len(same_point),
                             same_name_merges=int(s.merged_by_name.sum())))
    # O3b
    aliases, inserted, wd, r3b = ob.o3b_wikidata(G, sp, s, root, tt_codes - set(same_point), o["P"], run_c1.SNAP_M,
                                                 ALIAS_M, stations, name_only_codes=wd_codes - set(same_point))
    byname = set(wd.code[wd.fate == "alias_by_name"])
    src = {c: ("wikidata name, uncoded OSM station within 1 km" if c in byname else "wikidata position within 300 m")
           for c in aliases}
    for c, n in same_point.items():
        aliases[c] = n; src[c] = "same OSM track point"
    rep["O3b"] = r3b
    extra_pos = {r.code: (r.lon, r.lat) for r in inserted.itertuples()}
    resolve = lambda c: c if c in stations else aliases.get(c)
    pr = pairs_raw.assign(a=pairs_raw.a.map(resolve), b=pairs_raw.b.map(resolve)).dropna(subset=["a", "b"])
    pr = pr[pr.a != pr.b]
    code_of = {n: n for n in stations if not n.startswith("OSM:") and "~" not in n}
    def share(G):
        comps = sorted(nx.connected_components(G), key=lambda c: -len(c & stations))
        return round(len(comps[0] & stations) / len(stations), 4)
    rep["main_network_station_share_before_O5"] = share(G)
    # O5a station throats, then O5 joins
    F = ob.full_track_graph(o["W"], o["refs"], o["xy"])
    throats, r5a = ob.o5_throat(G, sp, F, o["reason"], o["P"], run_c1.MERGE_M, THROAT_MAX_KM, *THROAT_TEST,
                                short_gap_km=SHORT_GAP_KM)
    rep["O5a"] = r5a
    rep["seconds_throats"] = round(time.time() - t0, 1)
    j = dict(G=G, sp=sp, throats=throats, s=s, conflicts=conflicts, aliases=aliases, alias_source=src, inserted=inserted,
             wd=wd, stations=stations, extra_pos=extra_pos, rep=rep, pairs_raw=pairs_raw, pr=pr, code_of=code_of)
    if stage == "joins":
        with open(JOINS, "wb") as f:
            pickle.dump(j, f, protocol=5)
        return "joins"
    return contract_step(o, j, t0, F)


def contract_step(o, j, t0, F=None):
    """O5 joins, O4 contraction and conflict resolution on the track graph."""
    G, s, stations, rep, sp = j["G"], j["s"], j["stations"], j["rep"], j["sp"]
    if F is None:
        F = ob.full_track_graph(o["W"], o["refs"], o["xy"])
    joins = ob.o5_stitch(G, sp, o["E"], s, o["P"], o["LL"], F, o["reason"], j["pr"], o["nodes"], stations, j["code_of"],
                         j["extra_pos"], THROAT_MAX_KM, SEARCH_KM, SHARE_M)
    del F
    J = pd.DataFrame(joins)
    j["J"] = J
    rep["O5"] = dict(joins=len(J), **{f"stage_{k_}": dict(joins=int(len(g)), km=round(float(g.km.sum()), 2),
                                                         stations=int(g.stations_joined.sum()))
                                       for k_, g in J.groupby("stage")} if len(J) else {})
    H, _, r4 = ob.o4_contract(G, stations, *BYPASS)
    rep["O4"] = r4
    rep["conflicts_resolved"] = resolve_conflicts(H, s, stations, j["conflicts"], pr_all(j["pairs_raw"], stations, j["aliases"]))
    return dict(throats=j["throats"], o=o, s=s, conflicts=j["conflicts"], aliases=j["aliases"], alias_source=j["alias_source"],
                inserted=j["inserted"], wd=j["wd"], J=j["J"], H=H, stations=stations, extra_pos=j["extra_pos"], rep=rep, t0=t0)


def pr_all(pairs_raw, stations, aliases):
    """Timetable consecutive pairs (2017 and 2024) with each code resolved where it can be."""
    res = lambda c: c if c in stations else aliases.get(c, c)
    return pairs_raw.assign(a=pairs_raw.a.map(res), b=pairs_raw.b.map(res))


def resolve_conflicts(H, s, stations, conflicts, pairs):
    """V2-09: a code OSM gives to stations more than 2 km apart. The candidate whose network
    distances to the code's timetable neighbours best match the timetable takes the code; the
    others keep code~osmid. A code with no usable neighbour stays a conflict."""
    out = {}
    for code in conflicts:
        cands = sorted(n for n in stations if n.startswith(code + "~") and n in H)
        nb = pairs[(pairs.a == code) | (pairs.b == code)]
        nb = [(r.b if r.a == code else r.a, r.km) for r in nb.itertuples()]
        nb = [(y, km) for y, km in nb if y in H and y in stations]
        if len(cands) < 2 or not nb: out[code] = "unresolved: no timetable neighbour in the graph"; continue
        score = {}
        for c in cands:
            d = nx.single_source_dijkstra_path_length(H, c, cutoff=500, weight="km")
            score[c] = float(np.median([abs(d.get(y, 1e4) - km) for y, km in nb]))
        best = min(sorted(score), key=lambda c: score[c])
        if score[best] > 10:
            out[code] = f"unresolved: best candidate is {score[best]:.0f} km off the timetable"; continue
        assert code not in H, f"{code} already a node"
        nx.relabel_nodes(H, {best: code}, copy=False)
        stations.discard(best); stations.add(code)
        s.loc[s.graph_node == best, "graph_node"] = code
        out[code] = f"{best} (median {score[best]:.1f} km off the timetable over {len(nb)} neighbours)"
    return out


def tables(b):
    """nodes.csv / edges.csv in the v1.4 schema, so E-708's loaders and stages run on them."""
    o, s, H, stations = b["o"], b["s"], b["H"], b["stations"]
    W, seg, cid, paths, LL, nodes = o["W"], o["seg"], o["cid"], o["paths"], o["LL"], o["nodes"]
    E = o["E"]; chain = E.chain.values
    gv, gcov = ob.chain_attr(W, seg, cid, len(paths), "gauge")
    ev, ecov = ob.chain_attr(W, seg, cid, len(paths), "electrified", ob.ELECTRIFIED)
    lv, _ = ob.chain_attr(W, seg, cid, len(paths), "name")
    kmc = E.km.values
    sk = s[s.kept].drop_duplicates("graph_node").set_index("graph_node")
    def pos(v):
        if v in sk.index: return float(sk.at[v, "lon"]), float(sk.at[v, "lat"])
        if v in b["extra_pos"]: return b["extra_pos"][v]
        i = int(v[1:]); return (float(LL[i, 0]), float(LL[i, 1])) if v[0] == "s" else (float(nodes.lon.values[i]), float(nodes.lat.values[i]))
    def jid(v):
        if v in stations: return v
        if v[0] == "n": return f"JN:osm{int(nodes.osm_node.values[int(v[1:])])}"
        lo, la = pos(v); return f"JN:@{lo:.6f},{la:.6f}"
    ren = {v: jid(v) for v in H}
    comps = sorted(nx.connected_components(H), key=lambda c: (-len(c & stations), min(ren[x] for x in c)))
    lab = {v: i for i, c in enumerate(comps) for v in c}
    nrows = []
    ins = b["inserted"].set_index("code") if len(b["inserted"]) else pd.DataFrame()
    uncoded_code = {}                                   # an uncoded OSM station that carries a code
    for c_, v_ in sorted(b["aliases"].items()):
        if v_.startswith("OSM:"): uncoded_code.setdefault(v_, c_)
    for v in H:
        lo, la = pos(v); st = v in stations
        src = ("wikidata" if v in b["extra_pos"] else "osm") if st else "osm_track"
        nm = (ins.at[v, "name"] if v in b["extra_pos"] else sk.at[v, "name"]) if st else None
        code = v if st and not v.startswith("OSM:") and "~" not in v else uncoded_code.get(v)
        nrows.append(dict(node_id=ren[v], node_type="station" if st else "junction", node_name=nm,
                          station_code=code, longitude=round(lo, 7), latitude=round(la, 7),
                          coordinate_source=src, state=None, zone_code=None,
                          osm_node_id=(int(sk.at[v, "node_id"]) if st and v in sk.index else
                                       (int(nodes.osm_node.values[int(v[1:])]) if v[0] == "n" and not st else None)),
                          degree=H.degree(v), component_id=lab[v], in_giant=lab[v] == 0))
    nd = pd.DataFrame(nrows).sort_values("node_id").reset_index(drop=True)
    # V2-12: where the station meets its track, beside where OSM puts the station point
    tv = s[s.kept].drop_duplicates("graph_node").set_index("graph_node").vertex
    def track_pos(v):
        if v in b["extra_pos"]:
            t = int(ins.at[v, "sample"]); return float(LL[t, 0]), float(LL[t, 1])
        k = tv.get(v)
        if k is None: return (None, None)
        i = int(k[1:]); return (float(LL[i, 0]), float(LL[i, 1])) if k[0] == "s" else (float(nodes.lon.values[i]), float(nodes.lat.values[i]))
    tp = {ren[v]: track_pos(v) for v in H if v in stations}
    nd["track_lon"] = nd.node_id.map(lambda x: round(tp[x][0], 7) if x in tp and tp[x][0] is not None else None)
    nd["track_lat"] = nd.node_id.map(lambda x: round(tp[x][1], 7) if x in tp and tp[x][1] is not None else None)
    erows = []
    for u, v, d in H.edges(data=True):
        a, c = sorted((ren[u], ren[v]))
        rows = [r for r in d["rows"] if E.kind.values[r] == "track"]
        def maj(vals, w):
            t = {}
            for x, ww in zip(vals, w):
                if x is not None: t[x] = t.get(x, 0) + ww
            return max(sorted(t), key=lambda x: t[x]) if t else None
        w = [kmc[r] for r in rows]; ch = [chain[r] for r in rows]
        g = maj([gv[x] for x in ch], w); e = maj([ev[x] for x in ch], w)
        tot = sum(w) or 1.0
        via = sorted(d.get("via", frozenset()))
        src = "timetable" if "join_C" in via else "osm_track"
        lo1, la1 = pos(u); lo2, la2 = pos(v)
        erows.append(dict(edge_id=f"v2.0:{a}|{c}", from_node=a, to_node=c, length_km=round(d["km"], 4),
                          length_source=src, length_is_lower_bound=False,
                          length_chord_km=round(float(ob.hav_km(lo1, la1, lo2, la2)), 4),
                          gauge_code=GAUGE.get(str(g), str(g) if g else None),
                          gauge_tag_share=round(sum(wi * gcov[x] for wi, x in zip(w, ch)) / tot, 3) if rows else None,
                          electrified=e, electrified_tag_share=round(sum(wi * ecov[x] for wi, x in zip(w, ch)) / tot, 3) if rows else None,
                          line_name=maj([lv[x] for x in ch], w), joins=";".join(via) or None,
                          origin="osm", dataset_version="v2.0-open-work"))
    ed = pd.DataFrame(erows).sort_values("edge_id").reset_index(drop=True)
    nd["dataset_version"] = "v2.0-open-work"
    # D-066: the places view, derived; the physical graph above keeps its exact lengths
    Hp = H.copy()
    rp, place = ob.o4_places(Hp, stations, PLACE_KM)
    pid = {}
    for v in H:
        if v in Hp: pid[ren[v]] = ren[v]
        elif v in place and place[v] in Hp: pid[ren[v]] = ren[place[v]]
        else: pid[ren[v]] = None                    # a junction spliced out: it lies inside a places-view section
    nd["place_id"] = nd.node_id.map(pid)
    pn = nd[nd.node_id.isin({ren[v] for v in Hp})].drop(columns=["place_id"]).copy()
    pdeg = {ren[v]: Hp.degree(v) for v in Hp}
    pn["degree"] = pn.node_id.map(pdeg)
    pn["junctions_in_place"] = pn.node_id.map(nd.place_id.value_counts()).fillna(1).astype(int) - 1
    pe = []
    for u, v, d in Hp.edges(data=True):
        a, c = sorted((ren[u], ren[v]))
        via = sorted(d.get("via", frozenset()))
        pe.append(dict(edge_id=f"v2.0p:{a}|{c}", from_node=a, to_node=c, length_km=round(d["km"], 4),
                       length_source="timetable" if "join_C" in via else "osm_track", joins=";".join(via) or None))
    pe = pd.DataFrame(pe).sort_values("edge_id").reset_index(drop=True)
    b["rep"]["places_view"] = dict(**rp, nodes=int(len(pn)), edges=int(len(pe)), km=round(float(pe.length_km.sum()), 1),
                                   cycles=int(len(pe) - len(pn) + nx.number_connected_components(Hp)))
    b["places"] = (pn.sort_values("node_id").reset_index(drop=True), pe)
    cw = pd.DataFrame([dict(code=k_, resolution="alias", graph_node=v_, source=b["alias_source"][k_])
                       for k_, v_ in sorted(b["aliases"].items())])
    return nd, ed, cw


def attributes(root, nd, ed):
    """Service flags (V2-06, V2-07) and state (V2-14), added after the service layers exist."""
    import geo
    G3 = root / "03_graph_construction"
    e24 = pd.read_csv(G3 / "service_layer_v2_0_open/open/edge_service.csv")
    e17 = pd.read_csv(G3 / "service_layer_v2_0_open/open_2017/edge_service.csv")
    p24 = pd.read_csv(G3 / "service_layer_v2_0_open/open/service_edges_directed.csv")
    p17 = pd.read_csv(G3 / "service_layer_v2_0_open/open_2017/service_edges_directed.csv")
    s24 = set(e24.edge_id[e24.trains_per_day > 0]); s17 = set(e17.edge_id[e17.distinct_trains_2017 > 0])
    ed = ed.drop(columns=[c for c in ("served_2024", "scheduled_2017", "line_status") if c in ed])
    ed["served_2024"] = ed.edge_id.isin(s24); ed["scheduled_2017"] = ed.edge_id.isin(s17)
    ed["line_status"] = np.where(ed.served_2024, "served_2024", np.where(ed.scheduled_2017, "scheduled_2017_only", "no_service_data"))
    n24 = set(p24.from_station) | set(p24.to_station); n17 = set(p17.from_station) | set(p17.to_station)
    nd = nd.drop(columns=[c for c in ("served_2024", "scheduled_2017", "line_status") if c in nd])
    st = nd.node_type == "station"
    nd["served_2024"] = st & nd.node_id.isin(n24); nd["scheduled_2017"] = st & nd.node_id.isin(n17)
    nd["line_status"] = np.where(~st, None, np.where(nd.served_2024, "served_2024",
                                 np.where(nd.scheduled_2017, "scheduled_2017_only", "no_service_data")))
    P = geo.read_polygons_shp(root / "external_data/state_boundaries_datameet/Admin2.shp")
    h = geo.point_in_polygons(nd.longitude.values, nd.latitude.values, P)
    nd["state"] = [P[i][0] if i >= 0 else None for i in h]
    nd["state_source"] = np.where(h >= 0, "datameet Admin2 (CC BY 4.0), point in polygon", None)
    return nd, ed


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    stage = next((a[8:] for a in sys.argv[1:] if a.startswith("--stage=")), "all")   # all | c1 | joins | graph | service
    root = Path(args[0]) if args else HERE.parents[2]
    out = root / "03_graph_construction" / "graph_v2_0_open"
    work = out / "work"
    if stage in ("all", "c1", "joins", "graph", "rest"):
        b = build(root, stage)
        if b is None:
            print(f"C1 cached at {CACHE}"); return
        if b == "joins":
            print(f"joins cached at {JOINS}; run --stage=graph next"); return
        nd, ed, cw = tables(b)
        (out / "open").mkdir(parents=True, exist_ok=True); work.mkdir(exist_ok=True)
        nd.to_csv(out / "open" / "nodes.csv", index=False); ed.to_csv(out / "open" / "edges.csv", index=False)
        (out / "open" / "places").mkdir(exist_ok=True)
        b["places"][0].to_csv(out / "open" / "places" / "nodes.csv", index=False)
        b["places"][1].to_csv(out / "open" / "places" / "edges.csv", index=False)
        (cw if len(cw) else pd.DataFrame(columns=["code", "resolution", "graph_node", "source"])).to_csv(
            out / "station_code_crosswalk.csv", index=False)
        b["J"].to_csv(work / "c2_joins.csv", index=False)
        b["throats"].to_csv(work / "c2_throat_links.csv", index=False)
        b["wd"].drop(columns=["altLabels"], errors="ignore").to_csv(work / "c2_wikidata_placement.csv", index=False)
        pd.DataFrame(dict(code=b["conflicts"])).to_csv(work / "c2_code_conflicts.csv", index=False)
        rep = b["rep"]; rep["seconds_graph"] = round(time.time() - b["t0"], 1)
        (work / "c2_partial.json").write_text(json.dumps(rep, indent=1, default=str))
        if stage == "graph":
            print("graph written; run --stage=service next"); return
    rep = json.loads((work / "c2_partial.json").read_text())
    nd = pd.read_csv(out / "open" / "nodes.csv"); ed = pd.read_csv(out / "open" / "edges.csv")
    cw = pd.read_csv(out / "station_code_crosswalk.csv")
    t1 = time.time()
    # O6: E-708's service stage on this graph
    sys.path.insert(0, str(root / "03_graph_construction/experiments/E-708_v1_4_build"))
    import v14
    v14.SLUG = "v2_0_open"; v14.VERSION = "v2.0-open-work"
    r6 = v14.stage_service(root, out)
    def served(p):
        f = pd.read_csv(p); return set(f.from_station) | set(f.to_station)
    s2 = served(out.parent / "service_layer_v2_0_open/open/service_edges_directed.csv")
    p141 = out.parent / "service_layer_v1_4_1/open/service_edges_directed.csv"
    s141 = served(p141) if p141.exists() else None
    rep["O6"] = r6
    # the open service layer (GODL 2017) and the release attributes (P2 pass 4)
    import service17
    rep["O6_2017"] = service17.build(root)
    nd, ed = attributes(root, nd, ed)
    nd.to_csv(out / "open" / "nodes.csv", index=False); ed.to_csv(out / "open" / "edges.csv", index=False)
    st = nd[nd.node_type == "station"]
    main_share = round(float(st.in_giant.mean()), 4)
    r24 = pd.read_csv(root / "external_data/iitkgp_rstgcn_network_2024/Indian-Railway-Network-and-Delays/train_routes_Sep2024.csv",
                      dtype=str, usecols=["station_code"])
    c24 = set(r24.station_code.str.strip())
    al = dict(zip(cw.code, cw.graph_node)) if len(cw) else {}
    served_nodes = {c if c in set(st.node_id) else al.get(c) for c in c24} - {None}
    sv = st[st.node_id.isin(served_nodes)]
    chord_below = ed[(ed.length_source == "osm_track") & (ed.length_km < ed.length_chord_km * 0.999 - 0.001)]
    rep["graph"] = dict(nodes=int(len(nd)), stations=int(len(st)), junctions=int((nd.node_type == "junction").sum()),
                        edges=int(len(ed)), route_km=round(float(ed.length_km.sum()), 1),
                        components=int(nd.component_id.nunique()), cycles=int(len(ed) - len(nd) + nd.component_id.nunique()),
                        max_degree=int(nd.degree.max()),
                        edges_by_length_source=ed.length_source.value_counts().to_dict(),
                        edges_with_station_transfer=int(ed.joins.fillna("").str.contains("join_A2").sum()),
                        km_gauge_known=round(float(ed.loc[ed.gauge_code.notna(), "length_km"].sum() / ed.length_km.sum()), 4),
                        km_electrification_known=round(float(ed.loc[ed.electrified.notna(), "length_km"].sum() / ed.length_km.sum()), 4),
                        km_electrified_of_known=round(float(ed.loc[ed.electrified == "yes", "length_km"].sum() / ed.loc[ed.electrified.notna(), "length_km"].sum()), 4),
                        station_share_in_main=main_share,
                        served_2024_stations=int(len(sv)), served_2024_share_in_main=round(float(sv.in_giant.mean()), 4),
                        served_stations_v2=len(s2), served_stations_v141=len(s141) if s141 else None)
    rep["graph"]["sections_shorter_than_station_point_chord"] = int(len(chord_below))
    rep["graph"]["of_which_by_more_than_200m"] = int(((chord_below.length_chord_km - chord_below.length_km) > 0.2).sum())
    tags_ok = bool(ed.loc[ed.gauge_tag_share > 0, "gauge_code"].notna().all()
                   and ed.loc[ed.electrified_tag_share > 0, "electrified"].notna().all())
    gates = {"C2a_no_straight_line_lengths_and_tags_carried":
                 set(ed.length_source) <= {"osm_track", "timetable"} and tags_ok,
             # D-064: counted over stations with a train in September 2024 (decided 2026-10-19)
             "C2b_995_of_2024_served_stations_in_main_network":
                 rep["graph"]["served_2024_share_in_main"] >= GATE["min_station_share_in_main"],
             "C2c_served_stations_at_least_v141": s141 is not None and len(s2) >= len(s141),
             # D-065: the roadmap's C1a, measured where it means route km: on the station graph
             "C2d_route_km_within_7pct_of_official": abs(rep["graph"]["route_km"] / ob.OFFICIAL_ROUTE_KM - 1) <= 0.07}
    rep["gate"] = dict(thresholds=GATE, passed=gates, all_passed=all(gates.values()),
                       note_C2b=f"{rep['graph']['served_2024_share_in_main']:.2%} of 2024-served stations (the gate, D-064); {main_share:.2%} of all stations")
    rep["parameters"] = dict(station_merge_km=STATION_MERGE_KM, alias_m=ALIAS_M, throat_max_km=THROAT_MAX_KM,
                             short_gap_km=SHORT_GAP_KM, throat_test=THROAT_TEST, place_km=PLACE_KM,
                             search_km=SEARCH_KM, share_m=SHARE_M, bypass=BYPASS, decision="D-063")
    rep["seconds_service"] = round(time.time() - t1, 1)
    (work / "c2_report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps(rep, indent=1, default=str))


if __name__ == "__main__":
    main()
