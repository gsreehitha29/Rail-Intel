"""E-716 P3 - package graph v2.0-open as a release (D-060, D-067).

    python release.py [repo root] [--version=v2.0-open-rc1]

Reads the working build (graph_v2_0_open/, service_layer_v2_0_open/open_2017/) and writes
03_graph_construction/release/rail-intel-<version>/ and a zip of it. Only open inputs reach
the package: OpenStreetMap (ODbL), Wikidata (CC0), datameet state boundaries (CC BY 4.0)
and the data.gov.in 2017 timetable (GODL-India). Columns derived from the 2024 IIT Kharagpur
data (no licence stated) are left out. The package is byte-reproducible: rows and files
are sorted, floats are fixed, the zip carries fixed dates.
"""
import hashlib, json, re, sys, zipfile
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ZIP_DATE = (2026, 1, 1, 0, 0, 0)

NODE_COLS = ["node_id", "node_type", "node_name", "station_code", "longitude", "latitude", "coordinate_source",
             "track_lon", "track_lat", "state", "osm_node_id", "place_id", "degree", "component_id", "in_giant",
             "scheduled_2017"]
EDGE_COLS = ["edge_id", "from_node", "to_node", "length_km", "length_source", "length_chord_km", "gauge_code",
             "gauge_tag_share", "electrified", "electrified_tag_share", "line_name", "joins", "scheduled_2017",
             "trains_2017"]
PLACE_NODE_COLS = ["node_id", "node_type", "node_name", "station_code", "longitude", "latitude", "state",
                   "junctions_in_place", "degree", "component_id", "in_giant"]
PLACE_EDGE_COLS = ["edge_id", "from_node", "to_node", "length_km", "joins"]
DROPPED = {"zone_code": "no open source for railway zones (V2-14)",
           "served_2024": "derived from the 2024 IIT Kharagpur data, which has no stated licence (D-067)",
           "line_status": "combines the 2024 and 2017 service data; the release keeps scheduled_2017 (D-067)",
           "state_source": "one value for every node; stated in the datasheet",
           "length_is_lower_bound": "false for every section: no straight-line lengths in v2.0",
           "origin": "osm for every section",
           "dataset_version": "the version is the package's name"}
BUILD_CODE = ["geo.py", "osm_build.py", "release.py", "release_docs.py", "run_c1.py", "run_c2.py", "service17.py", "validate_c3.py"]
FORBIDDEN = re.compile(r"2024|served_2024|trains_per_day|iitkgp|rstgcn", re.I)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_csv(df: pd.DataFrame, p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, lineterminator="\n", float_format="%.7g")


def osm_id(x):
    return None if pd.isna(x) else str(int(x))


def tables(root: Path):
    g = root / "03_graph_construction/graph_v2_0_open"
    sv = root / "03_graph_construction/service_layer_v2_0_open/open_2017"
    n = pd.read_csv(g / "open/nodes.csv", low_memory=False)
    e = pd.read_csv(g / "open/edges.csv")
    pn = pd.read_csv(g / "open/places/nodes.csv", low_memory=False)
    pe = pd.read_csv(g / "open/places/edges.csv")
    es = pd.read_csv(sv / "edge_service.csv")
    sd = pd.read_csv(sv / "service_edges_directed.csv")
    cw = pd.read_csv(g / "station_code_crosswalk.csv")
    rep2 = json.loads((g / "work/c2_report.json").read_text())
    rep3 = json.loads((g / "work/c3_report.json").read_text())

    n = n.copy()
    n["osm_node_id"] = n.osm_node_id.map(osm_id)
    nodes = n[NODE_COLS].sort_values("node_id").reset_index(drop=True)
    e = e.merge(es.rename(columns={"distinct_trains_2017": "trains_2017"}), on="edge_id", how="left", validate="1:1")
    assert e.trains_2017.notna().all()
    e["trains_2017"] = e.trains_2017.astype(int)
    e["length_source"] = e.length_source.replace({"timetable": "timetable_2017"})   # D-068: 2017 only
    edges = e[EDGE_COLS].sort_values("edge_id").reset_index(drop=True)
    st = n.set_index("node_id").state
    pn = pn.copy(); pn["state"] = pn.node_id.map(st)
    pnodes = pn[PLACE_NODE_COLS].sort_values("node_id").reset_index(drop=True)
    pedges = pe[PLACE_EDGE_COLS].sort_values("edge_id").reset_index(drop=True)
    pairs = sd.rename(columns={"physical_path_km": "path_km", "physical_hops": "path_sections"})
    pairs["path_sections"] = pairs.path_sections.astype("Int64")
    pairs = pairs.sort_values(["from_station", "to_station"]).reset_index(drop=True)
    cw = cw.sort_values("code").reset_index(drop=True)

    j = pd.read_csv(g / "work/c2_joins.csv")
    joins = j[["stage", "a", "b", "km", "stations_joined", "example", "evidence"]].rename(
        columns={"a": "main_side", "b": "piece_side", "example": "example_station"})
    th = pd.read_csv(g / "work/c2_throat_links.csv").rename(columns={"a": "vertex_a", "b": "vertex_b"})
    th["osm_a"] = th.osm_a.map(osm_id); th["osm_b"] = th.osm_b.map(osm_id)
    wd = pd.read_csv(g / "work/c2_wikidata_placement.csv")
    wd = wd[["code", "item", "itemLabel", "lon", "lat", "fate", "nearest_osm_station_m", "nearest_track_m"]].rename(
        columns={"item": "wikidata_item", "itemLabel": "wikidata_label"}).sort_values("code").reset_index(drop=True)
    cf = pd.DataFrame(sorted(rep2["conflicts_resolved"].items()), columns=["code", "resolution"])
    prov = dict(joins=joins, throat_links=th.sort_values(["vertex_a", "vertex_b"]).reset_index(drop=True),
                wikidata_placements=wd, code_conflicts=cf)
    return dict(nodes=nodes, edges=edges, pnodes=pnodes, pedges=pedges, pairs=pairs, cw=cw, prov=prov,
                rep2=rep2, rep3=rep3)


def figures(t) -> dict:
    """The figures the datasheet quotes, computed from the package tables themselves."""
    n, e, pn, pe = t["nodes"], t["edges"], t["pnodes"], t["pedges"]
    G = nx.Graph(); G.add_nodes_from(n.node_id); G.add_edges_from(zip(e.from_node, e.to_node))
    P = nx.Graph(); P.add_nodes_from(pn.node_id); P.add_edges_from(zip(pe.from_node, pe.to_node))
    s = n[n.node_type == "station"]
    comp = nx.number_connected_components(G)
    km = float(e.length_km.sum())
    giant = max(nx.connected_components(G), key=len)
    r3 = t["rep3"]; g3 = r3["e708_gates"]["v2"]; g1 = r3["e708_gates"]["v141"]
    return dict(
        nodes=len(n), stations=len(s), junctions=int((n.node_type == "junction").sum()), edges=len(e),
        route_km=round(km, 1), route_km_vs_official=round(100 * (km / 69439 - 1), 1), components=comp,
        giant_share=round(100 * len(giant) / len(n), 2), cycles=len(e) - len(n) + comp,
        stations_coded=int(s.station_code.notna().sum()), stations_uncoded=int(s.node_id.str.startswith("OSM:").sum()),
        stations_conflict=int(s.node_id.str.contains("~").sum()), stations_isolated=int((s.degree == 0).sum()),
        stations_wikidata=int((s.coordinate_source == "wikidata").sum()),
        stations_in_main=round(100 * len(giant & set(s.node_id)) / len(s), 2),
        stations_2017=int(s.scheduled_2017.sum()), edges_2017=int(e.scheduled_2017.sum()),
        km_2017=round(100 * float(e.length_km[e.scheduled_2017].sum()) / km, 1),
        km_no_2017=round(100 - 100 * float(e.length_km[e.scheduled_2017].sum()) / km, 1),
        states=int(n.state.notna().sum()), states_share=round(100 * n.state.notna().mean(), 2),
        gauge_known=round(100 * float(e.length_km[e.gauge_code.notna()].sum()) / km, 1),
        elec_known=round(100 * float(e.length_km[e.electrified.isin(["yes", "no"])].sum()) / km, 1),
        throats=int((e.joins.fillna("").str.contains("throat")).sum()),
        timetable_lengths=int((e.length_source == "timetable_2017").sum()),
        timetable_km=round(float(e.length_km[e.length_source == "timetable_2017"].sum()), 1),
        joins=len(t["prov"]["joins"]), crosswalk=len(t["cw"]),
        place_nodes=len(pn), place_stations=int((pn.node_type == "station").sum()),
        place_junctions=int((pn.node_type == "junction").sum()), place_edges=len(pe),
        place_cycles=len(pe) - len(pn) + nx.number_connected_components(P),
        max_station_degree_places=int(pn.degree[pn.node_type == "station"].max()),
        pairs_2017=len(t["pairs"]), pairs_2017_unroutable=int(t["pairs"].path_km.isna().sum()),
        trains_2017=int(t["rep2"]["O6_2017"]["trains"]),
        irn=round(100 * g3["irn_within_5pct"], 1), irn_v14=round(100 * g1["irn_within_5pct"], 1),
        route_med=round(100 * g3["route_2024_median_err"], 2), route_med_v14=round(100 * g1["route_2024_median_err"], 2),
        route5=round(100 * g3["route_2024_within_5pct"], 1), route5_v14=round(100 * g1["route_2024_within_5pct"], 1),
        route17_med=round(100 * g3["route_2017_median_err"], 2), route17_unroutable=int(g3["route_2017_unroutable"]),
        e715=round(100 * r3["lengths"]["e715_pairs"]["v2"]["within_5pct"], 1),
        e715_v14=round(100 * r3["lengths"]["e715_pairs"]["v141"]["within_5pct"], 1),
        cut_agree=round(100 * r3["served_cut_point_differences"]["agreement"], 1),
        osm_date="2026-10-03 20:20 UTC")


def check(t):
    """Release rules: no 2024-derived column, every section measured on track, integrity."""
    for k in ("nodes", "edges", "pnodes", "pedges", "pairs", "cw"):
        bad = [c for c in t[k].columns if FORBIDDEN.search(c)]
        assert not bad, (k, bad)
    for k, df in t["prov"].items():
        bad = [c for c in df.columns if FORBIDDEN.search(c)]
        txt = df.astype(str).apply(lambda col: col.str.contains(r"(?<![\d.])2024(?![\d.])|Kharagpur|RSTGCN")).to_numpy().any()
        assert not bad and not txt, k
    n, e = t["nodes"], t["edges"]
    ids = set(n.node_id)
    assert n.node_id.is_unique and e.edge_id.is_unique
    assert e.from_node.isin(ids).all() and e.to_node.isin(ids).all()
    assert (e.length_km > 0).all() and set(e.length_source) <= {"osm_track", "timetable_2017"}
    assert (e.joins[e.length_source == "timetable_2017"] == "join_C").all()
    assert set(t["pnodes"].node_id) <= ids
    assert n.place_id.dropna().isin(set(t["pnodes"].node_id)).all()
    assert t["cw"].graph_node.isin(ids).all()


def build(root: Path, version: str, docs: dict, date: str = "2026-10-21") -> Path:
    import time; t0 = time.time()
    t = tables(root); check(t); f = figures(t)
    name = f"rail-intel-{version}"
    out = root / "03_graph_construction/release" / name
    out.mkdir(parents=True, exist_ok=True)
    write_csv(t["nodes"], out / "graph/nodes.csv"); write_csv(t["edges"], out / "graph/edges.csv")
    write_csv(t["cw"], out / "graph/station_code_crosswalk.csv")
    write_csv(t["pnodes"], out / "places/nodes.csv"); write_csv(t["pedges"], out / "places/edges.csv")
    write_csv(t["pairs"], out / "service_2017/station_pairs.csv")
    for k, df in t["prov"].items():
        write_csv(df, out / f"provenance/{k}.csv")
    f["version"] = version; f["date"] = date
    f["status"] = ("A release candidate: figures may change before the final lock." if "rc" in version
                   else "Final release: the files and their hashes are fixed (see manifest.json and SHA256SUMS).")
    for fn, text in docs.items():
        (out / fn).write_text(text.format(**f).rstrip() + "\n", encoding="utf-8", newline="\n")
    # files are overwritten in place (a connected folder may not allow deletes); a leftover
    # from an earlier layout would be hashed into the manifest, so refuse
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name not in ("manifest.json", "SHA256SUMS"))
    stale = [p.relative_to(out).as_posix() for p in files if p.stat().st_mtime < t0 - 1]
    assert not stale, f"files left from an earlier build, remove them: {stale}"
    man = dict(dataset=name, version=version, licence="ODbL-1.0", figures=f, files=[], inputs=inputs(root),
               build_code={n: sha(HERE / n) for n in BUILD_CODE},
               dropped_columns=DROPPED)
    for p in files:
        rel = p.relative_to(out).as_posix()
        rows = sum(1 for _ in p.open(encoding="utf-8")) - 1 if p.suffix == ".csv" else None
        man["files"].append(dict(path=rel, bytes=p.stat().st_size, rows=rows, sha256=sha(p)))
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n", encoding="utf-8", newline="\n")
    lines = [f"{x['sha256']}  {x['path']}" for x in man["files"]] + [f"{sha(out / 'manifest.json')}  manifest.json"]
    (out / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    z = out.parent / f"{name}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(p for p in out.rglob("*") if p.is_file()):
            zi = zipfile.ZipInfo(f"{name}/{p.relative_to(out).as_posix()}", ZIP_DATE)
            zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = 0o644 << 16
            zf.writestr(zi, p.read_bytes(), compresslevel=9)
    return z


def deposit_metadata(root: Path, version: str, z: Path):
    """Metadata for a Zenodo-style deposit, written beside the zip (not inside it)."""
    man = json.loads((z.parent / z.stem / "manifest.json").read_text())
    f = man["figures"]
    desc = (f"<p>A graph of Indian Railways' running lines built only from open data: {f['stations']:,} stations and "
            f"{f['junctions']:,} junctions joined by {f['edges']:,} track sections ({f['route_km']:,.1f} route km). "
            "Lengths are measured along OpenStreetMap track; gauge, electrification, state and scheduled trains per "
            "section (2017 timetable) are attached. Includes a places view for structural analysis, a record of every join "
            "and decision, and a manifest of hashes. Read DATASHEET.md for what it supports and what it does not.</p>"
            "<p>Derived database of OpenStreetMap, licensed under the ODbL 1.0. Also contains information from Wikidata (CC0), "
            "datameet (CC BY 4.0) and data.gov.in (GODL-India).</p>")
    meta = dict(upload_type="dataset", title=f"Rail-Intel: a station-level graph of the Indian railway network, built from open data ({version})",
                creators=[dict(name="Vinjamuri, Bhuvanesh")], description=desc, version=version, access_right="open",
                license="odc-odbl", publication_date="2026-10-21",
                keywords=["railway network", "Indian Railways", "spatial network", "network science", "OpenStreetMap", "graph dataset"],
                related_identifiers=[dict(relation="isDerivedFrom", identifier="https://www.openstreetmap.org/copyright", scheme="url"),
                                     dict(relation="isDerivedFrom", identifier="https://www.wikidata.org", scheme="url"),
                                     dict(relation="isDerivedFrom", identifier="https://github.com/datameet/maps", scheme="url"),
                                     dict(relation="isDerivedFrom", identifier="https://data.gov.in", scheme="url")],
                notes="Files in the zip: see manifest.json. sha256 of the zip is in deposit_checklist.txt.")
    (z.parent / f"{z.stem}.zenodo.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8", newline="\n")


def inputs(root: Path) -> list:
    m = json.loads((root / "external_data/download_manifest.json").read_text())
    use = re.compile(r"zone-261003\.osm\.pbf|wikidata_stations|Admin2\.(shp|dbf|shx|prj)|india-soi|Train_details_22122017")
    return sorted(({k: x.get(k) for k in ("folder", "file", "url", "sha256", "retrieved_utc")}
                   for x in m if use.search(x["file"])), key=lambda x: x["file"])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    version = next((a[10:] for a in sys.argv[1:] if a.startswith("--version=")), "v2.0-open-rc1")
    root = Path(args[0]) if args else HERE.parents[2]
    sys.path.insert(0, str(HERE)); import release_docs
    z = build(root, version, release_docs.DOCS)
    deposit_metadata(root, version, z)
    print(f"{z}  {z.stat().st_size} bytes  sha256 {sha(z)}")


if __name__ == "__main__":
    main()
