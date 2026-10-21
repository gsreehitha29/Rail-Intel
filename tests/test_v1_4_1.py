"""Milestone A1 of the build roadmap: the v1.4.1 working build.

These close I-04 for I-01 and I-02 (the test suite was blind to both). I-03 gets its
test at A3, with the coordinate fixes. Skipped until `make v141` has been run.
"""
import re

import networkx as nx
import pandas as pd
import pytest

from conftest import ROOT

V141 = ROOT / "03_graph_construction" / "graph_v1_4_1"
V14 = ROOT / "03_graph_construction" / "graph_v1_4"
pytestmark = pytest.mark.skipif(not (V141 / "open" / "nodes.csv").exists(),
                                reason="v1.4.1 not built; run `make v141`")
INFERRED = ["gauge_code", "zone_code", "n_tracks", "corridor_id"]
# what A1 could not infer; a later change may only lower these
MAX_UNRESOLVED = dict(gauge_code=1, zone_code=3, n_tracks=20, corridor_id=68)


@pytest.fixture(scope="module")
def nodes():
    return pd.read_csv(V141 / "open" / "nodes.csv")


@pytest.fixture(scope="module")
def edges():
    return pd.read_csv(V141 / "open" / "edges.csv")


@pytest.fixture(scope="module")
def repairs(edges):
    return edges[edges.origin != "graph_v1_3/open"]


def test_derived_node_columns_match_the_graph(nodes, edges):
    """I-01. v1.4 shipped 255 stale degrees. Every derived column must equal what the
    graph says, so a CSV reader and load_graph() can never disagree again."""
    G = nx.Graph()
    G.add_nodes_from(nodes.node_id)
    G.add_edges_from(zip(edges.from_node, edges.to_node))
    deg = dict(G.degree())
    assert (nodes.node_id.map(deg) == nodes.degree).all()
    comps = sorted(nx.connected_components(G), key=lambda c: (-len(c), min(c)))
    label = {n: i for i, c in enumerate(comps) for n in c}
    assert (nodes.node_id.map(label) == nodes.component_id).all()
    assert (nodes.in_giant == (nodes.component_id == 0)).all()


def test_repair_sections_carry_official_distance_and_source(repairs):
    """I-02. Every repair section was added because a timetable gave its distance, so
    it must carry that distance and say which timetable."""
    assert len(repairs) == 129
    assert repairs.official_km.notna().all() and (repairs.official_km > 0).all()
    assert repairs.official_source.notna().all()
    assert repairs.edge_origin.notna().all()
    assert repairs.raised_to_chord.notna().all()


def test_official_distance_is_the_one_in_the_evidence(repairs):
    """Cross-check against OVERRIDES.csv, read independently of the build code."""
    ov = pd.read_csv(V141 / "OVERRIDES.csv")
    ev = {}
    for r in ov[ov.action == "add_edge"].itertuples():
        km = float(re.search(r"\) at ([\d.]+) km", r.evidence).group(1))
        a, b = r.item_id.split("|")
        ev[(r.audit_file, frozenset((a, b)))] = km
    for r in repairs.itertuples():
        assert ev[(r.origin, frozenset((r.from_node, r.to_node)))] == r.official_km


def test_repair_attributes_are_filled_or_declared_unresolved(repairs):
    """I-02. Each of the four attributes is either filled and listed as inferred, or
    empty and listed as unresolved. Nothing is empty without saying so."""
    for r in repairs.itertuples():
        got = set(str(r.repair_attrs_inferred).split(";")) if pd.notna(r.repair_attrs_inferred) else set()
        miss = set(str(r.repair_attrs_unresolved).split(";")) if pd.notna(r.repair_attrs_unresolved) else set()
        assert got | miss == set(INFERRED) and not got & miss, r.edge_id
        for c in INFERRED:
            assert pd.notna(getattr(r, c)) == (c in got), (r.edge_id, c)
    for c, cap in MAX_UNRESOLVED.items():
        n = repairs.repair_attrs_unresolved.fillna("").str.split(";").apply(lambda s: c in s).sum()
        assert n <= cap, f"{c}: {n} unresolved, cap {cap}"


def test_misleading_columns_are_retired(nodes, edges):
    assert "overrides_applied" not in nodes.columns
    assert not {"service_direct", "service_load"} & set(edges.columns)


def test_a1_changes_no_topology_and_keeps_every_id(nodes, edges):
    """A1 fixes attributes only. The same stations, the same sections, the same ids as
    v1.4. A3 may change this, through OVERRIDES.csv, and then updates this test."""
    n14 = pd.read_csv(V14 / "open" / "nodes.csv")
    e14 = pd.read_csv(V14 / "open" / "edges.csv")
    assert set(nodes.node_id) == set(n14.node_id)
    assert set(edges.edge_id) == set(e14.edge_id)
    assert round(edges.length_km.sum(), 1) == round(e14.length_km.sum(), 1)
