"""E-716 - graph v2.0-open from OpenStreetMap alone (D-060). Stages O1-O3 (milestone C1).

  O1 filter    keep running lines; every dropped km counted by reason
  O2 collapse  merge side-by-side tracks into one route (OSM draws each track)
  O3 snap      put every station on its line

numpy / pandas / scipy only. Lengths are geodesic (haversine on WGS84 lon/lat);
distances between tracks are measured in EPSG:7755 metres.
"""
from __future__ import annotations

import glob, json, re, struct
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from geo import hav_km, lcc

OSM = "external_data/osm_india_rail"
SNAPSHOT = "Geofabrik India zone extracts, data 2026-10-03"
OFFICIAL_ROUTE_KM = 69439          # IR Year Book 2024-25
RUNNING = {"rail", "narrow_gauge"}
USAGE_KEEP = {None, "main", "branch", "freight", "passing_loop"}
# operators that are not Indian Railways (decision table; every row checked by hand)
NOT_IR = {
    "DFCCIL": "dedicated freight corridor",
    "National Capital Region Transport Corporation": "regional rapid transit",
    "NCRTC": "regional rapid transit",
    "Mahanadi Coalfields Ltd.": "industrial",
    "Chhattisgarh East Railway Limited": "industrial joint venture",
    "SAIL": "industrial",
    "BDRCL": "port joint venture",
    "Bangladesh Railway": "foreign",
    "Pakistan Railways": "foreign",
    "National Rail Museum (Indian Railways)": "museum",
    "Mysuru Railway Museum": "museum",
}
NOT_IR_NAME = {r"Dedicated Freight Corridor|\bWDFC\b|\bEDFC\b": "dedicated freight corridor",
               r"^NTPC Rail Track$": "industrial"}
KONKAN = {"KRCL", "KR"}             # Konkan Railway: kept, reported separately


def load(root: Path):
    d = root / OSM
    W = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(d / "rail_ways_*.parquet")))])
    S = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(d / "rail_stations_*.parquet")))])
    W = W.drop_duplicates("way_id").sort_values("way_id").reset_index(drop=True)
    S = S.drop_duplicates("node_id").sort_values("node_id").reset_index(drop=True)
    return W, S


def way_arrays(W: pd.DataFrame):
    """node ids and lon/lat for every way, aligned (checked)."""
    refs, xy = [], []
    for r, b in zip(W.node_refs, W.wkb):
        ids = np.frombuffer(r, "int64"); n = struct.unpack("<I", b[5:9])[0]
        assert n == len(ids)
        refs.append(ids); xy.append(np.frombuffer(b, "<f8", 2 * n, 9).reshape(n, 2))
    return refs, xy


# --------------------------------------------------------------------- O1
def o1_filter(W: pd.DataFrame, xy) -> tuple[np.ndarray, dict]:
    km = np.array([hav_km(p[:-1, 0], p[:-1, 1], p[1:, 0], p[1:, 1]).sum() if len(p) > 1 else 0.0 for p in xy])
    usage = W.usage.where(W.usage.notna(), None)
    reason = np.full(len(W), "", dtype=object)
    def mark(mask, why):
        m = mask & (reason == ""); reason[m] = why
    mark(~W.railway.isin(RUNNING).to_numpy(), "not a running line: railway=" )
    reason = np.where(reason == "not a running line: railway=", "not a running line: railway=" + W.railway.astype(str), reason)
    mark(W.service.notna().to_numpy(), "track inside a yard or station: service=")
    reason = np.where(reason == "track inside a yard or station: service=",
                      "track inside a yard or station: service=" + W.service.astype(str), reason)
    mark(~usage.isin(USAGE_KEEP).to_numpy(), "not a public line: usage=")
    reason = np.where(reason == "not a public line: usage=", "not a public line: usage=" + W.usage.astype(str), reason)
    op = W.operator.map(NOT_IR)
    for pat, why in NOT_IR_NAME.items():
        op = op.where(op.notna() | ~W.name.fillna("").str.contains(pat, regex=True), why)
    mark(op.notna().to_numpy(), "not Indian Railways: ")
    reason = np.where(reason == "not Indian Railways: ", "not Indian Railways: " + op.astype(str), reason)
    keep = reason == ""
    by = pd.Series(km[~keep]).groupby(pd.Series(reason[~keep])).sum().sort_values(ascending=False)
    rep = dict(ways_in=int(len(W)), km_in=round(float(km.sum()), 1),
               ways_kept=int(keep.sum()), km_kept=round(float(km[keep].sum()), 1),
               km_dropped_by_reason={k: round(float(v), 1) for k, v in by.items()},
               konkan_km_kept=round(float(km[keep & W.operator.isin(KONKAN).to_numpy()].sum()), 1))
    assert abs(rep["km_kept"] + sum(rep["km_dropped_by_reason"].values()) - rep["km_in"]) < 1.0
    return keep, rep, km, reason


# --------------------------------------------------------------------- network helpers
def segments(W, refs, xy, keep):
    """Undirected track segments between consecutive OSM nodes of the kept ways,
    deduplicated (overlapping ways share segments). Returns node table and segment table."""
    ids, lon, lat, U, V, WI = [], [], [], [], [], []
    for i in np.flatnonzero(keep):
        r, p = refs[i], xy[i]
        ids.append(r); lon.append(p[:, 0]); lat.append(p[:, 1])
        U.append(r[:-1]); V.append(r[1:]); WI.append(np.full(len(r) - 1, i))
    ids = np.concatenate(ids); lon = np.concatenate(lon); lat = np.concatenate(lat)
    nid, first = np.unique(ids, return_index=True)
    nodes = pd.DataFrame(dict(osm_node=nid, lon=lon[first], lat=lat[first]))
    U = np.searchsorted(nid, np.concatenate(U)); V = np.searchsorted(nid, np.concatenate(V))
    WI = np.concatenate(WI)
    a, b = np.minimum(U, V), np.maximum(U, V)
    seg = pd.DataFrame(dict(u=a, v=b, way=WI)).query("u != v").drop_duplicates(["u", "v"]).reset_index(drop=True)
    lo, la = nodes.lon.values, nodes.lat.values
    seg["km"] = hav_km(lo[seg.u], la[seg.u], lo[seg.v], la[seg.v])
    return nodes, seg


def make_key(C, paths):
    """Vertex name of a sample: its OSM node at a chain end, else s<sample>."""
    cptr = np.searchsorted(C, np.arange(len(paths) + 1))
    def key(s):
        c = C[s]
        if s == cptr[c]: return f"n{int(paths[c][0])}"
        if s == cptr[c + 1] - 1: return f"n{int(paths[c][-1])}"
        return f"s{int(s)}"
    return key


def chains(n_nodes: int, seg: pd.DataFrame):
    """Split the segment graph into chains: maximal runs between nodes of degree != 2.
    Returns chain id per segment and the chain's ordered node list."""
    u, v = seg.u.to_numpy(), seg.v.to_numpy()
    deg = np.bincount(np.concatenate([u, v]), minlength=n_nodes)
    adj_ptr = np.zeros(n_nodes + 1, dtype=np.int64)
    ends = np.concatenate([u, v]); other = np.concatenate([v, u]); sid = np.concatenate([np.arange(len(u))] * 2)
    order = np.argsort(ends, kind="stable")
    ends, other, sid = ends[order], other[order], sid[order]
    adj_ptr[1:] = np.cumsum(np.bincount(ends, minlength=n_nodes))
    cid = np.full(len(u), -1, dtype=np.int64); paths = []
    def walk(start, s0):
        path = [start]; s = s0; cur = start
        while True:
            cid[s] = len(paths)
            nxt = u[s] if v[s] == cur else v[s]
            path.append(nxt); cur = nxt
            if deg[cur] != 2: break
            lo, hi = adj_ptr[cur], adj_ptr[cur + 1]
            cand = [sid[k] for k in range(lo, hi) if cid[sid[k]] == -1]
            if not cand: break
            s = cand[0]
        paths.append(np.array(path))
    for n in np.flatnonzero(deg != 2):
        for k in range(adj_ptr[n], adj_ptr[n + 1]):
            if cid[sid[k]] == -1: walk(n, sid[k])
    for s in np.flatnonzero(cid == -1):            # pure loops
        if cid[s] == -1: walk(u[s], s)
    return cid, paths, deg


def densify(nodes: pd.DataFrame, paths, step_m: float = 10.0):
    """Sample every chain at <= step_m in EPSG:7755 metres. Returns xy, chain id, and the
    distance along the chain (m) of every sample."""
    X, Y = lcc(nodes.lon.values, nodes.lat.values)
    LO, LA = nodes.lon.values, nodes.lat.values
    out_xy, out_c, out_s, out_ll = [], [], [], []
    for c, p in enumerate(paths):
        x, y = X[p], Y[p]
        d = np.hypot(np.diff(x), np.diff(y)); cum = np.concatenate([[0], np.cumsum(d)])
        n = max(int(np.ceil(cum[-1] / step_m)), 1)
        t = np.linspace(0, cum[-1], n + 1)
        out_xy.append(np.c_[np.interp(t, cum, x), np.interp(t, cum, y)])
        out_c.append(np.full(n + 1, c)); out_s.append(t)
        out_ll.append(np.c_[np.interp(t, cum, LO[p]), np.interp(t, cum, LA[p])])
    return np.concatenate(out_xy), np.concatenate(out_c), np.concatenate(out_s), np.concatenate(out_ll)


# --------------------------------------------------------------------- O2
def chain_gauge(W, seg, cid, n_chains):
    """Length-weighted majority gauge of each chain; None where untagged."""
    g = W.gauge.to_numpy()[seg.way.to_numpy()]
    df = pd.DataFrame(dict(c=cid, g=g, km=seg.km.to_numpy())).dropna(subset=["g"])
    top = df.groupby(["c", "g"]).km.sum().reset_index().sort_values(["c", "km"], ascending=[True, False])
    out = np.full(n_chains, None, dtype=object)
    first = top.drop_duplicates("c")
    out[first.c.to_numpy()] = first.g.to_numpy()
    return out


def _compatible(g1, g2):
    if g1 is None or g2 is None: return True
    return bool(set(str(g1).split(";")) & set(str(g2).split(";")))


def o2_collapse(P, C, D, km_chain, gauge, d_m: float, min_run_m: float, chunk: int = 1_000_000):
    """Remove every stretch of track that runs within d_m of another, still-kept,
    gauge-compatible track for at least min_run_m. Chains are judged shortest first, so
    of two side-by-side tracks the longer stays. Works on 10 m samples, so a track that
    is parallel for part of its length loses only that part.

    Returns the alive mask over samples and a report."""
    n_chain = len(km_chain)
    T = cKDTree(P)
    src, dst = [], []
    for lo in range(0, len(P), chunk):
        q = np.arange(lo, min(lo + chunk, len(P)))
        dd, ii = T.query(P[q], k=12, distance_upper_bound=d_m)
        ok = np.isfinite(dd)
        ii = np.minimum(ii, len(P) - 1)
        m = ok & (C[ii] != C[q][:, None])
        r, k = np.nonzero(m)
        src.append(q[r].astype(np.int64)); dst.append(ii[r, k].astype(np.int64))
    src = np.concatenate(src); dst = np.concatenate(dst)
    order = np.argsort(src, kind="stable"); src, dst = src[order], dst[order]
    sptr = np.searchsorted(src, np.arange(len(P) + 1))
    cptr = np.searchsorted(C, np.arange(n_chain + 1))       # samples are contiguous per chain
    # gauge compatibility as a lookup table over the few distinct gauge values
    vals = sorted({str(g) for g in gauge if g is not None})
    code = np.array([-1 if g is None else vals.index(str(g)) for g in gauge])
    tab = np.ones((len(vals) + 1, len(vals) + 1), bool)
    for a, ga in enumerate(vals):
        for b, gb in enumerate(vals):
            tab[a, b] = _compatible(ga, gb)
    alive = np.ones(len(P), bool)
    gap = int(round(30 / 10)); runs_dropped = 0; runs = []
    for c in np.argsort(km_chain, kind="stable"):
        a, b = cptr[c], cptr[c + 1]
        lo, hi = sptr[a], sptr[b]
        if hi == lo: continue
        s_, t_ = src[lo:hi], dst[lo:hi]
        ok = alive[t_] & tab[code[c], code[C[t_]]]
        cov = np.zeros(b - a, bool); cov[s_[ok] - a] = True
        # close gaps of up to 30 m inside a covered stretch, then take runs
        idx = np.flatnonzero(cov)
        if idx.size == 0: continue
        brk = np.flatnonzero(np.diff(idx) > gap + 1)
        starts = np.r_[idx[0], idx[brk + 1]]; ends = np.r_[idx[brk], idx[-1]]
        for st, en in zip(starts, ends):
            if D[a + en] - D[a + st] >= min_run_m:
                alive[a + st: a + en + 1] = False; runs_dropped += 1; runs.append((a + st, a + en))
    return alive, dict(d_m=d_m, min_run_m=min_run_m, gap_closed_m=30, samples=int(len(P)),
                       samples_dropped=int((~alive).sum()), stretches_dropped=runs_dropped), runs


def o2_verify(P, LL, C, alive, runs, paths, deg, d_m, connect_m, ratio, slack_km, max_rounds=8):
    """Keep a removed stretch removed only if the kept track still offers its route.

    For each removed stretch, its two ends are put on the nearest kept track (within d_m),
    and the distance between those two points along the collapsed network is measured. If
    that is more than ratio x the stretch's own length + slack_km, or unreachable, the
    removal broke a route (typically in a large station, where the track kept is a platform
    line that ends) and the stretch is restored. Geometry only: no timetable is used, so the
    timetable remains an independent test. Repeats until nothing more is restored."""
    step = np.r_[hav_km(LL[:-1, 0], LL[:-1, 1], LL[1:, 0], LL[1:, 1]), 0.0]
    cum = np.cumsum(np.r_[0.0, step[:-1]])
    restored_total, rounds, per_round = 0, 0, []
    live = list(runs)
    for rounds in range(1, max_rounds + 1):
        st, en, pid, conn, _ = o2_connect(P, C, alive, paths, deg, connect_m)
        E, keys, key = build_network(P, LL, C, st, en, conn, pd.DataFrame({"sample": []}), paths)
        G = nx.Graph()
        for r in E.itertuples():
            if not G.has_edge(r.a, r.b) or G[r.a][r.b]["km"] > r.km: G.add_edge(r.a, r.b, km=r.km)
        trk = E[E.kind == "track"]
        row_of = np.full(len(P), -1)
        for i, (sa, sb) in enumerate(zip(trk.s_a.values, trk.s_b.values)): row_of[sa:sb + 1] = i
        ra, rb, rsa, rsb = trk.a.values, trk.b.values, trk.s_a.values, trk.s_b.values
        ia = np.flatnonzero(row_of >= 0); T = cKDTree(P[ia])
        def place(smp):
            d, j = T.query(P[smp], k=8, distance_upper_bound=d_m)
            for dd, jj in zip(np.atleast_1d(d), np.atleast_1d(j)):
                if np.isfinite(dd): return int(ia[jj])
            return None
        bad = []
        for (x, y) in live:
            length = cum[y] - cum[x]
            px, py = place(x), place(y)
            if px is None or py is None: bad.append((x, y)); continue
            r1, r2 = row_of[px], row_of[py]
            if r1 == r2:
                dist = abs(cum[py] - cum[px])
            else:
                lim = ratio * length + slack_km + 1.0
                ends1 = [(ra[r1], cum[px] - cum[rsa[r1]]), (rb[r1], cum[rsb[r1]] - cum[px])]
                ends2 = {ra[r2]: cum[py] - cum[rsa[r2]], rb[r2]: cum[rsb[r2]] - cum[py]}
                dist = np.inf
                for v0, off0 in ends1:
                    if v0 not in G: continue
                    dl = nx.single_source_dijkstra_path_length(G, v0, cutoff=lim, weight="km")
                    for v1, off1 in ends2.items():
                        if v1 in dl: dist = min(dist, off0 + dl[v1] + off1)
            if not dist <= ratio * length + slack_km:
                bad.append((x, y))
        per_round.append(len(bad))
        if not bad: break
        for x, y in bad: alive[x:y + 1] = True
        restored_total += len(bad)
        live = [r for r in live if r not in set(bad)]
    return alive, dict(stretches_checked=len(runs), stretches_restored=restored_total, rounds=rounds,
                       restored_per_round=per_round, ratio=ratio, slack_km=slack_km)


def alive_km(LL, C, alive):
    """Track km of the kept samples: consecutive kept samples on the same chain."""
    same = (C[1:] == C[:-1]) & alive[1:] & alive[:-1]
    d = hav_km(LL[:-1, 0], LL[:-1, 1], LL[1:, 0], LL[1:, 1])
    return float(d[same].sum())


def pieces(C, alive):
    """Maximal runs of kept samples on one chain: (first sample, last sample)."""
    newc = np.r_[True, C[1:] != C[:-1]]
    st = np.flatnonzero(alive & (newc | np.r_[True, ~alive[:-1]]))
    en = np.flatnonzero(alive & (np.r_[C[1:] != C[:-1], True] | np.r_[~alive[1:], True]))
    keep = en > st                                          # a lone sample has no length
    return st[keep], en[keep]


def o2_connect(P, C, alive, paths, deg, d_conn_m: float):
    """Re-join the network where a removed stretch used to carry the connection.

    A piece end is loose when it was cut by the collapse, or when it sits on an OSM node
    that had other track (degree >= 2) and no other kept piece now ends there. Each loose
    end is joined to the nearest kept sample of another piece within d_conn_m; a loose
    end with nothing that close stays a dead end and is counted."""
    st, en = pieces(C, alive)
    cptr = np.searchsorted(C, np.arange(len(paths) + 1))
    pid = np.full(len(P), -1); 
    for k, (a, b) in enumerate(zip(st, en)): pid[a:b + 1] = k
    def key(s):
        c = C[s]
        if s == cptr[c]: return ("n", int(paths[c][0]))
        if s == cptr[c + 1] - 1: return ("n", int(paths[c][-1]))
        return ("s", int(s))
    ends = [(s, key(s)) for s in np.r_[st, en]]
    count = {}
    for _, k in ends: count[k] = count.get(k, 0) + 1
    loose = [(s, k) for s, k in ends if k[0] == "s" or (count[k] == 1 and deg[k[1]] >= 2)]
    ia = np.flatnonzero(alive & (pid >= 0)); T = cKDTree(P[ia])
    conn, unjoined = [], 0
    for s, k in loose:
        dd, ii = T.query(P[s], k=16, distance_upper_bound=d_conn_m)
        hit = [ia[i] for d, i in zip(np.atleast_1d(dd), np.atleast_1d(ii)) if np.isfinite(d) and pid[ia[i]] != pid[s]]
        if hit: conn.append((s, hit[0]))
        else: unjoined += 1
    return st, en, pid, conn, dict(pieces=int(len(st)), loose_ends=len(loose), connectors=len(conn),
                                   loose_ends_left=unjoined)


# --------------------------------------------------------------------- O3
def station_table(S: pd.DataFrame) -> pd.DataFrame:
    S = S[S.railway.isin(["station", "halt"])].copy()
    S["code"] = S.railway_ref.fillna(S.ref).str.upper().str.strip()
    S.loc[S.code == "", "code"] = None
    return S.reset_index(drop=True)


def o3_snap(S, P, alive, pid, snap_m: float):
    """Each station to the nearest kept sample, if within snap_m; else listed, not forced."""
    X, Y = lcc(S.lon.values, S.lat.values)
    ia = np.flatnonzero(alive & (pid >= 0))
    dd, ii = cKDTree(P[ia]).query(np.c_[X, Y])
    S = S.assign(snap_m=dd.round(1), sample=np.where(dd <= snap_m, ia[ii], -1))
    coded = S.code.notna()
    rep = dict(snap_m=snap_m, stations=int(len(S)), snapped=int((S["sample"] >= 0).sum()),
               coded=int(coded.sum()), coded_snapped=int((coded & (S["sample"] >= 0)).sum()))
    rep["coded_snapped_share"] = round(rep["coded_snapped"] / rep["coded"], 4)
    return S, rep


# --------------------------------------------------------------------- network
def build_network(P, LL, C, st, en, conn, S, paths):
    """Vertices and edges of the collapsed network, split at connector targets and
    station snaps. Edge km is geodesic along the kept samples."""
    cptr = np.searchsorted(C, np.arange(len(paths) + 1))
    def key(s):
        c = C[s]
        if s == cptr[c]: return f"n{int(paths[c][0])}"
        if s == cptr[c + 1] - 1: return f"n{int(paths[c][-1])}"
        return f"s{int(s)}"
    step = np.r_[hav_km(LL[:-1, 0], LL[:-1, 1], LL[1:, 0], LL[1:, 1]), 0.0]
    cum = np.cumsum(np.r_[0.0, step[:-1]])                   # km from sample 0, valid within a chain
    splits = set(int(b) for _, b in conn) | set(int(x) for x in S["sample"] if x >= 0)
    sp = np.array(sorted(splits), dtype=np.int64)
    E = []
    for k, (a, b) in enumerate(zip(st, en)):
        inner = sp[(sp > a) & (sp < b)]
        cuts = np.r_[a, inner, b]
        for x, y in zip(cuts[:-1], cuts[1:]):
            E.append((key(x), key(y), cum[y] - cum[x], int(C[a]), int(x), int(y), "track"))
    for s, t in conn:
        E.append((key(s), key(t), float(hav_km(LL[s, 0], LL[s, 1], LL[t, 0], LL[t, 1])), int(C[s]), int(s), int(t), "connector"))
    E = pd.DataFrame(E, columns=["a", "b", "km", "chain", "s_a", "s_b", "kind"])
    E = E[E.a != E.b].reset_index(drop=True)
    keys = pd.unique(np.r_[E.a.values, E.b.values])
    return E, keys, key


def components(E: pd.DataFrame):
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components
    keys, inv = np.unique(np.r_[E.a.values, E.b.values], return_inverse=True)
    n = len(keys); m = len(E)
    A = csr_matrix((np.ones(m), (inv[:m], inv[m:])), shape=(n, n))
    k, lab = connected_components(A, directed=False)
    km = np.bincount(lab[inv[:m]], weights=E.km.values, minlength=k)
    return dict(keys=keys, label=lab, n=int(k), giant_km_share=round(float(km.max() / km.sum()), 4),
                over_10km=int((km > 10).sum()))


# --------------------------------------------------------------------- calibration and diagnostics
SPACING_BINS = [0, 2, 4, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60, 80, 100, 150, 300]
SNAP_BINS = [0, 25, 50, 75, 100, 150, 200, 300, 500, 1000, 2000, 5000, 1e9]


def spacing_distribution(P, C, km_chain, every: int = 5, min_chain_km: float = 0.3):
    """Calibration for O2: for every chain of at least min_chain_km, the median distance
    from its samples to the nearest sample of another chain (a 1-in-`every` sample of
    points). Double track shows as a mode; the merge distance sits where it has died away."""
    T = cKDTree(P); q = np.arange(0, len(P), every)
    dd, ii = T.query(P[q], k=24, distance_upper_bound=SPACING_BINS[-1])
    other = (C[np.minimum(ii, len(P) - 1)] != C[q][:, None]) & np.isfinite(dd)
    dn = np.where(other, dd, np.inf).min(1)
    med = pd.Series(dn).groupby(C[q]).median()
    med = med[km_chain[med.index] >= min_chain_km]
    cut = pd.cut(med, SPACING_BINS, right=False)
    t = pd.DataFrame(dict(chains=cut.value_counts(sort=False),
                          km=pd.Series(km_chain[med.index], index=med.index).groupby(cut, observed=False).sum()))
    t["chains_per_m"] = t.chains / np.diff(SPACING_BINS)
    t["share_of_peak_density"] = t.chains_per_m / t.chains_per_m.max()
    t.index = [f"{int(i.left)}-{int(i.right)}" for i in t.index]
    t.loc["no other track within 300 m"] = [int(np.isinf(med).sum()), float(km_chain[med.index][np.isinf(med.values)].sum()), np.nan, np.nan]
    return t.round(4)


def snap_distribution(S):
    c = S[S.code.notna()]
    t = pd.cut(c.snap_m, SNAP_BINS, right=True, include_lowest=True).value_counts(sort=False).rename("coded_stations").to_frame()
    t["cumulative_share"] = (t.coded_stations.cumsum() / len(c)).round(4)
    t.index = [f"{int(i.left)}-{int(i.right) if i.right < 1e9 else 'inf'}" for i in t.index]
    return t


def unsnapped_reasons(S, W, xy, keep, reason_of_way, near_m: float = 100.0):
    """For each station left unsnapped: the nearest dropped track within near_m and why
    O1 dropped it, else that the extract has no track there."""
    U = S[S["sample"] < 0].copy()
    pts, rs = [], []
    for i in np.flatnonzero(~keep):
        pts.append(np.c_[lcc(xy[i][:, 0], xy[i][:, 1])]); rs.append(np.full(len(xy[i]), i))
    pts = np.concatenate(pts); rs = np.concatenate(rs)
    X, Y = lcc(U.lon.values, U.lat.values)
    dd, ii = cKDTree(pts).query(np.c_[X, Y])
    U["nearest_dropped_track_m"] = dd.round(1)
    U["why"] = np.where(dd <= near_m, [reason_of_way[rs[i]] for i in ii], "no running track within 100 m in the extract")
    return U[["node_id", "name", "code", "railway", "lon", "lat", "snap_m", "nearest_dropped_track_m", "why"]]


def metro_distance(S, W, xy):
    """Distance (m) from each station to the nearest metro, monorail, light-rail or tram
    track. A snapped station closer to such a track than to its snap may be a metro
    station that happens to stand near the main line; C2 resolves it against the timetable."""
    sub = np.flatnonzero(W.railway.isin(["subway", "monorail", "light_rail", "tram"]).to_numpy())
    pts = np.concatenate([np.c_[lcc(xy[i][:, 0], xy[i][:, 1])] for i in sub])
    X, Y = lcc(S.lon.values, S.lat.values)
    return cKDTree(pts).query(np.c_[X, Y])[0].round(1)


# ===================================================================== C2: O4-O6
import networkx as nx                                                     # noqa: E402

ELECTRIFIED = {"contact_line": "yes", "yes": "yes", "rail": "yes", "no": "no", "construction": "no"}
THROAT = ("track inside a yard or station: service=",)                   # O1 reasons a throat link may use
NOT_RUNNING_NOW = ("not a running line: railway=construction", "not a running line: railway=disused",
                   "not a running line: railway=abandoned")


def chain_attr(W, seg, cid, n_chains, col, norm=None):
    """Length-weighted majority of a way tag per chain, and the share of its km tagged."""
    v = W[col].to_numpy()[seg.way.to_numpy()]
    if norm: v = np.array([norm.get(x) if isinstance(x, str) else None for x in v], dtype=object)
    df = pd.DataFrame(dict(c=cid, v=v, km=seg.km.to_numpy()))
    tot = df.groupby("c").km.sum()
    t = df.dropna(subset=["v"]).groupby(["c", "v"]).km.sum().reset_index().sort_values(["c", "km"], ascending=[True, False])
    top = t.drop_duplicates("c").set_index("c")
    val = np.full(n_chains, None, dtype=object); val[top.index.to_numpy()] = top.v.to_numpy()
    cov = np.zeros(n_chains); tagged = df.dropna(subset=["v"]).groupby("c").km.sum()
    cov[tagged.index.to_numpy()] = (tagged / tot.reindex(tagged.index)).to_numpy()
    return val, cov


CODE_RE = re.compile(r"^[A-Z][A-Z0-9]{0,6}$")


_NAME_DROP = re.compile(r"\b(railway|station|junction|jn|halt|rs|road stn)\b")


def name_key(name) -> str:
    """A station name reduced for matching: lower case, letters only, without 'railway',
    'station', 'junction', 'halt'. '' for no name."""
    if not isinstance(name, str) or not name.strip(): return ""
    t = _NAME_DROP.sub(" ", name.split("(")[0].lower())
    return re.sub(r"[^a-z]", "", t)


def station_nodes(St, timetable_codes, merge_km: float, inside=None, name_km: float = 1.0,
                  neighbours=None, near_km: float = 50.0):
    """Which snapped OSM stations become graph nodes, and their node ids.

    Kept: snapped stations inside India, except a station flagged review_metro that OSM tags
    station=subway/monorail/light_rail, unless a timetable knows its code and a timetable
    neighbour of that code stands within near_km. Codes must look like station codes (a letter, then letters or digits);
    a platform number stored as `ref` is not a code. Id: the station code; an uncoded station
    is OSM:<osm node id>. Same-code stations within merge_km are one node (one station,
    several platforms or lines); further apart is a conflict: code~<osm node id>, listed.
    Stations snapped to the same track point are one station: the one a timetable knows (or
    the first code) is the node, the others become its aliases. An uncoded station named as a
    coded station within name_km joins that station's node (merged_by_name).
    Returns (stations table, conflict codes, aliases {code: node})."""
    s = St[St.vertex.notna()].copy()
    s["code"] = s.code.where(s.code.fillna("").str.match(CODE_RE), None)
    s["in_timetable"] = s.code.isin(timetable_codes)
    rapid = s.station.isin(["subway", "monorail", "light_rail"]) if "station" in s else pd.Series(False, s.index)
    known = s.in_timetable.copy()
    if neighbours is not None:
        # a metro-tagged station carrying a timetable code: the code is its own only if a
        # timetable neighbour of that code stands within near_km (Durgapuri DGPI is a Lucknow
        # Metro station in OSM and a Gwalior-Sheopur halt in the timetable)
        pos = s[s.code.notna()].groupby("code")[["lon", "lat"]].first()
        for i in s.index[s.review_metro & rapid & s.in_timetable]:
            nb = [c for c in neighbours.get(s.at[i, "code"], ()) if c in pos.index]
            known[i] = any(float(hav_km(pos.at[c, "lon"], pos.at[c, "lat"], s.at[i, "lon"], s.at[i, "lat"])) <= near_km
                           for c in nb)
    s["kept"] = ~s.review_metro | ~rapid | known       # near a metro line, but tagged a railway station
    s["in_india"] = True if inside is None else inside[s.index]
    s["kept"] &= s.in_india
    s["graph_node"] = None
    conflicts = []
    k = s[s.kept & s.code.notna()]
    for code, g in k.groupby("code"):
        lo, la = g.lon.values, g.lat.values
        far = max((hav_km(lo[i], la[i], lo[j], la[j]) for i in range(len(g)) for j in range(i + 1, len(g))), default=0.0)
        if far <= merge_km:
            s.loc[g.index, "graph_node"] = code
        else:
            s.loc[g.index, "graph_node"] = [f"{code}~{n}" for n in g.node_id]; conflicts.append(code)
    nc = s.kept & s.code.isna()
    s.loc[nc, "graph_node"] = ["OSM:" + str(n) for n in s.loc[nc, "node_id"]]
    # an uncoded station with the name of a coded station within name_km is a second point of
    # that station (another line's platforms, mapped twice): it joins that station's node
    s["merged_by_name"] = False
    coded = s[s.kept & s.code.notna() & ~s.graph_node.fillna("").str.contains("~")]
    keys = {}
    for r in coded.itertuples():
        for nm in (r.name, getattr(r, "name_en", None)):
            k_ = name_key(nm)
            if k_: keys.setdefault(k_, []).append((r.lon, r.lat, r.graph_node))
    for i in s.index[nc]:
        best = None
        for nm in (s.at[i, "name"], s.at[i, "name_en"] if "name_en" in s else None):
            for lo, la, g in keys.get(name_key(nm), ()):
                d_ = float(hav_km(lo, la, s.at[i, "lon"], s.at[i, "lat"]))
                if d_ <= name_km and (best is None or d_ < best[0]): best = (d_, g)
        if best:
            s.at[i, "graph_node"] = best[1]; s.at[i, "merged_by_name"] = True
    # two uncoded stations of one name within name_km: one station mapped twice
    left = [i for i in s.index[nc] if not s.at[i, "merged_by_name"] and name_key(s.at[i, "name"])]
    left.sort(key=lambda i: s.at[i, "node_id"])
    for a_ in range(len(left)):
        i = left[a_]
        if s.at[i, "merged_by_name"]: continue
        for j in left[a_ + 1:]:
            if s.at[j, "merged_by_name"] or name_key(s.at[j, "name"]) != name_key(s.at[i, "name"]): continue
            if float(hav_km(s.at[i, "lon"], s.at[i, "lat"], s.at[j, "lon"], s.at[j, "lat"])) <= name_km:
                s.at[j, "graph_node"] = s.at[i, "graph_node"]; s.at[j, "merged_by_name"] = True
    aliases = {}
    kk = s[s.kept]
    for v, g in kk.groupby("vertex"):
        ids = list(dict.fromkeys(g.graph_node))
        if len(ids) < 2: continue
        rank = sorted(ids, key=lambda x: (not (x in timetable_codes), x.startswith("OSM:"), "~" in x, x))
        keep_id = rank[0]
        for other in rank[1:]:
            if not other.startswith("OSM:") and "~" not in other: aliases[other] = keep_id
            s.loc[s.kept & (s.graph_node == other) & (s.vertex == v), "graph_node"] = keep_id
    # a code merged away everywhere is an alias; a code still a node elsewhere is not
    still = set(s.loc[s.kept, "graph_node"])
    aliases = {a: b for a, b in aliases.items() if a not in still}
    return s, conflicts, aliases


def vertex_graph(E, vmap):
    """Vertex graph of the collapsed network, with station vertices renamed to their node id
    (so same-code vertices become one node). Parallel edges: the shorter stays. Every
    station is a node, even one left with no track."""
    G = nx.Graph()
    G.add_nodes_from(set(vmap.values()))
    for i, (a, b, km) in enumerate(zip(E.a.values, E.b.values, E.km.values)):
        a, b = vmap.get(a, a), vmap.get(b, b)
        if a == b: continue
        if G.has_edge(a, b) and G[a][b]["km"] <= km: continue
        G.add_edge(a, b, km=float(km), rows=(i,), via=frozenset())
    return G


def prune(G, protect):
    """Remove dangling track that ends without reaching a station. Returns km removed."""
    km = 0.0
    while True:
        d1 = [n for n, d in G.degree() if d <= 1 and n not in protect]
        if not d1: return km
        km += sum(d["km"] for n in d1 for *_, d in G.edges(n, data=True))
        G.remove_nodes_from(d1)


def splice(G, protect):
    """Remove every non-station vertex of degree 2, joining its two edges along the track.
    Where a join duplicates an existing edge, the shorter stays. Returns (km, count) dropped."""
    dropped, n_par = 0.0, 0
    todo = sorted(n for n, d in G.degree() if d == 2 and n not in protect)
    while todo:
        n = todo.pop()
        if n not in G or n in protect or G.degree(n) != 2: continue
        (a, da), (b, db) = [(x, G[n][x]) for x in sorted(G[n])]
        km = da["km"] + db["km"]; rows = da["rows"] + db["rows"]
        via = da.get("via", frozenset()) | db.get("via", frozenset())
        G.remove_node(n)
        if G.has_edge(a, b):
            n_par += 1
            if G[a][b]["km"] <= km: dropped += km
            else: dropped += G[a][b]["km"]; G[a][b].update(km=km, rows=rows, via=via)
            for x in (a, b):
                if x not in protect and G.degree(x) == 2: todo.append(x)
        else:
            G.add_edge(a, b, km=km, rows=rows, via=via)
    return dropped, n_par


def drop_bypasses(G, stations, max_km, ratio, slack_km):
    """An edge of at most max_km whose ends are also joined by another path no longer than
    ratio x its length + slack_km is a second line around a station or a leftover parallel.
    It goes if that other path passes a station; otherwise the longer of the two goes."""
    n, km = 0, 0.0
    for a, b, d in sorted(G.edges(data=True), key=lambda t: (-t[2]["km"], t[0], t[1])):
        if not G.has_edge(a, b) or d["km"] > max_km: continue
        e = dict(G[a][b]); G.remove_edge(a, b)
        try:
            L, path = nx.single_source_dijkstra(G, a, b, cutoff=ratio * e["km"] + slack_km, weight="km")
        except nx.NetworkXNoPath:
            L = None
        if L is not None and (any(p in stations for p in path[1:-1]) or e["km"] >= L):
            n += 1; km += e["km"]
        else:
            G.add_edge(a, b, **e)
    return n, km


def o4_places(G, stations, place_km: float):
    """Track points within place_km of each other along the track are one place (P2 pass 2).

    1  junction clusters: junctions joined by sections of at most place_km become one
       junction, placed at the cluster's most central point
    2  a junction within place_km of a station becomes part of that station (the nearest)
    The edges leaving a merged point keep their along-track length, plus the distance inside
    the cluster from where they leave to the point that stands for it. Returns a report."""
    def edges_from(x):
        return [(y, d) for y, d in G[x].items()]
    def attach(rep, y, km, d):
        rows, via = d.get("rows", ()), d.get("via", frozenset())
        if G.has_edge(rep, y):
            if G[rep][y]["km"] > km: G[rep][y].update(km=km, rows=rows, via=via)
        else:
            G.add_edge(rep, y, km=km, rows=rows, via=via)
    J = [n for n in G if n not in stations]
    S = nx.Graph(); S.add_nodes_from(J)
    S.add_edges_from((u, v, d) for u, v, d in G.edges(data=True)
                     if u not in stations and v not in stations and d["km"] <= place_km)
    clusters, merged = 0, 0
    place = {}
    for comp in sorted((c for c in nx.connected_components(S) if len(c) > 1), key=lambda c: min(c)):
        sub = S.subgraph(comp)
        dist = dict(nx.all_pairs_dijkstra_path_length(sub, weight="km"))
        rep = min(sorted(comp), key=lambda x: max(dist[x].values()))
        ext = [(y, dict(d), dist[rep][x]) for x in comp for y, d in edges_from(x) if y not in comp]
        G.remove_nodes_from(comp - {rep}); clusters += 1; merged += len(comp) - 1
        for x in comp - {rep}: place[x] = rep
        for y, d, off in ext: attach(rep, y, d["km"] + off, d)
    absorbed = 0
    for j in sorted(n for n in G if n not in stations):
        if j not in G: continue
        near = sorted((d["km"], s_) for s_, d in G[j].items() if s_ in stations)
        if not near or near[0][0] > place_km: continue
        off, st = near[0]
        for y, d in [(y, dict(d)) for y, d in edges_from(j) if y != st]:
            attach(st, y, d["km"] + off, d)
        G.remove_node(j); absorbed += 1; place[j] = st
    km, n = splice(G, stations)
    def final(x):
        while x in place: x = place[x]
        return x
    place = {x: final(x) for x in place}
    return dict(place_km=place_km, junction_clusters=clusters, junctions_merged=merged,
                junctions_absorbed_into_stations=absorbed, parallel_after=n, parallel_km_after=round(km, 1)), place


def o4_contract(G, stations, bypass_max_km, bypass_ratio, bypass_slack_km):
    """O4: contract the track-level graph (after O5's joins) to stations and junctions."""
    rep = dict(track_graph_km=round(sum(d["km"] for *_, d in G.edges(data=True)), 1))
    rep["dangling_km_pruned"] = round(prune(G, stations), 1)
    nost = [c for c in nx.connected_components(G) if not c & stations]
    rep["stationless_pieces"] = len(nost)
    rep["stationless_km"] = round(sum(d["km"] for c in nost for *_, d in G.subgraph(c).edges(data=True)), 1)
    G.remove_nodes_from(set().union(*nost) if nost else set())
    km, n = splice(G, stations); rep["parallel_routes_dropped"] = n; rep["parallel_km_dropped"] = round(km, 1)
    tb, tk = 0, 0.0
    while True:
        b, bk = drop_bypasses(G, stations, bypass_max_km, bypass_ratio, bypass_slack_km)
        pk = prune(G, stations); km, n = splice(G, stations)
        tb += b; tk += bk + pk; rep["parallel_routes_dropped"] += n; rep["parallel_km_dropped"] += round(km, 1)
        if b == 0 and n == 0: break
    rep["bypasses_dropped"] = tb; rep["bypass_km_dropped"] = round(tk, 1)
    rep["parallel_km_dropped"] = round(rep["parallel_km_dropped"], 1)
    return G, stations, rep


# --------------------------------------------------------------------- O5 stitch
def full_track_graph(W, refs, xy):
    """Every OSM rail way, kept or dropped, as one node graph: the search space for joins."""
    ids = np.concatenate(refs)
    lo = np.concatenate([p[:, 0] for p in xy]); la = np.concatenate([p[:, 1] for p in xy])
    nid, first = np.unique(ids, return_index=True)
    U, V, R = [], [], []
    for i, r in enumerate(refs):
        a = np.searchsorted(nid, r); U.append(a[:-1]); V.append(a[1:]); R.append(np.full(len(r) - 1, i))
    U, V, R = np.concatenate(U), np.concatenate(V), np.concatenate(R)
    km = hav_km(lo[first][U], la[first][U], lo[first][V], la[first][V])
    return dict(nid=nid, lon=lo[first], lat=la[first], U=U, V=V, way=R, km=km, look=SegLookup(U, V, len(nid)))


class SegLookup:
    """(node a, node b) -> index of the first segment joining them; numpy, not a dict (V2-15)."""
    def __init__(self, U, V, n):
        self.n = np.int64(n)
        k = np.minimum(U, V).astype(np.int64) * self.n + np.maximum(U, V)
        order = np.argsort(k, kind="stable"); self.k = k[order]; self.i = order
    def __getitem__(self, ab):
        a, b = ab; q = np.int64(min(a, b)) * self.n + max(a, b)
        j = np.searchsorted(self.k, q)
        if j >= len(self.k) or self.k[j] != q: raise KeyError(ab)
        return int(self.i[j])


def near_cells(P, idx, pts, cell_m=2000.0):
    """The samples idx whose grid cell (cell_m) is at or next to a cell holding one of pts:
    a KD tree over these answers queries near pts exactly as one over all of idx (V2-15)."""
    cp = np.floor(pts / cell_m).astype(np.int64)
    keys = set()
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            keys.update(map(tuple, (cp + [dx, dy]).tolist()))
    ci = np.floor(P[idx] / cell_m).astype(np.int64)
    kk = ci[:, 0] * 10_000_000 + ci[:, 1]
    want = np.array(sorted(a * 10_000_000 + b for a, b in keys), dtype=np.int64)
    return idx[np.isin(kk, want)]


def _adj(F, allowed_way):
    from scipy.sparse import csr_matrix
    m = allowed_way[F["way"]]
    U, V, w = F["U"][m], F["V"][m], F["km"][m] + 1e-9
    n = len(F["nid"])
    return csr_matrix((np.r_[w, w], (np.r_[U, V], np.r_[V, U])), shape=(n, n))


def timetable_pairs(root: Path, years=("2017", "2024")):
    """Consecutive stops (code a, code b, km) in the timetables of the given years: 2017
    (data.gov.in, GODL-India) and 2024 (IIT Kharagpur RSTGCN, no licence stated). trains counts
    the trains of those years; trains_2024 the 2024 ones (0 when 2024 is not used)."""
    parts = []
    if "2024" in years:
        X = root / "external_data/iitkgp_rstgcn_network_2024/Indian-Railway-Network-and-Delays/train_routes_Sep2024.csv"
        r = pd.read_csv(X, dtype=str, usecols=["trainNumber", "stnSerialNumber", "station_code", "distance"])
        parts.append(r.assign(t="24:" + r.trainNumber, q=r.stnSerialNumber.astype(int), c=r.station_code.str.strip(),
                              km=pd.to_numeric(r.distance, errors="coerce"))[["t", "q", "c", "km"]])
    if "2017" in years:
        t = pd.read_csv(root / "external_data/timetable_2017_datagovin/Train_details_22122017.csv", dtype=str,
                        usecols=["Train No", "SEQ", "Station Code", "Distance"])
        parts.append(t.assign(t="17:" + t["Train No"], q=pd.to_numeric(t.SEQ, errors="coerce"), c=t["Station Code"].str.strip(),
                              km=pd.to_numeric(t.Distance, errors="coerce"))[["t", "q", "c", "km"]])
    a = pd.concat(parts).dropna().sort_values(["t", "q"])
    nxt = a.shift(-1)
    m = (nxt.t == a.t) & (nxt.c != a.c)
    p = pd.DataFrame(dict(a=a.c[m].values, b=nxt.c[m].values, km=(nxt.km[m] - a.km[m]).values, t=a.t[m].values))
    p = p[p.km > 0]
    k = np.where(p.a < p.b, p.a + "|" + p.b, p.b + "|" + p.a)
    return p.assign(k=k, y24=p.t.str.startswith("24:")).groupby("k").agg(
        a=("a", "first"), b=("b", "first"), km=("km", "median"), trains=("t", "nunique"),
        trains_2024=("y24", "sum")).reset_index(drop=True)


class Splitter:
    """Places new vertices on the track-level graph at exact track positions.

    Every track edge of the vertex graph is one row of the C1 network table, covering
    samples s_a..s_b of one chain; a vertex at sample t splits it, and the two halves keep
    their measured along-track lengths."""

    def __init__(self, G, E, vm, LL):
        self.G = G
        step = np.r_[hav_km(LL[:-1, 0], LL[:-1, 1], LL[1:, 0], LL[1:, 1]), 0.0]
        self.cum = np.cumsum(np.r_[0.0, step[:-1]])
        self.Ea = [vm.get(x, x) for x in E.a.values]; self.Eb = [vm.get(x, x) for x in E.b.values]
        self.s_a, self.s_b, self.kind = E.s_a.values, E.s_b.values, E.kind.values
        self.splits = {}
        track = np.flatnonzero(self.kind == "track")
        self.row_of = np.full(len(LL), -1)
        for i in track:
            self.row_of[self.s_a[i]:self.s_b[i] + 1] = i

    def at(self, i, t, name=None):
        """The vertex at sample t of row i, splitting the edge that holds it (None if that
        row's edge is not in the graph, e.g. it lost to a shorter parallel)."""
        G, cum = self.G, self.cum
        if t == self.s_a[i]: return self.Ea[i]
        if t == self.s_b[i]: return self.Eb[i]
        sp = self.splits.setdefault(i, {})
        if t in sp: return sp[t]
        pts = sorted([self.s_a[i], self.s_b[i]] + list(sp))
        lo = max(x for x in pts if x < t); hi = min(x for x in pts if x > t)
        A = self.Ea[i] if lo == self.s_a[i] else sp[lo]; B = self.Eb[i] if hi == self.s_b[i] else sp[hi]
        if not G.has_edge(A, B) or i not in G[A][B]["rows"]: return None
        X = name or f"s{int(t)}"
        d = G[A][B]; via = d.get("via", frozenset())
        G.remove_edge(A, B)
        G.add_edge(A, X, km=float(cum[t] - cum[lo]), rows=(i,), via=via)
        G.add_edge(X, B, km=float(cum[hi] - cum[t]), rows=(i,), via=via)
        sp[t] = X
        return X


def o3b_wikidata(G, sp, s, root: Path, timetable_codes, P, snap_m: float, alias_m: float, stations: set,
                 name_km: float = 1.0, name_only_codes=()):
    """O3b: stations the timetables name but OSM has no coded station for.

    Placed from Wikidata (CC0). If a kept OSM station lies within alias_m of the Wikidata
    point, the timetable code is an alias of that station (a renamed or re-spelt code). If an
    uncoded OSM station with the item's name (or an alternative name) lies within name_km,
    that station carries the code (alias_by_name); this alone applies to name_only_codes, codes
    Wikidata has but no timetable used in the build. Otherwise, if the point is within snap_m of kept track, a station is inserted there.
    Otherwise the code stays unresolved. Returns (aliases, inserted rows, report)."""
    w = pd.read_csv(root / "external_data/wikidata_stations.csv")
    xy = w.coord.str.extract(r"Point\(([-\d.]+) ([-\d.]+)\)").astype(float)
    w = w.assign(lon=xy[0], lat=xy[1]).dropna(subset=["lon"]).drop_duplicates("code")
    k = s[s.kept & s.code.notna() & ~s.graph_node.str.contains("~", na=False)]
    have = set(s.loc[s.kept & s.code.notna(), "code"])      # conflict codes are present, not missing
    miss = w[w.code.isin(set(timetable_codes) | set(name_only_codes)) & ~w.code.isin(have)].sort_values("code").reset_index(drop=True)
    in_tt = miss.code.isin(set(timetable_codes)).to_numpy()
    kx, ky = lcc(k.lon.values, k.lat.values); KT = cKDTree(np.c_[kx, ky])
    mx, my = lcc(miss.lon.values, miss.lat.values)
    dk, jk = KT.query(np.c_[mx, my])
    tr = np.flatnonzero(sp.row_of >= 0)
    tr = near_cells(P, tr, np.c_[mx, my]) if len(mx) else tr[:0]
    TT = cKDTree(P[tr]) if len(tr) else None
    dt, jt = (TT.query(np.c_[mx, my], k=8) if TT is not None else (np.full((len(mx), 8), np.inf), np.zeros((len(mx), 8), int)))
    # an uncoded OSM station with the Wikidata item's name, within name_km: the code's station
    u = s[s.kept & s.code.isna() & s.graph_node.fillna("").str.startswith("OSM:")]
    ukeys = {}
    for r in u.itertuples():
        for nm in (r.name, getattr(r, "name_en", None)):
            if name_key(nm): ukeys.setdefault(name_key(nm), []).append((r.lon, r.lat, r.graph_node))
    def by_name(r):
        labels = [r.itemLabel] + [x for x in str(r.get("altLabels") or "").replace("|", ",").split(",") if x.strip()]
        best = None
        for nm in labels:
            for lo, la, g in ukeys.get(name_key(nm), ()):
                d_ = float(hav_km(lo, la, r.lon, r.lat))
                if d_ <= name_km and (best is None or d_ < best[0]): best = (d_, g)
        return best
    aliases, ins, fate = {}, [], []
    for n, r in miss.iterrows():
        if in_tt[n] and dk[n] <= alias_m:
            aliases[r.code] = k.graph_node.values[jk[n]]; fate.append("alias"); continue
        b_ = by_name(r)
        if b_ and b_[1] not in aliases.values():
            aliases[r.code] = b_[1]; fate.append("alias_by_name"); continue
        if not in_tt[n]:                       # a code no timetable has: only a name match places it
            fate.append("not_in_timetable"); continue
        placed = None
        for d_, j_ in zip(dt[n], jt[n]):
            if d_ > snap_m: break
            t = tr[j_]; v = sp.at(sp.row_of[t], t, name=r.code)
            if v is not None:
                if v != r.code:                       # landed on an existing vertex: rename it
                    if v in G and v not in stations:
                        nx.relabel_nodes(G, {v: r.code}, copy=False)
                        for row in sp.splits.values():
                            for kk, vv in list(row.items()):
                                if vv == v: row[kk] = r.code
                        sp.Ea = [r.code if x == v else x for x in sp.Ea]; sp.Eb = [r.code if x == v else x for x in sp.Eb]
                    else:
                        aliases[r.code] = v; placed = "alias"; break
                stations.add(r.code)
                placed = "inserted"; ins.append(dict(code=r.code, name=r.itemLabel, lon=r.lon, lat=r.lat,
                                                     snap_m=round(float(d_), 1), wikidata=r["item"], sample=int(t))); break
        fate.append(placed or "unresolved")
    miss["fate"] = fate; miss["nearest_osm_station_m"] = dk.round(1); miss["nearest_track_m"] = dt[:, 0].round(1)
    rep = dict(timetable_codes_without_osm_station=int(in_tt.sum()),
               wikidata_only_codes_checked_by_name=int((~in_tt).sum()),
               **{f"wikidata_{k_}": int(v) for k_, v in miss.fate.value_counts().items() if k_ != "not_in_timetable"})
    return aliases, pd.DataFrame(ins), miss, rep


def o5_stitch(G, sp, E, s, P, LL, F, reason, pairs, nodes, stations, code_of, extra_pos, throat_max_km: float,
              search_km: float, share_m: float, band=(0.9, 1.0, 1.15, 1.0), max_rounds: int = 6):
    """O5: join the pieces of the track-level graph to the main network, on evidence.

    A  throat   the piece reaches the main network along OSM running track, using at most
                throat_max_km of yard or station track (dropped in O1) to get there
    A2 shared station   the piece's track ends, or one of its stations stands, within
                share_m of a main-network station: one station, two gauges or two sets of
                platforms, joined at that station (the join's length is that short distance)
    B  timetable + track   a timetabled train stops consecutively in the piece and
                in the main network, and OSM has track between them that O1 set aside as
                not running (construction, disused, abandoned); the track gap must not
                exceed that timetable distance
    C  timetable only   such a train exists but OSM has no track for it: the two
                stations are joined at the timetable distance, if it lies within
                [0.9 x straight line - 1 km, 1.15 x straight line + 1 km] (the v1.3 band)

    A join lands at its true point on the track (an edge is split there), and its length
    is measured along the OSM track used. Returns the list of joins."""
    from scipy.sparse.csgraph import dijkstra
    s_a, s_b, kind = sp.s_a, sp.s_b, sp.kind
    vertex_at = sp.at
    PT = cKDTree(P); row_of = sp.row_of
    FX, FY = lcc(F["lon"], F["lat"]); FT = cKDTree(np.c_[FX, FY])
    reason = np.asarray(reason)
    ok_A = (reason == "") | np.char.startswith(reason.astype(str), THROAT[0])
    ok_B = ok_A | np.isin(reason, NOT_RUNNING_NOW)
    adjA, adjB = _adj(F, ok_A), _adj(F, ok_B)
    pk = {}
    for r in pairs[pairs.trains > 0].itertuples():
        pk.setdefault(r.a, []).append((r.b, r.km, r.trains)); pk.setdefault(r.b, []).append((r.a, r.km, r.trains))
    sk = s[s.kept].drop_duplicates("graph_node").set_index("graph_node")[["lon", "lat"]]
    def where(v):
        if v in sk.index: return sk.at[v, "lon"], sk.at[v, "lat"]
        if v in extra_pos: return extra_pos[v]
        i = int(v[1:])
        return (LL[i, 0], LL[i, 1]) if v[0] == "s" else (nodes.lon.values[i], nodes.lat.values[i])
    joins = []
    def rows_of(nodes_):
        out = set()
        for u, v, d in G.subgraph(nodes_).edges(data=True):
            for i in d["rows"]:
                if kind[i] == "track": out.add(i)
        return out
    def full_nodes(rows, extra_samples):
        """OSM nodes (full graph) lying on these rows' track, with the (row, sample) under them."""
        smp = [np.arange(s_a[i], s_b[i] + 1) for i in rows]
        rid = [np.full(s_b[i] - s_a[i] + 1, i) for i in rows]
        if extra_samples:
            smp.append(np.array([t for t, _ in extra_samples])); rid.append(np.array([-1] * len(extra_samples)))
        if not smp: return np.array([], int), np.array([], int), np.array([], int)
        smp = np.concatenate(smp); rid = np.concatenate(rid)
        dd, ii = FT.query(P[smp], distance_upper_bound=6.0)
        m = np.isfinite(dd)
        return ii[m], rid[m], smp[m]
    for rnd in range(max_rounds):
        comps = sorted(nx.connected_components(G), key=lambda c: (-len(c & stations), min(c)))
        giant = comps[0]
        frags = [c for c in comps[1:] if c & stations]
        if not frags: break
        gi, grow, gsmp = full_nodes(rows_of(giant), [])
        src_of = {}
        for a, b, c in zip(gi, grow, gsmp): src_of.setdefault(a, (b, c))
        srcs = np.array(sorted(src_of))
        dA, pA, sA = dijkstra(adjA, directed=False, indices=srcs, min_only=True, return_predecessors=True, limit=search_km)
        dB, pB, sB = dijkstra(adjB, directed=False, indices=srcs, min_only=True, return_predecessors=True, limit=search_km)
        gcodes = {code_of[n] for n in giant if n in code_of}
        gnames = sorted(n for n in giant if n in stations)
        gXY = np.array([lcc(*where(n)) for n in gnames])
        gT = cKDTree(gXY)
        grows = rows_of(giant)
        def gnames_near(f_):
            """main-network stations within share_m of any sample of the fragment's track"""
            smp = [np.arange(s_a[i], s_b[i] + 1) for i in rows_of(f_)]
            if not smp: return []
            hit = gT.query_ball_point(P[np.concatenate(smp)], share_m)
            return sorted({gnames[j] for h in hit for j in h})
        made = 0
        for f in frags:
            st_f = sorted(f & stations)
            lone = [(int(s.loc[(s.graph_node == n) & s.kept, "sample"].iloc[0]), n) for n in st_f
                    if G.degree(n) == 0 and n in sk.index]
            fi, frow, fsmp = full_nodes(rows_of(f), lone)
            ev = [(a, b, km, tr) for a in (code_of.get(n) for n in st_f) if a for b, km, tr in pk.get(a, []) if b in gcodes]
            ev.sort(key=lambda t: (-t[3], t[0], t[1]))
            done = False
            def try_path(stage, dist, pred):
                if len(fi) == 0: return False
                k = int(np.argmin(dist[fi]))
                if not np.isfinite(dist[fi][k]): return False
                t = fi[k]; path = [t]
                while pred[path[-1]] >= 0: path.append(pred[path[-1]])
                by = {}
                for a, b in zip(path, path[1:]):
                    w = F["look"][(int(min(a, b)), int(max(a, b)))]; rr = reason[F["way"][w]] or "running line"
                    by[rr] = by.get(rr, 0.0) + float(F["km"][w])
                dropped = sum(v for k_, v in by.items() if k_ != "running line")
                if stage == "A" and dropped > throat_max_km: return False
                if stage == "B" and float(dist[t]) > ev[0][2] + 2.0: return False
                gr, gt = src_of[path[-1]]
                X = vertex_at(gr, gt)
                Y = vertex_at(frow[k], fsmp[k]) if frow[k] >= 0 else dict((smp, n) for smp, n in lone)[fsmp[k]]
                if X is None or Y is None or X == Y: return False
                # the track path runs between OSM nodes; the vertices sit on samples beside them
                (x1, y1), (x2, y2) = where(X), where(Y)
                km = max(float(dist[t]), float(hav_km(x1, y1, x2, y2)))
                G.add_edge(X, Y, km=km, rows=(), via=frozenset({"join_" + stage}))
                joins.append(dict(round=rnd, stage=stage, a=X, b=Y, km=round(km, 4),
                                  stations_joined=len(st_f), example=st_f[0],
                                  track_used={k_: round(v, 3) for k_, v in sorted(by.items())},
                                  evidence=None if stage == "A" else f"{ev[0][0]}-{ev[0][1]} {ev[0][2]} km, {ev[0][3]} timetabled trains"))
                return True
            done = try_path("A", dA, pA)
            if not done:                                   # A2: a station shared with the main network
                cand = [v for v in f if G.degree(v) <= 1 or v in stations]
                best = None
                for v in sorted(cand):
                    lo, la = where(v); x, y = lcc(lo, la)
                    d_, j_ = gT.query([x, y], distance_upper_bound=share_m)
                    if np.isfinite(d_) and (best is None or d_ < best[0]): best = (float(d_), v, gnames[j_])
                # ... or a station of one side stands within share_m of the other side's track
                # (one station, two gauges, where neither line ends at the other's station point)
                frows = rows_of(f)
                def near_track(names, rows_ok):
                    out = None
                    for v in names:
                        if v not in sk.index and v not in extra_pos: continue
                        x, y = lcc(*where(v))
                        for t in sorted(PT.query_ball_point([x, y], share_m)):
                            i = row_of[t]
                            if i < 0 or i not in rows_ok: continue
                            d_ = float(np.hypot(P[t, 0] - x, P[t, 1] - y))
                            if out is None or d_ < out[0]: out = (d_, v, i, t)
                    return out
                cands = []
                if best: cands.append(("vertex", best))
                a = near_track(st_f, grows)                # fragment station beside main-network track
                if a: cands.append(("f_station", a))
                b = near_track(gnames_near(f), frows)      # main-network station beside the fragment's track
                if b: cands.append(("g_station", b))
                best = None                                # (metres, fragment side, main side, evidence)
                for kind_, c in sorted(cands, key=lambda z: (z[1][0], z[0])):
                    if kind_ == "vertex":
                        best = (c[0], c[1], c[2], f"{c[1]} stands {c[0]:.0f} m from main-network station {c[2]}")
                        break
                    X = vertex_at(c[2], c[3])
                    if X is None or X == c[1]: continue
                    if kind_ == "f_station":
                        best = (c[0], c[1], X, f"station {c[1]} stands {c[0]:.0f} m from main-network track")
                    else:
                        best = (c[0], X, c[1], f"main-network station {c[1]} stands {c[0]:.0f} m from the piece's track")
                    break
                if best:
                    G.add_edge(best[2], best[1], km=best[0] / 1000, rows=(), via=frozenset({"join_A2"}))
                    joins.append(dict(round=rnd, stage="A2", a=best[2], b=best[1], km=round(best[0] / 1000, 4),
                                      stations_joined=len(st_f), example=st_f[0], track_used={},
                                      evidence=best[3]))
                    done = True
            if not done and ev:
                done = try_path("B", dB, pB)
            if done: made += 1; continue
            if done or not ev: continue
            for a, b, km, tr in ev:
                (lo1, la1), (lo2, la2) = where(a), where(b)
                ch = float(hav_km(lo1, la1, lo2, la2))
                if band[0] * ch - band[1] <= km <= band[2] * ch + band[3]:
                    km = max(float(km), round(ch, 4))      # whole-km timetable: never below the straight line
                    G.add_edge(a, b, km=km, rows=(), via=frozenset({"join_C"}))
                    joins.append(dict(round=rnd, stage="C", a=a, b=b, km=float(km), stations_joined=len(st_f),
                                      example=st_f[0], track_used={},
                                      evidence=f"{a}-{b} {km} km, {tr} timetabled trains; straight line {ch:.2f} km"))
                    made += 1; break
        if made == 0: break
    return joins


def in_india(lon, lat, geojson: Path):
    """Inside the Survey of India outline (datameet; used as a filter only, not copied)."""
    import json as _j
    g = _j.loads(Path(geojson).read_text())
    lon = np.asarray(lon, float); lat = np.asarray(lat, float); inside = np.zeros(len(lon), bool)
    for f in g["features"]:
        geom = f["geometry"]; polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            ext = np.asarray(poly[0])
            bb = (lon >= ext[:, 0].min()) & (lon <= ext[:, 0].max()) & (lat >= ext[:, 1].min()) & (lat <= ext[:, 1].max())
            idx = np.flatnonzero(bb & ~inside)
            if idx.size == 0: continue
            hit = np.zeros(idx.size, bool)
            for ring in poly:
                r = np.asarray(ring); x1, y1 = r[:-1, 0], r[:-1, 1]; x2, y2 = r[1:, 0], r[1:, 1]
                for c0 in range(0, idx.size, 32):           # bounded memory on a 120k-vertex ring
                    sl = idx[c0:c0 + 32]
                    px, py = lon[sl][:, None], lat[sl][:, None]
                    cross = ((y1 > py) != (y2 > py)) & (px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-300) + x1)
                    hit[c0:c0 + 32] ^= (cross.sum(1) % 2 == 1)
            inside[idx] |= hit
    return inside


def o5_throat(G, sp, F, reason, P, d_m: float, max_km: float, ratio: float, slack_km: float,
              short_gap_km: float = 0.0):
    """O5a: station throats. Inside stations, OSM often carries the through route over
    crossovers and station tracks tagged service=crossover or siding, which O1 set aside.
    Where such track joins two points of kept running line, and the kept network between
    those two points is longer than ratio x the throat path + slack_km, the throat path
    (at most max_km of OSM track) is added at its measured length. Geometry and OSM
    topology only; no timetable is used."""
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra, connected_components
    reason = np.asarray(reason)
    wr = reason[F["way"]]
    svc = np.char.startswith(wr.astype(str), THROAT[0])
    if short_gap_km > 0:
        # a short way tagged as under construction or disused inside a running line (P2 pass 1,
        # Udaipura-Tikamgarh: 30 m of `construction` broke a line with 2024 trains)
        way_km = np.bincount(F["way"], weights=F["km"], minlength=int(F["way"].max()) + 1)
        gap = np.isin(wr, ["not a running line: railway=construction", "not a running line: railway=disused"])
        svc |= gap & (way_km[F["way"]] <= short_gap_km)
    kept = wr == ""
    n = len(F["nid"])
    U, V, w = F["U"][svc], F["V"][svc], F["km"][svc] + 1e-9
    A = csr_matrix((np.r_[w, w], (np.r_[U, V], np.r_[V, U])), shape=(n, n))
    touch_svc = np.zeros(n, bool); touch_svc[U] = True; touch_svc[V] = True
    touch_run = np.zeros(n, bool); touch_run[F["U"][kept]] = True; touch_run[F["V"][kept]] = True
    att = np.flatnonzero(touch_svc & touch_run)
    _, lab = connected_components(A, directed=False)
    # kept samples whose edge is in the graph, to place attachments on the track
    good = np.flatnonzero(sp.row_of >= 0)
    FX, FY = lcc(F["lon"][att], F["lat"][att])
    good = near_cells(P, good, np.c_[FX, FY])
    T = cKDTree(P[good])
    dd, jj = T.query(np.c_[FX, FY], distance_upper_bound=d_m)
    place = {int(a): int(good[j]) for a, d, j in zip(att, dd, jj) if np.isfinite(d)}
    groups = {}
    for a in att:
        if int(a) in place: groups.setdefault(lab[a], []).append(int(a))
    cum = sp.cum
    def where_on_graph(t):
        """(row, sample) -> the edge (A, B) of G holding t and the offsets to each end."""
        i = sp.row_of[t]
        spl = sp.splits.get(i, {})
        if t == sp.s_a[i]: return ((sp.Ea[i], 0.0),)
        if t == sp.s_b[i]: return ((sp.Eb[i], 0.0),)
        if t in spl: return ((spl[t], 0.0),)
        pts = sorted([sp.s_a[i], sp.s_b[i]] + list(spl))
        lo = max(x for x in pts if x < t); hi = min(x for x in pts if x > t)
        A_ = sp.Ea[i] if lo == sp.s_a[i] else spl[lo]; B_ = sp.Eb[i] if hi == sp.s_b[i] else spl[hi]
        return (A_, cum[t] - cum[lo]), (B_, cum[hi] - cum[t])
    # V2-15: nodes sorted by component, so each component is one diagonal block of A
    order = np.argsort(lab, kind="stable"); inv = np.empty_like(order); inv[order] = np.arange(len(order))
    starts = np.searchsorted(lab[order], np.arange(lab.max() + 2))
    Ap = A[order][:, order].tocsr()
    pl = np.full(n, -1, dtype=np.int64)
    for a_, t_ in place.items(): pl[a_] = t_
    PA, PB, PD = [], [], []
    for g, members in groups.items():
        if len(members) < 2: continue
        s0, s1 = starts[g], starts[g + 1]
        mem = np.asarray(members, dtype=np.int64)
        dist = dijkstra(Ap[s0:s1, s0:s1], directed=False, indices=inv[mem] - s0, limit=max_km)
        i, j = np.triu_indices(len(mem), 1)
        ds = dist[i, inv[mem[j]] - s0]
        ok = np.isfinite(ds) & (pl[mem[i]] != pl[mem[j]])
        PA.append(mem[i][ok]); PB.append(mem[j][ok]); PD.append(ds[ok])
    pairs = []
    if PA:
        PA, PB, PD = np.concatenate(PA), np.concatenate(PB), np.concatenate(PD)
        pairs = [(float(d_), int(a_), int(b_)) for d_, a_, b_ in zip(PD, PA, PB)]
    pairs.sort()
    # V2-15: a first pass on a snapshot of the graph, in C. Adding throats only shortens
    # distances, so a pair the snapshot already serves needs no throat later either; only the
    # pairs that fail it are checked again, in order, on the live graph. Same result, faster.
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra as _dij
    idx = {v: i for i, v in enumerate(G)}
    uu, vv, ww = [], [], []
    for u_, v_, d_ in G.edges(data=True):
        uu.append(idx[u_]); vv.append(idx[v_]); ww.append(d_["km"] + 1e-12)
    A = csr_matrix((np.r_[ww, ww], (np.r_[uu, vv], np.r_[vv, uu])), shape=(len(idx), len(idx)))
    need = []
    by_src = {}
    for k_, (ds, a, b) in enumerate(pairs):
        pa, pb = place[a], place[b]
        if sp.row_of[pa] < 0 or sp.row_of[pb] < 0: continue
        lim = ratio * ds + slack_km
        if sp.row_of[pa] == sp.row_of[pb] and abs(cum[pa] - cum[pb]) <= lim: continue
        ea, eb = where_on_graph(pa), where_on_graph(pb)
        for v0, o0 in ea:
            if v0 in idx and o0 <= lim:
                by_src.setdefault(v0, []).append((k_, o0, eb, lim))
        need.append(k_)
    best0 = {k_: np.inf for k_ in need}
    for v0, items in by_src.items():
        L = max(lim - o0 for _, o0, _, lim in items)
        d = _dij(A, directed=False, indices=idx[v0], limit=L)
        for k_, o0, eb, lim in items:
            for v1, o1 in eb:
                if v1 in idx:
                    x = o0 + d[idx[v1]] + o1
                    if x < best0[k_]: best0[k_] = x
    recheck = {k_ for k_ in need if not best0[k_] <= ratio * pairs[k_][0] + slack_km}
    added, checked = [], len(need)
    for k_, (ds, a, b) in enumerate(pairs):
        if k_ not in recheck: continue
        pa, pb = place[a], place[b]
        lim = ratio * ds + slack_km
        ea, eb = where_on_graph(pa), where_on_graph(pb)
        if sp.row_of[pa] == sp.row_of[pb] and abs(cum[pa] - cum[pb]) <= lim: continue
        best = np.inf
        for v0, o0 in ea:
            if v0 not in G or o0 > lim: continue
            dl = nx.single_source_dijkstra_path_length(G, v0, cutoff=lim - o0, weight="km")
            for v1, o1 in eb:
                if v1 in dl: best = min(best, o0 + dl[v1] + o1)
        if best <= lim: continue
        X = sp.at(sp.row_of[pa], pa); Y = sp.at(sp.row_of[pb], pb)
        if X is None or Y is None or X == Y: continue
        if G.has_edge(X, Y) and G[X][Y]["km"] <= ds: continue
        G.add_edge(X, Y, km=ds, rows=(), via=frozenset({"throat"}))
        added.append(dict(a=X, b=Y, km=round(ds, 4), osm_a=int(F["nid"][a]), osm_b=int(F["nid"][b])))
    return pd.DataFrame(added), dict(service_attachments=int(len(att)), pairs_checked=checked,
                                     throat_links=len(added), throat_km=round(sum(x["km"] for x in added), 2))
