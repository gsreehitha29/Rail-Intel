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

#: Export format revision. 1 = 2026-10-03 hand-listed attribute subset (superseded);
#: 2 = every attribute carried, GeoJSON complete (D-039, F-046).
EXPORT_REVISION = 2

#: Derived per-node structural attributes written alongside the stored ones.
#: These are recomputed from the graph being exported, not copied from the
#: shipped CSV, so they stay correct for any BuildSpec view (D-039).
DERIVED_NODE_ATTRS = ("degree", "component_id", "in_giant_component")

#: Columns that are constant across the artifact. They are carried once at
#: graph level (GraphML ``<graph>`` data, manifest) instead of on all 9,689
#: edges, and re-attached on the table exports.
GRAPH_LEVEL_CONSTANTS = ("dataset_version",)


def export_columns(G: nx.Graph) -> tuple[list[str], list[str]]:
    """Every attribute present on any node / any edge of G, in first-seen order.

    D-039: exports must carry *everything the graph carries*. The previous
    hand-maintained allow-lists silently dropped 10 node and 11 edge attributes
    from the GraphML (``is_dissolvable``, ``bridge_present``, ...). Discovering
    the columns from the graph itself makes that class of defect impossible; the
    round-trip check then proves it per attribute.
    """
    nc: dict[str, None] = {}
    for _, d in G.nodes(data=True):
        for k in d:
            nc.setdefault(k)
    ec: dict[str, None] = {}
    for _, _, d in G.edges(data=True):
        for k in d:
            ec.setdefault(k)
    ncols = [k for k in nc if k not in GRAPH_LEVEL_CONSTANTS]
    ncols += [k for k in DERIVED_NODE_ATTRS if k not in ncols]
    ecols = [k for k in ec if k not in GRAPH_LEVEL_CONSTANTS]
    return ncols, ecols


def derived_node_attrs(G: nx.Graph) -> dict[str, dict]:
    """degree / component_id / in_giant_component, from the graph as exported."""
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    cid = {n: i for i, c in enumerate(comps) for n in c}
    return {n: {"degree": int(G.degree(n)), "component_id": int(cid[n]),
                "in_giant_component": bool(cid[n] == 0)} for n in G}


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
    """GraphML takes typed scalars only and has no null.

    Returns ``None`` for a null, and the caller OMITS the attribute: an absent
    attribute is the only honest null in GraphML. (The earlier "" convention
    turned a missing float into a string and forced mixed-type columns.)
    """
    if v is None:
        return None
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if np.isnan(v) else float(v)
    if v is pd.NA or v is pd.NaT:
        return None
    if isinstance(v, (list, tuple, dict, set)):
        return json.dumps(list(v) if not isinstance(v, dict) else v, default=str)
    return str(v)


def _homogenise(rows: list[dict]) -> list[dict]:
    """One Python type per attribute (GraphML keys are typed). int+float -> float;
    any other mix is a bug upstream and is raised, not papered over."""
    kinds: dict[str, set] = {}
    for r in rows:
        for k, v in r.items():
            kinds.setdefault(k, set()).add(type(v))
    for k, ts in kinds.items():
        if len(ts) == 1:
            continue
        if ts == {int, float}:
            for r in rows:
                if k in r:
                    r[k] = float(r[k])
        else:
            raise TypeError(f"attribute {k!r} has mixed types {sorted(t.__name__ for t in ts)}")
    return rows


def _node_rows(G: nx.Graph) -> dict:
    der = derived_node_attrs(G)
    rows = {}
    for n, d in G.nodes(data=True):
        r = {k: _clean_for_graphml(v) for k, v in {**d, **der[n]}.items()
             if k not in GRAPH_LEVEL_CONSTANTS}
        rows[n] = {k: v for k, v in r.items() if v is not None}
    return rows


def _edge_rows(G: nx.Graph) -> list:
    out = []
    for u, v, d in G.edges(data=True):
        r = {k: _clean_for_graphml(x) for k, x in d.items()
             if k not in GRAPH_LEVEL_CONSTANTS}
        out.append((u, v, {k: x for k, x in r.items() if x is not None}))
    return out


def export_graphml(G: nx.Graph, path: Path) -> Path:
    """GraphML with every node/edge attribute the graph carries (D-039)."""
    nrows = _node_rows(G)
    erows = _edge_rows(G)
    _homogenise(list(nrows.values()))
    _homogenise([r for _, _, r in erows])
    H = nx.Graph()
    for n, r in nrows.items():
        H.add_node(n, **r)
    for u, v, r in erows:
        H.add_edge(u, v, **r)
    H.graph["dataset_version"] = str(G.graph.get("dataset_version", C.DATASET_VERSION))
    H.graph["spec_hash"] = str(G.graph.get("spec_hash", ""))
    # graph-level extras (v1.1 carries attribute_granularity here, since a
    # value constant across all 9,689 edges does not belong on each of them)
    for k in ("version", "provenance_spec_hash", "attribute_granularity",
              "export_revision"):
        if k in G.graph:
            H.graph[k] = _clean_for_graphml(G.graph[k])
    H.graph["export_revision"] = EXPORT_REVISION
    path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(H, path)
    return path


def export_tables(G: nx.Graph, out_dir: Path) -> dict[str, Path]:
    """Node and edge parquet. Same columns as the GraphML, plus the
    graph-level constants re-attached (a table row is read out of context)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    der = derived_node_attrs(G)
    # `in_giant` is the original column name (documented in DATASHEET); the
    # Phase 2 CSVs call the same thing `in_giant_component`. Both are kept.
    nodes = M.node_basics(G)
    stored = pd.DataFrame([{"node_id": n, **{k: v for k, v in d.items()}}
                           for n, d in G.nodes(data=True)])
    extra = [c for c in stored.columns if c not in nodes.columns]
    nodes = nodes.merge(stored[["node_id"] + extra], on="node_id", how="left")
    nodes["in_giant_component"] = nodes.node_id.map(
        {n: d["in_giant_component"] for n, d in der.items()})
    nodes["dataset_version"] = str(G.graph.get("dataset_version", C.DATASET_VERSION))
    rows = []
    for u, v, d in G.edges(data=True):
        r = {"from_node": u, "to_node": v}
        r.update(d)
        rows.append(r)
    edges = pd.DataFrame(rows)
    edges["dataset_version"] = str(G.graph.get("dataset_version", C.DATASET_VERSION))
    np_, ep = out_dir / "nodes.parquet", out_dir / "edges.parquet"
    nodes.to_parquet(np_, index=False)
    edges.to_parquet(ep, index=False)
    return {"nodes": np_, "edges": ep}


def export_geometry_table(alignments: pd.DataFrame, out_dir: Path) -> Path:
    """Per-edge geometry as WKB (EPSG:4326), for consumers without GeoJSON."""
    from .geometry import write_wkb_linestring
    out_dir.mkdir(parents=True, exist_ok=True)
    df = alignments.drop(columns=["coords"]).copy()
    df["wkb"] = [write_wkb_linestring(c) if c is not None else None
                 for c in alignments.coords]
    p = out_dir / "edge_geometry.parquet"
    df.to_parquet(p, index=False)
    return p


def export_geojson(G: nx.Graph, out_dir: Path,
                   alignments: pd.DataFrame | None = None) -> dict[str, Path]:
    """Nodes (Point) and edges (LineString), WGS84 (EPSG:4326).

    EVERY node and edge is a feature (D-039). One with no coordinate is written
    with ``"geometry": null`` -- valid GeoJSON, and visibly present -- instead
    of being dropped, which is how a missing edge goes unnoticed by a GIS user.

    Edge geometry is the true alignment where ``alignments`` provides it
    (``geometry_source == "spine"``, v1.1), otherwise the straight chord between
    the endpoints; ``geometry_source`` says which, per edge.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    nrows = _node_rows(G)
    nfeat = []
    for n, r in nrows.items():
        lon, lat = r.get("longitude"), r.get("latitude")
        geom = (None if lon is None or lat is None else
                {"type": "Point", "coordinates": [float(lon), float(lat)]})
        nfeat.append({"type": "Feature", "geometry": geom,
                      "properties": {"node_id": n, **r}})

    al = (alignments.set_index("edge_id") if alignments is not None else None)
    efeat = []
    for u, v, r in _edge_rows(G):
        a, b = G.nodes[u], G.nodes[v]
        props = {"from_node": u, "to_node": v, **r}
        geom = None
        if al is not None and r.get("edge_id") in al.index:
            row = al.loc[r["edge_id"]]
            props["geometry_source"] = row.geometry_source
            if row.geometry_corridor is not None and not pd.isna(row.geometry_corridor):
                props["geometry_corridor"] = row.geometry_corridor
            if not pd.isna(row.geometry_length_km):
                props["geometry_length_km"] = float(row.geometry_length_km)
            if row.coords is not None:
                geom = {"type": "LineString",
                        "coordinates": [[float(x), float(y)] for x, y in row.coords]}
        else:
            ok = not any(x is None or pd.isna(x) for x in
                         (a.get("longitude"), a.get("latitude"),
                          b.get("longitude"), b.get("latitude")))
            props["geometry_source"] = "chord" if ok else "none"
            if ok:
                geom = {"type": "LineString", "coordinates": [
                    [float(a["longitude"]), float(a["latitude"])],
                    [float(b["longitude"]), float(b["latitude"])]]}
        efeat.append({"type": "Feature", "geometry": geom, "properties": props})

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
                   outputs: dict[str, Path], *, doi: str | None = None,
                   version: str | None = None, filename: str | None = None,
                   extra: dict | None = None,
                   caveats: dict | None = None) -> Path:
    """Content-hashed manifest. This is what makes 'frozen' verifiable.

    `version`, `filename`, `extra` and `caveats` exist so the v1.1 provenance
    release (`E-400`) can write its own manifest through this same function
    rather than forking it.
    """
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
        "version": version or C.DATASET_VERSION,
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
                "per-edge `geometry_source`: `spine` = true track alignment "
                "(v1.1 release only), `chord` = straight line between the "
                "endpoints (schematic), `none` = an endpoint has no coordinate "
                "(feature kept, geometry null)"),
            "graphml_nulls": ("a null attribute is OMITTED, not written as an "
                              "empty string; absent == null (export revision 2)"),
            "export_revision": ("2 = every attribute carried, GeoJSON complete "
                                "(D-039). Revision 1 (2026-10-03) was a hand-listed "
                                "subset; its GraphML lacked is_dissolvable, "
                                "bridge_present and 19 other attributes (F-046)."),
            "length_km_bias": (
                "spine shortcutting affects 17.1% of consecutive pairs, median "
                "5% short (LIMITATIONS 1.1, D-019)"),
            "pickle_not_offered": "version-fragile and not interoperable (D-016)",
        },
    }
    if caveats:
        man["caveats"].update(caveats)
    if extra:
        man.update(extra)
    p = out_dir / (filename or "graph_v1.manifest.json")
    p.write_text(json.dumps(man, indent=2, default=str))
    return p


def export_all(G: nx.Graph | None = None, spec: BuildSpec | None = None,
               out_dir: Path | None = None, *, doi: str | None = None,
               alignments: pd.DataFrame | None = None) -> dict:
    """Write every format plus the manifest. The g02 deliverable."""
    from .build import load_graph
    spec = spec or BuildSpec(label="graph v1 release")
    G = G if G is not None else load_graph(spec)
    G.graph["export_revision"] = EXPORT_REVISION
    out_dir = out_dir or C.RELEASE
    out_dir.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, Path] = {}
    outputs["graphml"] = export_graphml(G, out_dir / "rail_graph_v1.graphml")
    outputs.update({f"parquet_{k}": v for k, v in export_tables(G, out_dir).items()})
    outputs.update({f"geojson_{k}": v
                    for k, v in export_geojson(G, out_dir, alignments).items()})
    if alignments is not None:
        outputs["parquet_edge_geometry"] = export_geometry_table(alignments, out_dir)
    manifest = write_manifest(G, spec, out_dir, outputs, doi=doi)
    return {"out_dir": out_dir, "outputs": outputs, "manifest": manifest}


def _eq(a, b, tol=1e-9) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(a)))
        except (TypeError, ValueError):
            return False
    return a == b


def _compare_attrs(expected: dict, got: dict) -> tuple[int, list[str]]:
    """Every non-null expected attribute must be present and equal in `got`."""
    bad = []
    for k, v in expected.items():
        if k not in got:
            bad.append(f"{k}:absent")
        elif not _eq(v, got[k]):
            bad.append(f"{k}:{v!r}!={got[k]!r}")
    return len(bad), bad


def verify_roundtrip(G: nx.Graph, out_dir: Path | None = None, *,
                     graphml: str = "rail_graph_v1.graphml") -> dict:
    """Does every export reload to the SAME graph, attribute by attribute?

    D-016 originally checked counts and one length sum. That passed while the
    GraphML silently lacked 10 node and 11 edge attributes (F-046), because it
    never asked whether each attribute survived. This asks, for every node and
    every edge, and for each of GraphML, parquet and GeoJSON.
    """
    out_dir = out_dir or C.RELEASE
    res: dict = {}
    ncols, ecols = export_columns(G)
    nexp = _node_rows(G)
    eexp = {r["edge_id"]: r for _, _, r in _edge_rows(G)}
    n_attr_total = sum(len(r) for r in nexp.values())
    e_attr_total = sum(len(r) for r in eexp.values())

    # ---- GraphML ---------------------------------------------------------
    H = nx.read_graphml(out_dir / graphml)
    nbad = ebad = 0
    nex: list[str] = []
    for n, exp in nexp.items():
        k, bad = _compare_attrs(exp, H.nodes[n]); nbad += k; nex += bad[:1]
    for u, v, d in H.edges(data=True):
        k, bad = _compare_attrs(eexp[d["edge_id"]], d); ebad += k; nex += bad[:1]
    gml_keys_n = {k for _, d in H.nodes(data=True) for k in d}
    gml_keys_e = {k for _, _, d in H.edges(data=True) for k in d}
    res["graphml"] = {
        "nodes_match": H.number_of_nodes() == G.number_of_nodes(),
        "edges_match": H.number_of_edges() == G.number_of_edges(),
        "node_attributes_checked": n_attr_total,
        "edge_attributes_checked": e_attr_total,
        "attribute_value_mismatches": nbad + ebad,
        "node_columns_missing": sorted(set(ncols) - gml_keys_n),
        "edge_columns_missing": sorted(set(ecols) - gml_keys_e),
        "first_mismatches": nex[:5],
        "length_km_sum_delta": abs(
            sum(float(d["length_km"]) for _, _, d in H.edges(data=True))
            - sum(d["length_km"] for _, _, d in G.edges(data=True))),
        "bytes": (out_dir / graphml).stat().st_size,
    }
    res["graphml"]["exact"] = (
        res["graphml"]["attribute_value_mismatches"] == 0
        and not res["graphml"]["node_columns_missing"]
        and not res["graphml"]["edge_columns_missing"])

    # ---- parquet ---------------------------------------------------------
    ne = pd.read_parquet(out_dir / "edges.parquet")
    nn = pd.read_parquet(out_dir / "nodes.parquet")
    pbad = 0
    for col in [c for c in ecols if c in ne.columns and c != "edge_id"]:
        s = ne.set_index("edge_id")[col]
        for eid, exp in eexp.items():
            if col in exp and not _eq(exp[col], s.get(eid)):
                pbad += 1
    for col in [c for c in ncols if c in nn.columns and c != "node_id"]:
        s = nn.set_index("node_id")[col]
        for nid, exp in nexp.items():
            if col in exp and not _eq(exp[col], s.get(nid)):
                pbad += 1
    res["parquet"] = {
        "nodes_match": len(nn) == G.number_of_nodes(),
        "edges_match": len(ne) == G.number_of_edges(),
        "node_columns_missing": sorted(set(ncols) - set(nn.columns)),
        "edge_columns_missing": sorted(set(ecols) - set(ne.columns)),
        "attribute_value_mismatches": pbad,
        "length_km_sum_delta": abs(ne.length_km.sum()
                                   - sum(d["length_km"] for _, _, d in G.edges(data=True))),
        "bytes": sum((out_dir / f"{x}.parquet").stat().st_size for x in ("nodes", "edges")),
    }
    res["parquet"]["exact"] = (
        pbad == 0 and not res["parquet"]["node_columns_missing"]
        and not res["parquet"]["edge_columns_missing"])

    # ---- GeoJSON ---------------------------------------------------------
    gj = json.loads((out_dir / "edges.geojson").read_text())
    gn = json.loads((out_dir / "nodes.geojson").read_text())
    gbad = 0
    for f in gn["features"]:
        k, _ = _compare_attrs(nexp[f["properties"]["node_id"]], f["properties"]); gbad += k
    for f in gj["features"]:
        k, _ = _compare_attrs(eexp[f["properties"]["edge_id"]], f["properties"]); gbad += k
    no_coord = [n for n, r in nexp.items()
                if "longitude" not in r or "latitude" not in r]
    null_edge = sum(1 for f in gj["features"] if f["geometry"] is None)
    null_node = sum(1 for f in gn["features"] if f["geometry"] is None)
    expected_null_edges = sum(1 for u, v in G.edges()
                              if u in set(no_coord) or v in set(no_coord))
    res["geojson"] = {
        "edge_features": len(gj["features"]),
        "node_features": len(gn["features"]),
        "edges_match": len(gj["features"]) == G.number_of_edges(),
        "nodes_match": len(gn["features"]) == G.number_of_nodes(),
        "edge_features_null_geometry": null_edge,
        "node_features_null_geometry": null_node,
        "null_geometry_fully_accounted": (null_edge == expected_null_edges
                                          and null_node == len(no_coord)),
        "nodes_without_coordinates": no_coord,
        "attribute_value_mismatches": gbad,
        "geometry_source_counts": pd.Series(
            [f["properties"].get("geometry_source") for f in gj["features"]]
        ).value_counts().to_dict(),
        "bytes": sum((out_dir / f"{x}.geojson").stat().st_size for x in ("nodes", "edges")),
    }
    res["geojson"]["exact"] = (
        res["geojson"]["edges_match"] and res["geojson"]["nodes_match"]
        and res["geojson"]["null_geometry_fully_accounted"] and gbad == 0)

    res["all_roundtrip_ok"] = all(res[f]["exact"] for f in ("graphml", "parquet", "geojson"))
    return res


def verify_against_shipped(out_dir: Path | None = None, *,
                           graphml: str = "rail_graph_v1.graphml",
                           length_col: str = "length_km") -> dict:
    """Does the release carry every column and value of the Phase 2 CSVs?

    This is the check Sreehitha's plan (items 2 and 3) amounts to: nothing the
    shipped `nodes.csv` / `edges.csv` provide may be lost on the way to the
    graph artifact. `length_col` names the exported column that must equal the
    CSV's `length_km` -- `length_km` for v1.0, `length_km_v10` for v1.1, whose
    `length_km` is the derived length by design (D-026).
    """
    out_dir = out_dir or C.RELEASE
    n_csv = pd.read_csv(C.DATASET / "nodes.csv")
    e_csv = pd.read_csv(C.DATASET / "edges.csv")
    H = nx.read_graphml(out_dir / graphml)
    ne = pd.read_parquet(out_dir / "edges.parquet")
    nn = pd.read_parquet(out_dir / "nodes.parquet")
    gj = json.loads((out_dir / "edges.geojson").read_text())
    gn = json.loads((out_dir / "nodes.geojson").read_text())
    skip_n = {"node_id", *GRAPH_LEVEL_CONSTANTS}
    skip_e = {"from_node", "to_node", *GRAPH_LEVEL_CONSTANTS}

    out: dict = {"nodes_csv_columns": len(n_csv.columns) - len(skip_n & set(n_csv.columns)),
                 "edges_csv_columns": len(e_csv.columns) - len(skip_e & set(e_csv.columns))}
    for name, keys_n, keys_e in (
            ("graphml", {k for _, d in H.nodes(data=True) for k in d},
                        {k for _, _, d in H.edges(data=True) for k in d}),
            ("parquet", set(nn.columns), set(ne.columns)),
            ("geojson", {k for f in gn["features"] for k in f["properties"]},
                        {k for f in gj["features"] for k in f["properties"]})):
        out[name] = {
            "node_columns_missing": sorted(set(n_csv.columns) - skip_n - keys_n),
            "edge_columns_missing": sorted(set(e_csv.columns) - skip_e - keys_e
                                           - ({"length_km"} if length_col != "length_km" else set())),
        }
    # value equality, edge table (parquet carries the full frame)
    m = e_csv.merge(ne, on="edge_id", suffixes=("_csv", ""))
    diffs = {}
    for c in e_csv.columns:
        if c in skip_e or c == "edge_id":
            continue
        col = length_col if c == "length_km" else c
        if col not in ne.columns:
            continue
        a, b = m[f"{c}_csv"] if f"{c}_csv" in m else m[c], m[col]
        if c == "length_km" and length_col != "length_km":
            a = m["length_km_csv"] if "length_km_csv" in m else m["length_km"]
        both_null = a.isna() & b.isna()
        if a.dtype.kind in "fi" and b.dtype.kind in "fi":
            ok = both_null | ((a - b).abs() <= 1e-9)
        else:
            ok = both_null | (a.astype(str) == b.astype(str))
        if not ok.all():
            diffs[c] = int((~ok).sum())
    out["edge_value_diffs_vs_csv"] = diffs
    mn = n_csv.merge(nn, on="node_id", suffixes=("_csv", ""))
    ndiffs = {}
    for c in n_csv.columns:
        if c in skip_n or c not in nn.columns:
            continue
        a = mn[f"{c}_csv"] if f"{c}_csv" in mn else mn[c]
        b = mn[c]
        both_null = a.isna() & b.isna()
        if a.dtype.kind in "fi" and b.dtype.kind in "fi":
            ok = both_null | ((a - b).abs() <= 1e-9)
        else:
            ok = both_null | (a.astype(str) == b.astype(str))
        if not ok.all():
            ndiffs[c] = int((~ok).sum())
    out["node_value_diffs_vs_csv"] = ndiffs
    out["complete"] = (all(not out[f][k] for f in ("graphml", "parquet", "geojson")
                           for k in ("node_columns_missing", "edge_columns_missing"))
                       and not diffs and not ndiffs)
    return out
