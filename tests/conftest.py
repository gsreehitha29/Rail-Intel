"""Shared fixtures. Tests run from the repo root: `make test` or `pytest -q`."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "03_graph_construction"))

RELEASE = "v1_4"
GRAPH_DIR = ROOT / "03_graph_construction" / f"graph_{RELEASE}"
E709 = ROOT / "04_analysis_modules" / "E-709_severance_criticality" / "out"


@pytest.fixture(scope="session")
def root():
    return ROOT


@pytest.fixture(scope="session")
def golden():
    return json.loads((Path(__file__).parent / "golden.json").read_text())


@pytest.fixture(scope="session")
def gates():
    return json.loads((GRAPH_DIR / "gates.json").read_text())


@pytest.fixture(scope="session")
def manifest():
    return json.loads((GRAPH_DIR / f"graph_{RELEASE}.manifest.json").read_text())


@pytest.fixture(scope="session")
def G():
    from railgraph.release import load_graph
    return load_graph(root=ROOT)
