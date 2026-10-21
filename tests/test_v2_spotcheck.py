"""Independent spot-checks of the release package (E-716 P3): stations everyone knows, real trains'
own timetable distances, and scans for the kind of fault a gate would not catch."""
import networkx as nx
import pandas as pd
import pytest

from conftest import ROOT

_R = ROOT / "03_graph_construction/release"
REL = _R / "rail-intel-v2.0-open" if (_R / "rail-intel-v2.0-open").exists() else _R / "rail-intel-v2.0-open-rc1"
TT = ROOT / "external_data/timetable_2017_datagovin/Train_details_22122017.csv"

STATIONS = {  # code: (part of name, state starts with)
    "NDLS": ("new delhi", "delhi"), "CSMT": ("csmt", "maharashtra"), "HWH": ("howrah", "west bengal"),
    "SBC": ("bengaluru", "karnataka"), "SC": ("secunderabad", "telangana"), "BZA": ("vijayawada", "andhra"),
    "PUNE": ("pune", "maharashtra"), "JP": ("jaipur", "rajasthan"), "LKO": ("lucknow", "uttar pradesh"),
    "BPL": ("bhopal", "madhya pradesh"), "NGP": ("nagpur", "maharashtra"), "ADI": ("ahmedabad", "gujarat"),
    "PNBE": ("patna", "bihar"), "GHY": ("guwahati", "assam"), "TVC": ("thiruvananthapuram", "kerala"),
    "ERS": ("ernakulam", "kerala"), "KYQ": ("kamakhya", "assam"), "JAT": ("jammu", "jammu"),
    "ASR": ("amritsar", "punjab"), "CDG": ("chandigarh", "chandigarh"), "BBS": ("bhubaneswar", "odisha"),
    "RNC": ("ranchi", "jharkhand"), "R": ("raipur", "chhattisgarh"), "DDN": ("dehradun", "uttarakhand"),
    "MAO": ("madgaon", "goa"), "VSKP": ("visakhapatnam", "andhra"), "CAPE": ("kanniyakumari", "tamil nadu"),
    "SHM": ("shalimar", "west bengal"), "DBRG": ("dibrugarh", "assam"), "NJP": ("new jalpaiguri", "west bengal"),
    "SML": ("shimla", "himachal"), "MAS": ("central", "tamil nadu")}
# real trains: the graph's length along the train's stops against the timetable's
TRAINS = ["12004", "12009", "12015", "12123", "12301", "12603", "12625", "12627", "12659", "12839", "12842", "12951", "16525"]


@pytest.fixture(scope="module")
def g():
    n = pd.read_csv(REL / "graph/nodes.csv", low_memory=False); e = pd.read_csv(REL / "graph/edges.csv")
    G = nx.Graph(); G.add_weighted_edges_from(zip(e.from_node, e.to_node, e.length_km), weight="km")
    return n, e, G


def test_well_known_stations(g):
    n, _, _ = g
    s = n[n.station_code.notna()].set_index("station_code")
    bad = []
    for c, (nm, st) in STATIONS.items():
        if c not in s.index: bad.append((c, "missing")); continue
        r = s.loc[c]
        if nm not in str(r.node_name).lower() or not str(r.state).lower().startswith(st): bad.append((c, r.node_name, r.state))
    assert not bad, bad


@pytest.mark.skipif(not TT.exists(), reason="2017 timetable not on this machine")
def test_real_trains_follow_their_timetable_distance(g):
    n, _, G = g
    t = pd.read_csv(TT, dtype=str); t["c"] = t["Station Code"].str.strip()
    t["d"] = pd.to_numeric(t.Distance, errors="coerce"); t["q"] = pd.to_numeric(t.SEQ, errors="coerce")
    codes = set(n.station_code.dropna()); bad = []
    for tr in TRAINS:
        x = t[t["Train No"] == tr].sort_values("q"); st = [c for c in x.c if c in codes]; d = dict(zip(x.c, x.d))
        tot = sum(nx.shortest_path_length(G, a, b, weight="km") for a, b in zip(st, st[1:]))
        ref = sum(d[b] - d[a] for a, b in zip(st, st[1:]))
        if abs(tot / ref - 1) > 0.03: bad.append((tr, round(tot), round(ref)))
    assert not bad, bad


def test_scans_for_faults_gates_miss(g):
    n, e, _ = g
    s = n[n.node_type == "station"]
    assert not ((s.latitude < 6) | (s.latitude > 37.5) | (s.longitude < 67) | (s.longitude > 98)).any()
    assert not s.station_code.dropna().duplicated().any()
    assert not s.duplicated(["node_name", "longitude", "latitude"]).any()
    assert s.node_name.isna().sum() <= 20
    assert e.length_km.max() < 90 and e.length_km.min() > 0
    # a section far longer than its straight line is a spiral or loop, which is real only in the hills
    odd = e[(e.length_km > 3 * e.length_chord_km) & (e.length_km > 5)]
    assert len(odd) <= 5 and odd.line_name.fillna("").str.contains("Himalayan|Shimla|Tunnel").all(), odd
    assert (e.length_km < e.length_chord_km - 0.2).sum() <= 12
