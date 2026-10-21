"""Graph v1.1 — the provenance and honesty layer.

v1.1 adds no new data source and no new capability. It makes existing
information stop overstating itself, which `E-300` identified as this
project's dominant failure mode. Every column here answers one question:
*how do we know this value?*

Implements `D-025` (station-match defect flag), `D-026` (hybrid length with
`length_source`), `D-027` (granularity markers), `D-029` (`speed_is_fallback`)
and `D-030` (conflict propagation). Specified in
`publication/ATTRIBUTE_ROADMAP.md` §A1, §A2, §C1-C4.

Two deliberate deviations from the ADRs as written, both recorded in
`F-042`/`F-043` rather than applied silently:

1. `D-026` assumed the shipped `length_km` is a haversine chord. It is not.
   Measurement (`F-042`) shows non-stitch edges already carry the along-spine
   measure and stitch edges carry the chord — the shipped graph was already a
   de facto hybrid, built by accident rather than by rule. The hybrid *rule*
   stays exactly as decided; its expected effect does not (+0.55%, not the
   +2.88% the ADR projected from the wrong base).

2. `D-025` says the defect thresholds live in `BuildSpec`. They live in
   `ProvenanceSpec` instead, because adding fields to `BuildSpec` changes
   `spec.hash` and would retire the frozen v1.0 identity `f9adf8ca9042` for a
   layer that is purely additive. The intent of the ADR — thresholds as
   varyable parameters rather than constants, available to the `g05` sweep —
   is preserved.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from . import config as C
from .build import haversine_km

#: Attribute granularity, from `E-300` part 1 (`F-027`). The share is the
#: percentage of corridors in which the attribute is constant; anything in the
#: high nineties is a corridor property being displayed per edge.
GRANULARITY = {
    "gauge_code": "corridor",      # constant within 99.09% of corridors
    "speed_kmph": "corridor",      # 96.62%  -- and a declared maximum (F-036)
    "n_tracks": "corridor",        # 97.09%
    "zone_code": "corridor",       # 96.62%
    "bridge_present": "segment",   # 16.92%  -- genuinely segment-level
    "tunnel_present": "corridor",  # 96.23%
    "length_km": "edge",           # genuinely per-edge (both components)
    "service_load": "edge",
    "service_direct": "edge",
}

#: Corridor conflict flags carried onto edges unchanged (`D-030`).
CONFLICT_COLS = ("speed_kmph_conflict", "gauge_conflict", "no_of_lanes_conflict",
                 "railway_zone_conflict", "any_attribute_conflict")

LENGTH_SOURCES = ("spine", "chord_fallback_offset", "chord_fallback_collapse",
                  "chord_no_spine", "stitch_as_built", "floored", "undefined")


@dataclass(frozen=True)
class ProvenanceSpec:
    """Parameters of the v1.1 layer. Separate from `BuildSpec` — see module docstring.

        length_mode        hybrid | spine | chord | asis   (D-026; `asis` reproduces v1.0)
        offset_trust_km    above this placement offset the spine measure is not
                           trusted and the chord is used instead (D-026)
        deficit_min        station_match_deficit at or above which an edge is
                           eligible for the suspect flag (D-025)
        suspect_len_km     length above which a deficit-carrying edge is suspect
        fallback_speed     the substituted speed whose use `speed_is_fallback`
                           records (D-029); mirrors weights.FALLBACK_SPEED_KMPH
        min_edge_km        length floor, mirrors BuildSpec.min_edge_km
    """

    length_mode: str = "hybrid"
    offset_trust_km: float = 0.25
    deficit_min: int = 3
    suspect_len_km: float = 10.0
    fallback_speed: float = 50.0
    min_edge_km: float = 0.05
    label: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        if self.length_mode not in ("hybrid", "spine", "chord", "asis"):
            raise ValueError("length_mode must be hybrid | spine | chord | asis")
        if self.offset_trust_km <= 0 or self.suspect_len_km <= 0:
            raise ValueError("offset_trust_km and suspect_len_km must be positive")
        if self.deficit_min < 0:
            raise ValueError("deficit_min must be non-negative")

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("label", None)
        d["provenance_version"] = "v1.1"
        return d

    @property
    def hash(self) -> str:
        blob = json.dumps(self.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:12]

    def __str__(self) -> str:
        return self.label or f"prov:{self.hash}"


# --------------------------------------------------------------------------- #
# components
# --------------------------------------------------------------------------- #

def pair_measures(sequences: pd.DataFrame | None = None,
                  offset_max_km: float | None = None) -> pd.DataFrame:
    """Per unordered station pair: along-spine distance and worst placement offset.

    Consecutive placements within one corridor. Where two corridors give the
    same pair, the shortest spine is kept — matching `parallel_policy='shortest'`.

    `offset_max_km` selects eligible placements by the *caller's* tolerance
    instead of the shipped `used_for_edges` column. The `g05` sweep must pass
    its cell's own tolerance, or a tolerance=1.0 cell would be scored against
    the spine set of the shipped 1.5 km build — which is precisely the
    tolerance × length_source interaction `D-026` requires be measured.
    """
    s = sequences if sequences is not None else pd.read_csv(
        C.DATASET / "station_sequences.csv")
    if offset_max_km is not None:
        s = s[pd.to_numeric(s.offset_km, errors="coerce") <= offset_max_km]
    elif "used_for_edges" in s.columns:
        s = s[s.used_for_edges.astype(bool)]
    s = s.sort_values(["corridor_id", "measure_km"])
    rows = []
    for cid, g in s.groupby("corridor_id", sort=False):
        code = g.station_code.to_numpy()
        meas = g.measure_km.to_numpy(float)
        off = g.offset_km.to_numpy(float)
        for i in range(len(code) - 1):
            a, b = code[i], code[i + 1]
            if a == b or not isinstance(a, str) or not isinstance(b, str):
                continue
            rows.append((min(a, b), max(a, b), abs(meas[i + 1] - meas[i]),
                         float(np.nanmax([off[i], off[i + 1]]))))
    df = pd.DataFrame(rows, columns=["a", "b", "spine_km", "offset_max_km"])
    return df.groupby(["a", "b"], as_index=False).agg(
        spine_km=("spine_km", "min"), offset_max_km=("offset_max_km", "min"))


def _chord_km(edges: pd.DataFrame, nodes: pd.DataFrame) -> np.ndarray:
    pos = nodes.set_index("node_id")[["longitude", "latitude"]]
    a = pos.reindex(edges.from_node).to_numpy(float)
    b = pos.reindex(edges.to_node).to_numpy(float)
    return haversine_km(a[:, 0], a[:, 1], b[:, 0], b[:, 1])


def derive_length(edges: pd.DataFrame, nodes: pd.DataFrame,
                  sequences: pd.DataFrame | None = None,
                  spec: ProvenanceSpec | None = None,
                  offset_max_km: float | None = None) -> pd.DataFrame:
    """`D-026` — hybrid length with per-edge provenance, plus `sinuosity` (`A2`).

    Adds `length_chord_km`, `length_spine_km`, `offset_max_km`, `length_source`,
    `sinuosity`, `length_km_v11`. Leaves the original `length_km` untouched so
    the two can be compared; the caller decides which one ships.
    """
    spec = spec or ProvenanceSpec()
    e = edges.copy()
    e["length_chord_km"] = _chord_km(e, nodes)

    pm = pair_measures(sequences, offset_max_km)
    key = pd.DataFrame({"a": np.minimum(e.from_node, e.to_node),
                        "b": np.maximum(e.from_node, e.to_node)})
    e = e.join(key.merge(pm, on=["a", "b"], how="left")[
        ["spine_km", "offset_max_km"]].rename(columns={"spine_km": "length_spine_km"}))

    chord, spine = e.length_chord_km, e.length_spine_km
    off = e.offset_max_km

    src = pd.Series("undefined", index=e.index, dtype=object)
    have_chord, have_spine = chord.notna(), spine.notna()
    # order matters: each test only fires where no earlier one did
    src[have_chord & ~have_spine] = "chord_no_spine"
    trusted = have_spine & have_chord & (off < spec.offset_trust_km) & (spine >= chord)
    src[have_spine & have_chord & (off >= spec.offset_trust_km)] = "chord_fallback_offset"
    src[have_spine & have_chord & (off < spec.offset_trust_km) & (spine < chord)] = \
        "chord_fallback_collapse"
    src[trusted] = "spine"
    # a spine with no chord (endpoint missing a coordinate) is still a measure
    src[have_spine & ~have_chord] = "spine"

    # D-026 specified the hybrid for consecutive station placements. Stitch
    # edges (D-005) reach their length by a different route in _finalise --
    # the corridor geodesic where no station was placed, the endpoint chord
    # otherwise -- and the ADR is silent on them. Applying the rule to them
    # anyway moves 892 edges and +1,073 km, more than the entire intended fix,
    # on a rule never examined for this case (F-043). They keep their as-built
    # length and say so.
    stitch = e.get("any_stitch")
    stitch = (stitch.astype(bool) if stitch is not None
              else pd.Series(False, index=e.index))

    if spec.length_mode == "asis":
        new = e.length_km.astype(float)
    elif spec.length_mode == "spine":
        new = spine.where(have_spine, chord)
    elif spec.length_mode == "chord":
        new = chord.where(have_chord, spine)
    else:  # hybrid
        new = np.where(src == "spine", spine, chord)
        new = pd.Series(new, index=e.index, dtype=float)
        new = new.fillna(e.length_km.astype(float))
        new[stitch] = e.loc[stitch, "length_km"].astype(float)
        src[stitch] = "stitch_as_built"

    floored = new.notna() & (new < spec.min_edge_km)
    src[floored] = "floored"
    new = new.clip(lower=spec.min_edge_km)
    src[new.isna()] = "undefined"
    new = new.fillna(e.length_km.astype(float))

    e["length_source"] = pd.Categorical(src, categories=list(LENGTH_SOURCES))
    e["length_km_v11"] = new.astype(float)
    # A2: defined only where the spine was trusted, per the roadmap
    e["sinuosity"] = np.where(
        (src == "spine") & have_chord & (chord > 0), spine / chord, np.nan)
    return e


def derive_defect_flags(edges: pd.DataFrame, corridors: pd.DataFrame,
                        spec: ProvenanceSpec | None = None,
                        length_col: str = "length_km") -> pd.DataFrame:
    """`D-025` — the `G-01` station-matching defect flag.

    `station_match_deficit = declared_no_of_stations - n_stations_found` for the
    edge's corridor; `suspect_long_edge` when the deficit and the length both
    exceed their thresholds. `F-041`: this is a path-analysis caveat, **not** a
    length filter — excluding these edges makes route-km agreement worse,
    because the length on them is real and only the intermediate nodes are
    missing.
    """
    spec = spec or ProvenanceSpec()
    e = edges.copy()
    c = corridors.set_index("corridor_id")
    dec = pd.to_numeric(c.declared_no_of_stations, errors="coerce")
    found = pd.to_numeric(c.n_stations_found, errors="coerce")
    deficit = (dec - found).reindex(e.corridor_id).to_numpy()
    e["station_match_deficit"] = deficit
    e["suspect_long_edge"] = (
        (pd.Series(deficit, index=e.index) >= spec.deficit_min)
        & (e[length_col].astype(float) > spec.suspect_len_km)
    ).fillna(False)
    return e


def derive_conflicts(edges: pd.DataFrame, corridors: pd.DataFrame) -> pd.DataFrame:
    """`D-030` — carry corridor attribute-conflict flags onto the edges. Pure join."""
    e = edges.copy()
    c = corridors.set_index("corridor_id")
    for col in CONFLICT_COLS:
        if col in c.columns:
            e[col] = c[col].reindex(e.corridor_id).fillna(False).to_numpy().astype(bool)
    return e


def derive_speed_fallback(edges: pd.DataFrame,
                          spec: ProvenanceSpec | None = None) -> pd.DataFrame:
    """`D-029` — record where `weights.travel_time_proxy` substitutes a constant.

    `F-031`: documenting the constant in `weights.py` did not stop it entering
    results indistinguishably from a measurement. The column does.
    """
    spec = spec or ProvenanceSpec()
    e = edges.copy()
    v = pd.to_numeric(e.get("speed_kmph"), errors="coerce")
    e["speed_is_fallback"] = v.isna() | (v <= 0)
    e["speed_used_kmph"] = v.where(~e.speed_is_fallback, spec.fallback_speed)
    return e


def derive_granularity(edges: pd.DataFrame) -> pd.DataFrame:
    """`D-027` — one `*_granularity` marker per inherited attribute.

    Two edges on one corridor are not two observations. Without this a
    downstream analysis treats 9,689 edges as 9,689 samples and is
    overconfident by roughly the edge-to-corridor ratio.
    """
    e = edges.copy()
    for col, grain in GRANULARITY.items():
        if col in e.columns:
            e[f"{col}_granularity"] = grain
    return e


# --------------------------------------------------------------------------- #
# the whole layer
# --------------------------------------------------------------------------- #

def enrich(edges: pd.DataFrame, nodes: pd.DataFrame,
           corridors: pd.DataFrame | None = None,
           sequences: pd.DataFrame | None = None,
           spec: ProvenanceSpec | None = None,
           *, adopt_length: bool = True,
           offset_max_km: float | None = None) -> pd.DataFrame:
    """Apply the whole v1.1 layer to a shipped edge table.

    With `adopt_length` the hybrid becomes `length_km` and the v1.0 value is
    preserved as `length_km_v10`, so no result loses its baseline.
    """
    spec = spec or ProvenanceSpec()
    corridors = corridors if corridors is not None else pd.read_csv(
        C.DATASET / "corridors.csv")

    e = derive_length(edges, nodes, sequences, spec, offset_max_km)
    if adopt_length:
        e["length_km_v10"] = e.length_km.astype(float)
        e["length_km"] = e.length_km_v11
    # the defect flag is evaluated on whichever length now ships
    e = derive_defect_flags(e, corridors, spec, length_col="length_km")
    e = derive_conflicts(e, corridors)
    e = derive_speed_fallback(e, spec)
    e = derive_granularity(e)
    e["provenance_version"] = "v1.1"
    e["provenance_spec_hash"] = spec.hash
    return e


def summarise(edges: pd.DataFrame) -> dict:
    """What the layer actually did — for the manifest and the validation report."""
    e = edges
    out: dict = {
        "n_edges": int(len(e)),
        "length_source": {str(k): int(v) for k, v in
                          e.length_source.value_counts(dropna=False).items()},
        "route_km_v11": round(float(e.length_km.sum()), 1),
        "sinuosity_defined": int(e.sinuosity.notna().sum()),
        "sinuosity_median": (round(float(e.sinuosity.median()), 4)
                             if e.sinuosity.notna().any() else None),
        "suspect_long_edge": int(e.suspect_long_edge.sum()),
        "suspect_route_km": round(float(e.loc[e.suspect_long_edge, "length_km"].sum()), 1),
        "speed_is_fallback": int(e.speed_is_fallback.sum()),
        "any_attribute_conflict": (int(e.any_attribute_conflict.sum())
                                   if "any_attribute_conflict" in e else None),
    }
    out["suspect_route_km_share"] = round(
        out["suspect_route_km"] / out["route_km_v11"], 4) if out["route_km_v11"] else None
    out["speed_fallback_share"] = round(out["speed_is_fallback"] / len(e), 4)
    if "length_km_v10" in e:
        d = e.length_km - e.length_km_v10
        out["route_km_v10"] = round(float(e.length_km_v10.sum()), 1)
        out["route_km_delta"] = round(float(d.sum()), 1)
        out["route_km_delta_pct"] = round(float(d.sum() / e.length_km_v10.sum()) * 100, 4)
        out["edges_changed"] = int((d.abs() > 1e-3).sum())
    return out


def load_graph_v11(spec=None, prov: ProvenanceSpec | None = None, *,
                   strict: bool = False):
    """Build a graph with the v1.1 provenance layer applied.

    The sweep entry point for treating length derivation as a factor (`W7`).
    `prov.length_mode='asis'` reproduces the v1.0 length exactly, which is what
    makes the derivation cells comparable against the existing `E-200` grid.
    """
    import networkx as nx  # noqa: F401  (kept local; build already imports nx)
    from .config import BuildSpec
    from .build import rebuild_tables, shipped_tables, to_graph, assert_invariants

    spec = spec or BuildSpec(label="shipped default")
    prov = prov or ProvenanceSpec()
    nodes, edges = (rebuild_tables(spec) if spec.needs_rebuild else shipped_tables())
    edges = enrich(edges, nodes, spec=prov, offset_max_km=spec.offset_max_km)
    G = to_graph(nodes, edges, spec)
    if spec.is_shipped_default and prov.length_mode == "asis":
        assert_invariants(G, strict=strict)
    G.graph["provenance_spec"] = prov.to_dict()
    G.graph["provenance_spec_hash"] = prov.hash
    return G
