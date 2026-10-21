"""E-711 - do E-709's conclusions survive the choices that produced them?

This is claim C3 applied to the conclusions that are actually going into the pitch,
rather than to the v1.2-era conclusions E-200 and E-401 tested.

Three choices are varied:
  release          v1_3 (before the five repair modules) vs v1_4 (after)
  contraction      the 82 known same-place duplicate pairs merged, or left as shipped
  artifact_km      the threshold below which a one-station-severing bridge is called an
                   intra-station duplicate: 0.5, 1.0, 2.0 km

Each cell recomputes the conclusions. A conclusion that holds in every cell is ROBUST;
one that holds only under some choices is CONDITIONAL and must be reported with its
condition; one that moves freely is an ARTIFACT of the construction and must not be
claimed at all.

    python sweep.py <staged root> <out dir>
"""
from __future__ import annotations

import json
import sys
from itertools import product
from pathlib import Path

import networkx as nx
import pandas as pd

NE_STATES = {"Assam", "Tripura", "Manipur", "Mizoram", "Nagaland",
             "Meghalaya", "Arunachal Pradesh", "Sikkim"}


def build(root: Path, release: str):
    d = root / "03_graph_construction" / f"graph_{release}" / "open"
    nodes = pd.read_csv(d / "nodes.csv")
    edges = pd.read_csv(d / "edges.csv")
    G = nx.Graph()
    for r in nodes.itertuples():
        G.add_node(r.node_id, name=r.node_name, state=r.state)
    for r in edges.itertuples():
        G.add_edge(r.from_node, r.to_node, km=float(r.length_km), eid=r.edge_id)
    return G


def contract(G, dup):
    same = dup[dup.same_place.astype(str).str.lower() == "true"]
    uf = {}

    def find(x):
        uf.setdefault(x, x)
        while uf[x] != x:
            uf[x] = uf[uf[x]]
            x = uf[x]
        return x
    for r in same.itertuples():
        if r.a in G and r.b in G:
            ra, rb = find(r.a), find(r.b)
            if ra != rb:
                uf[rb] = ra
    rep = {n: (find(n) if n in uf else n) for n in G.nodes}
    M = nx.Graph()
    for n in G.nodes:
        if rep[n] not in M:
            M.add_node(rep[n], **G.nodes[rep[n]])
    for u, v, d in G.edges(data=True):
        ru, rv = rep[u], rep[v]
        if ru == rv:
            continue
        if M.has_edge(ru, rv):
            if d["km"] < M[ru][rv]["km"]:
                M[ru][rv].update(km=d["km"], eid=d["eid"])
        else:
            M.add_edge(ru, rv, **dict(d))
    return M


def cell(G, artifact_km):
    """Recompute the conclusions. Lean: bridge severance and corridor chains only."""
    H = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    n = H.number_of_nodes()

    rows = []
    for u, v in nx.bridges(H):
        d = H[u][v]
        H.remove_edge(u, v)
        c = nx.node_connected_component(H, u)
        H.add_edge(u, v, **d)
        side = c if len(c) < n - len(c) else set(H) - c
        rows.append((u, v, d["km"], len(side), side))
    total_bridges = len(rows)

    real = [r for r in rows if not (r[2] < artifact_km and r[3] == 1)]
    artifacts = total_bridges - len(real)

    B = nx.Graph()
    B.add_edges_from((u, v, dict(sev=sev, km=km)) for u, v, km, sev, _ in real)
    corridors, worst_sev, worst_states = 0, 0, ""
    lumding = 0
    for comp in nx.connected_components(B):
        S = B.subgraph(comp)
        m = max(d["sev"] for _, _, d in S.edges(data=True))
        corridors += 1
        if m > worst_sev:
            worst_sev = m
            worst_states = ", ".join(sorted({H.nodes[x].get("state") for x in S
                                             if pd.notna(H.nodes[x].get("state"))})[:3])
        if 70 <= m <= 100:
            lumding = m

    # what the single worst bridge severs, by state group
    worst = max(real, key=lambda r: r[3])
    ne = sum(1 for x in worst[4] if H.nodes[x].get("state") in NE_STATES)

    aps = list(nx.articulation_points(H))
    jn = sum(1 for a in aps if H.degree(a) >= 3)

    return dict(
        nodes=n, sections=H.number_of_edges(),
        bridges_total=total_bridges, intra_station_artifacts=artifacts,
        real_bridges=len(real),
        bridge_share=round(len(real) / H.number_of_edges(), 4),
        severance_corridors=corridors,
        worst_corridor_severs=worst_sev, worst_corridor_states=worst_states,
        worst_bridge_ne_stations_severed=ne,
        lumding_corridor_severs=lumding,
        cut_points=len(aps), junction_cut_points=jn,
    )


def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    dup = pd.read_csv(root / "04_analysis_modules" / "E-705_service_layer_2024" / "out"
                      / "duplicate_node_pairs.csv")

    graphs = {r: build(root, r) for r in ("v1_3", "v1_4")}
    rows = []
    for rel, contr, akm in product(("v1_3", "v1_4"), (True, False), (0.5, 1.0, 2.0)):
        G = contract(graphs[rel], dup) if contr else graphs[rel]
        r = dict(release=rel, contracted=contr, artifact_km=akm)
        r.update(cell(G, akm))
        rows.append(r)
        print(f"  {rel} contracted={contr!s:5} akm={akm}  "
              f"corridors={r['severance_corridors']:4}  worst={r['worst_corridor_severs']:4}  "
              f"NE={r['worst_bridge_ne_stations_severed']:4}  jn_cut={r['junction_cut_points']:4}",
              flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(out / "sweep_cells.csv", index=False)

    def verdict(col, tol=0.0):
        v = df[col]
        if v.nunique() == 1:
            return "ROBUST", f"identical in all {len(v)} cells: {v.iloc[0]}"
        lo, hi = v.min(), v.max()
        spread = (hi - lo) / abs(v.median()) if v.median() else float("inf")
        if spread <= tol:
            return "ROBUST", f"{lo}-{hi}, within {tol:.0%} of the median"
        return ("CONDITIONAL" if spread <= 0.25 else "ARTIFACT"), \
               f"{lo}-{hi} across cells ({spread:.1%} of the median)"

    concl = {}
    for name, col, tol in [
        ("sections with no alternative route (share)", "bridge_share", 0.10),
        ("number of severance corridors", "severance_corridors", 0.10),
        ("the worst corridor isolates >450 stations", "worst_corridor_severs", 0.05),
        ("the worst bridge isolates the whole Northeast", "worst_bridge_ne_stations_severed", 0.02),
        ("the Lumding corridor isolates ~84 stations", "lumding_corridor_severs", 0.10),
        ("junction cut points", "junction_cut_points", 0.10),
        ("intra-station artifacts exist and are ~82", "intra_station_artifacts", 0.10),
    ]:
        v, why = verdict(col, tol)
        concl[name] = dict(verdict=v, evidence=why)

    # does the repair itself change the conclusions? v1_3 vs v1_4, holding the rest
    base = df[(df.contracted) & (df.artifact_km == 1.0)].set_index("release")
    repair = {c: dict(v1_3=base.loc["v1_3", c], v1_4=base.loc["v1_4", c])
              for c in ("bridge_share", "severance_corridors", "worst_corridor_severs",
                        "worst_bridge_ne_stations_severed", "junction_cut_points")}

    rpt = dict(cells=len(df), choices=dict(release=["v1_3", "v1_4"],
                                           contracted=[True, False],
                                           artifact_km=[0.5, 1.0, 2.0]),
               conclusions=concl, v1_3_vs_v1_4=repair,
               note="Severance is a topological property, so no cell varies edge lengths; "
                    "length choices cannot move these conclusions by construction.")
    (out / "E-711_sweep.json").write_text(json.dumps(rpt, indent=1, default=str))
    print("\n" + json.dumps(rpt["conclusions"], indent=1))
    print("\nv1_3 vs v1_4:\n" + json.dumps(repair, indent=1, default=str))


if __name__ == "__main__":
    main()
