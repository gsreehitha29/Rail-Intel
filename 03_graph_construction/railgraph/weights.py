"""Named edge-weight registry.

Blueprint §24 and D-010: a graph weight must never be implicit. Every metric
call names its weight from this registry, and every weight states what question
it answers and how it treats missing data.
"""
from __future__ import annotations

from typing import Callable

import networkx as nx
import numpy as np

#: Representative speed used by travel_time_proxy where speed_kmph is null.
#: D-012: speed is present on only 49.8% of corridors and the corridors that
#: have it are scattered, so the null cannot be dropped. Substituting a single
#: constant is an explicit, documented assumption -- never silent imputation.
#: Any result using this weight must report what fraction of its path length
#: relied on the fallback (see travel_time_coverage).
FALLBACK_SPEED_KMPH = 50.0


def _unit(_u, _v, _d) -> float:
    """Topological distance: every edge costs 1. For hop counts and transfers."""
    return 1.0


def _length_km(_u, _v, d) -> float:
    """True geodesic kilometres. The default physical weight (D-010).

    Carries the spine-shortcutting bias of 17.1% of pairs, median 5% short
    (LIMITATIONS §1.1, D-019). Report distance-weighted results accordingly.
    """
    return float(d["length_km"])


def _travel_time_proxy(_u, _v, d) -> float:
    """Minutes at sanctioned speed. A proxy, not a timetable travel time.

    Null speed falls back to FALLBACK_SPEED_KMPH, which is an assumption, not a
    measurement. For genuinely time-weighted work prefer the service layer's
    runtime_min_median (service_edges.csv), which is observed.
    """
    v = d.get("speed_kmph")
    if v is None or (isinstance(v, float) and np.isnan(v)) or v <= 0:
        v = FALLBACK_SPEED_KMPH
    return float(d["length_km"]) / float(v) * 60.0


def _service_impedance(_u, _v, d) -> float:
    """Distance discounted by how much service the edge carries.

    For resilience and routing questions where a well-served corridor is
    effectively 'closer'. load=0 is not treated as infinite cost: an edge with
    no observed service may be a reconstruction artifact or genuinely unserved,
    and the graph cannot tell which, so it is penalised, not removed.
    """
    load = d.get("service_load") or 0.0
    return float(d["length_km"]) / np.log1p(1.0 + float(load))


REGISTRY: dict[str, Callable] = {
    "unit": _unit,
    "length_km": _length_km,
    "travel_time_proxy": _travel_time_proxy,
    "service_impedance": _service_impedance,
}

DESCRIPTIONS = {
    "unit": "topological hops; no physical meaning",
    "length_km": "true geodesic km (D-010); carries the shortcutting bias",
    "travel_time_proxy": f"minutes at sanctioned speed, {FALLBACK_SPEED_KMPH} km/h fallback on 49% nulls",
    "service_impedance": "geodesic km discounted by log service load",
}


def get(name: str) -> Callable:
    if name not in REGISTRY:
        raise KeyError(f"unknown weight {name!r}; available: {sorted(REGISTRY)}")
    return REGISTRY[name]


def travel_time_coverage(G: nx.Graph) -> dict:
    """What fraction of the network travel_time_proxy actually measures.

    Any result using travel_time_proxy must report this, or it is claiming
    precision it does not have.
    """
    tot = n_known = km_tot = km_known = 0
    for _u, _v, d in G.edges(data=True):
        v = d.get("speed_kmph")
        known = not (v is None or (isinstance(v, float) and np.isnan(v)) or v <= 0)
        tot += 1
        km_tot += float(d["length_km"])
        if known:
            n_known += 1
            km_known += float(d["length_km"])
    return {
        "edges_with_speed": n_known,
        "edges_total": tot,
        "edge_share": n_known / tot if tot else 0.0,
        "km_with_speed": km_known,
        "km_total": km_tot,
        "km_share": km_known / km_tot if km_tot else 0.0,
    }
