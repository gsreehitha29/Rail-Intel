"""Milestone C1 of the build roadmap: OpenStreetMap stages O1-O3 (E-716, D-062).

Checks the working build in graph_v2_0_open/work. Skipped until `make osm-c1` has run.
"""
import json
import sys

import pandas as pd
import pytest

from conftest import ROOT

WORK = ROOT / "03_graph_construction" / "graph_v2_0_open" / "work"
sys.path.insert(0, str(ROOT / "03_graph_construction" / "experiments" / "E-716_osm_v2_build"))
pytestmark = pytest.mark.skipif(not (WORK / "c1_report.json").exists(),
                                reason="C1 not built; run `make osm-c1`")


@pytest.fixture(scope="module")
def rep():
    return json.loads((WORK / "c1_report.json").read_text())


def test_projection_matches_epsg_7755():
    """The numpy Lambert conformal conic against PROJ's EPSG:7755, to the millimetre."""
    from geo import lcc
    ref = {(77.209, 28.6139): (3731496.445, 4504443.321), (72.88, 19.07): (3262862.881, 3482733.682),
           (94.9, 27.5): (5443662.191, 4456842.34), (77.5, 8.1): (3719587.528, 2255418.628)}
    for (lo, la), (x, y) in ref.items():
        gx, gy = lcc(lo, la)
        assert abs(gx - x) < 0.01 and abs(gy - y) < 0.01


def test_c1_gate_passed(rep):
    """C1b here; C1a (route km) is gated on the station graph as C2d (D-065)."""
    assert rep["gate"]["all_passed"], rep["gate"]["passed"]
    assert rep["O3"]["coded_snapped_share"] >= 0.95


def test_collapse_keeps_routes(rep):
    """D-065: a removed stretch whose route the kept track does not replace is restored,
    and the check runs until nothing more is restored."""
    v = rep["O2"]["verify"]
    assert v["restored_per_round"][-1] == 0 and v["stretches_restored"] > 0


def test_every_dropped_km_has_a_reason(rep):
    o1 = rep["O1"]
    assert abs(o1["km_kept"] + sum(o1["km_dropped_by_reason"].values()) - o1["km_in"]) < 1.0


def test_parameters_are_the_recorded_decision(rep):
    """D-062 and D-065. A change here is a new decision, not a tweak."""
    assert rep["parameters"] == dict(step_m=10.0, merge_m=15.0, min_run_m=100.0, gap_closed_m=30,
                                     connect_m=30.0, snap_m=100.0, verify_ratio=1.3, verify_slack_km=0.2,
                                     decision="D-062, D-065")


def test_collapse_does_not_fragment_the_network(rep):
    before, after = rep["network_before_collapse"], rep["network_after_collapse"]
    assert after["components"] <= before["components"]
    assert after["giant_km_share"] >= before["giant_km_share"]


def test_merge_distance_sits_where_track_spacing_has_died_away():
    """D-062's rule: the first bin edge where spacing density is under 5% of its peak."""
    t = pd.read_csv(WORK / "calib_track_spacing.csv").dropna(subset=["share_of_peak_density"])
    peak = t.share_of_peak_density.idxmax()
    first_low = t.loc[peak:][t.loc[peak:].share_of_peak_density < 0.05].iloc[0]
    assert first_low.nearest_other_track_m.split("-")[0] == "15"


def test_every_unsnapped_station_is_listed_with_a_reason():
    s = pd.read_csv(WORK / "station_snaps.csv")
    u = pd.read_csv(WORK / "unsnapped_stations.csv")
    assert set(u.node_id) == set(s[s.vertex.isna()].node_id)
    assert u.why.notna().all()
