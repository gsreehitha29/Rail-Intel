"""The release contract. These tests are the promise `STABILITY.md` makes.

A failure here means downstream code that worked yesterday may break today. That is
either a bug or a deliberate new version — never something to paper over by editing
`golden.json` without a corresponding DECISIONS.md entry.
"""
import pandas as pd
import pytest

from conftest import GRAPH_DIR, ROOT


def test_graph_shape(G, golden):
    g = golden["graph"]
    assert G.number_of_nodes() == g["nodes"]
    assert G.number_of_edges() == g["edges"]


def test_total_km(G, golden):
    km = sum(d["km"] for _, _, d in G.edges(data=True))
    assert round(km, 1) == golden["graph"]["km"]


def test_every_edge_has_a_positive_length(G):
    bad = [(u, v) for u, v, d in G.edges(data=True)
           if d.get("km") is None or not d["km"] > 0]
    assert bad == [], f"{len(bad)} edges with no usable length, e.g. {bad[:5]}"


def test_connectivity(G, golden):
    import networkx as nx
    comps = sorted((len(c) for c in nx.connected_components(G)), reverse=True)
    assert len(comps) == golden["graph"]["components"]
    assert round(comps[0] / G.number_of_nodes(), 4) == golden["graph"]["giant_share"]


def test_degree_is_bounded(G, golden):
    """Spatially embedded networks have bounded degree (Barthelemy 2011). A jump here
    means a node has been over-merged."""
    assert max(d for _, d in G.degree()) == golden["graph"]["max_degree"]


def test_lower_bound_shares_match_the_published_caveat(golden):
    """The caveat in release_info() quotes the km-weighted share. If this changes, the
    caveat text has to change with it - they drifted apart once already."""
    e = pd.read_csv(GRAPH_DIR / "open" / "edges.csv")
    km = e.loc[e.length_is_lower_bound, "length_km"].sum() / e.length_km.sum()
    assert round(float(km), 4) == golden["graph"]["lower_bound_km_share"]

    from railgraph.release import release_info
    caveat = next(c for c in release_info(root=ROOT)["caveats"] if "lower bound" in c)
    assert f"{km:.1%}" in caveat, (
        f"caveat says {caveat!r} but the measured share is {km:.1%}")


def test_schema_is_stable(golden):
    """Columns may be added at the end. Removing or renaming one breaks consumers."""
    nodes = pd.read_csv(GRAPH_DIR / "open" / "nodes.csv", nrows=1)
    edges = pd.read_csv(GRAPH_DIR / "open" / "edges.csv", nrows=1)
    for name, got, want in (("nodes", nodes.columns, golden["schema"]["node_cols"]),
                            ("edges", edges.columns, golden["schema"]["edge_cols"])):
        missing = [c for c in want if c not in got]
        assert not missing, f"{name}.csv lost columns: {missing}"


def test_referential_integrity(G, golden):
    edges = pd.read_csv(GRAPH_DIR / "open" / "edges.csv")
    ids = set(pd.read_csv(GRAPH_DIR / "open" / "nodes.csv").node_id)
    dangling = set(edges.from_node) | set(edges.to_node) - ids
    assert not (dangling - ids), "edges reference nodes that do not exist"
    assert edges.edge_id.is_unique


def test_resolver_handles_renames(golden):
    """Current railway data uses codes the graph predates. Joining without the
    resolver silently drops those stops - the failure mode it exists to prevent."""
    from railgraph.release import load_resolver
    code = load_resolver(root=ROOT)
    for given, want in golden["resolver"].items():
        assert code(given) == want, f"{given} resolved to {code(given)!r}, want {want!r}"


def test_service_layer(golden):
    from railgraph.release import load_service
    svc = load_service(root=ROOT)
    assert len(svc) == golden["service"]["directed_pairs"]
    assert "trains_per_day" in svc.columns, (
        "trains_per_day is the only valid load measure; distinct_trains overstates 2.03x")
    assert svc.trains_per_day.gt(0).all()


@pytest.mark.parametrize("what", ["edges", "hourly", "per_edge", "frequency"])
def test_every_service_view_loads(what):
    from railgraph.release import load_service
    assert len(load_service(root=ROOT, what=what)) > 0


def test_overrides_all_carry_evidence(golden):
    """D-054: a row without evidence stops the build. A correction that is not in the
    overrides file does not exist."""
    ov = pd.read_csv(GRAPH_DIR / "OVERRIDES.csv")
    assert len(ov) == golden["overrides"]["rows"]
    assert ov.evidence.notna().all(), "override rows with no evidence"
    assert {k: int(v) for k, v in ov.action.value_counts().items()} == \
        golden["overrides"]["by_action"]


def test_crosswalk_accounts_for_every_code(golden):
    cw = pd.read_csv(GRAPH_DIR / "station_code_crosswalk.csv")
    assert {k: int(v) for k, v in cw.resolution.value_counts().items()} == golden["crosswalk"]
    assert cw.code.is_unique


def test_release_info_is_complete():
    from railgraph.release import release_info
    info = release_info(root=ROOT)
    assert info["version"] == "v1.4"
    assert info["gates_passed"] is True
    assert all(c for c in info["caveats"]), "a caveat is empty - the licence note is unset"
