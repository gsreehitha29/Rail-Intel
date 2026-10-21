"""E-709 stage 2 - collapse bridges into severance corridors, and separate the
intra-station artifacts from real vulnerabilities.

Two corrections to the raw structural counts, both forced by what the first pass showed:

1. INTRA-STATION ARTIFACTS. A bridge under 1 km that severs exactly one station is
   not a vulnerability, it is one station held as two nodes. The signature is
   structural, not a name match: two genuinely distinct stations 150 m apart with
   200 trains a day between them and nothing beyond is not a thing that exists.
   This catches the renames the 82-pair duplicate list missed - Allahabad Jn /
   Prayagraj Junction, Vishakapatnam / Waltair, Cheoki / Prayagraj Chheoki.

2. CORRIDORS, NOT EDGES. A single-line corridor with no alternative route appears as
   a chain of consecutive bridges, each severing almost the same set of stations.
   Counting edges counts the same vulnerability a dozen times. Maximal chains in the
   bridge subgraph are the unit that answers the real question: which corridors have
   no alternative route at all.

    python corridors.py <staged root> <out dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import networkx as nx
import pandas as pd

ARTIFACT_KM = 1.0          # a bridge shorter than this, severing exactly one station
ARTIFACT_SEVERED = 1


def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    gdir = root / "03_graph_construction" / "graph_v1_4" / "open"
    nodes = pd.read_csv(gdir / "nodes.csv")
    names = dict(zip(nodes.node_id, nodes.node_name))
    states = dict(zip(nodes.node_id, nodes.state))

    br = pd.read_csv(out / "bridges.csv")
    br = br[br.view == "merged"].copy()
    dep = pd.read_csv(out / "bridge_dependency.csv")
    depmap = {frozenset((r.a, r.b)): r.trains_per_day_dependent for r in dep.itertuples()}
    br["trains_per_day_dependent"] = [depmap.get(frozenset((a, b)), 0.0)
                                      for a, b in zip(br.a, br.b)]

    br["artifact"] = (br.km < ARTIFACT_KM) & (br.stations_severed == ARTIFACT_SEVERED)
    art = br[br.artifact].copy()
    real = br[~br.artifact].copy()
    art.sort_values("trains_per_day", ascending=False).to_csv(
        out / "intra_station_artifacts.csv", index=False)

    # maximal chains of real bridges = severance corridors
    B = nx.Graph()
    for r in real.itertuples():
        B.add_edge(r.a, r.b, km=r.km, tpd=r.trains_per_day, dep=r.trains_per_day_dependent,
                   severed=r.stations_severed, eid=r.eid)
    rows = []
    for comp in nx.connected_components(B):
        S = B.subgraph(comp)
        ed = [d for _, _, d in S.edges(data=True)]
        deg1 = [n for n in S if S.degree(n) == 1]
        st = sorted({states.get(n) for n in S if pd.notna(states.get(n))})
        rows.append(dict(
            corridor_id=f"SC{len(rows):04d}",
            sections=S.number_of_edges(), stations=S.number_of_nodes(),
            km=round(sum(e["km"] for e in ed), 1),
            max_stations_severed=max(e["severed"] for e in ed),
            min_stations_severed=min(e["severed"] for e in ed),
            max_trains_per_day=round(max(e["tpd"] for e in ed), 2),
            max_dependent_trains_per_day=round(max(e["dep"] for e in ed), 2),
            weakest_section_eid=max(ed, key=lambda e: e["severed"])["eid"],
            endpoints=" | ".join(names.get(n, n) for n in deg1[:4]),
            states=", ".join(st[:3]),
        ))
    co = pd.DataFrame(rows).sort_values(
        ["max_stations_severed", "max_dependent_trains_per_day"], ascending=False)
    co.to_csv(out / "severance_corridors.csv", index=False)

    # cut points that are real junctions, not degree-2 stations on a single line
    ap = pd.read_csv(out / "cut_points.csv")
    ap = ap[ap.view == "merged"].copy()
    jn = ap[(ap.degree >= 3) & (ap.stations_severed > 1)].copy()
    jn = jn.sort_values(["stations_severed", "trains_per_day_incident"], ascending=False)
    jn.to_csv(out / "junction_cut_points.csv", index=False)

    rpt = dict(
        bridges_total=len(br),
        intra_station_artifacts=int(br.artifact.sum()),
        artifact_traffic_max=round(float(art.trains_per_day.max()), 1) if len(art) else 0,
        real_bridges=len(real),
        severance_corridors=len(co),
        corridors_with_traffic=int((co.max_trains_per_day > 0).sum()),
        corridors_severing_over_50=int((co.max_stations_severed > 50).sum()),
        corridors_severing_over_200=int((co.max_stations_severed > 200).sum()),
        longest_chain_sections=int(co.sections.max()),
        cut_points_total=len(ap),
        cut_points_degree2_on_single_line=int(((ap.degree == 2)).sum()),
        junction_cut_points=len(jn),
        junction_cut_points_over_50=int((jn.stations_severed > 50).sum()),
    )
    (out / "E-709_corridors.json").write_text(json.dumps(rpt, indent=1, default=str))
    print(json.dumps(rpt, indent=1))
    print("\n=== severance corridors, worst 14")
    print(co.head(14)[["corridor_id", "sections", "km", "max_stations_severed",
                       "max_dependent_trains_per_day", "endpoints", "states"]]
          .to_string(index=False))
    print("\n=== junction cut points, worst 12")
    print(jn.head(12)[["name", "degree", "stations_severed", "fragments",
                       "trains_per_day_incident", "state"]].to_string(index=False))
    print("\n=== intra-station artifacts carrying traffic")
    print(art[art.trains_per_day > 0][["a_name", "b_name", "km", "trains_per_day"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
