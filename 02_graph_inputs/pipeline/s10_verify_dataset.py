"""
Stage 10 — verify the shipped dataset.

s09 builds graph_dataset/; this stage re-derives its guarantees from the files
themselves and fails loudly if any of them stops holding. It exists so the
claim "the dataset is internally consistent" is re-checked on every run rather
than asserted once. Writes graph_dataset/VERIFICATION.txt.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import PHASE_DIR, banner  # noqa: E402

DATASET_DIR = PHASE_DIR / "graph_dataset"
FILES = ["nodes.csv", "edges.csv", "stations.csv", "corridors.csv",
         "service_edges.csv", "station_sequences.csv"]
EXPECT_ZONES = 17
INDIA_BOUNDS = (68, 98, 6, 38)


def _norm(v):
    s = unicodedata.normalize("NFKC", str(v)).strip().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def main() -> None:
    banner("STAGE 10 — VERIFY SHIPPED DATASET")
    F = {f: pd.read_csv(DATASET_DIR / f, low_memory=False) for f in FILES}
    nd, e, st = F["nodes.csv"], F["edges.csv"], F["stations.csv"]
    co, sv, sq = F["corridors.csv"], F["service_edges.csv"], F["station_sequences.csv"]

    lines, failures = [], []

    def ck(cond, msg):
        cond = bool(cond)
        lines.append(("  PASS  " if cond else "  FAIL  ") + msg)
        if not cond:
            failures.append(msg)

    def sec(title):
        lines.append("")
        lines.append(f"-- {title} --")

    lines.append("DATASET VERIFICATION")
    lines.append("=" * 70)

    sec("keys")
    ck(nd.node_id.is_unique, "nodes.node_id unique")
    ck(e.edge_id.is_unique, "edges.edge_id unique")
    ck(st.station_code.is_unique, "stations.station_code unique")
    ck(co.corridor_id.is_unique, "corridors.corridor_id unique")
    pairs = [tuple(sorted(p)) for p in zip(e.from_node, e.to_node)]
    ck(len(set(pairs)) == len(pairs), "edges have no duplicate undirected pair")
    ck((e.from_node != e.to_node).all(), "edges have no self-loops")

    sec("referential integrity")
    N, S, C = set(nd.node_id), set(st.station_code), set(co.corridor_id)
    ck(set(e.from_node) <= N and set(e.to_node) <= N, "every edge endpoint exists in nodes.csv")
    ck(set(e.corridor_id.dropna()) <= C, "every edge.corridor_id exists in corridors.csv")
    stn = nd[nd.node_type == "station"]
    ck(set(stn.station_code) <= S, "every station node exists in stations.csv")
    ck(set(sq.station_code) <= S, "every sequenced station exists in stations.csv")
    ck(set(sv.from_station) <= S and set(sv.to_station) <= S, "every service endpoint exists in stations.csv")
    ck(stn.node_id.equals(stn.station_code), "station node_id == station_code")

    sec("controlled vocabularies")
    zc = set().union(*[set(d[c].dropna()) for d, c in
                       [(nd, "zone_code"), (e, "zone_code"), (st, "zone_code"), (co, "zone_code")]])
    ck(len(zc) == EXPECT_ZONES, f"exactly {EXPECT_ZONES} zone codes across all files (found {len(zc)})")
    zn = set().union(*[set(d[c].dropna()) for d, c in
                       [(nd, "zone_name"), (e, "zone_name"), (co, "zone_name")]])
    ck(len(zn) == EXPECT_ZONES, f"exactly {EXPECT_ZONES} zone names across all files (found {len(zn)})")
    ck(set(e.gauge_code.dropna()) <= {"BG", "MG", "NG", "SG"}, "gauge codes canonical")
    ck("Orissa" not in set(st.state.dropna()), "no 'Orissa' spelling remaining")
    ck(set(nd.node_type) == {"station", "operational_junction"}, "node_type vocabulary closed")
    ck(set(nd.zone_source.dropna()) <= {"station_master", "corridor_inferred"}, "zone_source vocabulary closed")

    collisions = []
    for fn, df in F.items():
        for col in df.columns:
            if df[col].dtype != object:
                continue
            vals = [v for v in df[col].dropna().unique()]
            if not (1 < len(vals) <= 260):
                continue
            g = {}
            for v in vals:
                g.setdefault(_norm(v), []).append(v)
            collisions += [(fn, col, v) for v in g.values() if len(v) > 1]
    ck(not collisions, f"no normalisation collisions in any categorical column ({len(collisions)} found)")
    for c in collisions[:5]:
        lines.append(f"         {c}")

    sec("values")
    ck((e.length_km > 0).all(), "all edge lengths > 0")
    ck(e.length_km.notna().all(), "no null edge lengths")
    lon, lat = nd.longitude.dropna(), nd.latitude.dropna()
    ck(lon.between(INDIA_BOUNDS[0], INDIA_BOUNDS[1]).all()
       and lat.between(INDIA_BOUNDS[2], INDIA_BOUNDS[3]).all(),
       "all node coordinates inside India bounds")
    ck(sv.runtime_min_median.dropna().between(0, 1440).all(), "run-times within 24h")
    ck((sv.n_trains > 0).all(), "service frequencies positive")

    sec("structure")
    G = nx.Graph()
    G.add_nodes_from(nd.node_id)
    G.add_edges_from(zip(e.from_node, e.to_node))
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    ck(G.number_of_nodes() == len(nd), f"node count matches nodes.csv ({G.number_of_nodes():,})")
    ck(G.number_of_edges() == len(e), f"edge count matches edges.csv ({G.number_of_edges():,})")
    ck(int(nd.in_giant_component.sum()) == len(comps[0]),
       f"in_giant_component flag matches recomputation ({len(comps[0]):,} nodes, "
       f"{len(comps[0])/G.number_of_nodes():.1%})")
    deg = dict(G.degree())
    ck((nd.set_index("node_id").degree == pd.Series(deg)).reindex(nd.node_id).all(),
       "degree column matches recomputation")
    ck(int(e.service_load.gt(0).sum()) >= int(e.service_direct.gt(0).sum()),
       f"service_load covers >= service_direct ({int(e.service_load.gt(0).sum()):,} vs "
       f"{int(e.service_direct.gt(0).sum()):,})")

    lines.append("")
    lines.append("=" * 70)
    lines.append("RESULT: ALL CHECKS PASSED" if not failures else
                 f"RESULT: {len(failures)} CHECK(S) FAILED")
    for f in failures:
        lines.append(f"  - {f}")
    text = "\n".join(lines) + "\n"
    print(text)
    (DATASET_DIR / "VERIFICATION.txt").write_text(text, encoding="utf-8")
    if failures:
        raise SystemExit(f"dataset verification failed: {len(failures)} check(s)")


if __name__ == "__main__":
    main()
