"""E-502 -- the service layer as its own artifact: directed, timed, mapped to track.

W-5 ("the graph is undirected, atemporal, uncapacitated"). The physical graph
stays undirected on purpose: the source records track, not running direction,
and Indian track is bidirectional (single lines) or direction-by-convention
(double lines) -- neither is in any input. Direction and time exist in the
TIMETABLE, so they are delivered there, as a layer that references the physical
graph rather than being mixed into it (Phase 3 plan item 6).

Writes service_layer/:
  service_edges_directed.parquet/.csv  one row per directed consecutive-stop pair
  service_hourly.csv                    departures per hour of day (0-23), per pair
  service_graph.graphml                 DiGraph of the above
  E-502_report.json                     validation against the Phase 2 service table

What remains impossible, stated in the report: running days (the timetable has
no days-of-operation field, so "trains per week" cannot be computed), and
capacity (no source holds line capacity, signalling or block sections).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PHASE3 = HERE.parents[1]
REPO = PHASE3.parent
OUT = Path(os.environ["E502_OUT"]) if os.environ.get("E502_OUT") else PHASE3 / "service_layer"
SCHED = REPO / "01_data_engineering" / "processed_data" / "cleaned_schedules.csv"
TRAINS = REPO / "01_data_engineering" / "processed_data" / "cleaned_trains.csv"
DS = REPO / "02_graph_inputs" / "graph_dataset"


def minutes(t, day):
    if pd.isna(t) or pd.isna(day):
        return np.nan
    h, m, *_ = str(t).split(":")
    return (int(day) - 1) * 1440 + int(h) * 60 + int(m)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sc = pd.read_csv(SCHED, usecols=["train_number", "station_code", "stop_sequence",
                                     "arrival", "departure", "day"])
    sc = sc.sort_values(["train_number", "stop_sequence"])
    sc["arr_min"] = [minutes(a, d) for a, d in zip(sc.arrival, sc.day)]
    sc["dep_min"] = [minutes(a, d) for a, d in zip(sc.departure, sc.day)]
    ttype = pd.read_csv(TRAINS, usecols=["train_number", "type"]).drop_duplicates("train_number") \
        .set_index("train_number")["type"]
    rows = []
    for t, g in sc.groupby("train_number", sort=False):
        s, dep, arr = g.station_code.to_numpy(), g.dep_min.to_numpy(), g.arr_min.to_numpy()
        for i in range(len(s) - 1):
            if s[i] == s[i + 1]:
                continue
            rt = arr[i + 1] - dep[i] if not (np.isnan(arr[i + 1]) or np.isnan(dep[i])) else np.nan
            if not np.isnan(rt) and (rt < 0 or rt > 24 * 60):
                rt = np.nan
            hour = int((dep[i] % 1440) // 60) if not np.isnan(dep[i]) else -1
            rows.append((s[i], s[i + 1], t, rt, hour))
    p = pd.DataFrame(rows, columns=["from_station", "to_station", "train_number", "runtime_min", "dep_hour"])
    p["train_type"] = p.train_number.map(ttype)
    agg = p.groupby(["from_station", "to_station"]).agg(
        n_trains=("train_number", "nunique"),
        runtime_min_median=("runtime_min", "median"),
        runtime_min_p10=("runtime_min", lambda x: x.quantile(.1)),
        runtime_min_p90=("runtime_min", lambda x: x.quantile(.9)),
        n_runtime_obs=("runtime_min", "count"),
        train_types=("train_type", lambda x: json.dumps(x.value_counts().to_dict()))).reset_index()
    hourly = p[p.dep_hour >= 0].pivot_table(index=["from_station", "to_station"], columns="dep_hour",
                                            values="train_number", aggfunc="nunique", fill_value=0)
    hourly.columns = [f"h{int(c):02d}" for c in hourly.columns]
    hourly = hourly.reset_index()

    # map every directed pair onto the physical graph (latest release)
    rel = Path(os.environ["E502_GRAPH"]) if os.environ.get("E502_GRAPH") else \
        PHASE3 / ("graph_v1_2" if (PHASE3 / "graph_v1_2" / "edges.parquet").exists() else "graph_v1")
    pe = pd.read_parquet(rel / "edges.parquet")
    Gp = nx.from_pandas_edgelist(pe, "from_node", "to_node", edge_attr="length_km")
    keyset = {(min(a, b), max(a, b)) for a, b in zip(pe.from_node, pe.to_node)}
    agg["both_in_physical_graph"] = agg.from_station.isin(Gp) & agg.to_station.isin(Gp)
    agg["is_direct_physical_edge"] = [(min(a, b), max(a, b)) in keyset
                                     for a, b in zip(agg.from_station, agg.to_station)]
    dist, hops = {}, {}
    for src in agg.loc[agg.both_in_physical_graph, "from_station"].unique():
        L, P = nx.single_source_dijkstra(Gp, src, cutoff=400, weight="length_km")
        for tgt in agg.loc[(agg.from_station == src) & agg.both_in_physical_graph, "to_station"]:
            if tgt in L:
                dist[(src, tgt)], hops[(src, tgt)] = L[tgt], len(P[tgt]) - 1
    agg["physical_path_km"] = [dist.get((a, b), np.nan) for a, b in zip(agg.from_station, agg.to_station)]
    agg["physical_hops"] = [hops.get((a, b), np.nan) for a, b in zip(agg.from_station, agg.to_station)]
    agg["observed_speed_kmph"] = agg.physical_path_km / (agg.runtime_min_median / 60)
    agg["physical_graph_release"] = rel.name if not os.environ.get("E502_GRAPH") else f"{rel.parent.name}/{rel.name}"
    agg.to_parquet(OUT / "service_edges_directed.parquet", index=False)
    agg.to_csv(OUT / "service_edges_directed.csv", index=False)
    hourly.to_csv(OUT / "service_hourly.csv", index=False)
    D = nx.DiGraph()
    for r in agg.itertuples(index=False):
        D.add_edge(r.from_station, r.to_station, **{k: (v if not (isinstance(v, float) and np.isnan(v)) else None)
               for k, v in r._asdict().items() if k not in ("from_station", "to_station")})
    for u, v, d in D.edges(data=True):
        for k in [k for k, x in d.items() if x is None]:
            del d[k]
        for k, x in list(d.items()):
            if isinstance(x, (np.bool_,)):
                d[k] = bool(x)
            elif isinstance(x, np.integer):
                d[k] = int(x)
            elif isinstance(x, np.floating):
                d[k] = float(x)
    nx.write_graphml(D, OUT / "service_graph.graphml")

    # ---------------- validation against the Phase 2 undirected service table ----------------
    p2 = pd.read_csv(DS / "service_edges.csv")
    und = agg.assign(a=np.minimum(agg.from_station, agg.to_station), b=np.maximum(agg.from_station, agg.to_station)) \
        .groupby(["a", "b"]).agg(n_dir=("n_trains", "sum"), dirs=("n_trains", "size")).reset_index()
    j = p2.merge(und, left_on=["from_station", "to_station"], right_on=["a", "b"], how="outer", indicator=True)
    both = j[j._merge == "both"]
    rt = agg.merge(p2, left_on=[np.minimum(agg.from_station, agg.to_station), np.maximum(agg.from_station, agg.to_station)],
                   right_on=["from_station", "to_station"], how="inner", suffixes=("", "_p2"))
    rel_rt = (rt.runtime_min_median - rt.runtime_min_median_p2).abs()
    gates = {
        "pair_sets_identical": bool((j._merge == "both").all()),
        "pairs_only_phase2": int((j._merge == "left_only").sum()),
        "pairs_only_directed": int((j._merge == "right_only").sum()),
        "train_count_agreement_share": float((both.n_trains == both.n_dir).mean()) if len(both) else None,
        "runtime_median_abs_diff_min_median": float(rel_rt.median()),
    }
    rep = {"experiment": "E-502", "physical_graph_release": str(agg.physical_graph_release.iloc[0]),
           "directed_pairs": int(len(agg)), "undirected_pairs": int(len(und)),
           "pairs_served_in_both_directions": int((und.dirs == 2).sum()),
           "pairs_served_one_direction_only": int((und.dirs == 1).sum()),
           "trains": int(p.train_number.nunique()),
           "both_in_physical_graph_share": float(agg.both_in_physical_graph.mean()),
           "direct_physical_edge_share": float(agg.is_direct_physical_edge.mean()),
           "resolved_within_400km_share": float(agg.physical_path_km.notna().mean()),
           "observed_speed_kmph_median": float(agg.observed_speed_kmph.median()),
           "validation_vs_phase2": gates,
           "not_possible": {
               "running_days": "no days-of-operation field in cleaned_schedules or cleaned_trains; "
                               "n_trains counts distinct trains, not trains per day or week",
               "capacity": "no input holds line capacity, signalling, block sections or train paths; "
                           "n_tracks (single/double line) is the only proxy and is corridor-level",
               "physical_direction": "the GIS records track, not running direction"}}
    (OUT / "E-502_report.json").write_text(json.dumps(rep, indent=2, default=str))
    print(json.dumps(rep, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
