"""Graph v1.3 — external-evidence build (E-600).

Two variants are produced from the same stages so the OpenStreetMap licence
decision stays reversible:

  * open : uses only sources whose terms add no share-alike condition
           (datameet/maps states CC BY 4.0, data.gov.in timetables GODL-India,
           Wikidata CC0). OSM may be used to *check* a value, never to supply it.
  * full : additionally takes values from OpenStreetMap (ODbL 1.0): routed
           lengths, zone codes, coordinates, connector edges, inserted stations,
           maxspeed / electrification along the path. Every such value carries
           `*_source == 'osm...'`, so the variant is ODbL as a whole.

Nothing here changes v1.0–v1.2. All thresholds are module constants and are
recorded in the manifest; every stage writes a parquet into graph_v1_3/_stages
so later stages can be re-run alone.
"""
from __future__ import annotations
import json, os, re, struct, glob
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[2]
V12 = ROOT / "03_graph_construction" / "graph_v1_2"
OUT = ROOT / "03_graph_construction" / "graph_v1_3"
STG = OUT / "_stages"
EXT = ROOT / "external_data"
OSM = EXT / "osm_india_rail"

# ---- thresholds (recorded in the manifest) --------------------------------
MISPLACED_KM = 10.0        # graph coord this far from BOTH osm and wikidata ...
AGREE_KM = 2.0             # ... while osm and wikidata agree within this -> replace
SNAP_KM = 1.0              # node -> OSM network snap tolerance for routing
OFFICIAL_TOL = (1.0, 0.05) # |x - official| <= max(1 km, 5%) counts as agreement
OFFICIAL_SRC_AGREE_KM = 2.0
DETOUR_MAX = 1.6           # OSM path counted as a valid *check* only if <= max(1.6*chord, chord+5)
DETOUR_ADD_KM = 5.0
OFFICIAL_SINUOSITY_CAP = 1.15  # official distance used only if <= 1.15*chord + 1 km (tuned on 700 trains, E-600 F)
OFFICIAL_CAP_ADD_KM = 1.0
OSM_LENGTHS_USED = False   # OSM routed lengths worsened route accuracy in every tested setting -> check only
CONNECT_MAX_KM = 30.0      # small-component connector length cap
INSERT_NEAR_KM = 1.0       # OSM station within this of an edge geometry ...
INSERT_ROUTE_TOL = (1.0, 0.05)  # ... and u->s->v within max(1 km,5%) of u->v
MERGE_DUP_KM = 2.0         # duplicate junction/station merge distance
ZONES = {'CR','ECR','ECoR','ER','KR','NCR','NER','NFR','NR','NWR','SCR','SECR','SER','SR','SWR','WCR','WR'}
ZONE_ALIAS = {'ECOR':'ECoR','KRCL':'KR','NE':'NER','SCOR':None}

def hav(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2-lat1)/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin((lon2-lon1)/2)**2
    return 2*6371.0088*np.arcsin(np.sqrt(a))

def key(a, b): return '|'.join(sorted((str(a), str(b))))

def thresholds():
    return {k: v for k, v in globals().items() if k.isupper() and k not in ('ROOT','V12','OUT','STG','EXT','OSM')
            and isinstance(v, (int, float, tuple, set, dict))}

# ---------------------------------------------------------------------------
# loaders
# ---------------------------------------------------------------------------
def osm_stations():
    S = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(OSM/'rail_stations_*.parquet')))]).drop_duplicates('node_id')
    S = S[S.railway.isin(['station', 'halt'])].copy()
    S['code'] = S.railway_ref.fillna(S.ref).str.strip().str.upper()
    return S[S.code.notna()].drop_duplicates('code').set_index('code')

def wikidata():
    w = pd.read_csv(EXT/'wikidata_stations.csv', dtype=str)
    w['code'] = w.code.str.strip().str.upper()
    xy = w.coord.str.extract(r'Point\(([-\d.]+) ([-\d.]+)\)').astype(float)
    w['lon'], w['lat'] = xy[0], xy[1]
    return w.dropna(subset=['lon']).drop_duplicates('code').set_index('code')

def osm_network():
    """Rail+NG network (no industrial/military/tourism), node coords, segment->way."""
    W = pd.concat([pd.read_parquet(f, columns=['way_id','railway','service','usage','gauge','maxspeed',
                   'electrified','node_refs','wkb']) for f in sorted(glob.glob(str(OSM/'rail_ways_*.parquet')))])
    W = W.drop_duplicates('way_id')
    W = W[W.railway.isin(['rail','narrow_gauge']) & ~W.usage.isin(['industrial','military','tourism'])].reset_index(drop=True)
    ids, xs, ys, A, B, WI = [], [], [], [], [], []
    for i, (refs, b) in enumerate(zip(W.node_refs, W.wkb)):
        r = np.frombuffer(refs, 'int64'); n = struct.unpack('<I', b[5:9])[0]
        xy = np.frombuffer(b, '<f8', 2*n, 9).reshape(n, 2)
        ids.append(r); xs.append(xy[:, 0]); ys.append(xy[:, 1]); A.append(r[:-1]); B.append(r[1:]); WI.append(np.full(len(r)-1, i))
    ids = np.concatenate(ids); u, first = np.unique(ids, return_index=True)
    lon = np.concatenate(xs)[first]; lat = np.concatenate(ys)[first]
    A = np.searchsorted(u, np.concatenate(A)); B = np.searchsorted(u, np.concatenate(B)); WI = np.concatenate(WI)
    d = np.maximum(hav(lon[A], lat[A], lon[B], lat[B]), 1e-6)
    from scipy.sparse import csr_matrix
    N = len(u)
    G = csr_matrix((np.concatenate([d, d]), (np.concatenate([A, B]), np.concatenate([B, A]))), shape=(N, N))
    seg = {}
    for a, b, w, dd in zip(A, B, WI, d):
        k = (a, b) if a < b else (b, a)
        if k not in seg: seg[k] = (w, dd)
    def num(x):
        try: return float(str(x).split(';')[0].split()[0])
        except Exception: return np.nan
    ms = W.maxspeed.map(num).to_numpy(float)
    el_tag = W.electrified.notna().to_numpy()
    el_yes = W.electrified.isin(['contact_line', 'rail', 'yes', '4th_rail']).to_numpy()
    gauge = W.gauge.fillna('').to_numpy()
    return dict(G=G, lon=lon, lat=lat, A=A, B=B, d=d, seg=seg, ms=ms, el_tag=el_tag, el_yes=el_yes, gauge=gauge)

def proj(lon, lat):
    return np.c_[np.asarray(lon)*111.32*np.cos(np.radians(22.0)), np.asarray(lat)*110.57]

# ---------------------------------------------------------------------------
# stage 1 — node attributes
# ---------------------------------------------------------------------------
def stage1():
    import shapefile
    from shapely.geometry import shape, Point
    from shapely.strtree import STRtree
    n = pd.read_parquet(V12/'nodes.parquet').copy()
    S, wd = osm_stations(), wikidata()
    n['lon_osm'] = n.node_id.map(S.lon); n['lat_osm'] = n.node_id.map(S.lat)
    n['lon_wd'] = n.node_id.map(wd.lon); n['lat_wd'] = n.node_id.map(wd.lat)
    d_osm = hav(n.longitude, n.latitude, n.lon_osm, n.lat_osm)
    d_wd = hav(n.longitude, n.latitude, n.lon_wd, n.lat_wd)
    d_ow = hav(n.lon_osm, n.lat_osm, n.lon_wd, n.lat_wd)
    n['coord_dist_osm_km'] = d_osm; n['coord_dist_wd_km'] = d_wd
    cand = (d_osm > MISPLACED_KM) & (d_wd > MISPLACED_KM) & (d_ow <= AGREE_KM)
    # a move is accepted only if it brings the node's straight-line distances to its graph
    # neighbours closer to their measured lengths; otherwise the *code* is suspect, not the place
    e = pd.read_parquet(V12/'edges.parquet')
    off = pd.read_parquet(STG/'s2a_official.parquet').set_index('edge_id').official_km if (STG/'s2a_official.parquet').exists() else pd.Series(dtype=float)
    e['ref'] = e.edge_id.map(off).fillna(e.length_km)
    P = n.set_index('node_id')
    fix = pd.Series(False, index=n.index)
    for i in n.index[cand]:
        nid = n.at[i, 'node_id']
        inc = e[(e.from_node == nid) | (e.to_node == nid)]
        other = np.where(inc.from_node == nid, inc.to_node, inc.from_node)
        olo, ola = P.longitude.reindex(other).to_numpy(), P.latitude.reindex(other).to_numpy()
        err_old = np.nanmedian(np.abs(hav(n.at[i,'longitude'], n.at[i,'latitude'], olo, ola) - inc.ref.to_numpy()))
        err_new = np.nanmedian(np.abs(hav(n.at[i,'lon_osm'], n.at[i,'lat_osm'], olo, ola) - inc.ref.to_numpy()))
        fix[i] = err_new < err_old
    n['coord_move_candidate'] = cand
    n['code_identity_suspect'] = cand & ~fix
    n['coord_fixed'] = fix
    for v, (lo, la) in {'open': ('lon_wd', 'lat_wd'), 'full': ('lon_osm', 'lat_osm')}.items():
        n[f'longitude_{v}'] = np.where(fix, n[lo], n.longitude)
        n[f'latitude_{v}'] = np.where(fix, n[la], n.latitude)
    n['coordinate_source_open'] = np.where(fix, 'wikidata_checked_by_osm', 'v1.2')
    n['coordinate_source_full'] = np.where(fix, 'osm_checked_by_wikidata', 'v1.2')
    # states from polygons (datameet/maps, CC BY 4.0) on the fixed coordinates
    sf = shapefile.Reader(str(EXT/'state_boundaries_datameet'/'Admin2.shp'))
    polys = [shape(s.__geo_interface__) for s in sf.shapes()]; names = [r[0] for r in sf.records()]
    tree = STRtree(polys)
    def st(x, y):
        if not np.isfinite(x): return None
        p = Point(x, y)
        for i in tree.query(p):
            if polys[i].contains(p): return names[i]
        # nearest polygon within 2 km (coastal / border points)
        i = tree.nearest(p)
        return names[i] if polys[i].distance(p) * 111 <= 2 else None
    norm = lambda s: None if s is None or (isinstance(s, float) and np.isnan(s)) else re.sub(r'[^a-z]', '', str(s).lower().replace('&', 'and').replace('nct', ''))
    for v in ('open', 'full'):
        n[f'state_{v}'] = [st(x, y) for x, y in zip(n[f'longitude_{v}'], n[f'latitude_{v}'])]
        n[f'state_source_{v}'] = np.where(pd.notna(n[f'state_{v}']), 'polygon_datameet_ccby4', 'none')
    n['state_v12_disagrees'] = n.state_best.notna() & n.state_open.notna() & (n.state_best.map(norm) != n.state_open.map(norm))
    # zones: open keeps v1.2; full fills nulls from OSM station operator
    op = S.operator.map(lambda z: None if pd.isna(z) else ZONE_ALIAS.get(str(z).strip().upper(), str(z).strip()))
    op = op.where(op.isin(ZONES))
    n['zone_code_open'] = n.zone_code; n['zone_source_open'] = n.zone_source.fillna('none')
    fillz = n.zone_code.isna() & n.node_id.map(op).notna()
    n['zone_code_full'] = np.where(fillz, n.node_id.map(op), n.zone_code)
    n['zone_source_full'] = np.where(fillz, 'osm_operator', n.zone_source.fillna('none'))
    STG.mkdir(parents=True, exist_ok=True)
    n.to_parquet(STG/'s1_nodes.parquet')
    return dict(coord_fixed=int(fix.sum()), coord_fixed_ids=n.node_id[fix].tolist(), code_identity_suspect=n.node_id[n.code_identity_suspect].tolist(),
                state_open=int(n.state_open.notna().sum()), state_full=int(n.state_full.notna().sum()),
                state_v12_disagrees=int(n.state_v12_disagrees.sum()), zone_filled_full=int(fillz.sum()),
                zone_null_open=int(n.zone_code_open.isna().sum()), zone_null_full=int(pd.isna(n.zone_code_full).sum()))

# ---------------------------------------------------------------------------
# stage 2 — evidence per edge: official distances (GODL) and OSM routing
# ---------------------------------------------------------------------------
def _official(df, t, c, d, s):
    df = df.sort_values([t, s]); out = []
    for _, g in df.groupby(t, sort=False):
        cc = g[c].tolist(); dv = g[d].tolist()
        for i in range(len(cc)-1):
            if cc[i] != cc[i+1] and pd.notna(dv[i]) and pd.notna(dv[i+1]) and dv[i+1]-dv[i] > 0:
                out.append((key(cc[i], cc[i+1]), dv[i+1]-dv[i]))
    o = pd.DataFrame(out, columns=['k', 'd'])
    return o.groupby('k').d.agg(['median', 'min', 'max', 'size'])

def stage2a():
    e = pd.read_parquet(V12/'edges.parquet'); e['k'] = [key(a, b) for a, b in zip(e.from_node, e.to_node)]
    t17 = pd.read_csv(EXT/'timetable_2017_datagovin'/'Train_details_22122017.csv', dtype=str)
    t17['Distance'] = pd.to_numeric(t17.Distance, errors='coerce'); t17['SEQ'] = pd.to_numeric(t17.SEQ, errors='coerce')
    t17['Station Code'] = t17['Station Code'].str.strip().str.upper()
    t15 = pd.read_csv(EXT/'timetable_2015_datagovin'/'isl_wise_train_detail_03082015_v1.csv', dtype=str)
    t15.columns = [c.strip().lower() for c in t15.columns]
    t15['distance'] = pd.to_numeric(t15.distance, errors='coerce'); t15['islno'] = pd.to_numeric(t15.islno, errors='coerce')
    t15['station code'] = t15['station code'].str.strip().str.upper()
    o17 = _official(t17, 'Train No', 'Station Code', 'Distance', 'SEQ')
    o15 = _official(t15, 'train no.', 'station code', 'distance', 'islno')
    ie = pd.read_csv(EXT/'iitkgp_rstgcn_network_2024'/'Indian-Railway-Network-and-Delays'/'IRN_edges.csv')
    ie['k'] = [key(a, b) for a, b in zip(ie['from'], ie['to'])]; o24 = ie.groupby('k').distance.median()
    ev = pd.DataFrame({'edge_id': e.edge_id, 'k': e.k})
    ev['off17'] = e.k.map(o17['median']); ev['off17_spread'] = e.k.map(o17['max'] - o17['min'])
    ev['off15'] = e.k.map(o15['median']); ev['iitkgp24_check'] = e.k.map(o24)
    both = ev.off17.notna() & ev.off15.notna()
    ev['official_sources_disagree'] = both & ((ev.off17 - ev.off15).abs() > OFFICIAL_SRC_AGREE_KM)
    ev['official_km'] = ev.off17.combine_first(ev.off15)
    ev['official_source'] = np.where(ev.off17.notna(), 'datagovin_2017', np.where(ev.off15.notna(), 'datagovin_2015', None))
    ev.to_parquet(STG/'s2a_official.parquet')
    return dict(edges_with_official=int(ev.official_km.notna().sum()), from_2017=int(ev.off17.notna().sum()),
                only_2015=int((ev.off17.isna() & ev.off15.notna()).sum()), sources_disagree=int(ev.official_sources_disagree.sum()),
                within_train_spread_gt2=int((ev.off17_spread > 2).sum()))

def _snap(net, n, lo, la):
    from scipy.spatial import cKDTree
    T = cKDTree(proj(net['lon'], net['lat']))
    S = osm_stations()
    slo, sla = n.node_id.map(S.lon), n.node_id.map(S.lat)
    use = slo.notna() & (hav(slo, sla, n[lo], n[la]) <= 2.0)
    qlo = np.where(use, slo, n[lo]); qla = np.where(use, sla, n[la])
    ok = np.isfinite(qlo) & np.isfinite(qla)
    d = np.full(len(n), np.inf); i = np.full(len(n), -1)
    dd, ii = T.query(proj(qlo[ok], qla[ok])); d[ok] = dd; i[ok] = ii
    return pd.DataFrame({'node_id': n.node_id.values, 'snap': i, 'snap_km': d,
                         'snap_by': np.where(use, 'osm_station_code', 'graph_coordinate')})

def _path_tags(net, pred, s, t):
    """Walk predecessors t->s; km-weighted tag summary along the OSM path."""
    seg = net['seg']; ws = []; ds = []; cur = t; steps = 0
    while cur != s and steps < 500000:
        p = pred[cur]
        if p < 0: return None
        w, dd = seg[(p, cur) if p < cur else (cur, p)]; ws.append(w); ds.append(dd); cur = p; steps += 1
    ws = np.array(ws); ds = np.array(ds); tot = ds.sum()
    if tot <= 0: return None
    ms = net['ms'][ws]; m = np.isfinite(ms)
    elt = net['el_tag'][ws]; ely = net['el_yes'][ws]; g = net['gauge'][ws]
    gl = pd.Series(ds[g != '']).groupby(g[g != '']).sum()
    return dict(osm_maxspeed_kmph=(float(ms[m].min()) if m.any() else np.nan), osm_maxspeed_cover=float(ds[m].sum()/tot),
                osm_electrified_share=(float(ds[ely].sum()/ds[elt].sum()) if elt.any() else np.nan),
                osm_electrified_cover=float(ds[elt].sum()/tot), osm_gauge=(gl.idxmax() if len(gl) else None),
                osm_path_segments=int(len(ws)))

def stage2b(part: int, nparts: int = 2, budget_s: float = 165):
    import time
    from scipy.sparse.csgraph import dijkstra
    t0 = time.time()
    net = osm_network()
    n = pd.read_parquet(STG/'s1_nodes.parquet')
    sn = _snap(net, n, 'longitude_full', 'latitude_full').set_index('node_id')
    if part == 0:
        sn.reset_index().to_parquet(STG/'s2b_snap.parquet')
    e = pd.read_parquet(V12/'edges.parquet')
    pos = n.set_index('node_id')
    e['chord13'] = hav(e.from_node.map(pos.longitude_full), e.from_node.map(pos.latitude_full),
                       e.to_node.map(pos.longitude_full), e.to_node.map(pos.latitude_full))
    ev = pd.read_parquet(STG/'s2a_official.parquet').set_index('edge_id')
    e = e.iloc[part::nparts]
    out = []
    for r in e.itertuples():
        a, b = sn.loc[r.from_node], sn.loc[r.to_node]
        rec = dict(edge_id=r.edge_id, osm_km=np.nan, snap_km_max=max(a.snap_km, b.snap_km))
        if a.snap_km <= SNAP_KM and b.snap_km <= SNAP_KM and a.snap != b.snap:
            off = ev.official_km.get(r.edge_id, np.nan)
            lim = max(3*r.chord13, r.chord13 + 20, (3*off if np.isfinite(off) else 0))
            dist, pred = dijkstra(net['G'], indices=int(a.snap), limit=lim, return_predecessors=True)
            L = dist[int(b.snap)]
            if np.isfinite(L):
                rec['osm_km'] = float(L)
                tg = _path_tags(net, pred, int(a.snap), int(b.snap))
                if tg: rec.update(tg)
        out.append(rec)
        if time.time() - t0 > budget_s: raise RuntimeError(f'budget exceeded at {len(out)} of {len(e)}')
    pd.DataFrame(out).to_parquet(STG/f's2b_osm_part{part}.parquet')
    return dict(part=part, edges=len(out), routed=int(np.isfinite(pd.DataFrame(out).osm_km).sum()), seconds=round(time.time()-t0))

# ---------------------------------------------------------------------------
# stage 3 — length rule (both variants) + OSM attributes (full)
# ---------------------------------------------------------------------------
GAUGE_MM = {'BG': '1676', 'MG': '1000', 'NG': ('762', '610'), 'SG': '1435'}

def _agree(x, off):
    return (np.abs(x - off) <= np.maximum(OFFICIAL_TOL[0], OFFICIAL_TOL[1]*off))

def stage3():
    e = pd.read_parquet(V12/'edges.parquet')
    n = pd.read_parquet(STG/'s1_nodes.parquet').set_index('node_id')
    ev = pd.read_parquet(STG/'s2a_official.parquet').set_index('edge_id')
    osm = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(STG/'s2b_osm_part*.parquet')))]).set_index('edge_id')
    e = e.join(ev[['official_km', 'official_source', 'official_sources_disagree', 'off17_spread', 'iitkgp24_check']], on='edge_id')
    e = e.join(osm, on='edge_id')
    rep = {}
    for v in ('open', 'full'):
        chord = hav(e.from_node.map(n[f'longitude_{v}']), e.from_node.map(n[f'latitude_{v}']),
                    e.to_node.map(n[f'longitude_{v}']), e.to_node.map(n[f'latitude_{v}']))
        chord = pd.Series(chord, index=e.index)
        spine = e.length_source.eq('spine')
        off = e.official_km
        ch0 = chord.fillna(0)
        too_short = off.notna() & (off < 0.9*ch0 - 1.0)
        too_long = off.notna() & (off > OFFICIAL_SINUOSITY_CAP*ch0 + OFFICIAL_CAP_ADD_KM)
        off_ok = off.notna() & ~too_short & ~too_long
        conflict = too_short; detour = too_long
        osm_ok = pd.Series(False, index=e.index)
        if v == 'full':
            L = e.osm_km
            osm_ok = L.notna() & (L >= 0.98*chord) & (L <= np.maximum(DETOUR_MAX*chord, chord + DETOUR_ADD_KM))
            osm_ok &= ~(off_ok & ~_agree(L, off))
            osm_check_ok = osm_ok.copy()
            if not OSM_LENGTHS_USED: osm_ok = pd.Series(False, index=e.index)
        Lv12 = e.length_km
        out = pd.Series(np.nan, index=e.index); src = pd.Series(None, index=e.index, dtype=object)
        # spine vs official disagreement: OSM length arbitrates (as a check in 'open', never copied)
        osm_seen = e.osm_km.notna()
        o_sp = osm_seen & _agree(e.osm_km, Lv12); o_of = osm_seen & _agree(e.osm_km, off)
        sp_dis = off_ok & spine & ~_agree(Lv12, off)
        to_off = sp_dis & o_of & ~o_sp
        c1 = off_ok & spine & ~to_off
        c2 = off_ok & ~c1 & osm_ok & _agree(e.osm_km, off)
        c3 = off_ok & ~c1 & ~c2
        c4 = ~off_ok & spine
        c5 = ~off_ok & ~spine & osm_ok
        c6 = ~off_ok & ~spine & ~osm_ok
        out[c1] = Lv12[c1]
        src[c1 & ~sp_dis] = 'spine_confirmed_by_official'
        src[c1 & sp_dis & o_sp & ~o_of] = 'spine_official_disputed_osm_sides_spine'
        src[c1 & sp_dis & ~(o_sp & ~o_of)] = 'spine_official_disputed_unresolved'
        out[c2] = e.osm_km[c2]; src[c2] = 'osm_routed_confirmed_by_official'
        out[c3] = off[c3]; src[c3] = 'official_timetable'
        src[c3 & to_off] = 'official_osm_sides_official'
        out[c4] = Lv12[c4]; src[c4] = 'spine'
        out[c5] = e.osm_km[c5]; src[c5] = 'osm_routed'
        lb = np.maximum(Lv12, chord.fillna(0))
        out[c6] = lb[c6]; src[c6] = 'lower_bound_straight_line'
        raised = out < chord.fillna(0)
        out = np.maximum(out, chord.fillna(0)).clip(lower=0.05)
        lower = c6 & ~spine
        df = pd.DataFrame({'edge_id': e.edge_id, 'length_km_v13': out, 'length_source_v13': src,
                           'length_is_lower_bound': lower, 'length_chord_v13': chord,
                           'official_km': off, 'official_source': e.official_source, 'official_conflict': conflict, 'official_detour': detour, 'raised_to_chord': raised,
                           'official_sources_disagree': e.official_sources_disagree,
                           'spine_disagrees_official': off_ok & spine & ~_agree(Lv12, off),
                           'length_km_v12': Lv12})
        if v == 'full':
            df['osm_km'] = e.osm_km; df['osm_length_check_ok'] = osm_check_ok
            # speeds: OSM maxspeed only replaces an imputed speed if it beats the imputation on declared edges
            dec = e.speed_source.isin(['declared_segment', 'declared_corridor']) & (e.osm_maxspeed_cover >= 0.8)
            mae_osm = float((e.osm_maxspeed_kmph[dec] - e.speed_used_kmph[dec]).abs().mean()) if dec.any() else np.nan
            rep['osm_maxspeed_vs_declared_mae'] = round(mae_osm, 1); rep['osm_maxspeed_validation_n'] = int(dec.sum())
            use = (~e.speed_source.isin(['declared_segment', 'declared_corridor'])) & (e.osm_maxspeed_cover >= 0.8) & (mae_osm < 11.4)
            df['speed_used_kmph_v13'] = np.where(use, e.osm_maxspeed_kmph, e.speed_used_kmph)
            df['speed_source_v13'] = np.where(use, 'osm_maxspeed', e.speed_source)
            df['osm_maxspeed_kmph'] = e.osm_maxspeed_kmph; df['osm_maxspeed_cover'] = e.osm_maxspeed_cover
            df['electrified_share_osm'] = np.where(e.osm_electrified_cover >= 0.8, e.osm_electrified_share, np.nan)
            g12 = e.gauge_code.map(lambda g: GAUGE_MM.get(g))
            gm = [(og in gg) if isinstance(gg, tuple) else (og == gg) for og, gg in zip(e.osm_gauge, g12)]
            df['gauge_osm_mm'] = e.osm_gauge
            df['gauge_disagrees_osm'] = e.osm_gauge.notna() & g12.notna() & ~pd.Series(gm, index=e.index)
            rep['speed_replaced_by_osm'] = int(use.sum()); rep['electrified_known'] = int(df.electrified_share_osm.notna().sum())
            rep['gauge_disagrees_osm'] = int(df.gauge_disagrees_osm.sum()); rep['osm_check_ok'] = int(osm_check_ok.sum())
        else:
            df['speed_used_kmph_v13'] = e.speed_used_kmph; df['speed_source_v13'] = e.speed_source
        df.to_parquet(STG/f's3_edges_{v}.parquet')
        rep[v] = dict(src=df.length_source_v13.value_counts().to_dict(), km=round(float(df.length_km_v13.sum())),
                      lower_bound=int(lower.sum()), lower_bound_km=round(float(df.length_km_v13[lower].sum())),
                      below_chord=int((df.length_km_v13 < 0.98*df.length_chord_v13).sum()),
                      official_conflict=int(conflict.sum()), official_detour=int(detour.sum()), raised_to_chord=int(raised.sum()), spine_vs_official=int(df.spine_disagrees_official.sum()))
    return rep

# ---------------------------------------------------------------------------
# stage 4 — topology repairs (full variant only; every change is OSM-evidenced)
# ---------------------------------------------------------------------------
def _state_fn():
    import shapefile
    from shapely.geometry import shape, Point
    from shapely.strtree import STRtree
    sf = shapefile.Reader(str(EXT/'state_boundaries_datameet'/'Admin2.shp'))
    polys = [shape(s.__geo_interface__) for s in sf.shapes()]; names = [r[0] for r in sf.records()]
    tree = STRtree(polys)
    def st(x, y):
        p = Point(x, y)
        for i in tree.query(p):
            if polys[i].contains(p): return names[i]
        i = tree.nearest(p)
        return names[i] if polys[i].distance(p)*111 <= 2 else None
    return st

def _norm(s):
    s = re.sub(r'\(.*?\)', ' ', str(s).lower())
    s = re.sub(r'\b(jn|junction|railway station|station|halt|cabin|rs|road)\b', ' ', s)
    return re.sub(r'[^a-z]', '', s)

def stage4(budget_s=160):
    import time, networkx as nx
    from scipy.sparse.csgraph import dijkstra
    from scipy.spatial import cKDTree
    t0 = time.time(); rep = {}
    n = pd.read_parquet(STG/'s1_nodes.parquet')
    e = pd.read_parquet(V12/'edges.parquet').merge(pd.read_parquet(STG/'s3_edges_full.parquet'), on='edge_id')
    n['lon'] = n.longitude_full; n['lat'] = n.latitude_full
    e['edge_origin'] = 'v1.2'
    # ---- a. merges -------------------------------------------------------
    wd = pd.read_csv(EXT/'wikidata_stations.csv', dtype=str)
    alias = {}
    for c, lab, al in zip(wd.code.str.strip().str.upper(), wd.itemLabel, wd.altLabels):
        for nm in [lab] + (str(al).split('|') if pd.notna(al) else []):
            alias.setdefault(_norm(nm), set()).add(c)
    st = n[n.node_type == 'station'].copy(); st['k'] = st.node_name.map(_norm)
    jn = n[n.node_type != 'station'].copy(); jn['k'] = jn.node_name.map(_norm)
    merges = []
    for j in jn.itertuples():
        if not np.isfinite(j.lon) or not j.k: continue
        codes = alias.get(j.k, set()) | set(st.node_id[st.k == j.k])
        cand = st[st.node_id.isin(codes)]
        if len(cand):
            d = np.asarray(hav(j.lon, j.lat, cand.lon.to_numpy(), cand.lat.to_numpy()), float)
            i = int(np.argmin(d))
            if d[i] <= MERGE_DUP_KM: merges.append((j.node_id, cand.node_id.iloc[i], 'junction_is_station', float(d[i])))
    done = {m[0] for m in merges}
    for k, g in jn[jn.k != ''].groupby('k'):
        g = g[~g.node_id.isin(done) & g.lon.notna()]
        if len(g) < 2: continue
        g = g.sort_values('degree', ascending=False); keep = g.iloc[0]
        for r in g.iloc[1:].itertuples():
            d = float(hav(keep.lon, keep.lat, r.lon, r.lat))
            if d <= 1.0: merges.append((r.node_id, keep.node_id, 'junction_name_variant', d)); done.add(r.node_id)
    mp = {a: b for a, b, _, _ in merges}
    e['from_node'] = e.from_node.replace(mp); e['to_node'] = e.to_node.replace(mp)
    selfloop = e.from_node == e.to_node
    e = e[~selfloop].copy()
    e['k'] = [key(a, b) for a, b in zip(e.from_node, e.to_node)]
    e = e.sort_values(['k', 'length_is_lower_bound', 'length_km_v13']).drop_duplicates('k')
    n = n[~n.node_id.isin(mp)].copy()
    n.loc[n.node_id.isin(set(mp.values())), 'merged_from'] = n.node_id.map(lambda x: '|'.join(a for a, b in mp.items() if b == x) or None)
    rep['merged_nodes'] = len(mp); rep['merge_selfloops_dropped'] = int(selfloop.sum())
    pd.DataFrame(merges, columns=['removed_node', 'kept_node', 'reason', 'distance_km']).to_csv(STG/'s4_merges.csv', index=False)
    # ---- shared OSM network ------------------------------------------------
    net = osm_network(); G = net['G']
    sn = pd.read_parquet(STG/'s2b_snap.parquet').set_index('node_id')
    snap = lambda x: (int(sn.at[x, 'snap']), float(sn.at[x, 'snap_km'])) if x in sn.index else (-1, np.inf)
    # ---- b. connectors for small components --------------------------------
    H = nx.Graph(); H.add_nodes_from(n.node_id); H.add_edges_from(zip(e.from_node, e.to_node))
    comps = sorted(nx.connected_components(H), key=len, reverse=True); giant = comps[0]
    gs = {}
    for x in giant:
        s, d = snap(x)
        if d <= SNAP_KM: gs.setdefault(s, x)
    gidx = np.array(sorted(gs))
    conn = []
    for c in comps[1:]:
        srcs = [(snap(x)[0], x) for x in c if snap(x)[1] <= SNAP_KM]
        if not srcs: conn.append((sorted(c)[0], None, None)); continue
        D = dijkstra(G, indices=[s for s, _ in srcs], limit=CONNECT_MAX_KM)
        sub = D[:, gidx]; i, j = np.unravel_index(np.argmin(sub), sub.shape)
        if np.isfinite(sub[i, j]):
            conn.append((srcs[i][1], gs[gidx[j]], float(sub[i, j])))
        else: conn.append((srcs[0][1], None, None))
    P = n.set_index('node_id')
    rows = []
    for a, b, L in conn:
        if b is None: continue
        ch = float(hav(P.at[a, 'lon'], P.at[a, 'lat'], P.at[b, 'lon'], P.at[b, 'lat']))
        rows.append(dict(edge_id=f'C{len(rows)+1:05d}', from_node=a, to_node=b, length_km_v13=max(L, ch), length_source_v13='osm_connector',
                         length_chord_v13=ch, length_is_lower_bound=False, edge_origin='osm_connector', osm_km=L))
    e = pd.concat([e, pd.DataFrame(rows)], ignore_index=True)
    rep['small_components'] = len(comps)-1; rep['connected'] = len(rows)
    pd.DataFrame(conn, columns=['component_node', 'giant_node', 'osm_km']).to_csv(STG/'s4_connectors.csv', index=False)
    # ---- c. insert OSM stations lying on existing edges --------------------
    S = osm_stations(); S = S[~S.index.isin(n.node_id)]
    T = cKDTree(proj(net['lon'], net['lat']))
    ds, si = T.query(proj(S.lon, S.lat)); S['snap'] = si; S['snap_km'] = ds
    S = S[S.snap_km <= 0.5]
    eg = pd.read_parquet(V12/'edge_geometry.parquet').set_index('edge_id')
    pts, own = [], []
    for eid in e.edge_id[e.edge_origin == 'v1.2']:
        b = eg.wkb.get(eid)
        if b is None: continue
        m = struct.unpack('<I', b[5:9])[0]; xy = np.frombuffer(b, '<f8', 2*m, 9).reshape(m, 2)
        for i in range(m-1):
            k = max(1, int(np.hypot(*(xy[i+1]-xy[i]))*111/0.25))
            t = np.linspace(0, 1, k, endpoint=False)[:, None]; pts.append(xy[i] + t*(xy[i+1]-xy[i])); own += [eid]*k
    pts = np.vstack(pts); own = np.array(own); TE = cKDTree(proj(pts[:, 0], pts[:, 1]))
    near = TE.query_ball_point(proj(S.lon, S.lat), r=INSERT_NEAR_KM)
    cand = {}
    for code, idxs in zip(S.index, near):
        for eid in sorted(set(own[idxs])): cand.setdefault(eid, []).append(code)
    E = e.set_index('edge_id'); acc = {}
    for eid, codes in sorted(cand.items()):   # deterministic order (E-600 reproducibility)
        codes = sorted(set(codes))
        if time.time()-t0 > budget_s: rep['insert_budget_hit'] = True; break
        u, v = E.at[eid, 'from_node'], E.at[eid, 'to_node']
        (su, du), (sv, dv) = snap(u), snap(v)
        if du > SNAP_KM or dv > SNAP_KM: continue
        Du = dijkstra(G, indices=su, limit=3*E.at[eid, 'length_km_v13']+10); Dv = dijkstra(G, indices=sv, limit=3*E.at[eid, 'length_km_v13']+10)
        Luv = Du[sv]
        if not np.isfinite(Luv) or Luv <= 0: continue
        for c in codes:
            s = int(S.at[c, 'snap']); exc = Du[s] + Dv[s] - Luv
            if np.isfinite(exc) and exc <= max(INSERT_ROUTE_TOL[0], INSERT_ROUTE_TOL[1]*Luv) and 0 < Du[s] < Luv:
                if c not in acc or (round(exc, 9), eid) < (round(acc[c][2], 9), acc[c][0]): acc[c] = (eid, Du[s]/Luv, exc)
    rep['insert_candidates'] = int(sum(len(v) for v in cand.values())); rep['inserted_stations'] = len(acc)
    # split edges
    stf = _state_fn(); new_nodes, new_edges, drop = [], [], set()
    byedge = {}
    for c, (eid, f, exc) in acc.items(): byedge.setdefault(eid, []).append((f, c))
    zone_op = S.operator.map(lambda z: None if pd.isna(z) else ZONE_ALIAS.get(str(z).strip().upper(), str(z).strip()))
    for eid, lst in byedge.items():
        lst = sorted(lst); r = E.loc[eid]; L = r.length_km_v13
        chain = [r.from_node] + [c for _, c in lst] + [r.to_node]; fr = [0.0] + [f for f, _ in lst] + [1.0]
        for i in range(len(chain)-1):
            d = r.to_dict(); d.update(edge_id=f'{eid}_{i+1}', from_node=chain[i], to_node=chain[i+1],
                                      length_km_v13=max(L*(fr[i+1]-fr[i]), 0.05), edge_origin='split_by_osm_station',
                                      split_parent=eid, length_source_v13=f'split:{r.length_source_v13}')
            new_edges.append(d)
        drop.add(eid)
        for _, c in lst:
            s = S.loc[c]; z = zone_op.get(c)
            new_nodes.append(dict(node_id=c, node_type='station', node_name=s['name'], station_code=c, lon=s.lon, lat=s.lat,
                                  longitude_full=s.lon, latitude_full=s.lat, state_full=stf(s.lon, s.lat), state_source_full='polygon_datameet_ccby4',
                                  zone_code_full=z if z in ZONES else r.zone_code, zone_source_full='osm_operator' if z in ZONES else 'parent_edge',
                                  coordinate_source_full='osm_inserted', node_origin='osm_inserted_station'))
    e = pd.concat([e[~e.edge_id.isin(drop)], pd.DataFrame(new_edges)], ignore_index=True)
    n['node_origin'] = 'v1.2'
    n = pd.concat([n, pd.DataFrame(new_nodes)], ignore_index=True)
    rep['edges_split'] = len(drop); rep['edges_now'] = len(e); rep['nodes_now'] = len(n)
    e.drop(columns=['k'], errors='ignore').to_parquet(STG/'s4_edges_full.parquet'); n.to_parquet(STG/'s4_nodes_full.parquet')
    rep['seconds_used'] = round(time.time()-t0)
    return rep

# ---------------------------------------------------------------------------
# stage 5 — assemble both variants, gates, exports
# ---------------------------------------------------------------------------
OSM_LEN_SOURCES = {'osm_routed', 'osm_routed_confirmed_by_official', 'osm_connector'}
KEEP_E = ['corridor_id', 'gauge_code', 'zone_code', 'n_tracks', 'bridge_present_edge', 'tunnel_present_edge', 'service_direct',
          'service_load', 'suspect_long_edge', 'geometry_unsupported', 'geometry_source', 'station_match_deficit', 'speed_expected_abs_error_kmph']

def _assemble(v):
    n1 = pd.read_parquet(STG/'s1_nodes.parquet')
    if v == 'open':
        e = pd.read_parquet(V12/'edges.parquet')[['edge_id', 'from_node', 'to_node'] + KEEP_E].merge(pd.read_parquet(STG/'s3_edges_open.parquet'), on='edge_id')
        e['edge_origin'] = 'v1.2'; n = n1.copy(); n['node_origin'] = 'v1.2'
    else:
        e = pd.read_parquet(STG/'s4_edges_full.parquet'); n = pd.read_parquet(STG/'s4_nodes_full.parquet')
    N = pd.DataFrame({'node_id': n.node_id, 'node_type': n.node_type, 'node_name': n.node_name,
                      'station_code': n.get('station_code'), 'longitude': n[f'longitude_{v}'], 'latitude': n[f'latitude_{v}'],
                      'coordinate_source': n[f'coordinate_source_{v}'], 'state': n[f'state_{v}'], 'state_source': n[f'state_source_{v}'],
                      'zone_code': n[f'zone_code_{v}'], 'zone_source': n[f'zone_source_{v}'],
                      'state_v12': n.get('state_best'), 'state_v12_disagrees': n.get('state_v12_disagrees'),
                      'code_identity_suspect': n.get('code_identity_suspect'), 'coord_fixed': n.get('coord_fixed'),
                      'node_origin': n.node_origin, 'merged_from': n.get('merged_from'), 'match_confidence': n.get('match_confidence'),
                      'match_method': n.get('match_method')})
    cols = ['edge_id', 'from_node', 'to_node', 'length_km_v13', 'length_source_v13', 'length_is_lower_bound', 'length_chord_v13',
            'official_km', 'official_source', 'official_conflict', 'official_detour', 'official_sources_disagree', 'spine_disagrees_official',
            'raised_to_chord', 'length_km_v12', 'speed_used_kmph_v13', 'speed_source_v13', 'edge_origin'] + KEEP_E
    if v == 'full':
        cols += ['osm_km', 'osm_length_check_ok', 'electrified_share_osm', 'gauge_osm_mm', 'gauge_disagrees_osm', 'split_parent']
    E = e[[c for c in cols if c in e.columns]].rename(columns={'length_km_v13': 'length_km', 'length_source_v13': 'length_source',
            'length_chord_v13': 'length_chord_km', 'speed_used_kmph_v13': 'speed_used_kmph', 'speed_source_v13': 'speed_source'})
    # chord on final coordinates; physical floor
    P = N.set_index('node_id')
    E['length_chord_km'] = hav(E.from_node.map(P.longitude), E.from_node.map(P.latitude), E.to_node.map(P.longitude), E.to_node.map(P.latitude))
    E['length_km'] = np.maximum(E.length_km.astype(float), E.length_chord_km.fillna(0)).clip(lower=0.05)
    E['travel_time_min'] = E.length_km / E.speed_used_kmph * 60
    N, E = _post(N, E, v)
    E['dataset_version'] = f'v1.3-{v}'; N['dataset_version'] = f'v1.3-{v}'
    return N, E

def _structure(N, E):
    import networkx as nx
    G = nx.Graph(); G.add_nodes_from(N.node_id); G.add_edges_from(zip(E.from_node, E.to_node))
    cc = sorted(nx.connected_components(G), key=len, reverse=True); g = G.subgraph(cc[0])
    return G, dict(n_nodes=G.number_of_nodes(), n_edges=G.number_of_edges(), total_km=round(float(E.length_km.sum()), 1),
                   n_components=len(cc), giant_nodes=len(cc[0]), giant_edges=g.number_of_edges(),
                   bridges_giant=sum(1 for _ in nx.bridges(g)), articulation_giant=sum(1 for _ in nx.articulation_points(g)),
                   independent_cycles=G.number_of_edges()-G.number_of_nodes()+len(cc)), cc

def stage5():
    import hashlib, networkx as nx
    rep = {}
    for v in ('open', 'full'):
        N, E = _assemble(v); G, s, cc = _structure(N, E)
        comp = {x: i for i, c in enumerate(cc) for x in c}
        N['component_id'] = N.node_id.map(comp); N['in_giant'] = N.component_id.eq(0)
        N['degree'] = N.node_id.map(dict(G.degree())).fillna(0).astype(int)
        gates = {}
        gates['G1_no_edge_below_straight_line'] = bool((E.length_km + 1e-9 >= E.length_chord_km.fillna(0)).all())
        gates['G2_every_edge_has_length_and_source'] = bool(E.length_km.notna().all() and E.length_source.notna().all())
        gates['G3_referential_integrity'] = bool(E.from_node.isin(N.node_id).all() and E.to_node.isin(N.node_id).all()
                                                 and N.node_id.is_unique and E.edge_id.is_unique and (E.from_node != E.to_node).all()
                                                 and not pd.Series([key(a, b) for a, b in zip(E.from_node, E.to_node)]).duplicated().any())
        if v == 'open':
            osm_vals = E.length_source.isin(OSM_LEN_SOURCES).sum() + N.zone_source.astype(str).str.startswith('osm').sum() \
                       + N.coordinate_source.astype(str).str.startswith('osm').sum() + E.speed_source.eq('osm_maxspeed').sum()
            gates['G4_open_carries_no_osm_values'] = bool(osm_vals == 0 and not any(c.startswith('osm') for c in E.columns))
        gates['G5_state_coverage_ge_99pct'] = bool(N.state.notna().mean() >= 0.99)
        # exports
        d = OUT/v; d.mkdir(parents=True, exist_ok=True)
        N.to_parquet(d/'nodes.parquet', index=False); E.to_parquet(d/'edges.parquet', index=False); E.to_csv(d/'edges.csv', index=False)
        N.to_csv(d/'nodes.csv', index=False)
        H = nx.Graph(); H.graph['dataset_version'] = f'v1.3-{v}'
        clean = lambda r: {k: (bool(x) if isinstance(x, (np.bool_,)) else (float(x) if isinstance(x, (np.floating,)) else (int(x) if isinstance(x, (np.integer,)) else x)))
                           for k, x in r.items() if x is not None and not (isinstance(x, float) and np.isnan(x))}
        for r in N.to_dict('records'): H.add_node(r['node_id'], **clean({k: x for k, x in r.items() if k != 'node_id'}))
        for r in E.to_dict('records'): H.add_edge(r['from_node'], r['to_node'], **clean({k: x for k, x in r.items() if k not in ('from_node', 'to_node')}))
        gm = d/f'rail_graph_v1_3_{v}.graphml'; nx.write_graphml(H, gm)
        R = nx.read_graphml(gm)
        rN, rE = pd.read_parquet(d/'nodes.parquet'), pd.read_parquet(d/'edges.parquet')
        gates['G6_exports_roundtrip'] = bool(R.number_of_nodes() == len(N) and R.number_of_edges() == len(E) and len(rN) == len(N)
                                             and len(rE) == len(E) and np.allclose(rE.length_km, E.length_km))
        files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.iterdir()) if p.is_file() and p.suffix in ('.parquet', '.csv', '.graphml')}
        rep[v] = dict(structure=s, gates=gates, length_sources=E.length_source.value_counts().to_dict(),
                      lower_bound_edges=int(E.length_is_lower_bound.fillna(False).astype(bool).sum()),
                      lower_bound_km=round(float(E.length_km[E.length_is_lower_bound.fillna(False).astype(bool)].sum()), 1), files=files)
    rep['G7_full_not_less_connected'] = rep['full']['structure']['n_components'] <= rep['open']['structure']['n_components']
    json.dump(rep, open(STG/'s5_report.json', 'w'), indent=1, default=str)
    return {v: dict(structure=rep[v]['structure'], gates=rep[v]['gates']) for v in ('open', 'full')} | {'G7': rep['G7_full_not_less_connected']}

def stage5b(n_trains=1500, seed=13):
    """Validation: (1) whole-train route length vs declared train distance (datameet, CC0) on a fixed
    random sample of trains; (2) per-edge agreement with IIT KGP 2024 distances (check only)."""
    import networkx as nx
    tr = pd.read_csv(ROOT/'01_data_engineering'/'processed_data'/'cleaned_trains.csv', dtype={'train_number': str})
    tr = tr[tr.distance_quality_status.eq('valid') & tr.distance.gt(0)].drop_duplicates('train_number').set_index('train_number')
    sc = pd.read_csv(ROOT/'01_data_engineering'/'processed_data'/'cleaned_schedules.csv', dtype={'train_number': str},
                     usecols=['train_number', 'station_code', 'stop_sequence'])
    sc = sc[sc.train_number.isin(tr.index)].sort_values(['train_number', 'stop_sequence'])
    stops = {t: g.station_code.tolist() for t, g in sc.groupby('train_number')}
    sample = pd.Series(sorted(stops)).sample(n=min(n_trains, len(stops)), random_state=seed).tolist()
    ie = pd.read_csv(EXT/'iitkgp_rstgcn_network_2024'/'Indian-Railway-Network-and-Delays'/'IRN_edges.csv')
    iit = pd.Series(ie.distance.values, index=[key(a, b) for a, b in zip(ie['from'], ie['to'])]).groupby(level=0).median()
    graphs = {'v1.2': pd.read_parquet(V12/'edges.parquet')}
    for v in ('open', 'full'): graphs[v] = pd.read_parquet(OUT/v/'edges.parquet')
    Gs = {}
    for name, E in graphs.items():
        G = nx.Graph(); G.add_weighted_edges_from(zip(E.from_node, E.to_node, E.length_km)); Gs[name] = G
    common = [t for t in sample if all(stops[t][0] in G and stops[t][-1] in G for G in Gs.values())]
    out = {}
    for name, E in graphs.items():
        G = Gs[name]
        k = [key(a, b) for a, b in zip(E.from_node, E.to_node)]
        m = pd.Series(k).isin(iit.index).to_numpy(); ref = iit.reindex(pd.Series(k)[m]).to_numpy(); L = E.length_km.to_numpy()[m]
        ok = np.abs(L - ref) <= np.maximum(1, 0.05*ref)
        errs = []
        for t in common:
            st = [s for s in stops[t] if s in G]
            try: tot = sum(nx.shortest_path_length(G, a, b, weight='weight') for a, b in zip(st[:-1], st[1:]) if a != b)
            except nx.NetworkXNoPath: continue
            D = float(tr.at[t, 'distance']); errs.append((tot - D)/D*100)
        errs = np.array(errs)
        out[name] = dict(iitkgp_edges=int(m.sum()), iitkgp_within_tol_pct=round(float(ok.mean()*100), 1),
                         trains_routed=len(errs), of_sample=len(common), train_median_abs_err_pct=round(float(np.median(np.abs(errs))), 2),
                         train_median_signed_err_pct=round(float(np.median(errs)), 2), train_within_5pct=round(float((np.abs(errs) <= 5).mean()*100), 1))
    json.dump(out, open(STG/'s5b_validation.json', 'w'), indent=1)
    return out

# ---------------------------------------------------------------------------
# stage 6 — audit lists for human review
# ---------------------------------------------------------------------------
def stage6():
    import networkx as nx
    from scipy.spatial import cKDTree
    A = OUT/'audit'; A.mkdir(parents=True, exist_ok=True); rep = {}
    n1 = pd.read_parquet(STG/'s1_nodes.parquet'); e12 = pd.read_parquet(V12/'edges.parquet')
    o = pd.read_parquet(OUT/'open'/'edges.parquet'); f = pd.read_parquet(OUT/'full'/'edges.parquet')
    nf = pd.read_parquet(OUT/'full'/'nodes.parquet'); no = pd.read_parquet(OUT/'open'/'nodes.parquet')
    nm = n1.set_index('node_id').node_name
    def save(name, df, why):
        df = df.copy(); df.insert(0, 'check', why); df.to_csv(A/name, index=False); rep[name] = len(df)
    cols = ['node_id', 'node_name', 'node_type', 'longitude', 'latitude', 'lon_osm', 'lat_osm', 'lon_wd', 'lat_wd', 'coord_dist_osm_km', 'coord_dist_wd_km', 'degree']
    save('01_code_identity_suspects.csv', n1[n1.code_identity_suspect][cols],
         'Graph station is >10 km from where OSM and Wikidata (which agree) put this code, and moving it would break its links. Confirm which station this node really is; fix the code or the coordinate.')
    save('02_coordinate_fixes_applied.csv', n1[n1.coord_fixed][cols], 'Coordinate moved to the OSM/Wikidata position. Spot-check on a map.')
    ed = lambda d: d.assign(from_name=d.from_node.map(nm), to_name=d.to_node.map(nm))
    base = ['edge_id', 'from_node', 'to_node', 'length_km', 'length_source', 'length_chord_km', 'official_km', 'length_km_v12']
    save('03_official_shorter_than_straight_line.csv', ed(o[o.official_conflict][base]),
         'Timetable distance is shorter than the straight line between the two stations: a wrong code, a wrong coordinate, or a timetable error.')
    save('04_official_longer_route.csv', ed(o[o.official_detour][base]),
         'Timetable distance is more than 1.15x the straight line + 1 km: trains probably take a different route than this edge. Check whether the edge or a link is missing.')
    save('05_spine_vs_official_unresolved.csv', ed(o[o.length_source.eq('spine_official_disputed_unresolved')][base]),
         'Track-measured length and timetable distance disagree and OSM cannot decide. Pick one from an official source (e.g. working timetable, sectional km posts).')
    lb = o[o.length_is_lower_bound.fillna(False).astype(bool)].sort_values('length_km', ascending=False)
    save('06_lower_bound_lengths.csv', ed(lb[base + ['suspect_long_edge']]),
         'No measured length: the straight line is used and real track is longer. Highest-km rows matter most.')
    # dead-end junctions with an OSM branch nearby / off-network OSM stations
    net = osm_network(); deg = np.bincount(np.concatenate([net['A'], net['B']]), minlength=len(net['lon']))
    T = cKDTree(proj(net['lon'], net['lat']))
    dj = no[(no.node_type != 'station') & (no.degree == 1) & no.longitude.notna()].copy()
    dj['osm_branch_within_300m'] = [bool((deg[T.query_ball_point(proj([x], [y])[0], r=0.3)] >= 3).any()) for x, y in zip(dj.longitude, dj.latitude)]
    save('07_dead_end_junctions.csv', dj[['node_id', 'node_name', 'longitude', 'latitude', 'osm_branch_within_300m']].sort_values('osm_branch_within_300m', ascending=False),
         'Junction with one link only. Where OSM shows a branch, the branch line is missing from the graph and should be added (needs track source).')
    S = osm_stations(); S = S[~S.index.isin(nf.node_id)]
    save('08_osm_stations_not_in_graph.csv', S[['name', 'lon', 'lat', 'operator', 'wikidata']].reset_index().rename(columns={'index': 'code'}),
         'OSM station/halt with a code that is still not a graph node (not on any existing edge). Usually a line missing from the graph.')
    mg = pd.read_csv(STG/'s4_merges.csv')
    save('09_merges_applied.csv', mg, 'Duplicate nodes merged in the full variant. Spot-check.')
    for nm_, extra in [('arambagh', 'JN::Arambagh'), ('paru', 'JN::PARU KHAS')]: pass
    pv = no[no.node_id.isin(['JN::Arambagh (Prafulla Chandra Sen', 'JN::Arambagh (Prafulla Chandra Sen)', 'JN::PARU KHAS', 'JN::Paru Khas'])][['node_id', 'node_name', 'longitude', 'latitude', 'degree']]
    save('10_duplicate_candidates_not_merged.csv', pv, 'Same name, 9-14 km apart: one location is wrong. Decide which, then merge.')
    cn = pd.read_csv(STG/'s4_connectors.csv'); save('11_component_connections.csv', cn,
         'Small components joined via OSM track (full). Rows with no giant_node are still disconnected: find the missing link.')
    save('12_zone_missing.csv', nf[nf.zone_code.isna()][['node_id', 'node_name', 'node_type', 'state']], 'No railway zone. Look up the station\'s zone/division.')
    save('13_state_changed_from_v12.csv', no[no.state_v12_disagrees.fillna(False).astype(bool)][['node_id', 'node_name', 'state_v12', 'state']],
         'Boundary map gives a different state than v1.2. Mostly Andhra Pradesh -> Telangana; spot-check others.')
    save('14_state_missing.csv', no[no.state.isna()][['node_id', 'node_name', 'longitude', 'latitude']], 'No state (no coordinate or outside every polygon).')
    ins = nf[nf.node_origin.eq('osm_inserted_station')][['node_id', 'node_name', 'longitude', 'latitude', 'state', 'zone_code']]
    par = f[f.edge_origin.eq('split_by_osm_station')].groupby('from_node').split_parent.first()
    ins['parent_edge'] = ins.node_id.map(par)
    save('15_inserted_stations.csv', ins, 'Station inserted from OSM into an existing edge (full). Check it sits on the right line; trains stopping at these show larger route errors.')
    save('16_gauge_disagrees_osm.csv', f[f.gauge_disagrees_osm.fillna(False).astype(bool)][['edge_id', 'from_node', 'to_node', 'gauge_code', 'gauge_osm_mm']],
         'GIS gauge differs from OSM gauge along the path. Check for gauge conversion.')
    sp = o[~o.speed_source.isin(['declared_segment', 'declared_corridor'])][['edge_id', 'from_node', 'to_node', 'speed_used_kmph', 'speed_source', 'length_km']].sort_values('length_km', ascending=False)
    save('17_speeds_estimated.csv', sp, 'Speed is estimated. Needs sectional speed (IR route classification / working timetable).')
    m = pd.read_csv(ROOT/'02_graph_inputs'/'graph_dataset'/'stations.csv', dtype={'station_code': str})
    nc = m[m.longitude.isna()].copy(); S2 = osm_stations(); wd = wikidata()
    nc['osm_lon'] = nc.station_code.map(S2.lon); nc['osm_lat'] = nc.station_code.map(S2.lat); nc['wd_lon'] = nc.station_code.map(wd.lon); nc['wd_lat'] = nc.station_code.map(wd.lat)
    save('18_master_stations_without_coordinates.csv', nc[['station_code', 'station_name', 'zone_code', 'state', 'osm_lon', 'osm_lat', 'wd_lon', 'wd_lat']],
         'Station in the master list with no coordinate. Where OSM/Wikidata give one, it can be placed; the rest need lookup.')
    return rep

def stage5c(n=700, tune_seed=7, hold_seed=99):
    """Hold-out route test on 2017 timetable trains disjoint from the tuning sample."""
    import networkx as nx
    t = pd.read_csv(EXT/'timetable_2017_datagovin'/'Train_details_22122017.csv', dtype=str)
    t['Distance'] = pd.to_numeric(t.Distance, errors='coerce'); t['SEQ'] = pd.to_numeric(t.SEQ, errors='coerce'); t['Station Code'] = t['Station Code'].str.strip()
    t = t.sort_values(['Train No', 'SEQ']); stops = {k: (g['Station Code'].tolist(), g.Distance.max()) for k, g in t.groupby('Train No')}
    allk = pd.Series(sorted(stops)); hold = allk.drop(allk.sample(n=n, random_state=tune_seed).index).sample(n=n, random_state=hold_seed).tolist()
    out = {}
    for name, E in [('v1.2', pd.read_parquet(V12/'edges.parquet')), ('open', pd.read_parquet(OUT/'open'/'edges.parquet')), ('full', pd.read_parquet(OUT/'full'/'edges.parquet'))]:
        G = nx.Graph(); G.add_weighted_edges_from(zip(E.from_node, E.to_node, E.length_km)); err = []
        for s in hold:
            st = [x for x in stops[s][0] if x in G]
            if len(st) < 2 or st[0] != stops[s][0][0] or st[-1] != stops[s][0][-1] or stops[s][1] <= 20: continue
            try: tot = sum(nx.shortest_path_length(G, x, y, weight='weight') for x, y in zip(st[:-1], st[1:]) if x != y)
            except nx.NetworkXNoPath: continue
            err.append((tot - stops[s][1])/stops[s][1]*100)
        e = np.array(err); out[name] = [round(float(np.median(e)), 2), round(float(np.median(np.abs(e))), 2), round(float((np.abs(e) <= 2).mean()*100), 1)]
    json.dump(out, open(STG/'s5c_holdout2017.json', 'w'))
    return out


# ---------------------------------------------------------------------------
# post-assembly: overrides, connector attributes, flags, service (E-600 rev 2)
# ---------------------------------------------------------------------------
OVERRIDES = Path(os.environ.get('RAIL_OVERRIDES', OUT/'audit'/'OVERRIDES.csv'))
OVERRIDE_ACTIONS = {'set', 'recode', 'move', 'merge', 'add_edge', 'remove_edge', 'reject', 'confirm'}
DEFICIT_MIN, SUSPECT_LEN_KM = 3, 10.0   # mirrors provenance.ProvenanceSpec (D-025)

def apply_overrides(N, E, v):
    """Apply audit/OVERRIDES.csv. Every row needs evidence; unknown ids or actions fail loudly."""
    log = []; N = N.copy(); E = E.copy()
    if not OVERRIDES.exists(): return N, E, log
    o = pd.read_csv(OVERRIDES, dtype=str).fillna('')
    o = o[o.get('variant', pd.Series('', index=o.index)).isin(['', v])] if 'variant' in o else o
    for i, r in o.iterrows():
        act = r.action.strip()
        if act not in OVERRIDE_ACTIONS: raise ValueError(f'OVERRIDES row {i}: unknown action {act!r}')
        if not r.evidence.strip(): raise ValueError(f'OVERRIDES row {i}: evidence is required')
        tid, fld, val = r.item_id.strip(), r.field.strip(), r.new_value.strip()
        if act == 'confirm': log.append((i, act, tid, 'ok')); continue
        if act == 'set':
            tgt = E if tid in set(E.edge_id) else (N if tid in set(N.node_id) else None)
            if tgt is None: raise ValueError(f'OVERRIDES row {i}: id {tid} not in {v}')
            col = 'edge_id' if tgt is E else 'node_id'
            x = pd.to_numeric(val, errors='coerce'); tgt.loc[tgt[col] == tid, fld] = val if pd.isna(x) else float(x)
            if tgt is E and fld == 'length_km': E.loc[E.edge_id == tid, 'length_source'] = 'manual_override'; E.loc[E.edge_id == tid, 'length_is_lower_bound'] = False
        elif act == 'move':
            lon, lat = map(float, val.split(',')); N.loc[N.node_id == tid, ['longitude', 'latitude']] = [lon, lat]
            N.loc[N.node_id == tid, 'coordinate_source'] = 'manual_override'
        elif act in ('recode', 'merge'):
            if tid not in set(N.node_id): raise ValueError(f'OVERRIDES row {i}: node {tid} not in {v}')
            if act == 'merge' and val not in set(N.node_id): raise ValueError(f'OVERRIDES row {i}: merge target {val} not in {v}')
            E['from_node'] = E.from_node.replace({tid: val}); E['to_node'] = E.to_node.replace({tid: val})
            if act == 'merge' or val in set(N.node_id): N = N[N.node_id != tid]
            else: N.loc[N.node_id == tid, 'node_id'] = val
            E = E[E.from_node != E.to_node]
            E = E.assign(_k=[key(a, b) for a, b in zip(E.from_node, E.to_node)]).drop_duplicates('_k').drop(columns='_k')
        elif act == 'remove_edge':
            E = E[E.edge_id != tid]
        elif act == 'add_edge':
            a, b = tid.split('|'); L = float(val)
            E = pd.concat([E, pd.DataFrame([dict(edge_id=f'M{i:05d}', from_node=a, to_node=b, length_km=L, length_source='manual_override',
                                                  length_is_lower_bound=False, edge_origin='manual_override')])], ignore_index=True)
        elif act == 'reject':  # undo an inserted station: rejoin its two pieces
            if tid not in set(N.node_id): log.append((i, act, tid, 'skipped_not_in_variant')); continue
            inc = E[(E.from_node == tid) | (E.to_node == tid)]
            if len(inc) == 2:
                ends = [x for x in pd.concat([inc.from_node, inc.to_node]) if x != tid]
                row = inc.iloc[0].to_dict(); row.update(edge_id=str(inc.iloc[0].get('split_parent') or f'R{i:05d}'), from_node=ends[0], to_node=ends[1],
                                                        length_km=float(inc.length_km.sum()), edge_origin='override_rejoined')
                E = pd.concat([E[~E.edge_id.isin(inc.edge_id)], pd.DataFrame([row])], ignore_index=True)
            N = N[N.node_id != tid]
        log.append((i, act, tid, 'applied'))
    return N, E, log

def _post(N, E, v):
    N, E, log = apply_overrides(N, E, v)
    N['overrides_applied'] = sum(1 for x in log if x[3] in ('applied', 'ok'))
    if log: pd.DataFrame(log, columns=['row', 'action', 'item_id', 'result']).to_csv(STG/f'overrides_log_{v}.csv', index=False)
    P = N.set_index('node_id')
    # connectors: gauge from neighbouring edges, zone from endpoint, speed imputed below
    if 'edge_origin' in E and (E.edge_origin == 'osm_connector').any():
        inc = pd.concat([E[['from_node', 'gauge_code']].rename(columns={'from_node': 'n'}), E[['to_node', 'gauge_code']].rename(columns={'to_node': 'n'})]).dropna()
        gmode = inc.groupby('n').gauge_code.agg(lambda x: x.mode().iloc[0])
        c = E.edge_origin == 'osm_connector'
        E.loc[c, 'gauge_code'] = E.loc[c, 'from_node'].map(gmode).fillna(E.loc[c, 'to_node'].map(gmode))
        E.loc[c, 'zone_code'] = E.loc[c, 'to_node'].map(P.zone_code).fillna(E.loc[c, 'from_node'].map(P.zone_code))
    # speeds still missing: gauge x zone median of declared speeds in this graph, else gauge median
    dec = E[E.speed_source.isin(['declared_segment', 'declared_corridor'])]
    gz = dec.groupby(['gauge_code', 'zone_code']).speed_used_kmph.median(); gg = dec.groupby('gauge_code').speed_used_kmph.median()
    miss = E.speed_used_kmph.isna() & E.gauge_code.notna()
    for i in E.index[miss]:
        g, z = E.at[i, 'gauge_code'], E.at[i, 'zone_code']
        if (g, z) in gz.index: E.at[i, 'speed_used_kmph'] = gz[(g, z)]; E.at[i, 'speed_source'] = 'imputed_gauge_zone_median'
        elif g in gg.index: E.at[i, 'speed_used_kmph'] = gg[g]; E.at[i, 'speed_source'] = 'imputed_gauge_median'
    E['travel_time_min'] = E.length_km / E.speed_used_kmph * 60
    # G-01 flags on v1.3 lengths; inserted stations reduce their corridor's deficit
    cor = pd.read_csv(ROOT/'02_graph_inputs'/'graph_dataset'/'corridors.csv')
    deficit = (pd.to_numeric(cor.declared_no_of_stations, errors='coerce') - pd.to_numeric(cor.n_stations_found, errors='coerce'))
    deficit.index = cor.corridor_id
    if 'node_origin' in N and (N.node_origin == 'osm_inserted_station').any():
        sp = E[E.get('edge_origin', pd.Series(index=E.index, dtype=object)).eq('split_by_osm_station')]
        ins_per_cor = (sp.groupby('corridor_id').size() - sp.groupby('corridor_id').split_parent.nunique())
        deficit = deficit.sub(ins_per_cor, fill_value=0)
    E['station_match_deficit'] = E.corridor_id.map(deficit)
    E['suspect_long_edge'] = (E.station_match_deficit >= DEFICIT_MIN) & (E.length_km > SUSPECT_LEN_KM)
    # service attributes recomputed on this variant (stage5s); otherwise marked as inherited
    f = STG/f's5s_service_{v}.parquet'
    if f.exists():
        sv = pd.read_parquet(f).set_index('edge_id')
        E['service_direct'] = E.edge_id.map(sv.service_direct).fillna(0).astype(int)
        E['service_load'] = E.edge_id.map(sv.service_load).fillna(0).astype(int)
        E['service_source'] = 'recomputed_v1.3'
    else:
        E['service_source'] = 'inherited_v1.2'
    return N, E

def stage5s(v):
    """Recompute service_direct / service_load on the variant's own topology and lengths
    with the Phase 2 projection (s09.build_service, unchanged)."""
    import sys, contextlib, io
    sys.path.insert(0, str(ROOT/'02_graph_inputs'/'pipeline'))
    import s09_graph_dataset as s9
    f = STG/f's5s_service_{v}.parquet'
    if f.exists(): f.unlink()
    N, E = _assemble(v)
    with contextlib.redirect_stdout(io.StringIO()):
        svc, load, direct = s9.build_service(E[['edge_id', 'from_node', 'to_node', 'length_km']], N)
    out = pd.DataFrame({'edge_id': E.edge_id, 'service_direct': E.edge_id.map(direct).fillna(0).astype(int),
                        'service_load': E.edge_id.map(load).fillna(0).astype(int)})
    out.to_parquet(f)
    return dict(variant=v, edges_with_direct=int((out.service_direct > 0).sum()), edges_with_load=int((out.service_load > 0).sum()),
                service_pairs=len(svc), pairs_direct=int(svc.is_direct_edge.sum()))

def stage5g():
    """GeoJSON export: nodes as points; edges as lines from v1.2 alignment where the edge is unchanged,
    the parent alignment sliced by split position for inserted-station pieces, else the straight line."""
    eg = pd.read_parquet(V12/'edge_geometry.parquet').set_index('edge_id')
    def xy(b):
        m = struct.unpack('<I', b[5:9])[0]; return np.frombuffer(b, '<f8', 2*m, 9).reshape(m, 2)
    def cut(c, f0, f1):
        seg = hav(c[:-1, 0], c[:-1, 1], c[1:, 0], c[1:, 1]); cum = np.concatenate([[0], np.cumsum(seg)]); L = cum[-1]
        if L <= 0: return c
        def pt(m):
            i = min(int(np.searchsorted(cum, m, side='right')-1), len(c)-2); sp = cum[i+1]-cum[i]
            return c[i] + (0 if sp <= 0 else (m-cum[i])/sp)*(c[i+1]-c[i])
        a, b = f0*L, f1*L; inner = c[(cum > a) & (cum < b)]
        return np.vstack([pt(a), inner, pt(b)])
    rep = {}
    for v in ('open', 'full'):
        N = pd.read_parquet(OUT/v/'nodes.parquet'); E = pd.read_parquet(OUT/v/'edges.parquet'); P = N.set_index('node_id')
        feats = []
        for r in N.to_dict('records'):
            g = None if pd.isna(r['longitude']) else {'type': 'Point', 'coordinates': [r['longitude'], r['latitude']]}
            feats.append({'type': 'Feature', 'geometry': g, 'properties': {k: (None if (isinstance(x, float) and np.isnan(x)) else (x.item() if hasattr(x, 'item') else x)) for k, x in r.items()}})
        json.dump({'type': 'FeatureCollection', 'features': feats}, open(OUT/v/'nodes.geojson', 'w'))
        if 'split_parent' in E:
            grp = E[E.split_parent.notna()].copy()
            grp['share'] = grp.length_km / grp.groupby('split_parent').length_km.transform('sum')
            grp['f1'] = grp.groupby('split_parent').share.cumsum(); grp['f0'] = grp.f1 - grp.share
            frac = grp.set_index('edge_id')[['split_parent', 'f0', 'f1']]
        else: frac = pd.DataFrame(columns=['split_parent', 'f0', 'f1'])
        feats = []; src = {}
        for r in E.to_dict('records'):
            eid = r['edge_id']; c = None; gs = 'none'
            pa, pb = P.loc[r['from_node'], ['longitude', 'latitude']].to_numpy(float), P.loc[r['to_node'], ['longitude', 'latitude']].to_numpy(float)
            if eid in eg.index and eg.at[eid, 'wkb'] is not None and r.get('edge_origin', 'v1.2') == 'v1.2':
                c = xy(eg.at[eid, 'wkb']); gs = eg.at[eid, 'geometry_source']
            elif eid in frac.index and frac.at[eid, 'split_parent'] in eg.index and eg.at[frac.at[eid, 'split_parent'], 'wkb'] is not None:
                c = cut(xy(eg.at[frac.at[eid, 'split_parent'], 'wkb']), frac.at[eid, 'f0'], frac.at[eid, 'f1']); gs = 'parent_slice'
            elif np.isfinite(pa).all() and np.isfinite(pb).all():
                c = np.vstack([pa, pb]); gs = 'chord'
            src[gs] = src.get(gs, 0) + 1
            props = {k: (None if (isinstance(x, float) and np.isnan(x)) else (x.item() if hasattr(x, 'item') else x)) for k, x in r.items()}
            props['geometry_source_v13'] = gs
            feats.append({'type': 'Feature', 'geometry': None if c is None else {'type': 'LineString', 'coordinates': c.tolist()}, 'properties': props})
        json.dump({'type': 'FeatureCollection', 'features': feats}, open(OUT/v/'edges.geojson', 'w'))
        back = json.load(open(OUT/v/'edges.geojson'))
        rep[v] = dict(geometry_sources=src, features=len(back['features']), roundtrip=len(back['features']) == len(E))
    return rep

def stage_manifest():
    """Manifest: thresholds, latest stage outputs, gates, validation, conclusions, SHA-256 of every export."""
    import hashlib, datetime
    s5 = json.load(open(STG/'s5_report.json')); s5b = json.load(open(STG/'s5b_validation.json')); ho = json.load(open(STG/'s5c_holdout2017.json'))
    last = {}
    for l in open(STG/'stage_log.jsonl'):
        r = json.loads(l); last[r['stage'] + str(r.get('part', r.get('variant', '')))] = {k: x for k, x in r.items() if k not in ('coord_fixed_ids', 'code_identity_suspect')}
    e601 = ROOT/'03_graph_construction'/'experiments'/'E-601_v1_3_conclusions'/'report.json'
    files = {}
    for d in [OUT/'open', OUT/'full', ROOT/'03_graph_construction'/'service_layer_v1_3'/'open', ROOT/'03_graph_construction'/'service_layer_v1_3'/'full']:
        if d.exists():
            files[str(d.relative_to(ROOT/'03_graph_construction'))] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.iterdir()) if p.is_file()}
    man = dict(artifact='Rail-Intell station-level physical railway graph', version='v1.3', revision=2, experiment='E-600 (+E-601, E-502 on v1.3)',
               built_at_utc=datetime.datetime.utcnow().isoformat(timespec='seconds') + 'Z',
               supersedes='v1.2 (graph_v1_2/)',
               variants={'open': 'no OpenStreetMap-derived values (OSM only checks/arbitrates). datameet/maps CC BY 4.0, data.gov.in GODL-India, Wikidata CC0, on top of v1.2 sources.',
                         'full': 'open + OSM-derived topology and attributes; ODbL 1.0 applies to the variant as a whole.'},
               base_source_licence_caveat='All variants derive from 01_data_engineering/Railway_Network_.csv, origin unconfirmed; schema matches Esri India Living Atlas "Railway Network of India" (Esri India Master Terms of Use, no offline export). Release blocked until resolved.',
               thresholds={k: (list(x) if isinstance(x, (tuple, set)) else x) for k, x in thresholds().items()},
               overrides_file=str(OVERRIDES.relative_to(ROOT)) if str(OVERRIDES).startswith(str(ROOT)) else str(OVERRIDES),
               overrides_present=OVERRIDES.exists(),
               stages=last, structure={v: s5[v]['structure'] for v in ('open', 'full')},
               gates={v: s5[v]['gates'] for v in ('open', 'full')} | {'G7_full_not_less_connected': s5['G7_full_not_less_connected']},
               validation={'datameet_trains_seed13': s5b, 'timetable2017_holdout_seed99': {k: dict(zip(['median_signed_pct', 'median_abs_pct', 'within_2pct'], x)) for k, x in ho.items()}},
               conclusions_E601=json.load(open(e601)) if e601.exists() else None, files=files)
    json.dump(man, open(OUT/'graph_v1_3.manifest.json', 'w'), indent=1, default=str)
    return dict(files=sum(len(x) for x in files.values()), conclusions_ok=bool(man['conclusions_E601'] and all(x['all_within_band'] for x in man['conclusions_E601'].values())))
