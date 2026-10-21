"""True track alignment for graph edges (v2 roadmap W1, pulled forward).

Phase 2 keeps one LineString per *corridor* (`corridor_spines.parquet`, WKB) and
places each station on it by `measure_km` (cumulative great-circle km along the
spine). An edge between two consecutive stations is therefore the slice of its
corridor's spine between the two measures. No shapely: the spines are plain
2-D LineStrings, so WKB is parsed and written here directly, which keeps the
dependency set unchanged.

Rules (each one is asserted by E-402, none is trusted by construction):

  * `geometry_source = "spine"`  only where `length_source == "spine"` -- the
    placement offset is under the trust threshold and the spine is not shorter
    than the chord (D-026). The slice is the real alignment.
  * Orientation (F-047): `station_sequences.measure_km` runs along the spine *as
    oriented by Phase 2*, and `corridors.orientation == "reversed_to_a"` (1,090
    of 2,279 corridors) means that is the REVERSE of the stored LineString. The
    position on the stored line is then `L - measure_km`. Skipping this puts
    ~half of all geometry in the wrong place while every length check still
    passes (a slice's length is |dm| either way); only an endpoint-vs-node
    check can see it, which is why E-402 has one. Corridors whose orientation
    is `unknown` (5) are not sliced.
  * `geometry_source = "chord"`  otherwise, when both endpoints have
    coordinates: a straight line, and says so. Never a spine slice whose
    placements D-026 declined to trust.
  * `geometry_source = "none"`   when an endpoint has no coordinate
    (JN::Khandala). The GeoJSON feature is kept with `geometry: null` rather
    than dropped -- a silent absence is how a missing edge goes unnoticed.

The slice is NOT snapped to the node coordinates. Stations sit up to
`offset_max_km` (<0.25 km for trusted spines) off the line; snapping would
invent track that does not exist. The offset is exposed per edge instead.
"""
from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C
from .build import haversine_km

SPINES = C.REPO / "02_graph_inputs" / "pipeline" / "cache" / "corridor_spines.parquet"


# --------------------------------------------------------------------------- #
# WKB (2-D LineString only)
# --------------------------------------------------------------------------- #

def read_wkb_linestring(b: bytes) -> np.ndarray:
    o = "<" if b[0] == 1 else ">"
    t = struct.unpack(o + "I", b[1:5])[0]
    if t != 2:
        raise ValueError(f"expected 2-D LineString (type 2), got WKB type {t}")
    n = struct.unpack(o + "I", b[5:9])[0]
    return np.frombuffer(b, dtype=o + "f8", count=2 * n, offset=9).reshape(n, 2).copy()


def write_wkb_linestring(xy: np.ndarray) -> bytes:
    xy = np.asarray(xy, dtype="<f8")
    return b"\x01" + struct.pack("<II", 2, len(xy)) + xy.tobytes()


# --------------------------------------------------------------------------- #
# spine slicing
# --------------------------------------------------------------------------- #

class Spine:
    """One corridor LineString with cumulative great-circle distance."""
    __slots__ = ("xy", "cum")

    def __init__(self, xy: np.ndarray):
        self.xy = xy
        seg = haversine_km(xy[:-1, 0], xy[:-1, 1], xy[1:, 0], xy[1:, 1])
        self.cum = np.concatenate([[0.0], np.cumsum(seg)])

    @property
    def length_km(self) -> float:
        return float(self.cum[-1])

    def point_at(self, m: float) -> np.ndarray:
        m = min(max(m, 0.0), self.cum[-1])
        i = int(np.searchsorted(self.cum, m, side="right") - 1)
        i = min(i, len(self.xy) - 2)
        span = self.cum[i + 1] - self.cum[i]
        f = 0.0 if span <= 0 else (m - self.cum[i]) / span
        return self.xy[i] + f * (self.xy[i + 1] - self.xy[i])

    def substring(self, m0: float, m1: float) -> np.ndarray:
        """Coordinates of the spine between two measures, in the order m0 -> m1."""
        rev = m0 > m1
        lo, hi = (m1, m0) if rev else (m0, m1)
        lo, hi = max(lo, 0.0), min(hi, self.cum[-1])
        inner = (self.cum > lo) & (self.cum < hi)
        pts = np.vstack([self.point_at(lo), self.xy[inner], self.point_at(hi)])
        return pts[::-1] if rev else pts


def load_spines(path: Path | None = None) -> dict[str, Spine]:
    df = pd.read_parquet(path or SPINES)
    return {cid: Spine(read_wkb_linestring(b)) for cid, b in zip(df.corridor_id, df.wkb)}


def path_km(xy) -> float:
    if xy is None or len(xy) < 2:
        return 0.0
    return float(haversine_km(xy[:-1, 0], xy[:-1, 1], xy[1:, 0], xy[1:, 1]).sum())


# --------------------------------------------------------------------------- #
# per-edge placement lookup
# --------------------------------------------------------------------------- #

def pair_placements(sequences: pd.DataFrame, offset_max_km: float) -> dict:
    """For each unordered station pair, the shortest consecutive placement.

    Mirrors `provenance.pair_measures` (same eligibility, same shortest-spine
    tie-break) but keeps *which corridor* and *where on it*, which is what a
    slice needs. Kept separate so the length derivation stays untouched; E-402
    asserts the two agree on every edge.
    """
    s = sequences[pd.to_numeric(sequences.offset_km, errors="coerce") <= offset_max_km]
    s = s.sort_values(["corridor_id", "measure_km"])
    best: dict = {}
    for cid, g in s.groupby("corridor_id", sort=False):
        code = g.station_code.to_numpy()
        meas = g.measure_km.to_numpy(float)
        off = g.offset_km.to_numpy(float)
        for i in range(len(code) - 1):
            a, b = code[i], code[i + 1]
            if a == b or not isinstance(a, str) or not isinstance(b, str):
                continue
            spine_km = abs(meas[i + 1] - meas[i])
            k = (a, b) if a < b else (b, a)
            rec = {"corridor": cid, "m": {a: meas[i], b: meas[i + 1]},
                   "spine_km": spine_km,
                   "offset": float(np.nanmax([off[i], off[i + 1]]))}
            if k not in best or spine_km < best[k]["spine_km"]:
                best[k] = rec
    return best


def build_alignments(edges: pd.DataFrame, nodes: pd.DataFrame,
                     sequences: pd.DataFrame, spines: dict[str, Spine],
                     offset_max_km: float,
                     corridors: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per edge: geometry_source, geometry_length_km, coords (object col).

    `edges` must carry `length_source` (the v1.1 derivation) -- geometry trust
    is defined by it, not re-decided here.
    """
    pl = pair_placements(sequences, offset_max_km)
    corridors = corridors if corridors is not None else pd.read_csv(
        C.DATASET / "corridors.csv")
    orient = corridors.set_index("corridor_id").orientation.to_dict()
    pos = nodes.set_index("node_id")[["longitude", "latitude"]]
    out = []
    for r in edges.itertuples(index=False):
        a, b = r.from_node, r.to_node
        pa, pb = pos.loc[a].to_numpy(float), pos.loc[b].to_numpy(float)
        has_coord = not (np.isnan(pa).any() or np.isnan(pb).any())
        coords, src, gcid, off = None, "none", None, np.nan
        if r.length_source == "spine":
            rec = pl.get((a, b) if a < b else (b, a))
            if rec is not None:
                sp = spines.get(rec["corridor"])
                o = orient.get(rec["corridor"])
                if sp is not None and o in ("as_built", "reversed_to_a"):
                    m_a, m_b = rec["m"][a], rec["m"][b]
                    if o == "reversed_to_a":
                        m_a, m_b = sp.length_km - m_a, sp.length_km - m_b
                    coords = sp.substring(m_a, m_b)
                    src, gcid, off = "spine", rec["corridor"], rec["offset"]
        if coords is None and has_coord:
            coords, src = np.vstack([pa, pb]), "chord"
        out.append((r.edge_id, src, gcid, off, coords))
    df = pd.DataFrame(out, columns=["edge_id", "geometry_source", "geometry_corridor",
                                    "geometry_offset_km", "coords"])
    df["geometry_length_km"] = [path_km(c) if c is not None else np.nan for c in df.coords]
    df["geometry_n_vertices"] = [0 if c is None else len(c) for c in df.coords]
    return df
