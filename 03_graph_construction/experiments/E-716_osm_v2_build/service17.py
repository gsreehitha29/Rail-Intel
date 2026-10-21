"""E-716 - the open service layer: the data.gov.in timetable of 22 Dec 2017 (GODL-India).

    python service17.py [repo root]

The redistributable counterpart of E-708's 2024 layer (V2-19). The 2017 file has no running
days, so it gives scheduled trains per section, not trains per day. Writes
service_layer_v2_0_open/open_2017/: service_edges_directed.csv, edge_service.csv.
"""
import json, sys
from collections import defaultdict
from pathlib import Path

import networkx as nx
import pandas as pd

HERE = Path(__file__).resolve().parent


def build(root: Path) -> dict:
    sys.path.insert(0, str(root / "03_graph_construction/experiments/E-708_v1_4_build"))
    import v14
    v14.SLUG = "v2_0_open"
    G, nodes, edges = v14.load_v14(root)
    node = v14._resolver(root)
    T17, _ = v14._timetables(root, node)
    out = root / "03_graph_construction/service_layer_v2_0_open/open_2017"; out.mkdir(parents=True, exist_ok=True)
    pairs = defaultdict(set); cache = {}
    for t, stops in T17:
        s = [x for x, _ in stops]
        for a, b in zip(s, s[1:]): pairs[(a, b)].add(t)
    rows, cnt = [], defaultdict(set)
    for (a, b) in sorted(pairs):
        k = (a, b) if a < b else (b, a)
        if k not in cache:
            try: cache[k] = nx.single_source_dijkstra(G, k[0], k[1], weight="km", cutoff=400)
            except (nx.NetworkXNoPath, nx.NodeNotFound): cache[k] = (None, None)
        km, path = cache[k]
        rows.append(dict(from_station=a, to_station=b, n_trains_2017=len(pairs[(a, b)]),
                         physical_path_km=round(km, 4) if km is not None else None,
                         physical_hops=len(path) - 1 if path else None))
        if path:
            for u, v in zip(path, path[1:]):
                cnt[G[u][v]["eid"]] |= pairs[(a, b)]
    se = pd.DataFrame(rows)
    se.to_csv(out / "service_edges_directed.csv", index=False)
    es = pd.DataFrame(dict(edge_id=edges.edge_id, distinct_trains_2017=[len(cnt.get(e, ())) for e in edges.edge_id]))
    es.to_csv(out / "edge_service.csv", index=False)
    served = set(se.from_station) | set(se.to_station)
    rep = dict(source="data.gov.in Train_details_22122017.csv (GODL-India)", trains=len(T17), directed_pairs=len(se),
               unroutable_pairs=int(se.physical_path_km.isna().sum()), served_stations=len(served),
               edges_with_service=int((es.distinct_trains_2017 > 0).sum()),
               km_share=round(float(edges.length_km[es.distinct_trains_2017.values > 0].sum() / edges.length_km.sum()), 4),
               note="no running days in the source: counts are scheduled trains, not trains per day")
    (root / "03_graph_construction/graph_v2_0_open/work/c2_service_2017.json").write_text(json.dumps(rep, indent=1))
    return rep


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[2]
    print(json.dumps(build(root), indent=1))


if __name__ == "__main__":
    main()
