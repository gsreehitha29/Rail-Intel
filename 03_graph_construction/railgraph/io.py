"""Export and versioning for graph v1 (g02).

Four formats, chosen to satisfy blueprint §13 (interoperable tabular *plus*
graph-native) and [WIL16] FAIR Interoperability:

  GraphML   graph-native, typed attributes, the citable primary
  parquet    node and edge tables, the fast path for the Phase 4 modules
  GeoJSON    node points and edge lines, WGS84, for QGIS and web maps
  manifest   content hashes of every input and output, library versions, git
             SHA, the full BuildSpec, and a DOI slot

Pickle is deliberately not offered: it is version-fragile, unreadable outside
Python, and fails FAIR Interoperability. A graph database is not offered either
-- at 9,095 nodes it is operational burden with no analytical gain (D-016).

The manifest is what makes "frozen" mean something. A graph is frozen when its
manifest reproduces on a clean run from the raw sources.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

from . import config as C
from . import metrics as M
from .config import BuildSpec

#: Attributes written to GraphML. GraphML cannot hold nulls or Python objects,
#: so every value is coerced and the coercion is recorded in the manifest.
GRAPHML_NODE_ATTRS = ("node_type", "station_code", "node_name", "longitude",
                      "latitude", "zone_code", "zone_name", "zone_source",
                      "state", "junction_class", "n_corridors", "degree")
GRAPHML_EDGE_ATTRS = ("edge_id", "length_km", "corridor_id", "gauge_code",
                      "zone_code", "speed_kmph", "n_tracks", "service_load",
                      "service_direct", "any_stitch", "core_v2", "core_v4")


def _sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while blob := f.read(chunk):
            h.update(blob)
    return h.hexdigest()


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(C.REPO), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return None


def _clean_for_graphml(v):
    """GraphML takes scalars only, and no NaN."""
    if v is None:
        return ""
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return "" if (isinstance(v, float) and np.isnan(v)) else float(v)
    if isinstance(v, (list, tuple, dict, set)):
        return json.dumps(list(v) if not isinstance(v, dict) else v, default=str)
    return str(v)


def export_graphml(G: nx.Graph, path: Path) -> Path:
    H = nx.Graph()
    for n, d in G.nodes(data=True):
        H.add_node(n, **{k: _clean_for_graphml(d.get(k))
                         for k in GRAPHML_NODE_ATTRS if k in d})
    for u, v, d in G.edges(data=True):
        H.add_edge(u, v, **{k: _clean_for_graphml(d.get(k))
                            for k in GRAPHML_EDGE_ATTRS if k in d})
    H.graph["dataset_version"] = str(G.graph.get("dataset_version", C.DATASET_VERSION))
    H.graph["spec_hash"] = str(G.graph.get("spec_hash", ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(H, path)
    return path


def export_tables(G: nx.Graph, out_dir: Path) -> dict[str, Path]:
    """Node and edge parquet, carrying the graph-derived columns too."""
    out_dir.mkdir(parents=True, exist_ok=True)
    nodes = M.node_basics(G)
    nodes_src = pd.read_csv(C.DATASET / "nodes.csv")
    nodes = nodes.merge(
        nodes_src[["node_id", "in_scope", "junction_class", "match_confidence",
                   "match_method", "spatial_gap_km", "coordinate_shared",
                   "is_dissolvable"]],
        on="node_id", how="left")
    rows = []
    for u, v, d in G.edges(data=True):
        r = {"from_node": u, "to_node": v}
        r.update(d)
        rows.append(r)
    edges = pd.DataFrame(rows)
    np_, ep = out_dir / "nodes.parquet", out_dir / "edges.parquet"
    nodes.to_parquet(np_, index=False)
    edges.to_parquet(ep, index=False)
    return {"nodes": np_, "edges": ep}


def export_geojson(G: nx.Graph, out_dir: Path) -> dict[str, Path]:
    """Node points and straight-line edge geometry, WGS84 (EPSG:4326).

    The edge geometry is the chord between its two endpoints, NOT the true
    track alignment: the corridor spine that produced the edge is not retained
    per-edge by s09. So this is a schematic, correct for topology and for
    mapping at national scale, and wrong for anything that needs the real
    alignment. Stated in the manifest and in the dataset README rather than
    left for a user to discover.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    nfeat = []
    for n, d in G.nodes(data=True):
        lon, lat = d.get("longitude"), d.get("latitude")
        if lon is None or pd.isna(lon) or lat is None or pd.isna(lat):
            continue
        nfeat.append({"type": "Feature",
                      "geometry": {"type": "Point",
                                   "coordinates": [float(lon), float(lat)]},
                      "properties": {k: _clean_for_graphml(d.get(k))
                                     for k in GRAPHML_NODE_ATTRS if k in d}
                                    | {"node_id": n}})
    efeat = []
    for u, v, d in G.edges(data=True):
        a, b = G.nodes[u], G.nodes[v]
        if any(x is None or pd.isna(x) for x in
               (a.get("longitude"), a.get("latitude"),
                b.get("longitude"), b.get("latitude"))):
            continue
        efeat.append({"type": "Feature",
                      "geometry": {"type": "LineString",
                                   "coordinates": [
                                       [float(a["longitude"]), float(a["latitude"])],
                                       [float(b["longitude"]), float(b["latitude"])]]},
                      "properties": {k: _clean_for_graphml(d.get(k))
                                     for k in GRAPHML_EDGE_ATTRS if k in d}
                                    | {"from_node": u, "to_node": v}})

    paths = {}
    for name, feats in (("nodes", nfeat), ("edges", efeat)):
        p = out_dir / f"{name}.geojson"
        p.write_text(json.dumps({
            "type": "FeatureCollection",
            "crs": {"type": "name",
                    "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
            "features": feats}))
        paths[name] = p
    return paths


def write_manifest(G: nx.Graph, spec: BuildSpec, out_dir: Path,
                   outputs: dict[str, Path], *, doi: str | None = None) -> Path:
    """Content-hashed manifest. This is what makes 'frozen' verifiable."""
    inputs = {}
    for p in sorted(C.DATASET.glob("*.csv")):
        inputs[f"02_graph_inputs/graph_dataset/{p.name}"] = {
            "sha256": _sha256(p), "bytes": p.stat().st_size}
    nj = C.INPUTS / "nodes_junctions.csv"
    if nj.exists():
        inputs["02_graph_inputs/graph_inputs/nodes_junctions.csv"] = {
            "sha256": _sha256(nj), "bytes": nj.stat().st_size}

    man = {
        "artifact": "Rail-Intell station-level physical railway graph",
        "version": C.DATASET_VERSION,
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": _git_sha(),
        "doi": doi,
        "build_spec": spec.to_dict(),
        "spec_hash": spec.hash,
        "structure": M.cut_structure(G),
        "inputs": inputs,
        "outputs": {k: {"path": str(v.relative_to(out_dir.parent)),
                        "sha256": _sha256(v), "bytes": v.stat().st_size}
                    for k, v in outputs.items()},
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "networkx": nx.__version__,
        },
        "caveats": {
            "geojson_edge_geometry": (
                "straight chord between endpoints, not the true track "
                "alignment -- schematic only"),
            "graphml_nulls": "nulls written as empty strings; NaN not representable",
            "length_km_bias": (
                "spine shortcutting affects 17.1% of consecutive pairs, median "
                "5% short (LIMITATIONS 1.1, D-019)"),
            "pickle_not_offered": "version-fragile and not interoperable (D-016)",
        },
    }
    p = out_dir / "graph_v1.manifest.json"
    p.write_text(json.dumps(man, indent=2, default=str))
    return p


def export_all(G: nx.Graph | None = None, spec: BuildSpec | None = None,
               out_dir: Path | None = None, *, doi: str | None = None) -> dict:
    """Write every format plus the manifest. The g02 deliverable."""
    from .build import load_graph
    spec = spec or BuildSpec(label="graph v1 release")
    G = G if G is not None else load_graph(spec)
    out_dir = out_dir or C.RELEASE
    out_dir.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, Path] = {}
    outputs["graphml"] = export_graphml(G, out_dir / "rail_graph_v1.graphml")
    outputs.update({f"parquet_{k}": v for k, v in export_tables(G, out_dir).items()})
    outputs.update({f"geojson_{k}": v for k, v in export_geojson(G, out_dir).items()})
    manifest = write_manifest(G, spec, out_dir, outputs, doi=doi)
    return {"out_dir": out_dir, "outputs": outputs, "manifest": manifest}


def verify_roundtrip(G: nx.Graph, out_dir: Path | None = None) -> dict:
    """Does every export reload to the same graph? The D-016 evidence."""
    out_dir = out_dir or C.RELEASE
    res: dict = {}

    H = nx.read_graphml(out_dir / "rail_graph_v1.graphml")
    res["graphml"] = {
        "nodes_match": H.number_of_nodes() == G.number_of_nodes(),
        "edges_match": H.number_of_edges() == G.number_of_edges(),
        "length_km_sum_delta": abs(
            sum(float(d["length_km"]) for _, _, d in H.edges(data=True))
            - sum(float(d["length_km"]) for _, _, d in G.edges(data=True))),
        "bytes": (out_dir / "rail_graph_v1.graphml").stat().st_size,
    }

    ne = pd.read_parquet(out_dir / "edges.parquet")
    nn = pd.read_parquet(out_dir / "nodes.parquet")
    res["parquet"] = {
        "nodes_match": len(nn) == G.number_of_nodes(),
        "edges_match": len(ne) == G.number_of_edges(),
        "length_km_sum_delta": abs(ne.length_km.sum()
                                   - sum(d["length_km"] for _, _, d in G.edges(data=True))),
        "bytes": sum((out_dir / f"{x}.parquet").stat().st_size
                     for x in ("nodes", "edges")),
    }

    # GeoJSON cannot represent a feature with no coordinate, so some loss is
    # expected. Loss is only acceptable if it is fully ACCOUNTED FOR -- an
    # unexplained missing feature is a silent data loss, which the project's
    # engineering principles forbid.
    gj = json.loads((out_dir / "edges.geojson").read_text())
    gn = json.loads((out_dir / "nodes.geojson").read_text())
    no_coord = [n for n, d in G.nodes(data=True)
                if d.get("longitude") is None or pd.isna(d.get("longitude"))
                or d.get("latitude") is None or pd.isna(d.get("latitude"))]
    expected_edge_loss = sum(1 for u, v in G.edges()
                             if u in set(no_coord) or v in set(no_coord))
    edge_loss = G.number_of_edges() - len(gj["features"])
    node_loss = G.number_of_nodes() - len(gn["features"])
    res["geojson"] = {
        "edge_features": len(gj["features"]),
        "node_features": len(gn["features"]),
        "edge_loss": edge_loss,
        "node_loss": node_loss,
        "expected_edge_loss_from_missing_coords": expected_edge_loss,
        "expected_node_loss_from_missing_coords": len(no_coord),
        "loss_fully_accounted": (edge_loss == expected_edge_loss
                                 and node_loss == len(no_coord)),
        "nodes_without_coordinates": no_coord,
        "edges_match": edge_loss == expected_edge_loss,
        "nodes_match": node_loss == len(no_coord),
        "bytes": sum((out_dir / f"{x}.geojson").stat().st_size
                     for x in ("nodes", "edges")),
    }
    res["all_roundtrip_ok"] = all(
        res[f].get("edges_match") and res[f].get("nodes_match", True)
        for f in ("graphml", "parquet", "geojson"))
    res["geometry_loss_note"] = (
        f"{edge_loss} edge and {node_loss} node feature(s) omitted from GeoJSON, "
        f"fully explained by {len(no_coord)} node(s) without coordinates: "
        f"{no_coord}. See F-021 -- the affected edge's length_km is not a "
        f"measurement.")
    return res
