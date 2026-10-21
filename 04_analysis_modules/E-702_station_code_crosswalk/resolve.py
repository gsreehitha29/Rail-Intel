"""Shared station-code resolver (gap G1).

Any join between the graph and current railway data goes through this, so the whole
project resolves codes the same way and nothing silently drops a renamed station.

    from resolve import load_resolver
    res = load_resolver(ROOT)
    node = res.node("DDU")        # -> 'MGS'   (renamed station, mapped)
    node = res.node("QLN")        # -> None    (Kollam Jn is absent from the graph)
    res.status("QLN")             # -> 'missing_station'

`node()` returns the graph node id for a code, or None when the graph has no node for
it. Codes the graph already holds pass straight through.
"""
from pathlib import Path

import pandas as pd


class Resolver:
    def __init__(self, graph_ids, alias, status, meta):
        self._ids, self._alias, self._status, self.meta = graph_ids, alias, status, meta

    def node(self, code):
        """Graph node id for a station code, or None if the graph has no such station."""
        if code in self._ids: return code
        return self._alias.get(code)

    def status(self, code):
        """'in_graph' | 'alias' | 'missing_station' | 'unresolved' | 'unknown'."""
        if code in self._ids: return "in_graph"
        return self._status.get(code, "unknown")

    def map_series(self, s):
        """Vectorised: map a pandas Series of codes to node ids (NaN where absent)."""
        return s.map(lambda c: self.node(c))

    @property
    def aliases(self):
        return dict(self._alias)


def load_resolver(root, crosswalk=None):
    root = Path(root)
    crosswalk = Path(crosswalk) if crosswalk else (
        root / "04_analysis_modules/E-702_station_code_crosswalk/out/crosswalk.csv")
    nodes = pd.read_csv(root / "03_graph_construction/graph_v1_3/open/nodes.csv")
    cw = pd.read_csv(crosswalk)
    al = cw[cw.resolution == "alias"]
    return Resolver(set(nodes.node_id),
                    dict(zip(al.code, al.graph_node)),
                    dict(zip(cw.code, cw.resolution)),
                    dict(crosswalk=str(crosswalk), aliases=len(al),
                         missing=int((cw.resolution == "missing_station").sum()),
                         unresolved=int((cw.resolution == "unresolved").sum())))
