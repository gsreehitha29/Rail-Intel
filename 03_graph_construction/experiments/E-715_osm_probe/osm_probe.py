"""E-715 - what the OpenStreetMap extracts can give an open rebuild, measured."""
import json, struct, sys, glob
from pathlib import Path
import numpy as np, pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra

root = Path(sys.argv[1]); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
O = root / "external_data/osm_india_rail"
def hav(lo1, la1, lo2, la2):
    lo1, la1, lo2, la2 = map(np.radians, (lo1, la1, lo2, la2))
    a = np.sin((la2-la1)/2)**2 + np.cos(la1)*np.cos(la2)*np.sin((lo2-lo1)/2)**2
    return 2*6371.0088*np.arcsin(np.sqrt(a))
R = {}
W = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(O/"rail_ways_*.parquet")))]).drop_duplicates("way_id").reset_index(drop=True)
S = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(O/"rail_stations_*.parquet")))]).drop_duplicates("node_id")

# per-way geometry and length
ids, xs, ys, A, B, WI, wkm = [], [], [], [], [], [], []
for i, (refs, b) in enumerate(zip(W.node_refs, W.wkb)):
    r = np.frombuffer(refs, "int64"); n = struct.unpack("<I", b[5:9])[0]
    xy = np.frombuffer(b, "<f8", 2*n, 9).reshape(n, 2)
    ids.append(r); xs.append(xy[:,0]); ys.append(xy[:,1])
    A.append(r[:-1]); B.append(r[1:]); WI.append(np.full(len(r)-1, i))
    wkm.append(float(hav(xy[:-1,0], xy[:-1,1], xy[1:,0], xy[1:,1]).sum()) if n > 1 else 0.0)
W["km"] = wkm
def kmby(col): return {str(k): round(float(v), 0) for k, v in W.groupby(W[col].fillna("(none)")).km.sum().sort_values(ascending=False).head(12).items()}
R["ways"] = dict(n=int(len(W)), km_total=round(float(W.km.sum())), by_railway=kmby("railway"), by_usage=kmby("usage"),
                 by_service=kmby("service"), by_gauge=kmby("gauge"))
main = W.railway.isin(["rail", "narrow_gauge"]) & ~W.usage.isin(["industrial", "military", "tourism"]) & W.service.isna()
M = W[main]
def cover(col): return round(float(M.loc[M[col].notna(), "km"].sum() / M.km.sum()), 4)
el = M.electrified.isin(["contact_line", "rail", "yes", "4th_rail"])
R["mainline"] = dict(km=round(float(M.km.sum())), ways=int(len(M)),
    tag_cover_km_share=dict(gauge=cover("gauge"), electrified=cover("electrified"), maxspeed=cover("maxspeed"), tracks=cover("tracks"), usage=cover("usage")),
    electrified_share_of_tagged=round(float(M.loc[el, "km"].sum() / M.loc[M.electrified.notna(), "km"].sum()), 4))

# topology of the mainline node graph
mi = np.flatnonzero(main.to_numpy())
allids = np.concatenate([ids[i] for i in mi]); u, first = np.unique(allids, return_index=True)
lon = np.concatenate([xs[i] for i in mi])[first]; lat = np.concatenate([ys[i] for i in mi])[first]
a = np.searchsorted(u, np.concatenate([A[i] for i in mi])); b = np.searchsorted(u, np.concatenate([B[i] for i in mi]))
d = np.maximum(hav(lon[a], lat[a], lon[b], lat[b]), 1e-6)
N = len(u); G = csr_matrix((np.r_[d, d], (np.r_[a, b], np.r_[b, a])), shape=(N, N))
nc, lab = connected_components(G, directed=False)
km_by_comp = np.bincount(lab[a], weights=d, minlength=nc)
deg = np.diff(G.indptr)
R["mainline_topology"] = dict(nodes=int(N), components=int(nc), giant_km_share=round(float(km_by_comp.max()/km_by_comp.sum()), 4),
    components_over_10km=int((km_by_comp > 10).sum()), junction_nodes_deg3plus=int((deg >= 3).sum()), dead_ends=int((deg == 1).sum()))

# stations: codes, on-track, match to our graph
S = S[S.railway.isin(["station", "halt"])].copy()
S["code"] = S.railway_ref.fillna(S.ref).astype(str).str.strip().str.upper().replace({"NAN": np.nan, "NONE": np.nan})
on = np.isin(S.node_id.to_numpy(), u)
S["on_track"] = on
gdir = root / "03_graph_construction/graph_v1_4"
nodes = pd.read_csv(gdir/"open/nodes.csv"); cw = pd.read_csv(gdir/"station_code_crosswalk.csv")
ours = set(nodes.station_code.dropna().str.upper())
missing = set(cw.loc[cw.resolution == "missing_station", "code"].str.upper())
codes = set(S.code.dropna())
R["stations"] = dict(osm_station_or_halt=int(len(S)), with_code=int(S.code.notna().sum()), unique_codes=int(len(codes)),
    on_mainline_track=round(float(on.mean()), 4),
    our_coded_stations_found_in_osm=int(len(ours & codes)), our_coded_stations=int(len(ours)),
    our_missing_228_found_in_osm=int(len(missing & codes)),
    kollam_QLN_in_osm=bool("QLN" in codes),
    osm_codes_not_in_our_graph=int(len(codes - ours)))

# head-to-head: OSM track length vs ours, against official consecutive-stop distances
e = pd.read_csv(gdir/"open/edges.csv")
sc = S[S.code.notna() & S.on_track].drop_duplicates("code").set_index("code")
pos = {c: int(np.searchsorted(u, nid)) for c, nid in sc.node_id.items()}
nid2code = dict(zip(nodes.node_id, nodes.station_code.str.upper()))
off = e[e.official_km.notna()].copy()
off["ca"] = off.from_node.map(nid2code); off["cb"] = off.to_node.map(nid2code)
off = off[off.ca.isin(pos) & off.cb.isin(pos)]
rng = np.random.default_rng(20261019)
samp = off.sample(min(800, len(off)), random_state=7)
src = sorted({pos[c] for c in samp.ca})
dist = dijkstra(G, directed=False, indices=src, limit=400.0)
row = {s: i for i, s in enumerate(src)}
samp["osm_km"] = [dist[row[pos[r.ca]], pos[r.cb]] for r in samp.itertuples()]
samp = samp[np.isfinite(samp.osm_km)]
eo = (samp.osm_km/samp.official_km - 1).abs(); eg = (samp.length_km/samp.official_km - 1).abs()
lb = samp.length_is_lower_bound.astype(bool)
R["length_head_to_head"] = dict(pairs=int(len(samp)),
    osm_within_5pct=round(float((eo <= .05).mean()), 4), ours_within_5pct=round(float((eg <= .05).mean()), 4),
    osm_median_err=round(float(eo.median()), 4), ours_median_err=round(float(eg.median()), 4),
    on_our_floor_sections=dict(n=int(lb.sum()), osm_within_5pct=round(float((eo[lb] <= .05).mean()), 4) if lb.any() else None,
                               ours_within_5pct=round(float((eg[lb] <= .05).mean()), 4) if lb.any() else None))
(out/"E-715_osm_probe.json").write_text(json.dumps(R, indent=1, default=str))
print(json.dumps(R, indent=1, default=str))
