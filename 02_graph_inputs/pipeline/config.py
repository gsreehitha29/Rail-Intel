"""
Shared configuration and helpers for the Rail-Intell graph-input pipeline.

This module is the single source of truth for paths, normalisation rules and
geodesic helpers. Every pipeline stage imports from here so that the same rule
is never re-implemented twice (the root cause of the conflicting corridor
counts found during validation).
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

# Repo layout (as of the 2026-09-29 reorganization):
#   <repo_root>/
#     01_data_engineering/            raw sources + processed_data + notebooks
#     02_graph_inputs/                this phase: pipeline/ + graph_inputs/
# pipeline/config.py lives at <repo_root>/02_graph_inputs/pipeline/config.py
PHASE_DIR = Path(__file__).resolve().parent.parent          # .../02_graph_inputs
REPO_ROOT = PHASE_DIR.parent                                 # repo root
DATA_ENG_DIR = REPO_ROOT / "01_data_engineering"

RAW_NETWORK_CSV = DATA_ENG_DIR / "Railway_Network_.csv"
RAW_NETWORK_GEOJSON = DATA_ENG_DIR / "Railway_Network_.geojson"
CLEANED_STATIONS = DATA_ENG_DIR / "processed_data" / "cleaned_stations.csv"
CLEANED_SCHEDULES = DATA_ENG_DIR / "processed_data" / "cleaned_schedules.csv"
CLEANED_TRAINS = DATA_ENG_DIR / "processed_data" / "cleaned_trains.csv"

OUT_DIR = PHASE_DIR / "graph_inputs"
CACHE_DIR = Path(__file__).resolve().parent / "cache"

OUT_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# Dataset version stamped into every output file.
GRAPH_INPUT_VERSION = "v1.0"

# --------------------------------------------------------------------------
# Provenance / vintage of each source (required by the project blueprint)
# --------------------------------------------------------------------------

SOURCE_VINTAGE = {
    "Railway_Network_.csv": "Indian railway GIS segment export (vintage not stated in source)",
    "Railway_Network_.geojson": "Geometry for the same GIS segment export",
    "railways-master/stations.json": "Community station master (via cleaned_stations.csv)",
    "railways-master/trains.json": "Community train metadata (via cleaned_trains.csv)",
    "railways-master/schedules.json": "Community schedule data (via cleaned_schedules.csv)",
}

# --------------------------------------------------------------------------
# Name normalisation
# --------------------------------------------------------------------------

def normalize_junction_name(value) -> str:
    """Canonical form of a raw GIS junction name.

    Deliberately identical in behaviour to `normalize_junction_name` in
    Railway_networks_EDA.ipynb (cell 143) so that canonical names stay
    comparable with the existing EDA work. The difference here is that this
    pipeline actually *groups on* the canonical name, rather than computing it
    only as a diagnostic afterwards.
    """
    if value is None:
        return ""
    s = str(value)
    if s.strip().lower() in {"nan", "none", ""}:
        return ""
    # Carriage returns / newlines embedded in the raw source become spaces.
    s = s.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    # Non-breaking and other unicode spaces.
    s = s.replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    # Punctuation spacing.
    s = re.sub(r"\s+([.,)])", r"\1", s)
    s = re.sub(r"([(])\s+", r"\1", s)
    return s


def match_key(value) -> str:
    """Aggressive key used ONLY for name matching between junctions and the
    station master. Never used as an identifier or written out as a name."""
    s = normalize_junction_name(value).upper()
    s = s.replace(".", "").replace(",", "").replace("'", "")
    s = re.sub(r"[^A-Z0-9 ()]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Suffixes stripped only for the fuzzy/relaxed matching tier.
RELAXED_SUFFIXES = [
    "JUNCTION", "JN", "HALT", "CABIN", "BLOCK HUT", "BLOCK HUT A", "YARD",
    "BYPASS", "CHORD", "OUTER CABIN", "NORTH CABIN", "SOUTH CABIN",
    "EAST CABIN", "WEST CABIN", "CENTRAL", "CITY", "TOWN", "NG", "BG", "MG",
]


def relaxed_key(value) -> str:
    """Match key with common railway suffixes removed."""
    s = match_key(value)
    changed = True
    while changed:
        changed = False
        for suf in sorted(RELAXED_SUFFIXES, key=len, reverse=True):
            if s.endswith(" " + suf):
                s = s[: -(len(suf) + 1)].strip()
                changed = True
    return s


# --------------------------------------------------------------------------
# Controlled vocabularies
# --------------------------------------------------------------------------
# The GIS layer spells zones out in full (with four typos); the station and
# train masters use abbreviations. Neither could be joined to the other. Both
# are mapped onto one canonical pair (zone_code, zone_name) here, so node and
# edge attributes finally speak the same language.

ZONE_NAME = {
    "CR":   "Central Railway",
    "ECR":  "East Central Railway",
    "ECoR": "East Coast Railway",
    "ER":   "Eastern Railway",
    "KR":   "Konkan Railway",
    "NCR":  "North Central Railway",
    "NER":  "North Eastern Railway",
    "NFR":  "Northeast Frontier Railway",
    "NR":   "Northern Railway",
    "NWR":  "North Western Railway",
    "SCR":  "South Central Railway",
    "SECR": "South East Central Railway",
    "SER":  "South Eastern Railway",
    "SR":   "Southern Railway",
    "SWR":  "South Western Railway",
    "WCR":  "West Central Railway",
    "WR":   "Western Railway",
}

# Every spelling observed in any source, mapped to its canonical code.
# The four misspellings are from Railway_Network_.csv and are corrected here
# rather than in the raw file, so the raw source stays untouched.
_ZONE_ALIASES = {
    "east coast railwa":          "ECoR",   # typo, 1 corridor
    "southen railway":            "SR",     # typo, 3 corridors
    "westem railway":             "WR",     # typo, 1 corridor
    "north frontier railway":     "NFR",    # 121 corridors; the real zone is
    "northeast frontier railway": "NFR",    # Northeast Frontier Railway
}

_ZONE_LOOKUP = {}
for _code, _name in ZONE_NAME.items():
    _ZONE_LOOKUP[_code.lower()] = _code
    _ZONE_LOOKUP[_name.lower()] = _code
_ZONE_LOOKUP.update(_ZONE_ALIASES)

# Values that mean "not recorded" but are written as if they were data.
NULL_TOKENS = {"", "?", "-", "na", "n/a", "none", "null", "nan", "unknown"}


def zone_code(value):
    """Canonical zone abbreviation (e.g. 'SCR') from any observed spelling.

    Returns None for missing values and for the '?' sentinel used in the
    station and train masters.
    """
    if value is None:
        return None
    s = str(value).replace("\xa0", " ").strip()
    if s.lower() in NULL_TOKENS:
        return None
    return _ZONE_LOOKUP.get(s.lower())


def zone_name(value):
    """Canonical full zone name from any observed spelling."""
    c = zone_code(value)
    return ZONE_NAME.get(c) if c else None


GAUGE_CODE = {
    "broad gauge": "BG", "metre gauge": "MG", "meter gauge": "MG",
    "narrow gauge": "NG", "standard gauge": "SG",
}


def gauge_code(value):
    """Canonical gauge abbreviation, or None when not recorded."""
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in NULL_TOKENS:
        return None
    return GAUGE_CODE.get(s.lower())


# State names that appear under more than one spelling in the station master.
_STATE_ALIASES = {"orissa": "Odisha"}

# Territory outside the Indian rail network's scope; retained in the station
# master but flagged so it never silently enters a national analysis.
OUT_OF_SCOPE_STATES = {"Bangladesh"}


def normalize_state(value):
    """Canonical state name, or None when not recorded."""
    if value is None:
        return None
    s = str(value).replace("\xa0", " ").strip()
    if s.lower() in NULL_TOKENS:
        return None
    return _STATE_ALIASES.get(s.lower(), s)


def clean_token(value):
    """Strip a free-text field and map sentinel values to None."""
    if value is None:
        return None
    s = str(value).replace("\xa0", " ").strip()
    return None if s.lower() in NULL_TOKENS else s


# --------------------------------------------------------------------------
# Junction classification
# --------------------------------------------------------------------------

OPERATIONAL_PATTERNS = [
    (r"\bCABIN\b", "cabin"),
    (r"\bBLOCK HUT\b", "block_hut"),
    (r"\bYARD\b", "yard"),
    (r"\bBYPASS\b", "bypass"),
    (r"\bCHORD\b", "chord"),
    (r"\bSIDING\b", "siding"),
    (r"\bGOODS\b", "goods"),
    (r"\bLOCO\b", "loco"),
    (r"\bGATE\b", "gate"),
    (r"\bBRIDGE\b(?!.*\bJUNCTION\b)", "bridge"),
]


def classify_junction(name: str) -> str:
    """Split junction names into classes.

    Operational infrastructure (cabins, block huts, yards, bypasses, chords)
    is NOT expected to appear in a passenger station master, so failing to
    match one is not a data-quality failure. Everything else is treated as
    station-like and a missing match IS a gap worth resolving.
    """
    key = match_key(name)
    for pattern, label in OPERATIONAL_PATTERNS:
        if re.search(pattern, key):
            return label
    return "station_like"


# --------------------------------------------------------------------------
# Geodesy
# --------------------------------------------------------------------------

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lon1, lat1, lon2, lat2):
    """Vectorised great-circle distance in kilometres (WGS84 sphere)."""
    lon1, lat1, lon2, lat2 = map(
        lambda a: np.radians(np.asarray(a, dtype=float)), (lon1, lat1, lon2, lat2)
    )
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


# Local equirectangular projection anchored on India. Used only for building
# KD-trees and for linear referencing, where a locally-accurate planar
# approximation is sufficient and far cheaper than a full CRS transform.
INDIA_LAT0 = 22.0

def to_local_xy(lon, lat):
    """Project lon/lat (degrees) to approximate local kilometres."""
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    x = np.radians(lon) * EARTH_RADIUS_KM * np.cos(np.radians(INDIA_LAT0))
    y = np.radians(lat) * EARTH_RADIUS_KM
    return x, y


COORD_PRECISION = 6  # decimal places used to snap geometry endpoints together


def coord_key(lon, lat):
    return (round(float(lon), COORD_PRECISION), round(float(lat), COORD_PRECISION))


def banner(title: str) -> None:
    print("=" * 78)
    print(title)
    print("=" * 78)
