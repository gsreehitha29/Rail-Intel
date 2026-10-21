"""E-716 milestone C1 - OpenStreetMap stages O1 to O3, with their gate.

    python run_c1.py [repo root]

Writes 03_graph_construction/graph_v2_0_open/work/ (a working build, not a release):
  c1_report.json            every count, the parameters, and the C1 gate
  calib_track_spacing.csv   the calibration the merge distance was read from (D-062)
  calib_snap_distance.csv   the calibration the snap distance was read from (D-062)
  network_edges.parquet     the collapsed track network, split at stations and joins
  network_vertices.parquet  its vertices with coordinates
  station_snaps.csv         every OSM station: where it snapped, or how far it was;
                            review_metro marks a snap that may be a metro station
  unsnapped_stations.csv    the stations left off the line, each with a reason
"""
import json, sys, time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import osm_build as ob                                                # noqa: E402

# D-062: chosen from the calibration tables before any route-km figure was computed
STEP_M = 10.0          # sample spacing along track
MERGE_M = 15.0         # tracks closer than this are one route
MIN_RUN_M = 100.0      # ...for at least this long (so a turnout is not a merge)
CONNECT_M = 30.0       # a loose end re-joins kept track within this (2 x MERGE_M)
SNAP_M = 100.0         # a station joins its line within this
VERIFY_RATIO = 1.3     # D-065: a removed stretch must be replaced by kept track no longer than this x its length
VERIFY_SLACK_KM = 0.2  # ...plus this
GATE = dict(route_km_tolerance=0.07, min_coded_snapped_share=0.95)


def c1(root: Path) -> dict:
    """Stages O1-O3 in memory. Returns everything later stages need."""
    W, S = ob.load(root)
    refs, xy = ob.way_arrays(W)
    keep, r1, way_km, reason = ob.o1_filter(W, xy)
    nodes, seg = ob.segments(W, refs, xy, keep)
    cid, paths, deg = ob.chains(len(nodes), seg)
    km_chain = np.bincount(cid, weights=seg.km.to_numpy(), minlength=len(paths))
    gauge = ob.chain_gauge(W, seg, cid, len(paths))
    P, C, D, LL = ob.densify(nodes, paths, STEP_M)
    alive, r2, runs = ob.o2_collapse(P, C, D, km_chain, gauge, MERGE_M, MIN_RUN_M)
    alive, r2v = ob.o2_verify(P, LL, C, alive, runs, paths, deg, MERGE_M, CONNECT_M, VERIFY_RATIO, VERIFY_SLACK_KM)
    r2.update(verify=r2v)
    st, en, pid, conn, r2c = ob.o2_connect(P, C, alive, paths, deg, CONNECT_M)
    St = ob.station_table(S)
    St, r3 = ob.o3_snap(St, P, alive, pid, SNAP_M)
    E, keys, key = ob.build_network(P, LL, C, st, en, conn, St, paths)
    St["vertex"] = [key(s) if s >= 0 else None for s in St["sample"]]
    St["metro_track_m"] = ob.metro_distance(St, W, xy)
    St["review_metro"] = St.vertex.notna() & (St.metro_track_m < St.snap_m)
    return dict(W=W, S=S, refs=refs, xy=xy, keep=keep, r1=r1, reason=reason, nodes=nodes, seg=seg,
                cid=cid, paths=paths, deg=deg, km_chain=km_chain, gauge=gauge, P=P, C=C, D=D, LL=LL,
                alive=alive, r2=r2, st=st, en=en, pid=pid, conn=conn, r2c=r2c, St=St, r3=r3,
                E=E, keys=keys, key=key)


def main():
    t0 = time.time()
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]
    out = root / "03_graph_construction" / "graph_v2_0_open" / "work"; out.mkdir(parents=True, exist_ok=True)
    o = c1(root)
    W, xy, keep, reason, nodes, seg, paths, deg = (o[k] for k in ("W", "xy", "keep", "reason", "nodes", "seg", "paths", "deg"))
    P, C, LL, km_chain, gauge = o["P"], o["C"], o["LL"], o["km_chain"], o["gauge"]
    r1, r2, r2c, r3, St, E, keys, key = (o[k] for k in ("r1", "r2", "r2c", "r3", "St", "E", "keys", "key"))
    ob.spacing_distribution(P, C, km_chain).to_csv(out / "calib_track_spacing.csv", index_label="nearest_other_track_m")
    allv = np.ones(len(P), bool)
    s0, e0, _, _, _ = ob.o2_connect(P, C, allv, paths, deg, 0.0)
    E0, _, _ = ob.build_network(P, LL, C, s0, e0, [], pd.DataFrame({"sample": []}), paths)
    c0 = ob.components(E0)
    ob.snap_distribution(St).to_csv(out / "calib_snap_distance.csv", index_label="distance_m")
    c1n = ob.components(E)

    # outputs
    E.assign(gauge=[gauge[c] for c in E.chain]).drop(columns=["s_a", "s_b"]).to_parquet(out / "network_edges.parquet", index=False)
    vs = pd.Series(keys)
    samp = vs.str.startswith("s"); idx = vs.str.slice(1).astype(np.int64)
    nll = nodes.set_index(np.arange(len(nodes)))
    lon = np.where(samp, LL[np.where(samp, idx, 0), 0], nll.lon.values[np.where(samp, 0, idx)])
    lat = np.where(samp, LL[np.where(samp, idx, 0), 1], nll.lat.values[np.where(samp, 0, idx)])
    osm_node = np.where(samp, -1, nodes.osm_node.values[np.where(samp, 0, idx)])
    pd.DataFrame(dict(vertex=vs, lon=lon.round(7), lat=lat.round(7), osm_node=osm_node,
                      kind=np.where(samp, "split", "osm_node"))).to_parquet(out / "network_vertices.parquet", index=False)
    metro_only = St.vertex.isna() & (St.metro_track_m <= SNAP_M)
    coded = St.code.notna()
    r3["coded_metro_only_unsnapped"] = int((coded & metro_only).sum())
    r3["coded_snapped_share_excluding_metro_only"] = round(
        float((coded & St.vertex.notna()).sum() / (coded & ~metro_only).sum()), 4)
    r3["snapped_nearer_a_metro_line_review"] = int(St.review_metro.sum())
    St.drop(columns=["sample"]).to_csv(out / "station_snaps.csv", index=False)
    U = ob.unsnapped_reasons(St.assign(sample=[1 if v else -1 for v in St.vertex.notna()]), W, xy, keep, reason)
    U.to_csv(out / "unsnapped_stations.csv", index=False)

    route_km = float(E.km.sum()); track_km = float(E[E.kind == "track"].km.sum())
    err = route_km / ob.OFFICIAL_ROUTE_KM - 1
    # D-065: C1a is measured on the station graph (C2's gate C2d). The collapse now keeps any
    # parallel stretch whose removal would lengthen a route, and C2 removes the duplicates
    # that remain, so the track km here is an intermediate figure, reported, not gated.
    gates = {"C1b_95pct_of_coded_stations_snapped": r3["coded_snapped_share"] >= GATE["min_coded_snapped_share"]}
    rep = dict(milestone="C1", snapshot=ob.SNAPSHOT,
               parameters=dict(step_m=STEP_M, merge_m=MERGE_M, min_run_m=MIN_RUN_M, gap_closed_m=30,
                               connect_m=CONNECT_M, snap_m=SNAP_M, verify_ratio=VERIFY_RATIO,
                               verify_slack_km=VERIFY_SLACK_KM, decision="D-062, D-065"),
               O1=r1, chains=dict(n=len(paths), osm_nodes=int(len(nodes)), segments=int(len(seg))),
               network_before_collapse=dict(km=round(float(E0.km.sum()), 1), components=c0["n"],
                                            giant_km_share=c0["giant_km_share"], components_over_10km=c0["over_10km"]),
               O2=dict(**r2, **r2c, track_km=round(track_km, 1),
                       connector_km=round(route_km - track_km, 1)),
               network_after_collapse=dict(route_km=round(route_km, 1), vs_official=round(err, 4),
                                           official_route_km=ob.OFFICIAL_ROUTE_KM,
                                           note="intermediate; gated on the station graph (C2d, D-065)", edges=int(len(E)),
                                           vertices=int(len(keys)), components=c1n["n"],
                                           giant_km_share=c1n["giant_km_share"], components_over_10km=c1n["over_10km"]),
               O3=r3, unsnapped_by_reason=U.groupby(U.code.notna().map({True: "coded", False: "uncoded"})).why
                   .value_counts().unstack(0).fillna(0).astype(int).to_dict(),
               gate=dict(thresholds=GATE, passed=gates, all_passed=all(gates.values())),
               seconds=round(time.time() - t0, 1))
    (out / "c1_report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps(rep, indent=1, default=str))
    if not rep["gate"]["all_passed"]:
        raise SystemExit(f"C1 GATE FAILED: {[k for k, v in gates.items() if not v]}")


if __name__ == "__main__":
    main()
