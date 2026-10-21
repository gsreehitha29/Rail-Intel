"""P3 pre-release fixes (E-716): stations shared by two lines, and stations mapped twice."""
import sys
from pathlib import Path

import networkx as nx
import pandas as pd
import pytest

from conftest import ROOT

from conftest import ROOT as _ROOT
HERE = _ROOT / "03_graph_construction/experiments/E-716_osm_v2_build"
sys.path.insert(0, str(HERE))
import osm_build as ob  # noqa: E402

G3 = ROOT / "03_graph_construction"


@pytest.fixture(scope="module")
def graph():
    n = pd.read_csv(G3 / "graph_v2_0_open/open/nodes.csv", low_memory=False)
    e = pd.read_csv(G3 / "graph_v2_0_open/open/edges.csv")
    G = nx.Graph()
    G.add_weighted_edges_from(zip(e.from_node, e.to_node, e.length_km), weight="km")
    return n, e, G


def test_timetable_lengths_only_where_osm_has_no_track(graph):
    """Coimbatore-Mettupalayam and Bilimora-Gandevi, once joined at a timetable distance, are
    stations shared by two lines, now joined at the station (A2). What is left at a 2017
    timetable distance (D-068) are two isolated stations on lines OSM does not map:
    Patal Pani (Mhow heritage line) and Samni."""
    _, e, _ = graph
    tt = e[e.length_source != "osm_track"]
    assert set(tt.length_source) <= {"timetable"} and len(tt) <= 2
    assert set(tt.joins) <= {"join_C"}
    assert not tt.edge_id.str.contains("CBE|MTP|BIM|GNV", regex=True).any()


@pytest.mark.parametrize("a,b,lo,hi", [("CBE", "MTP", 33.0, 38.0), ("BIM", "GNV", 4.0, 6.5)])
def test_branches_reach_their_junction_along_track(graph, a, b, lo, hi):
    """Coimbatore-Mettupalayam (35 km in the 2017 timetable) and Bilimora-Gandevi (5 km)."""
    _, e, G = graph
    km = nx.shortest_path_length(G, a, b, weight="km")
    assert lo <= km <= hi


def test_name_key():
    assert ob.name_key("Karepalli Junction Railway Station") == "karepalli"
    assert ob.name_key("Kulukkallur Railway Station (കുലുക്കല്ലൂർ)") == "kulukkallur"
    assert ob.name_key("DHANBAD JUNCTION") == ob.name_key("Dhanbad Junction")
    assert ob.name_key(None) == "" and ob.name_key("  ") == ""


def test_stations_mapped_twice_are_one_node(graph):
    """An uncoded OSM station named as another station within 1 km is the same station."""
    n, _, _ = graph
    s = n[n.node_type == "station"]
    unc = s[s.station_code.isna() & s.node_id.str.startswith("OSM:")]
    cod = s[s.station_code.notna() | s.node_id.str.startswith("OSM:")]
    keys = {}
    for r in cod.itertuples():
        keys.setdefault(ob.name_key(r.node_name), []).append((r.longitude, r.latitude))
    left = 0
    for r in unc.itertuples():
        for lo, la in keys.get(ob.name_key(r.node_name), ()):
            if 0 < ob.hav_km(lo, la, r.longitude, r.latitude) <= 0.9: left += 1
    assert left == 0
    assert "Coimbatore North" not in set(unc.node_name)
