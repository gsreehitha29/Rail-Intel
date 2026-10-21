"""The gates and the manifest. A drifted release must not be able to ship quietly."""
import hashlib

import pytest

from conftest import GRAPH_DIR, ROOT


def test_all_gates_passed(gates):
    failed = [k for k, v in gates["gates"].items() if not v]
    assert gates["all_passed"] is True, f"gates not met: {failed}"


def test_each_measured_value_still_meets_its_threshold(gates):
    """Restated independently of the build, so a bug in the gate logic cannot hide
    a drifted measurement."""
    m, t = gates["measured"], gates["thresholds"]
    assert m["edges_below_straight_line"] <= t["max_edges_below_straight_line"]
    assert m["edges_without_length"] == 0
    assert m["referential_integrity"] is True
    assert m["components"] <= t["max_components"]
    assert m["giant_share"] >= t["min_giant_share"]
    assert m["route_2024_within_5pct"] >= t["min_route_2024_within_5pct"]
    assert m["route_2024_median_err"] <= t["max_route_2024_median_err"]
    assert m["route_2024_unroutable"] <= t["max_unroutable_2024"]
    assert m["irn_within_5pct"] >= t["min_irn_within_5pct"]
    assert m["off_spine_detour_km"] <= t["max_off_spine_detour_km"]


def test_independent_reference_was_never_used_in_construction(gates):
    """The 2024 timetable and the IIT KGP distances are the external test set. Both
    must still be reported, or the validation claim is unsupported."""
    for k in ("route_2024_within_5pct", "irn_within_5pct", "route_2017_within_5pct"):
        assert gates["measured"].get(k) is not None


def test_manifest_hashes_match_the_files_on_disk(manifest):
    """Catches a release file edited by hand after the build - which D-054 forbids."""
    bad = []
    for rel, meta in manifest["files"].items():
        if not meta.get("byte_reproducible"):
            continue
        p = GRAPH_DIR.parent / rel if not (GRAPH_DIR / rel).exists() else GRAPH_DIR / rel
        if not p.exists():
            bad.append((rel, "missing"))
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h != meta["sha256"]:
            bad.append((rel, "hash differs"))
    assert bad == [], f"release files changed since the build: {bad}"


def test_manifest_is_scoped_to_the_release(manifest):
    """It hashed the whole construction directory once. 14 files, not 146."""
    assert 1 <= len(manifest["files"]) <= 40


def test_parquet_is_flagged_as_not_byte_reproducible(manifest):
    """Arrow embeds its writer version, so parquet differs across machines. CSV is
    canonical. If this starts passing, the flag logic has broken."""
    pq = [k for k in manifest["files"] if k.endswith(".parquet")]
    assert pq, "no parquet in the manifest"
    assert all(not manifest["files"][k].get("byte_reproducible") for k in pq)
