"""E-720 - E-711's robustness sweep of the severance conclusions, on v2.x-open (remediation Step 9).

Choices varied: release (v2_0_open, v2_1_open) x view (physical, places; D-066) x artifact_km
(0.5, 1.0, 2.0). E-711's duplicate contraction is dropped (no known v2 duplicates, V2-25), and
severance counts stations only. Same verdict rule as E-711: ROBUST within tolerance in every cell,
CONDITIONAL within 25% spread, ARTIFACT beyond.

    python sweep_v2.py
"""
import json
from itertools import product
from pathlib import Path
import networkx as nx
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NE = {"Assam", "Tripura", "Manipur", "Mizoram", "Nagaland", "Meghalaya", "Arunachal Pradesh", "Sikkim"}


def giant(ver, view):
    # the released packages: their places view carries `state` (the working build's does not)
    d = ROOT / "03_graph_construction" / "release" / f"rail-intel-{ver.replace('_open', '-open').replace('_', '.')}" / ("places" if view == "places" else "graph")
    n = pd.read_csv(d / "nodes.csv", low_memory=False); e = pd.read_csv(d / "edges.csv")
    G = nx.Graph()
    for r in n.itertuples(): G.add_node(r.node_id, state=r.state, st=r.node_type == "station")
    for r in e.itertuples(): G.add_edge(r.from_node, r.to_node, km=float(r.length_km))
    return G.subgraph(max(nx.connected_components(G), key=len)).copy()


def bridges(H):
    tot = sum(1 for x in H if H.nodes[x]["st"]); rows = []
    for u, v in nx.bridges(H):
        d = H[u][v]; H.remove_edge(u, v); c = nx.node_connected_component(H, u); H.add_edge(u, v, **d)
        side = c if sum(1 for x in c if H.nodes[x]["st"]) <= tot / 2 else set(H) - c
        stn = [x for x in side if H.nodes[x]["st"]]
        rows.append((u, v, d["km"], len(stn), sum(1 for x in stn if H.nodes[x]["state"] in NE), stn))
    return rows


def cell(H, rows, akm):
    real = [r for r in rows if not (r[2] < akm and r[3] == 1)]
    B = nx.Graph(); B.add_edges_from((u, v, dict(sev=s)) for u, v, km, s, ne, _ in real)
    worst, wstates, n_corr = 0, "", 0
    for comp in nx.connected_components(B):
        n_corr += 1; S = B.subgraph(comp); m = max(d["sev"] for *_, d in S.edges(data=True))
        if m > worst:
            worst = m; wstates = ", ".join(sorted({str(H.nodes[x]["state"]) for x in S if pd.notna(H.nodes[x]["state"])})[:3])
    wb = max(real, key=lambda r: r[3])
    aps = list(nx.articulation_points(H))
    return dict(sections=H.number_of_edges(), bridges_total=len(rows), intra_station_artifacts=len(rows) - len(real),
                real_bridges=len(real), bridge_share=round(len(real) / H.number_of_edges(), 4), severance_corridors=n_corr,
                worst_corridor_severs=worst, worst_corridor_states=wstates, worst_bridge_ne_stations_severed=wb[4],
                cut_points=len(aps), junction_cut_points=sum(1 for a in aps if H.degree(a) >= 3))


cells = []
for ver, view in product(("v2_0_open", "v2_1_open"), ("physical", "places")):
    H = giant(ver, view); rows = bridges(H)
    for akm in (0.5, 1.0, 2.0):
        cells.append(dict(release=ver, view=view, artifact_km=akm, **cell(H, rows, akm)))
df = pd.DataFrame(cells)
out = HERE / "out"; out.mkdir(exist_ok=True); df.to_csv(out / "sweep_cells.csv", index=False)


def verdict(d, col, tol):
    v = d[col]
    if v.nunique() == 1: return "ROBUST", f"identical in all {len(v)} cells: {v.iloc[0]}"
    lo, hi, med = v.min(), v.max(), v.median()
    spread = (hi - lo) / abs(med) if med else float("inf")
    if spread <= tol: return "ROBUST", f"{lo}-{hi}, within {tol:.0%} of the median"
    return ("CONDITIONAL" if spread <= 0.25 else "ARTIFACT"), f"{lo}-{hi} across cells ({spread:.1%} of the median)"


TESTS = [("sections with no alternative route (share)", "bridge_share", 0.10),
         ("number of severance corridors", "severance_corridors", 0.10),
         ("size of the worst corridor (stations severed)", "worst_corridor_severs", 0.05),
         ("Northeast stations severed by the worst bridge", "worst_bridge_ne_stations_severed", 0.02),
         ("junction cut points", "junction_cut_points", 0.10),
         ("intra-station artifact bridges", "intra_station_artifacts", 0.10)]
rpt = dict(cells=len(df), choices=dict(release=["v2_0_open", "v2_1_open"], view=["physical", "places"], artifact_km=[0.5, 1.0, 2.0]))
for scope, d in (("all_cells", df), ("v2_1_only", df[df.release == "v2_1_open"])):
    rpt[scope] = {name: dict(zip(("verdict", "evidence"), verdict(d, col, tol))) for name, col, tol in TESTS}
base = df[df.artifact_km == 1.0].set_index(["release", "view"])
rpt["v2_0_vs_v2_1_at_1km"] = base[["bridge_share", "severance_corridors", "worst_corridor_severs", "worst_corridor_states",
                                   "worst_bridge_ne_stations_severed", "junction_cut_points", "intra_station_artifacts"]].reset_index().to_dict("records")
(out / "E-720_sweep.json").write_text(json.dumps(rpt, indent=1, default=str))
print(df[["release", "view", "artifact_km", "bridge_share", "severance_corridors", "worst_corridor_severs", "worst_corridor_states",
          "worst_bridge_ne_stations_severed", "junction_cut_points", "intra_station_artifacts"]].to_string(index=False))
for s in ("all_cells", "v2_1_only"):
    print("\n" + s); [print(f"  {k}: {v['verdict']} — {v['evidence']}") for k, v in rpt[s].items()]
