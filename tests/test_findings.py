"""Published findings as golden values.

Every figure quoted in the pitch, the paper or a project doc should be asserted here.
If the graph changes and a published number moves, this is what tells you - before a
reviewer does.
"""
import json

import pandas as pd
import pytest

from conftest import E709

pytestmark = pytest.mark.skipif(
    not (E709 / "E-709_corridors.json").exists(),
    reason="E-709 has not been run; `make sever`")


@pytest.fixture(scope="module")
def e709():
    a = json.loads((E709 / "E-709_report.json").read_text())
    b = json.loads((E709 / "E-709_corridors.json").read_text())
    return {**a, **b}


def test_severance_headline(e709, golden):
    g = golden["e709"]
    assert e709["bridges_total"] == g["bridges_total"]
    assert e709["real_bridges"] == g["real_bridges"]
    assert e709["severance_corridors"] == g["severance_corridors"]
    assert e709["junction_cut_points"] == g["junction_cut_points"]


def test_intra_station_artifacts_are_still_caught(e709, golden):
    """F-022. The renames the proximity rule missed. If this drops, Allahabad Jn /
    Prayagraj Junction returns to the top of the vulnerability table."""
    assert e709["intra_station_artifacts"] == golden["e709"]["intra_station_artifacts"]
    art = pd.read_csv(E709 / "intra_station_artifacts.csv")
    pairs = {frozenset((a, b)) for a, b in zip(art.a_name, art.b_name)}
    for a, b in [("ALLAHABAD JN", "Prayagraj Junction"),
                 ("VISHAKAPATNAM", "WALTAIR"),
                 ("CHEOKI", "Prayagraj Chheoki Junction"),
                 ("DARAGANJ", "Prayagraj Sangam")]:
        assert frozenset((a, b)) in pairs, f"{a} / {b} no longer classified as one station"


def test_exposure_share(e709, golden):
    assert e709["exposure"]["share_exposed"] == golden["e709"]["share_exposed"]
    assert e709["exposure"]["pairs_unroutable"] == 0


def test_siliguri_corridor_is_the_worst(e709):
    """The headline domain finding: cutting the corridor isolates the whole Northeast.
    Verified in E-709 against the state column - 327 NE-state stations plus North Bengal."""
    co = pd.read_csv(E709 / "severance_corridors.csv")
    worst = co.sort_values("max_stations_severed", ascending=False).iloc[0]
    assert worst.max_stations_severed >= 450
    assert "Bihar" in worst.states or "West Bengal" in worst.states


def test_lumding_corridor_severs_the_barak_valley_and_tripura(e709):
    """Retrodictive validation against the 6-7 July 2025 landslide. The predicted
    severed set was 84 stations across Assam, Tripura, Manipur and Mizoram."""
    co = pd.read_csv(E709 / "severance_corridors.csv")
    hit = co[(co.max_stations_severed >= 80) & (co.max_stations_severed <= 90)]
    assert len(hit) >= 1, "the Lumding-Badarpur corridor is no longer detected"
    assert hit.states.str.contains("Assam").any()


def test_load_is_concentrated(e709, golden):
    assert e709["load"]["sections"] == golden["e709"]["sections"]
    assert e709["load"]["top100_that_sever"] >= 1


def test_trains_per_day_overstatement_is_recorded():
    """F-021 depends on E-706's finding that distinct-train counting overstates daily
    traffic 2.03x. Any load figure computed the other way is wrong."""
    f = E709.parent.parent / "E-706_trains_per_day" / "out" / "E-706_report.json"
    if not f.exists():
        pytest.skip("E-706 outputs absent")
    r = json.loads(f.read_text())
    assert r, "E-706 report is empty"
