"""E-501 -- audit of graph v1.2 (run after E-500). Two parts, each < 3 min.

  --part A   W-1 robustness: removal count under other thresholds, and the
             independent timetable test -- do trains that travel between a
             removed edge's endpoints stop along the route v1.2 keeps?
  --part B   Do the paper's conclusions survive the repair? The same battery
             as every sweep cell (sensitivity.measure_graph) on v1.2, compared
             with v1.0 (E-200 default) and v1.1 (E-401 length=hybrid) under the
             published tolerance bands.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PHASE3 = HERE.parents[1]
REPO = PHASE3.parent
sys.path.insert(0, str(PHASE3))
from railgraph import repair, sensitivity as S  # noqa: E402

V11, V12 = PHASE3 / "graph_v1_1", PHASE3 / "graph_v1_2"
SCHED = REPO / "01_data_engineering" / "processed_data" / "cleaned_schedules.csv"


def part_a() -> dict:
    e = pd.read_parquet(V11 / "edges.parquet")
    c = pd.read_csv(REPO / "02_graph_inputs" / "graph_dataset" / "corridors.csv")
    rem = pd.read_csv(V12 / "removed_edges.csv")
    sens = {}
    for name, kw in (("default", {}), ("cross_band_0.85_1.20", {"cross_band": (0.85, 1.2)}),
                     ("cross_band_0.85_1.50", {"cross_band": (0.85, 1.5)}),
                     ("same_band_0.90_1.10", {"same_band": (0.9, 1.1)}),
                     ("support_max_0.25", {"support_max": 0.25}),
                     ("support_max_0.75", {"support_max": 0.75})):
        r = repair.find_removals(e, c, **kw)
        sens[name] = {"n": int(len(r)), "overlap_with_default": int(len(set(r.edge_id) & set(rem.edge_id)))}
    # timetable confirmation
    sc = pd.read_csv(SCHED, usecols=["train_number", "station_code", "stop_sequence"]) \
        .sort_values(["train_number", "stop_sequence"])
    trains = {t: g.station_code.tolist() for t, g in sc.groupby("train_number")}
    pos = collections.defaultdict(list)
    for t, s in trains.items():
        for i, x in enumerate(s):
            pos[x].append((t, i))
    e12 = pd.read_parquet(V12 / "edges.parquet")
    G = nx.from_pandas_edgelist(e12, "from_node", "to_node", edge_attr="length_km")
    rows = []
    for x in rem.itertuples():
        pv = {t: i for t, i in pos[x.from_node]}
        conf = other = direct = 0
        for t, j in pos[x.to_node]:
            i = pv.get(t)
            if i is None or abs(j - i) > 40:
                continue
            lo, hi = sorted((i, j))
            seq = trains[t][lo:hi + 1]
            if len(seq) == 2:
                direct += 1
                continue
            try:
                L = sum(nx.dijkstra_path_length(G, a, b, weight="length_km") for a, b in zip(seq, seq[1:]))
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                L = np.inf
            if L <= 1.35 * x.alt_km:
                conf += 1
            else:
                other += 1
        rows.append({"edge_id": x.edge_id, "kind": x.kind, "trains_stopping_along_kept_route": conf,
                     "trains_other_route": other, "trains_nonstop": direct})
    d = pd.DataFrame(rows)
    d.to_csv(HERE / "removal_timetable_evidence.csv", index=False)
    anyt = d[["trains_stopping_along_kept_route", "trains_other_route", "trains_nonstop"]].sum(1) > 0
    return {"removal_sensitivity": sens, "timetable": {
        "removed": int(len(d)), "with_any_train_between_endpoints": int(anyt.sum()),
        "confirmed_trains_stop_along_kept_route": int((d.trains_stopping_along_kept_route > 0).sum()),
        "only_nonstop_trains": int((anyt & (d.trains_stopping_along_kept_route == 0) & (d.trains_other_route == 0)).sum()),
        "inconclusive_other_route_only": int(((d.trains_other_route > 0) & (d.trains_stopping_along_kept_route == 0)).sum()),
        "no_train_evidence": int((~anyt).sum())}}


def part_b() -> dict:
    n = pd.read_parquet(V12 / "nodes.parquet")
    e = pd.read_parquet(V12 / "edges.parquet")
    G = nx.Graph()
    for r in n.itertuples(index=False):
        G.add_node(r.node_id, longitude=r.longitude, latitude=r.latitude, node_type=r.node_type)
    for r in e.itertuples(index=False):
        G.add_edge(r.from_node, r.to_node, length_km=float(r.length_km), corridor_id=r.corridor_id,
                   service_load=float(r.service_load) if pd.notna(r.service_load) else 0.0,
                   edge_id=r.edge_id)
    rk = json.loads((PHASE3 / "experiments" / "E-401_derivation_sweep" / "rankings.json").read_text())
    ref = rk.get("default") or rk["length=asis"]   # length=asis is the v1.0 default
    row = S.measure_graph(G, {"cell": "v1.2"}, ref_corridors=ref.get("top_corridors"),
                          ref_nodes=ref.get("top_nodes"))
    c200 = pd.read_csv(PHASE3 / "experiments" / "E-200" / "cells.csv").set_index("cell").loc["default"]
    c401 = pd.read_csv(PHASE3 / "experiments" / "E-401_derivation_sweep" / "cells_derivation.csv").set_index("cell").loc["length=hybrid"]
    out = []
    for k, band in S.BANDS.items():
        v = row.get(k)
        for refname, refrow in (("v1.0", c200), ("v1.1", c401)):
            if k.endswith("_overlap"):
                dev = 1.0 - float(v) if v is not None else np.nan   # overlap with v1.0 default ranking
                if refname == "v1.1":
                    continue
            else:
                rv = float(refrow[k])
                dev = abs(float(v) - rv) / abs(rv) if k in S.RELATIVE else abs(float(v) - rv)
            out.append({"conclusion": k, "vs": refname, "v1_2": float(v),
                        "reference": None if k.endswith("_overlap") else float(refrow[k]),
                        "deviation": float(dev), "band": band, "within_band": bool(dev <= band)})
    t = pd.DataFrame(out)
    t.to_csv(HERE / "conclusions_v1_2.csv", index=False)
    return {"structure": {k: row[k] for k in ("n_nodes", "n_edges", "n_components", "giant_nodes",
                                              "bridges", "independent_cycles", "meshedness", "route_km")},
            "conclusions": out, "all_within_band": bool(t.within_band.all())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=["A", "B"], required=True)
    a = ap.parse_args()
    res = part_a() if a.part == "A" else part_b()
    p = HERE / "report.json"
    rep = json.loads(p.read_text()) if p.exists() else {"experiment": "E-501"}
    rep[f"part_{a.part}"] = res
    p.write_text(json.dumps(rep, indent=2, default=str))
    print(json.dumps(res, indent=1, default=str)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
