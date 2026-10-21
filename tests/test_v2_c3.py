"""Milestone C3 of the build roadmap: v2.0-open validated against v1.4.1 (E-716).

Reads graph_v2_0_open/work/c3_report.json. Skipped until `make osm-c3` has run.
"""
import json

import pandas as pd
import pytest

from conftest import ROOT

WORK = ROOT / "03_graph_construction" / "graph_v2_0_open" / "work"
pytestmark = pytest.mark.skipif(not (WORK / "c3_report.json").exists(), reason="C3 not run; `make osm-c3`")


@pytest.fixture(scope="module")
def rep():
    return json.loads((WORK / "c3_report.json").read_text())


def test_c3_gate(rep):
    assert rep["gate"]["all_passed"], rep["gate"]["passed"]


def test_lengths_at_least_as_good_on_the_e715_pairs(rep):
    L = rep["lengths"]["e715_pairs"]
    assert L["comparable"] == L["pairs"] == 423
    assert L["v2"]["within_5pct"] >= L["v141"]["within_5pct"]


def test_v14_gates_hold_on_v2(rep):
    assert all(rep["e708_gates"]["v2_passed"].values()), rep["e708_gates"]["v2_passed"]


def test_route_accuracy_not_worse_than_v141(rep):
    """Out of sample for v2.0: its construction used no timetable distance except two joins."""
    a, b = rep["e708_gates"]["v2"], rep["e708_gates"]["v141"]
    assert a["route_2024_median_err"] <= b["route_2024_median_err"]
    assert a["irn_within_5pct"] >= b["irn_within_5pct"]


def test_retrodictive_cases_reproduced(rep):
    for case, rows in rep["retrodictive"].items():
        assert rows and rows[0]["jaccard"] >= 0.8, case


def test_every_cut_point_difference_is_listed():
    d = pd.read_csv(WORK / "c3_cut_point_differences.csv")
    assert d.cause.notna().all()
