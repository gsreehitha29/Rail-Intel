"""Graph v1.2 enrichment: edge-level attributes, speed imputation, state inference.

Three of the five "known weaknesses" (2026-10-04), each fixed only as far as
the evidence allows and each with its own proof in `E-500`:

  W-2  attribute granularity  -- `segment_overlay()`: every GIS segment is
       clipped to the stretch of corridor spine each edge occupies, so an edge
       carries the attributes of the track it is actually made of. Bridges,
       tunnels and zone genuinely vary within corridors and become edge-level;
       speed, gauge and track count do NOT vary in the source (0.04-0.5% of
       network km differs from the corridor value), so for those the corridor
       value is the finest the source holds, and is labelled as such.
  W-3  substituted speeds     -- `impute_speed()`: the constant 50 km/h
       (cross-validated MAE 56 km/h) is replaced by the gauge x zone median
       (MAE 11.4 km/h, grouped-by-corridor 5-fold CV), with the source and the
       expected error on every edge. It is an estimate and says so.
  W-4  state coverage         -- `infer_state()`: k-nearest labelled stations,
       assigned only where all 7 neighbours agree and the nearest is within
       25 km (leave-one-out accuracy 99.5% against the source labels). Every
       "Andhra Pradesh" label is flagged ambiguous: the source predates
       Telangana (2014) and labels Hyderabad, Warangal and Nizamabad AP.

Phase 2's zone and gauge normalisers are loaded read-only from its config so a
spelling is never resolved two different ways in the project.
"""
from __future__ import annotations

import collections
import importlib.util
import struct

import numpy as np
import pandas as pd

from . import config as C

R_EARTH = 6371.0088
SEGMENTS = C.REPO / "02_graph_inputs" / "pipeline" / "cache" / "segments_geometry.parquet"
SEG_MAP = C.REPO / "02_graph_inputs" / "pipeline" / "cache" / "segment_corridor_map.parquet"
RAW_GIS = C.REPO / "01_data_engineering" / "Railway_Network_.csv"
SCHEDULES = C.REPO / "01_data_engineering" / "processed_data" / "cleaned_schedules.csv"


def _phase2_config():
    spec = importlib.util.spec_from_file_location(
        "p2config", C.REPO / "02_graph_inputs" / "pipeline" / "config.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- #
# geometry helpers (no shapely)
# --------------------------------------------------------------------------- #

def _project(xy: np.ndarray, cum: np.ndarray, pts: np.ndarray):
    """Offset (km) and measure (km, stored frame) of points onto a polyline."""
    lat0 = np.radians(np.nanmean(pts[:, 1]))
    kx, ky = R_EARTH * np.cos(lat0) * np.pi / 180, R_EARTH * np.pi / 180
    A = np.c_[xy[:-1, 0] * kx, xy[:-1, 1] * ky]
    B = np.c_[xy[1:, 0] * kx, xy[1:, 1] * ky]
    AB = B - A
    L2 = np.maximum((AB ** 2).sum(1), 1e-18)
    P = np.c_[pts[:, 0] * kx, pts[:, 1] * ky]
    off = np.full(len(P), np.nan)
    mea = np.full(len(P), np.nan)
    for s0 in range(0, len(P), 256):
        p = P[s0:s0 + 256, None, :]
        t = np.clip(((p - A) * AB).sum(2) / L2, 0, 1)
        d = np.sqrt((((A + AB * t[..., None]) - p) ** 2).sum(2))
        i = d.argmin(1)
        r = np.arange(len(i))
        off[s0:s0 + 256] = d[r, i]
        mea[s0:s0 + 256] = cum[i] + t[r, i] * (cum[i + 1] - cum[i])
    return off, mea


# --------------------------------------------------------------------------- #
# W-2  segment overlay
# --------------------------------------------------------------------------- #

def load_segments() -> pd.DataFrame:
    """Raw GIS attributes + corridor + start/end points, one row per segment.

    Applies Phase 2's own value rules (s02 ZERO_AS_UNKNOWN): 0 speed / track
    count means *unknown*, a negative track count is invalid.
    """
    raw = pd.read_csv(RAW_GIS, low_memory=False,
                      usecols=["objectid", "speed", "type", "nooflanes",
                               "railwayzone", "bridge_yn", "tunnel_yn"])
    geo = pd.read_parquet(SEGMENTS, columns=["objectid", "length_km", "start_lon",
                                             "start_lat", "end_lon", "end_lat"])
    mp = pd.read_parquet(SEG_MAP, columns=["objectid", "corridor_id"])
    s = raw.merge(mp, on="objectid").merge(geo, on="objectid")
    s.loc[s.speed <= 0, "speed"] = np.nan
    s.loc[s.nooflanes <= 0, "nooflanes"] = np.nan
    p2 = _phase2_config()
    s["gauge_code_seg"] = s["type"].map(p2.gauge_code)
    s["zone_code_seg"] = s["railwayzone"].map(p2.zone_code)
    return s


def segment_overlay(edges: pd.DataFrame, nodes: pd.DataFrame, spines: dict,
                    segments: pd.DataFrame | None = None,
                    max_offset_km: float = 1.5, min_coverage: float = 0.5) -> pd.DataFrame:
    """Per-edge attributes from the GIS segments the edge physically spans.

    Each segment's start and end are projected onto its corridor spine; each
    edge's endpoints likewise. The overlap of the two measure intervals is the
    length of that segment lying within the edge. Attributes are then
    length-weighted over the overlap. Edges whose overlap covers less than
    `min_coverage` of their own span keep the corridor value
    (`edge_attr_source = corridor_fallback`).
    """
    s = segments if segments is not None else load_segments()
    pos = nodes.set_index("node_id")[["longitude", "latitude"]]
    rows = []
    for cid, g in s.groupby("corridor_id", sort=False):
        sp = spines.get(cid)
        E = edges[edges.corridor_id == cid]
        if sp is None or len(E) == 0:
            continue
        o1, m1 = _project(sp.xy, sp.cum, g[["start_lon", "start_lat"]].to_numpy(float))
        o2, m2 = _project(sp.xy, sp.cum, g[["end_lon", "end_lat"]].to_numpy(float))
        on = np.maximum(o1, o2) <= max_offset_km
        s_lo, s_hi = np.minimum(m1, m2), np.maximum(m1, m2)
        span = np.maximum(s_hi - s_lo, 1e-9)
        seg_km = g.length_km.to_numpy(float)
        ends = np.vstack([pos.reindex(E.from_node).to_numpy(float),
                          pos.reindex(E.to_node).to_numpy(float)])
        okc = ~np.isnan(ends).any(1)
        em = np.full(len(ends), np.nan)
        if okc.any():
            _, em[okc] = _project(sp.xy, sp.cum, ends[okc])
        k = len(E)
        cols = {c: g[c].to_numpy() for c in ("speed", "gauge_code_seg", "nooflanes",
                                             "zone_code_seg", "bridge_yn", "tunnel_yn")}
        for j, eid in enumerate(E.edge_id.to_numpy()):
            mu, mv = em[j], em[k + j]
            if np.isnan(mu) or np.isnan(mv):
                rows.append({"edge_id": eid, "overlay_span_km": np.nan})
                continue
            lo, hi = min(mu, mv), max(mu, mv)
            ov = np.clip(np.minimum(s_hi, hi) - np.maximum(s_lo, lo), 0, None)
            hit = (ov > 0) & on
            w = np.minimum(ov[hit] * seg_km[hit] / span[hit], seg_km[hit])
            r = {"edge_id": eid, "overlay_span_km": hi - lo,
                 "overlay_spine_km": float(ov[hit].sum()), "overlay_km": float(w.sum()),
                 "n_segments": int(hit.sum())}
            if hit.any():
                def wmode(arr):
                    a = arr[hit]
                    ok = pd.notna(a)
                    if not ok.any():
                        return None
                    acc = collections.defaultdict(float)
                    for val, ww in zip(a[ok], w[ok]):
                        acc[val] += ww
                    return max(acc.items(), key=lambda kv: (kv[1], str(kv[0])))[0]
                br = cols["bridge_yn"][hit] == "Y"
                tu = cols["tunnel_yn"][hit] == "Y"
                r.update({
                    "bridge_km": float(w[br].sum()), "n_bridge_segments": int(br.sum()),
                    "tunnel_km": float(w[tu].sum()), "n_tunnel_segments": int(tu.sum()),
                    "speed_kmph_seg": wmode(cols["speed"]),
                    "gauge_code_seg": wmode(cols["gauge_code_seg"]),
                    "n_tracks_seg": wmode(cols["nooflanes"]),
                    "zone_code_seg": wmode(cols["zone_code_seg"]),
                    "speed_known_km": float(w[pd.notna(cols["speed"][hit])].sum()),
                })
            rows.append(r)
    ov = pd.DataFrame(rows)
    out = edges[["edge_id"]].merge(ov, on="edge_id", how="left")
    out["overlay_coverage"] = out.overlay_spine_km / out.overlay_span_km.where(out.overlay_span_km > 0)
    good = out.overlay_coverage >= min_coverage
    out["edge_attr_source"] = np.where(good, "segment_overlay", "corridor_fallback")
    # object dtype so a missing value stays None and True/False stay booleans
    out["bridge_present_edge"] = (out.n_bridge_segments.fillna(0) > 0).astype(object).where(good, None)
    out["tunnel_present_edge"] = (out.n_tunnel_segments.fillna(0) > 0).astype(object).where(good, None)
    for c in ("bridge_km", "tunnel_km", "speed_kmph_seg", "gauge_code_seg",
              "n_tracks_seg", "zone_code_seg", "n_bridge_segments", "n_tunnel_segments"):
        out.loc[~good, c] = np.nan
    return out


# --------------------------------------------------------------------------- #
# W-3  speed imputation
# --------------------------------------------------------------------------- #

def _speed_models(train: pd.DataFrame):
    gz = train.groupby(["gauge_key", "zone_for_speed"]).speed_declared_kmph.median()
    gm = train.groupby("gauge_key").speed_declared_kmph.median()
    return gz, gm


def speed_cv(e: pd.DataFrame, folds: int = 5, seed: int = 0) -> dict:
    """Grouped-by-corridor CV of the imputation, and of the old 50 km/h constant.

    Grouping matters: speed is a corridor constant, so a random split would
    score an edge against its own corridor-mates and flatter the method.
    """
    d = e[e.speed_declared_kmph.notna()].copy()
    corr = d.corridor_id.unique()
    rng = np.random.default_rng(seed)
    rng.shuffle(corr)
    f = {c: i % folds for i, c in enumerate(corr)}
    d["fold"] = d.corridor_id.map(f)
    preds = []
    for k in range(folds):
        tr, te = d[d.fold != k], d[d.fold == k].copy()
        gz, gm = _speed_models(tr)
        te["pred"] = [gz.get((g, z), gm.get(g, np.nan))
                      for g, z in zip(te.gauge_key, te.zone_for_speed)]
        preds.append(te)
    p = pd.concat(preds)
    err = (p.pred - p.speed_declared_kmph).abs()
    err50 = (50.0 - p.speed_declared_kmph).abs()
    by_gauge = {g: {"n": int(len(s)), "mae": float((s.pred - s.speed_declared_kmph).abs().mean()),
                    "bias": float((s.pred - s.speed_declared_kmph).mean())}
                for g, s in p.groupby("gauge_key") if len(s) >= 10}
    return {"n": int(len(p)), "mae_kmph": float(err.mean()),
            "within_10": float((err <= 10).mean()), "within_20": float((err <= 20).mean()),
            "bias_kmph": float((p.pred - p.speed_declared_kmph).mean()),
            "old_constant_50_mae_kmph": float(err50.mean()), "by_gauge": by_gauge}


def impute_speed(e: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Declared (edge-level where the overlay has it) else gauge x zone median."""
    e = e.copy()
    seg = pd.to_numeric(e.get("speed_kmph_seg"), errors="coerce")
    cor = pd.to_numeric(e.speed_kmph, errors="coerce").where(lambda v: v > 0)
    e["speed_declared_kmph"] = seg.where(seg.notna(), cor)
    e["zone_for_speed"] = e.get("zone_code_seg").fillna(e.zone_code) \
        if "zone_code_seg" in e else e.zone_code
    # a grouping key only -- gauge_code itself is source data and is not rewritten
    e["gauge_key"] = e.gauge_code.fillna("unknown").astype(str)
    cv = speed_cv(e)
    gz, gm = _speed_models(e[e.speed_declared_kmph.notna()])
    src = np.where(seg.notna(), "declared_segment",
                   np.where(cor.notna(), "declared_corridor", None)).astype(object)
    imp = []
    for i, (g, z, v) in enumerate(zip(e.gauge_key, e.zone_for_speed, e.speed_declared_kmph)):
        if pd.notna(v):
            imp.append(v)
        elif (g, z) in gz.index:
            imp.append(gz[(g, z)]); src[i] = "imputed_gauge_zone_median"
        elif g in gm.index:
            imp.append(gm[g]); src[i] = "imputed_gauge_median"
        else:
            imp.append(np.nan); src[i] = "none"
    e["speed_used_kmph"] = imp
    e["speed_source"] = src
    e["speed_is_fallback"] = ~pd.Series(src).isin(["declared_segment", "declared_corridor"]).to_numpy()
    e["speed_expected_abs_error_kmph"] = np.where(e.speed_is_fallback, cv["mae_kmph"], 0.0)
    return e.drop(columns=["zone_for_speed", "gauge_key"]), cv


# --------------------------------------------------------------------------- #
# W-4  state inference
# --------------------------------------------------------------------------- #

def _hav(lo1, la1, lo2, la2):
    lo1, la1, lo2, la2 = map(np.radians, (lo1, la1, lo2, la2))
    a = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 2 * R_EARTH * np.arcsin(np.sqrt(a))


def _vote(d, idx, labels):
    w = 1.0 / np.maximum(d, 0.5)
    acc = collections.defaultdict(float)
    for j, ww in zip(idx, w):
        acc[labels[j]] += ww
    best = max(acc.items(), key=lambda kv: (kv[1], kv[0]))
    return best[0], best[1] / w.sum()


def infer_state(nodes: pd.DataFrame, k: int = 7, max_nn_km: float = 25.0,
                min_agreement: float = 0.999) -> tuple[pd.DataFrame, dict]:
    n = nodes.copy()
    lab = n[n.state.notna() & n.longitude.notna()].reset_index(drop=True)
    LX, LY, LS = lab.longitude.to_numpy(), lab.latitude.to_numpy(), lab.state.to_numpy()

    def knn(x, y, exclude=None):
        d = _hav(x, y, LX, LY)
        if exclude is not None:
            d[exclude] = np.inf
        idx = np.argpartition(d, k)[:k]
        idx = idx[np.argsort(d[idx])]
        return idx, d[idx]

    # leave-one-out validation of the exact rule that is then applied
    loo = []
    for i in range(len(lab)):
        idx, d = knn(LX[i], LY[i], exclude=i)
        pred, share = _vote(d, idx, LS)
        loo.append((LS[i], pred, share, d[0]))
    L = pd.DataFrame(loo, columns=["true", "pred", "share", "d1"])
    rule = (L.share >= min_agreement) & (L.d1 <= max_nn_km)
    val = {"k": k, "max_nn_km": max_nn_km, "min_agreement": min_agreement,
           "labelled": int(len(L)),
           "loo_accuracy_all": float((L.true == L.pred).mean()),
           "loo_rule_coverage": float(rule.mean()),
           "loo_rule_accuracy": float((L.true == L.pred)[rule].mean()),
           "loo_rule_errors": int((L.true != L.pred)[rule].sum())}

    best, share, src = [], [], []
    for r in n.itertuples():
        if pd.notna(r.state):
            best.append(r.state); share.append(1.0); src.append("station_master")
        elif pd.isna(r.longitude):
            best.append(None); share.append(np.nan); src.append("none")
        else:
            idx, d = knn(r.longitude, r.latitude)
            pred, sh = _vote(d, idx, LS)
            if sh >= min_agreement and d[0] <= max_nn_km:
                best.append(pred); share.append(sh); src.append("inferred_knn")
            else:
                best.append(None); share.append(sh); src.append("none")
    n["state_best"] = best
    n["state_source"] = src
    n["state_knn_agreement"] = share
    # The source labels predate Telangana: an AP label cannot be trusted to mean
    # present-day Andhra Pradesh. Flag, do not guess.
    n["state_ambiguous_ap_tg"] = n.state_best.eq("Andhra Pradesh")
    val.update({"coverage_before": float(n.state.notna().mean()),
                "coverage_after": float(pd.Series(best).notna().mean()),
                "inferred": int((pd.Series(src) == "inferred_knn").sum()),
                "ambiguous_ap_tg": int(n.state_ambiguous_ap_tg.sum())})
    return n, val
