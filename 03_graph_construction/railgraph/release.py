"""railgraph.release - load the frozen graph release. The one entry point for analysis.

Every analysis module should start here rather than reading CSVs or re-running repairs,
so that all of them work on the same network and a later release changes one line.

    import sys; sys.path.insert(0, "<repo>/03_graph_construction")
    from railgraph.release import load_graph, load_service, load_resolver, release_info

    G = load_graph()                     # networkx graph, v1.4 open
    svc = load_service()                 # directed service pairs, with trains_per_day
    code = load_resolver()               # map a station code from any dataset to a node
    code("DDU")                          # -> 'MGS'  (renamed station, resolved)
    code("QLN")                          # -> None   (Kollam Jn is absent from the graph)

Edges carry `km`, `eid`, `origin` (which release or repair put them there),
`length_source` and `length_is_lower_bound` - that last one matters, because a quarter
of the network's kilometres are a floor rather than a measurement.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import networkx as nx
import pandas as pd

DEFAULT_RELEASE = "v1_4"


def _root(root=None) -> Path:
    if root: return Path(root)
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "03_graph_construction").is_dir(): return p
    raise RuntimeError("could not locate the repository root from railgraph/release.py")


def _dir(root=None, release=DEFAULT_RELEASE) -> Path:
    d = _root(root) / "03_graph_construction" / f"graph_{release}"
    if not d.is_dir():
        raise FileNotFoundError(f"{d} not found - run `make v14` to build the release")
    return d


@lru_cache(maxsize=4)
def _frames(root=None, release=DEFAULT_RELEASE, variant="open"):
    d = _dir(root, release) / variant
    return (pd.read_csv(d / "nodes.csv"), pd.read_csv(d / "edges.csv"))


def load_graph(root=None, release=DEFAULT_RELEASE, variant="open", weight="km"):
    """The physical graph. `weight` picks the default edge weight: 'km' only for now."""
    nodes, edges = _frames(root, release, variant)
    G = nx.Graph()
    for r in nodes.itertuples():
        G.add_node(r.node_id, name=r.node_name, lon=r.longitude, lat=r.latitude,
                   state=r.state, zone=r.zone_code, node_type=r.node_type)
    for r in edges.itertuples():
        G.add_edge(r.from_node, r.to_node, km=float(r.length_km), eid=r.edge_id,
                   origin=r.origin, length_source=r.length_source,
                   length_is_lower_bound=bool(r.length_is_lower_bound),
                   gauge=r.gauge_code, tracks=r.n_tracks, zone=r.zone_code)
    return G


def load_nodes(root=None, release=DEFAULT_RELEASE, variant="open"):
    return _frames(root, release, variant)[0].copy()


def load_edges(root=None, release=DEFAULT_RELEASE, variant="open"):
    return _frames(root, release, variant)[1].copy()


def load_service(root=None, release=DEFAULT_RELEASE, variant="open", what="edges"):
    """`what`: 'edges' directed station pairs | 'hourly' departures by hour |
    'per_edge' trains over each physical section | 'frequency' per-train running days."""
    d = _root(root) / "03_graph_construction" / f"service_layer_{release}" / variant
    name = {"edges": "service_edges_directed.csv", "hourly": "service_hourly.csv",
            "per_edge": "edge_service.csv", "frequency": "train_frequency.csv"}[what]
    return pd.read_csv(d / name)


def load_resolver(root=None, release=DEFAULT_RELEASE):
    """Station code -> graph node, or None when the graph has no such station.

    Current railway data uses codes the graph predates (Mughalsarai is DDU now,
    Allahabad is Prayagraj). Joining without this silently drops those stops.
    """
    d = _dir(root, release)
    cw = pd.read_csv(d / "station_code_crosswalk.csv")
    ids = set(pd.read_csv(d / "open" / "nodes.csv").node_id)
    alias = dict(zip(cw.loc[cw.resolution == "alias", "code"],
                     cw.loc[cw.resolution == "alias", "graph_node"]))

    def resolve(code):
        if code in ids: return code
        return alias.get(code)
    resolve.aliases = alias
    resolve.status = dict(zip(cw.code, cw.resolution))
    return resolve


def release_info(root=None, release=DEFAULT_RELEASE) -> dict:
    """Version, what changed, gate results and the caveats a user should know."""
    d = _dir(root, release)
    man = json.loads((d / f"graph_{release}.manifest.json").read_text())
    gates = json.loads((d / "gates.json").read_text()) if (d / "gates.json").exists() else {}
    return dict(version=man["version"], supersedes=man.get("supersedes"),
                built_at_utc=man.get("built_at_utc"), what_changed=man.get("what_changed"),
                gates_passed=gates.get("all_passed"), measured=gates.get("measured"),
                caveats=[
                    "25.3% of route km is a straight-line lower bound, not a measurement",
                    "declared speeds are unusable; use observed runtimes from the service layer",
                    "82 node pairs duplicate one station, which understates junction criticality",
                    "228 stations are absent; see station_code_crosswalk.csv",
                    "undirected, no turn restrictions, no capacity, passenger trains only",
                    man.get("base_source_licence_caveat", "")])
