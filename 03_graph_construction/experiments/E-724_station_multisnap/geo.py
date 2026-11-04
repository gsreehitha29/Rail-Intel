"""Small geodesy helpers, numpy only, so the build runs wherever pandas and scipy do."""
import numpy as np

_A, _F = 6378137.0, 1 / 298.257223563
_E = np.sqrt(2 * _F - _F ** 2)
# EPSG:7755, WGS 84 / India NSF LCC
_LAT1, _LAT2, _LAT0, _LON0, _X0, _Y0 = 12.472955, 35.17280444444444, 24.0, 80.0, 4e6, 4e6


def _m(p): return np.cos(p) / np.sqrt(1 - (_E * np.sin(p)) ** 2)
def _t(p): return np.tan(np.pi / 4 - p / 2) / ((1 - _E * np.sin(p)) / (1 + _E * np.sin(p))) ** (_E / 2)


_p1, _p2, _p0 = np.radians([_LAT1, _LAT2, _LAT0])
_N = (np.log(_m(_p1)) - np.log(_m(_p2))) / (np.log(_t(_p1)) - np.log(_t(_p2)))
_FF = _m(_p1) / (_N * _t(_p1) ** _N)
_R0 = _A * _FF * _t(_p0) ** _N


def lcc(lon, lat):
    """lon/lat degrees -> EPSG:7755 metres (ellipsoidal Lambert conformal conic, Snyder 15)."""
    p = np.radians(np.asarray(lat, float)); th = _N * np.radians(np.asarray(lon, float) - _LON0)
    r = _A * _FF * _t(p) ** _N
    return _X0 + r * np.sin(th), _Y0 + _R0 - r * np.cos(th)


def hav_km(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * np.arcsin(np.sqrt(a))


def read_polygons_shp(shp_path):
    """Polygons from an ESRI shapefile (types 5/15/25) and the first text field of its .dbf,
    with numpy and struct only. Returns [(name, [ring arrays (n, 2) lon/lat])]."""
    import struct
    from pathlib import Path
    shp = Path(shp_path).read_bytes(); dbf = Path(shp_path).with_suffix(".dbf").read_bytes()
    nrec, hlen, rlen = struct.unpack("<IHH", dbf[4:12])
    fields, off = [], 32
    while dbf[off] != 0x0D:
        name = dbf[off:off + 11].split(b"\0")[0].decode(); flen = dbf[off + 16]
        fields.append((name, flen)); off += 32
    names = []
    for i in range(nrec):
        rec = dbf[hlen + i * rlen + 1: hlen + (i + 1) * rlen]
        names.append(rec[:fields[0][1]].decode("utf-8", "replace").strip())
    out, pos, k = [], 100, 0
    while pos < len(shp):
        _, clen = struct.unpack(">ii", shp[pos:pos + 8]); body = shp[pos + 8: pos + 8 + clen * 2]; pos += 8 + clen * 2
        st = struct.unpack("<i", body[:4])[0]
        if st in (5, 15, 25):
            nparts, npts = struct.unpack("<ii", body[36:44])
            parts = list(struct.unpack(f"<{nparts}i", body[44:44 + 4 * nparts])) + [npts]
            pts = np.frombuffer(body, "<f8", 2 * npts, 44 + 4 * nparts).reshape(npts, 2)
            out.append((names[k], [pts[parts[j]:parts[j + 1]] for j in range(nparts)]))
        k += 1
    return out


def point_in_polygons(lon, lat, polys, chunk=64):
    """Index into polys of the polygon holding each point (even-odd over all its rings), or -1."""
    lon = np.asarray(lon, float); lat = np.asarray(lat, float); hit = np.full(len(lon), -1)
    for pi, (_, rings) in enumerate(polys):
        allp = np.concatenate(rings)
        bb = (lon >= allp[:, 0].min()) & (lon <= allp[:, 0].max()) & (lat >= allp[:, 1].min()) & (lat <= allp[:, 1].max())
        idx = np.flatnonzero(bb & (hit < 0) & np.isfinite(lon))
        if idx.size == 0: continue
        inside = np.zeros(idx.size, bool)
        for r in rings:
            x1, y1, x2, y2 = r[:-1, 0], r[:-1, 1], r[1:, 0], r[1:, 1]
            rb = (lon[idx] >= r[:, 0].min()) & (lon[idx] <= r[:, 0].max()) & (lat[idx] >= r[:, 1].min()) & (lat[idx] <= r[:, 1].max())
            sub = np.flatnonzero(rb)
            for c0 in range(0, sub.size, chunk):
                sl = sub[c0:c0 + chunk]; px = lon[idx[sl]][:, None]; py = lat[idx[sl]][:, None]
                cr = ((y1 > py) != (y2 > py)) & (px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-300) + x1)
                inside[sl] ^= (cr.sum(1) % 2 == 1)
        hit[idx[inside]] = pi
    return hit
