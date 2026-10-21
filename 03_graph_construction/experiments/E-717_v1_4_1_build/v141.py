"""graph v1.4.1 - v1.4 with the closure-audit fixes, built by the same machinery.

v1.4 is frozen (D-055) and is never edited. v1.4.1 reuses E-708's stages unchanged and
replaces only the graph stage, adding the fixes the closure audit found. Milestones of
the build roadmap (D-061):

  A1  (this file, now)  I-01  derived node columns recomputed from the graph
                        I-02  the 129 repair sections given their attributes
                        retire columns whose values mislead
  A3  (after your audit) I-03 coordinate fixes and I-05 sign-off arrive as new
                        OVERRIDES.csv rows; docs and manifest stages then freeze it

Every value this file fills is either recomputed from the graph or read from the
evidence row in OVERRIDES.csv that created the section. Values inferred from
neighbouring sections are listed per edge in `repair_attrs_inferred`; what could not
be inferred is listed in `repair_attrs_unresolved`, so nothing is silently guessed.
"""
from __future__ import annotations

import hashlib, re, shutil, sys
from pathlib import Path

import networkx as nx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "E-708_v1_4_build"))
import v14                                                            # noqa: E402

BORN = v14.VERSION                     # "v1.4": repair edge ids keep the version they were born in
v14.VERSION, v14.SLUG = "v1.4.1", "v1_4_1"
VERSION, SLUG = v14.VERSION, v14.SLUG
FROM = "graph_v1_4"                    # decisions are inherited from here, byte for byte

# A1: columns whose values mislead a reader, removed from the release.
RETIRED = dict(
    nodes=["overrides_applied"],       # 0 on every node although 179 overrides were applied (I-23);
                                       # the decision trail is OVERRIDES.csv
    edges=["service_direct",           # 2017 timetable counts that read as 2024 load (I-22);
           "service_load"],            # 2024 service is in service_layer_v1_4_1/
)
# I-02: attributes a repair section takes from the sections it joins.
INFERRED = ["gauge_code", "zone_code", "n_tracks", "corridor_id"]
# the timetable each repair's evidence cites (E-703 / E-704)
SOURCES = {"2017": "datagovin_2017", "2024": "iitkgp_routes_2024",
           "2017+2024": "datagovin_2017+iitkgp_routes_2024"}
EVIDENCE = re.compile(r"\((?P<yrs>[\d+]+)\) at (?P<km>[\d.]+) km")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# --------------------------------------------------------------------- stages
def stage_overrides(root: Path, out: Path) -> dict:
    """Inherit v1.4's decisions unchanged. A3 adds the audited rows on top."""
    src = root / "03_graph_construction" / FROM
    wrote = {}
    for f in ("OVERRIDES.csv", "station_code_crosswalk.csv"):
        shutil.copyfile(src / f, out / f)
        assert sha256(src / f) == sha256(out / f)
        wrote[f] = sha256(out / f)[:12]
    ov = pd.read_csv(out / "OVERRIDES.csv")
    return dict(inherited_from=FROM, files=wrote, rows=len(ov),
                by_action=ov.action.value_counts().to_dict(), new_rows_in_v141=0)


def fix_nodes(nd: pd.DataFrame, G: nx.Graph) -> tuple[pd.DataFrame, dict]:
    """I-01: degree, component_id and in_giant recomputed from the graph itself.

    v1.4 carried v1.3's values; the repairs added and removed sections, so 255 degrees
    were stale. component_id keeps v1.3's scheme (rank by size, ties by smallest id),
    which reproduces every v1.4 label."""
    before = nd.set_index("node_id")[["degree", "component_id", "in_giant"]].copy()
    comps = sorted(nx.connected_components(G), key=lambda c: (-len(c), min(c)))
    label = {n: i for i, c in enumerate(comps) for n in c}
    deg = dict(G.degree())
    nd["degree"] = nd.node_id.map(deg).astype(int)
    nd["component_id"] = nd.node_id.map(label).astype(int)
    nd["in_giant"] = nd.component_id == 0
    after = nd.set_index("node_id")[["degree", "component_id", "in_giant"]]
    changed = {c: int((before[c] != after[c]).sum()) for c in after.columns}
    return nd, changed


def fix_edges(ed: pd.DataFrame, adds: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """I-02: the repair sections get their attributes.

    Read from the override's evidence: official_km, official_source, raised_to_chord.
    Inferred from neighbours: a value is taken only when the sections touching the two
    ends agree on exactly one value; otherwise it stays empty and is listed."""
    base = ed[ed.origin == v14.BASE]
    rep = ed.origin != v14.BASE
    incident: dict[str, list[int]] = {}
    for i, r in zip(base.index, base.itertuples()):
        incident.setdefault(r.from_node, []).append(i)
        incident.setdefault(r.to_node, []).append(i)

    for c in ("repair_attrs_inferred", "repair_attrs_unresolved"):
        ed[c] = pd.Series(pd.NA, index=ed.index, dtype="object")
    unresolved = {c: 0 for c in INFERRED}
    for i in ed.index[rep]:
        a, b = ed.at[i, "from_node"], ed.at[i, "to_node"]
        hit = adds[adds.item_id.isin([f"{a}|{b}", f"{b}|{a}"]) & (adds.audit_file == ed.at[i, "origin"])]
        assert len(hit) == 1, f"{len(hit)} evidence rows for {a}|{b}"
        ev = hit.iloc[0]
        m = EVIDENCE.search(ev.evidence)
        assert m, f"no official distance in the evidence for {a}|{b}"
        ed.at[i, "official_km"] = float(m["km"])
        ed.at[i, "official_source"] = SOURCES[m["yrs"]]
        ed.at[i, "raised_to_chord"] = "floored to the" in ev.evidence
        ed.at[i, "edge_origin"] = BORN
        got, miss = [], []
        for c in INFERRED:
            sa = {ed.at[j, c] for j in incident.get(a, []) if pd.notna(ed.at[j, c])}
            sb = {ed.at[j, c] for j in incident.get(b, []) if pd.notna(ed.at[j, c])}
            pick = sa & sb if len(sa & sb) == 1 else (sa | sb if len(sa | sb) == 1 else set())
            if pick:
                ed.at[i, c] = next(iter(pick)); got.append(c)
            else:
                miss.append(c); unresolved[c] += 1
        ed.at[i, "repair_attrs_inferred"] = ";".join(got) or pd.NA
        ed.at[i, "repair_attrs_unresolved"] = ";".join(miss) or pd.NA
    return ed, dict(repair_sections=int(rep.sum()), unresolved=unresolved,
                    floored_to_chord=int(ed.loc[rep, "raised_to_chord"].sum()))


def stage_graph(root: Path, out: Path) -> dict:
    """E-708's graph stage plus fix_nodes, fix_edges and the retirements."""
    v14.VERSION = BORN                 # build_graph stamps new edge ids with VERSION
    try:
        G, applied, nodes, edges = v14.build_graph(root, out / "OVERRIDES.csv")
    finally:
        v14.VERSION = VERSION
    ov = pd.read_csv(out / "OVERRIDES.csv")
    adds = ov[ov.action == "add_edge"]
    d = out / "open"; d.mkdir(parents=True, exist_ok=True)

    ncols = [c for c in nodes.columns if c not in RETIRED["nodes"]]
    nd = pd.DataFrame([dict(node_id=n, **{c: G.nodes[n].get(c) for c in ncols if c != "node_id"})
                       for n in sorted(G.nodes())])
    nd["dataset_version"] = f"{VERSION}-open"
    nd, nodes_changed = fix_nodes(nd, G)

    ecols = [c for c in edges.columns if c not in ("from_node", "to_node")]
    ed = pd.DataFrame([dict(from_node=u, to_node=v, origin=G[u][v].get("origin"),
                            **{c: G[u][v].get(c) for c in ecols})
                       for u, v in sorted(tuple(sorted(e)) for e in G.edges())])
    ed["dataset_version"] = f"{VERSION}-open"
    pos = dict(zip(nd.node_id, zip(nd.longitude, nd.latitude)))
    ed["length_chord_km"] = [v14.hav(pos.get(r.from_node), pos.get(r.to_node)) for r in ed.itertuples()]
    ed, edge_fix = fix_edges(ed, adds)
    ed = ed.drop(columns=RETIRED["edges"]).sort_values("edge_id")

    nd.to_csv(d / "nodes.csv", index=False); nd.to_parquet(d / "nodes.parquet", index=False)
    ed.to_csv(d / "edges.csv", index=False); ed.to_parquet(d / "edges.parquet", index=False)
    H = nx.Graph()
    for r in nd.itertuples(index=False):
        H.add_node(r.node_id, **{c: ("" if pd.isna(v) else str(v)) for c, v in r._asdict().items() if c != "node_id"})
    for r in ed.to_dict("records"):
        H.add_edge(r["from_node"], r["to_node"], **{c: ("" if pd.isna(v) else str(v)) for c, v in r.items()
                                                    if c not in ("from_node", "to_node")})
    nx.write_graphml(H, d / f"rail_graph_{SLUG}_open.graphml")

    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    return dict(applied=applied, nodes=G.number_of_nodes(), edges=G.number_of_edges(),
                route_km=round(float(ed.length_km.sum()), 1), components=len(comps),
                giant_share=round(len(comps[0]) / G.number_of_nodes(), 4),
                I01_node_values_changed=nodes_changed, I02=edge_fix, retired=RETIRED)
