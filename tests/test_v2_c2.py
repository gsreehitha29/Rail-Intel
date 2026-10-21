"""Milestone C2 of the build roadmap: OpenStreetMap stages O3b, O5, O4, O6 (E-716, D-063).

Checks the working build in graph_v2_0_open/. Skipped until `make osm-c2` has run.
"""
import json
import sys

import networkx as nx
import pandas as pd
import pytest

from conftest import ROOT

G3 = ROOT / "03_graph_construction"
OUT = G3 / "graph_v2_0_open"
pytestmark = pytest.mark.skipif(not (OUT / "work" / "c2_report.json").exists(),
                                reason="C2 not built; run `make osm-c2`")


@pytest.fixture(scope="module")
def rep():
    return json.loads((OUT / "work" / "c2_report.json").read_text())


@pytest.fixture(scope="module")
def nodes():
    return pd.read_csv(OUT / "open" / "nodes.csv")


@pytest.fixture(scope="module")
def edges():
    return pd.read_csv(OUT / "open" / "edges.csv")


def test_tables_are_a_well_formed_graph(nodes, edges):
    assert nodes.node_id.is_unique and edges.edge_id.is_unique
    ids = set(nodes.node_id)
    assert set(edges.from_node) <= ids and set(edges.to_node) <= ids
    assert (edges.length_km > 0).all()
    assert not (edges.from_node == edges.to_node).any()


def test_derived_node_columns_match_the_graph(nodes, edges):
    G = nx.Graph(); G.add_nodes_from(nodes.node_id); G.add_edges_from(zip(edges.from_node, edges.to_node))
    assert (nodes.node_id.map(dict(G.degree())) == nodes.degree).all()
    giant = max(nx.connected_components(G), key=lambda c: sum(1 for x in c if not x.startswith("JN:")))
    assert (nodes.node_id.isin(giant) == nodes.in_giant).all()


def test_C2a_no_straight_line_lengths(edges, rep):
    """Every length is measured along OSM track, except joins made on a timetable distance."""
    assert set(edges.length_source) <= {"osm_track", "timetable"}
    assert rep["gate"]["passed"]["C2a_no_straight_line_lengths_and_tags_carried"]
    j = pd.read_csv(OUT / "work" / "c2_joins.csv")
    assert (edges.length_source == "timetable").sum() <= (j.stage == "C").sum()


def test_C2a_tags_carried_where_osm_has_them(edges):
    assert edges.loc[edges.gauge_tag_share > 0, "gauge_code"].notna().all()
    assert edges.loc[edges.electrified_tag_share > 0, "electrified"].notna().all()


def test_every_join_states_its_evidence():
    j = pd.read_csv(OUT / "work" / "c2_joins.csv")
    assert set(j.stage) <= {"A", "A2", "B", "C"}
    assert j.loc[j.stage != "A", "evidence"].notna().all()
    assert (j.loc[j.stage == "A2", "km"] <= 0.1).all()


def test_C2c_served_stations_at_least_v141(rep):
    g = rep["graph"]
    assert g["served_stations_v141"] is not None and g["served_stations_v2"] >= g["served_stations_v141"]


def test_served_stations_are_in_the_main_network(rep):
    """Of stations with a train in September 2024, at least 99.5% are in the main network."""
    assert rep["graph"]["served_2024_share_in_main"] >= 0.995


def test_C2b_gate(rep):
    """D-064: the share is counted over stations with a train in September 2024."""
    assert rep["gate"]["passed"]["C2b_995_of_2024_served_stations_in_main_network"]


def test_C2d_route_km(rep):
    """D-065: the roadmap's route-km test, on the station graph."""
    assert rep["gate"]["passed"]["C2d_route_km_within_7pct_of_official"]


def test_every_throat_link_is_short_osm_track():
    t = pd.read_csv(OUT / "work" / "c2_throat_links.csv")
    assert len(t) and (t.km <= 2.0).all() and t.osm_a.notna().all()


def test_stations_outside_the_main_network_are_unserved(rep):
    """What D-064 relies on: almost every station left outside has no 2024 train."""
    g = rep["graph"]
    outside_all = round((1 - g["station_share_in_main"]) * g["stations"])
    outside_served = round((1 - g["served_2024_share_in_main"]) * g["served_2024_stations"])
    # 2 of the 35 left outside have a 2024 train (CP3: joins A2 brought 3 more pieces in)
    assert outside_served <= 0.1 * outside_all and outside_served <= 0.001 * g["served_2024_stations"]


def test_loads_through_the_release_loader():
    """The v1.4 schema, so E-708's loaders and stages run on v2.0 unchanged."""
    sys.path.insert(0, str(G3 / "experiments" / "E-708_v1_4_build"))
    import v14
    old = v14.SLUG
    try:
        v14.SLUG = "v2_0_open"
        G, n, e = v14.load_v14(ROOT)
        assert G.number_of_nodes() == len(n) and G.number_of_edges() == len(e)
    finally:
        v14.SLUG = old
