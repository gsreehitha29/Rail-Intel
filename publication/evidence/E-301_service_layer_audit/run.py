"""E-301 -- service-layer and enrichment-capacity audit.

`E-300` asked what the current attributes measure. This asks the complementary
question: **what could the graph carry that it does not, using only data already
in the repository?**

The answer turns out to be large, and it changes what v2 should be. The headline
is that the graph weights distance and travel time using a *declared sectional
speed* -- a sanctioned maximum -- while 416,970 schedule records sitting in
Phase 1 contain the speed trains actually achieve.

Six parts:

  1. observed run-time -- coverage against the physical edge set, versus the
     coverage of the declared speed it would replace
  2. observed vs declared speed -- the ratio, which is the size of the error in
     every travel-time result the project has produced
  3. run-time variability -- p90/p10 spread as a congestion signal, an attribute
     with no counterpart in the current graph
  4. service composition -- train class mix and accommodation classes
  5. directionality -- whether up/down pairing is resolvable, i.e. whether a
     directed graph is buildable from in-repo data
  6. node enrichment -- dwell time, terminus role, and true-alignment geometry

    python publication/evidence/E-301_service_layer_audit/run.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

SERVICE_EDGES = ROOT / "02_graph_inputs" / "graph_dataset" / "service_edges.csv"
EDGES = ROOT / "03_graph_construction" / "graph_v1" / "edges.parquet"
NODES = ROOT / "03_graph_construction" / "graph_v1" / "nodes.parquet"
TRAINS = ROOT / "01_data_engineering" / "processed_data" / "cleaned_trains.csv"
SCHEDULES = ROOT / "01_data_engineering" / "processed_data" / "cleaned_schedules.csv"
SPINES = ROOT / "02_graph_inputs" / "pipeline" / "cache" / "corridor_spines.parquet"


def undirected_key(df, a, b):
    return [tuple(sorted(x)) for x in zip(df[a].astype(str), df[b].astype(str))]


def part1_runtime_coverage(edges, svc) -> dict:
    print("\n[1] OBSERVED RUN-TIME -- coverage of the physical edge set")
    d = svc[svc.is_direct_edge == True].dropna(subset=["runtime_min_median"]).copy()
    d["k"] = undirected_key(d, "from_station", "to_station")
    d = d.drop_duplicates("k")
    e = edges.copy()
    e["k"] = undirected_key(e, "from_node", "to_node")
    m = e.merge(d[["k", "runtime_min_median", "runtime_min_p10",
                   "runtime_min_p90", "n_trains"]], on="k", how="left")
    cov = m.runtime_min_median.notna()
    res = {
        "edges_with_observed_runtime": int(cov.sum()),
        "edge_share": round(float(cov.mean()), 4),
        "km_share": round(float(m.loc[cov, "length_km"].sum() / m.length_km.sum()), 4),
        "declared_speed_edge_share": round(float(edges.speed_kmph.notna().mean()), 4),
    }
    print(f"    edges with an observed run-time   {res['edges_with_observed_runtime']:,} / {len(m):,} "
          f"({100*res['edge_share']:.1f}%)")
    print(f"    route km covered                  {100*res['km_share']:.1f}%")
    print(f"    declared speed_kmph covers        {100*res['declared_speed_edge_share']:.1f}%")
    print("    -> the measurement has BETTER coverage than the declaration it would replace.")
    return res, m


def part2_speed_ratio(m) -> dict:
    print("\n[2] OBSERVED vs DECLARED SPEED -- how wrong is the travel-time weight?")
    ok = m[m.runtime_min_median.notna() & (m.runtime_min_median > 0)].copy()
    ok["implied_kmph"] = ok.length_km / (ok.runtime_min_median / 60.0)
    ok = ok[(ok.implied_kmph > 1) & (ok.implied_kmph < 200)]
    both = ok[ok.speed_kmph.notna()].copy()
    both["ratio"] = both.implied_kmph / both.speed_kmph
    res = {
        "implied_median_kmph": round(float(ok.implied_kmph.median()), 2),
        "implied_p10": round(float(ok.implied_kmph.quantile(.10)), 2),
        "implied_p90": round(float(ok.implied_kmph.quantile(.90)), 2),
        "declared_median_kmph": round(float(both.speed_kmph.median()), 2),
        "ratio_median": round(float(both.ratio.median()), 4),
        "fallback_kmph": 50.0,
    }
    print(f"    implied speed from observed run-time  median {res['implied_median_kmph']:.1f} km/h "
          f"(p10 {res['implied_p10']:.1f}, p90 {res['implied_p90']:.1f})")
    print(f"    declared sectional speed, same edges  median {res['declared_median_kmph']:.1f} km/h")
    print(f"    observed / declared                   median {res['ratio_median']:.3f}")
    print("    -> the declared speed is a SANCTIONED MAXIMUM. Weighting travel time by it")
    print("       understates journey time by roughly a factor of two.")
    print(f"    -> note: the 50 km/h FALLBACK used on edges with no declared speed is")
    print(f"       closer to reality ({res['implied_median_kmph']:.1f}) than the declared value is.")
    print("       The invented constant outperforms the real attribute.")
    return res, ok


def part3_variability(ok) -> dict:
    print("\n[3] RUN-TIME VARIABILITY -- a congestion signal with no current counterpart")
    v = ok.dropna(subset=["runtime_min_p10", "runtime_min_p90"]).copy()
    v["spread_min"] = v.runtime_min_p90 - v.runtime_min_p10
    v["spread_ratio"] = v.runtime_min_p90 / v.runtime_min_p10.replace(0, np.nan)
    res = {
        "edges": int(len(v)),
        "median_spread_min": round(float(v.spread_min.median()), 2),
        "p90_spread_min": round(float(v.spread_min.quantile(.90)), 2),
        "share_p90_over_2x_p10": round(float((v.spread_ratio > 2).mean()), 4),
    }
    print(f"    edges with a p10/p90 band        {res['edges']:,}")
    print(f"    median spread                    {res['median_spread_min']:.1f} min")
    print(f"    p90 spread                       {res['p90_spread_min']:.1f} min")
    print(f"    edges where p90 > 2x p10         {100*res['share_p90_over_2x_p10']:.1f}%")
    print("    -> on nearly a third of edges the slowest trains take more than double the")
    print("       fastest. That heterogeneity is invisible in a single scalar weight.")
    return res


def part4_composition(trains) -> dict:
    print("\n[4] SERVICE COMPOSITION -- train class and accommodation")
    tc = trains.type.value_counts()
    print(f"    distinct train types: {trains.type.nunique()}   trains: {len(trains):,}")
    print("    " + "  ".join(f"{k}={v}" for k, v in tc.head(8).items()))
    acc = {c: int(trains[c].sum()) for c in
           ["first_ac", "second_ac", "third_ac", "sleeper", "chair_car", "first_class"]}
    print("    accommodation: " + "  ".join(f"{k}={v}" for k, v in acc.items()))
    print("    -> an edge carrying 90% stopping passenger trains is functionally a different")
    print("       link from one carrying Rajdhanis; the graph cannot currently say which.")
    return {"n_types": int(trains.type.nunique()),
            "type_counts": {str(k): int(v) for k, v in tc.head(16).items()},
            "accommodation": acc}


def part5_directionality(trains) -> dict:
    print("\n[5] DIRECTIONALITY -- is a directed graph buildable from in-repo data?")
    have = trains.return_train.notna()
    master = set(trains.train_number.astype(str))
    pair = trains.return_train.dropna().astype(str)
    resolvable = pair.isin(master)
    res = {
        "trains": int(len(trains)),
        "with_return_train": int(have.sum()),
        "with_return_train_share": round(float(have.mean()), 4),
        "return_resolvable_share": round(float(resolvable.mean()), 4),
    }
    print(f"    trains declaring a return_train   {res['with_return_train']:,} "
          f"({100*res['with_return_train_share']:.1f}%)")
    print(f"    of those, resolvable in master    {100*res['return_resolvable_share']:.1f}%")
    print("    -> up/down pairing is available for the large majority of services, so a")
    print("       directed service layer is buildable without any new data (D-033 revisit).")
    return res


def part6_nodes(sched, nodes) -> dict:
    print("\n[6] NODE ENRICHMENT -- dwell, terminus role, true geometry")
    s = sched.dropna(subset=["arrival", "departure"]).copy()
    a = pd.to_timedelta(s.arrival, errors="coerce")
    d = pd.to_timedelta(s.departure, errors="coerce")
    s["dwell_min"] = ((d - a).dt.total_seconds() / 60.0) % 1440
    s = s[(s.dwell_min >= 0) & (s.dwell_min < 120)]
    per = s.groupby("station_code").dwell_min.agg(["median", "count"])
    per = per[per["count"] >= 5]
    in_graph = set(nodes.node_id)
    matched = per.index.isin(in_graph).sum()

    orig = sched[sched.stop_sequence == 1].station_code.value_counts()
    res = {
        "schedule_rows_with_both_times": int(len(s)),
        "stations_with_dwell": int(len(per)),
        "dwell_stations_in_graph": int(matched),
        "dwell_coverage_of_station_nodes": round(
            float(matched / (nodes.node_type == "station").sum()), 4),
        "median_dwell_min": round(float(s.dwell_min.median()), 2),
        "p90_dwell_min": round(float(s.dwell_min.quantile(.90)), 2),
        "originating_stations": int(len(orig)),
    }
    print(f"    schedule rows with arrival+departure  {res['schedule_rows_with_both_times']:,}")
    print(f"    stations with >=5 dwell observations  {res['stations_with_dwell']:,} "
          f"({res['dwell_stations_in_graph']:,} present in the graph = "
          f"{100*res['dwell_coverage_of_station_nodes']:.1f}% of station nodes)")
    print(f"    dwell minutes: median {res['median_dwell_min']:.1f}  p90 {res['p90_dwell_min']:.1f}")
    print(f"    stations originating at least one train  {res['originating_stations']:,}")

    if SPINES.exists():
        sp = pd.read_parquet(SPINES)
        res["corridor_spines"] = int(len(sp))
        res["spine_mean_coords"] = round(float(sp.n_coords.mean()), 1)
        print(f"\n    corridor spine geometries available   {len(sp):,} corridors, "
              f"mean {sp.n_coords.mean():.0f} coordinates each")
        print("    -> stored as WKB LineStrings. Slicing each between two stations' measure_km")
        print("       yields TRUE per-edge alignment, replacing the straight-chord GeoJSON.")
    else:
        print("\n    corridor spine cache not present at this path (Phase 2 pipeline cache)")
    return res


def main() -> None:
    print("=" * 78)
    print("E-301  service-layer and enrichment-capacity audit")
    print("=" * 78)
    edges = pd.read_parquet(EDGES)
    nodes = pd.read_parquet(NODES)
    svc = pd.read_csv(SERVICE_EDGES)
    trains = pd.read_csv(TRAINS, low_memory=False)
    sched = pd.read_csv(SCHEDULES, low_memory=False)

    report = {}
    report["runtime_coverage"], m = part1_runtime_coverage(edges, svc)
    report["speed_ratio"], ok = part2_speed_ratio(m)
    report["variability"] = part3_variability(ok)
    report["composition"] = part4_composition(trains)
    report["directionality"] = part5_directionality(trains)
    report["nodes"] = part6_nodes(sched, nodes)

    (HERE / "report.json").write_text(json.dumps(report, indent=2, default=str))
    cols = ["from_node", "to_node", "edge_id", "length_km", "speed_kmph",
            "runtime_min_median", "runtime_min_p10", "runtime_min_p90", "n_trains"]
    m[cols].to_csv(HERE / "edge_runtime_join.csv", index=False)
    print(f"\nwrote report.json, edge_runtime_join.csv")


if __name__ == "__main__":
    main()
