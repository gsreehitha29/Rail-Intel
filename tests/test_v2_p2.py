"""Phase P2 of the v2.0 execution plan: gap closing (E-716, D-066, issue register passes 1-5)."""
import json

import pandas as pd
import pytest

from conftest import ROOT

G3 = ROOT / "03_graph_construction"
OUT = G3 / "graph_v2_0_open"
pytestmark = pytest.mark.skipif(not (OUT / "open" / "places" / "nodes.csv").exists(),
                                reason="v2.0 P2 build not present; run `make osm-c2`")


@pytest.fixture(scope="module")
def nodes():
    return pd.read_csv(OUT / "open" / "nodes.csv")


@pytest.fixture(scope="module")
def edges():
    return pd.read_csv(OUT / "open" / "edges.csv")


@pytest.fixture(scope="module")
def rep():
    return json.loads((OUT / "work" / "c2_report.json").read_text())


def test_places_view_is_a_contraction_of_the_physical_graph(nodes):
    """D-066. Every places-view node is a physical node; every station is its own place."""
    pn = pd.read_csv(OUT / "open" / "places" / "nodes.csv")
    pe = pd.read_csv(OUT / "open" / "places" / "edges.csv")
    assert set(pn.node_id) <= set(nodes.node_id)
    assert set(pe.from_node) | set(pe.to_node) <= set(pn.node_id)
    st = nodes[nodes.node_type == "station"]
    assert (st.place_id == st.node_id).all()
    j = nodes[(nodes.node_type == "junction") & nodes.place_id.notna()]
    assert set(j.place_id) <= set(pn.node_id)


def test_places_view_cycles_not_above_v141(rep):
    """V2-05: the station-level view has no more independent cycles than v1.4.1 (682)."""
    assert rep["places_view"]["cycles"] <= 682


def test_service_flags_and_line_status(nodes, edges, rep):
    """V2-06, V2-07."""
    assert set(edges.line_status) <= {"served_2024", "scheduled_2017_only", "no_service_data"}
    st = nodes[nodes.node_type == "station"]
    assert set(st.line_status) <= {"served_2024", "scheduled_2017_only", "no_service_data"}
    assert int(st.served_2024.sum()) == rep["graph"]["served_2024_stations"]


def test_open_2017_service_layer():
    """V2-19: the redistributable layer, from the GODL 2017 timetable."""
    d = G3 / "service_layer_v2_0_open" / "open_2017"
    es = pd.read_csv(d / "edge_service.csv"); se = pd.read_csv(d / "service_edges_directed.csv")
    assert (es.distinct_trains_2017 >= 0).all() and len(se) > 20000


def test_state_and_track_position(nodes):
    """V2-14, V2-12."""
    assert nodes.state.notna().mean() >= 0.999
    st = nodes[nodes.node_type == "station"]
    assert st.track_lon.notna().all() and st.track_lat.notna().all()


def test_code_conflicts_resolved_or_listed(rep):
    """V2-09: each conflict code either taken by one station on timetable evidence, or kept as listed."""
    r = rep["conflicts_resolved"]
    assert r and all(v.startswith("unresolved") or "off the timetable" in v for v in r.values())
