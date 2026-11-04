"""v2.1-open release package (E-726, release.py; copied from test_v2_release.py). Checks the built package."""
import hashlib, json, re, sys, zipfile
from pathlib import Path

import networkx as nx
import pandas as pd
import pytest

from conftest import ROOT

_R = ROOT / "03_graph_construction/release"
REL = _R / "rail-intel-v2.1-open" if (_R / "rail-intel-v2.1-open").exists() else _R / "rail-intel-v2.1-open-rc1"
FORBIDDEN = re.compile(r"served_2024|trains_per_day|iitkgp|rstgcn|Kharagpur", re.I)


@pytest.fixture(scope="module")
def pkg():
    assert REL.exists(), "run release.py first"
    return dict(n=pd.read_csv(REL / "graph/nodes.csv", low_memory=False), e=pd.read_csv(REL / "graph/edges.csv"),
                pn=pd.read_csv(REL / "places/nodes.csv", low_memory=False), pe=pd.read_csv(REL / "places/edges.csv"),
                man=json.loads((REL / "manifest.json").read_text()))


def test_manifest_hashes_match_files(pkg):
    for f in pkg["man"]["files"]:
        assert hashlib.sha256((REL / f["path"]).read_bytes()).hexdigest() == f["sha256"], f["path"]
    sums = dict(l.split("  ", 1)[::-1] for l in (REL / "SHA256SUMS").read_text().splitlines())
    assert sums["manifest.json"] == hashlib.sha256((REL / "manifest.json").read_bytes()).hexdigest()


def test_nothing_derived_from_the_2024_data(pkg):
    strict = re.compile(r"served_2024|trains_per_day|iitkgp|rstgcn", re.I)   # 'Kharagpur' is also a station
    for p in REL.rglob("*"):
        if p.is_file() and p.suffix in (".csv", ".json") and p.name != "manifest.json":   # the manifest names the columns left out
            assert not strict.search(p.read_text(encoding="utf-8")), p.name
    for k in ("n", "e", "pn", "pe"):
        assert not [c for c in pkg[k].columns if FORBIDDEN.search(c)]
    assert "served_2024" not in pkg["n"] and "line_status" not in pkg["n"]


def test_graph_integrity(pkg):
    n, e = pkg["n"], pkg["e"]
    ids = set(n.node_id)
    assert n.node_id.is_unique and e.edge_id.is_unique
    assert e.from_node.isin(ids).all() and e.to_node.isin(ids).all()
    assert (e.length_km > 0).all() and not e.length_km.isna().any()
    assert set(e.length_source) <= {"osm_track", "timetable_2017"}
    assert pkg["pn"].node_id.isin(ids).all()
    assert n.place_id.dropna().isin(set(pkg["pn"].node_id)).all()


def test_golden_figures(pkg):
    """Key figures of v2.1 (D-074). A change here is a change to the dataset and needs a recorded reason."""
    n, e, pn, pe = pkg["n"], pkg["e"], pkg["pn"], pkg["pe"]
    f = pkg["man"]["figures"]
    assert (len(n), len(e)) == (11809, 13051) and (f["stations"], f["junctions"]) == (9507, 2302)
    assert round(e.length_km.sum(), 1) == 69200.7
    assert (len(pn), len(pe)) == (9924, 10336) and f["place_cycles"] == 420
    assert e.edge_id.str.startswith("v2.1:").all()
    G = nx.Graph(); G.add_nodes_from(n.node_id); G.add_edges_from(zip(e.from_node, e.to_node))
    assert nx.number_connected_components(G) == 8


def test_zip_matches_directory_and_is_deterministic():
    z = REL.parent / f"{REL.name}.zip"
    with zipfile.ZipFile(z) as zf:
        names = sorted(i.filename for i in zf.infolist())
        assert all(i.date_time == (2026, 1, 1, 0, 0, 0) for i in zf.infolist())
        for i in zf.infolist():
            assert zf.read(i) == (REL.parent / i.filename).read_bytes()
    assert names == sorted(f"{REL.name}/{p.relative_to(REL).as_posix()}" for p in REL.rglob("*") if p.is_file())


def test_licence_files_present():
    for fn in ("LICENSE", "ATTRIBUTION.md", "DATASHEET.md", "README.md"):
        assert (REL / fn).stat().st_size > 200
    t = (REL / "ATTRIBUTION.md").read_text()
    for s in ("OpenStreetMap", "Wikidata", "datameet", "data.gov.in"):
        assert s in t


# --- the three v2.1 fixes (D-071), each on its named case
def _G(pkg):
    G = nx.Graph()
    for u, v, km in zip(pkg["e"].from_node, pkg["e"].to_node, pkg["e"].length_km): G.add_edge(u, v, km=km)
    return G


@pytest.mark.parametrize("a,b,max_km", [("CSMT", "MSD", 1.5), ("JND", "TORA", 20), ("MJ", "MRWS", 20), ("SPN", "SZN", 5)])
def test_v2_26_station_links_restored(pkg, a, b, max_km):
    """v2.0: 14.2, 181.2, 524.1 and 208.4 km."""
    assert nx.shortest_path_length(_G(pkg), a, b, weight="km") <= max_km


def test_v2_27_through_stations_on_the_line(pkg):
    G = _G(pkg)
    through = ["MSD", "MDP", "BTNR", "BHS", "CRP", "SZM", "TMR", "CPT", "MKG", "DIG", "KGP", "RJT"]
    assert all(G.degree(s) >= 2 for s in through), [s for s in through if G.degree(s) < 2]


@pytest.mark.parametrize("code", ["MMCT", "DDU", "PRYJ", "MBDP", "PRRB"])
def test_v2_28_renamed_stations_carry_2017_trains(pkg, code):
    e = pkg["e"]
    assert e[(e.from_node == code) | (e.to_node == code)].trains_2017.max() > 0


def test_v2_28_crosswalk_aliases():
    cw = pd.read_csv(REL / "graph/station_code_crosswalk.csv")
    al = dict(zip(cw.code, cw.graph_node))
    assert al["BCT"] == "MMCT" and al["MGS"] == "DDU" and al["ALD"] == "PRYJ"
    assert not {"BRY", "SLTP"} & set(al)      # rejected in E-723
