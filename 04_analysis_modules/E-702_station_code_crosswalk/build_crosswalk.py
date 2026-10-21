"""G1 - Station-code crosswalk: resolve station codes used by current data but absent
from graph v1.3.

The graph's station codes predate a wave of station renamings (Mughalsarai -> DDU,
Allahabad -> Prayagraj, Habibganj -> Rani Kamalapati, ...) and some new terminals.
Any join between the graph and current data silently drops those stops, which is
gap G1 in the gap register.

Method - every resolution must be carried by evidence, never by a hand-written list:

  1. Anchor the unknown code to a coordinate, from OSM `ref` or Wikidata `code`.
  2. Propose the nearest graph nodes to that anchor (<= 25 km).
  3. Score each proposal on four independent signals:
       name    - fuzzy match of the unknown name against the node's name, including
                 OSM old_name/alt_name/official_name and Wikidata aliases
       dist    - how close the anchor sits to the node
       route   - in the Sept 2024 timetables the unknown code sits between two stops
                 the graph does know, with cumulative km on each. A true alias of node
                 N reproduces those two km gaps when walked over the graph from N.
       retired - the decisive one. A rename retires the old code: of the renames
                 confirmed by hand (MGS, JHS, HBJ, CSTM, BCT, GR, MUV, HBD, UHP, BIH,
                 FD, ALD, ACOI) not one still appears in the 2024 timetables. A
                 candidate whose own code is still in service is a live, different
                 station - this is what separates Ayodhya Cantt -> FAIZABAD JN (code
                 retired, 0.02 km away) from Ayodhya Cantt -> AYODHYA (still running).

   Two hard vetoes, because they are facts rather than scores:
       co-occurrence - a code cannot alias a node listed in the same train's own
                 stops; the train calls at both, so they are two places.
       (and the absence of any node near the anchor, which makes it a missing station)
  4. Classify: alias (rename or second code for a node the graph has) / missing
     (a real station the graph lacks - G2/G3, not G1) / unresolved.

Outputs (crosswalk.csv, report.json, OVERRIDES_G1.csv) and verification are the
caller's; this module only measures and decides.

Run:  python build_crosswalk.py <Rail-Intell root> <output dir>
"""
import json, math, re, sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)

# thresholds (stated once, reported in the output so a reviewer can retune them)
TH = dict(anchor_search_km=25.0, alias_max_km=6.0, route_tol_km=4.0, route_tol_frac=0.18,
          name_strong=0.86, name_weak=0.62, accept_score=2.0, review_floor=1.0)

# ----------------------------------------------------------------- inputs
nodes = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/nodes.csv")
edges = pd.read_csv(ROOT / "03_graph_construction/graph_v1_3/open/edges.csv")
r24 = pd.read_csv(ROOT / "external_data/iitkgp_rstgcn_network_2024/"
                  "Indian-Railway-Network-and-Delays/train_routes_Sep2024.csv", dtype=str)
wd = pd.read_csv(ROOT / "external_data/wikidata_stations.csv")
osm = pd.concat([pd.read_parquet(p) for p in
                 sorted((ROOT / "external_data/osm_india_rail").glob("rail_stations_*.parquet"))],
                ignore_index=True)

ids = set(nodes.node_id)
pos = {r.node_id: (r.longitude, r.latitude) for r in nodes.itertuples()
       if pd.notna(r.longitude)}
nname = dict(zip(nodes.node_id, nodes.node_name))

G = nx.Graph()
for r in edges.itertuples():
    if G.has_edge(r.from_node, r.to_node) and G[r.from_node][r.to_node]["km"] <= r.length_km:
        continue
    G.add_edge(r.from_node, r.to_node, km=float(r.length_km))

# ----------------------------------------------------------------- helpers
SUFFIX = re.compile(r"\b(JN|JUNCTION|JCT|HALT|H|CITY|CANTT|CANTONMENT|TERMINUS|TERMINAL|"
                    r"TRM|HLT|STATION|RAILWAY|HALTS|ROAD|RD|NAGAR|BG|MG|NG|CHORD|LINE|"
                    r"NEW|OLD|EAST|WEST|NORTH|SOUTH|UPPER|LOWER|PF|YARD|GOODS|OUTER)\b")
NOISE = re.compile(r"[^A-Z0-9 ]+")

def norm(s):
    if not isinstance(s, str): return ""
    s = NOISE.sub(" ", s.upper())
    s = SUFFIX.sub(" ", s)
    return " ".join(s.split())

def sim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b: return 0.0
    if a == b: return 1.0
    base = SequenceMatcher(None, a, b).ratio()
    ta, tb = set(a.split()), set(b.split())
    if ta and tb:
        jac = len(ta & tb) / len(ta | tb)
        # one name fully contained in the other (Prayagraj / Prayagraj Jn)
        if ta <= tb or tb <= ta: jac = max(jac, 0.9)
        base = max(base, jac)
    return base

def hav(a, b):
    (lo1, la1), (lo2, la2) = a, b
    p = math.pi / 180
    h = (math.sin((la2 - la1) * p / 2) ** 2 +
         math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(min(1, h)))

_sp = {}
def spkm(a, b):
    """Shortest path km between two graph nodes, None if unreachable. Cached."""
    k = (a, b) if a < b else (b, a)
    if k not in _sp:
        try:
            _sp[k] = nx.shortest_path_length(G, a, b, weight="km")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            _sp[k] = None
    return _sp[k]

# ----------------------------------------------------------------- evidence tables
# OSM: code -> coordinate + every name it is known by
osm["code"] = osm.ref.fillna(osm.railway_ref).astype(str).str.strip().str.upper()
osm = osm[osm.code.str.match(r"^[A-Z]{2,6}$", na=False)]
osm_by_code = {}
for r in osm.itertuples():
    names = [x for x in (r.name, r.name_en, r.official_name, r.alt_name, r.old_name)
             if isinstance(x, str)]
    cur = osm_by_code.setdefault(r.code, dict(lon=r.lon, lat=r.lat, names=[], wikidata=r.wikidata))
    cur["names"].extend(names)

wd["code"] = wd.code.astype(str).str.strip().str.upper()
wd_by_code = {}
for r in wd.itertuples():
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", str(r.coord))
    names = [r.itemLabel] + (str(r.altLabels).split("|") if isinstance(r.altLabels, str) else [])
    cur = wd_by_code.setdefault(r.code, dict(lon=float(m.group(1)) if m else None,
                                             lat=float(m.group(2)) if m else None,
                                             names=[], item=r.item))
    cur["names"].extend([x for x in names if isinstance(x, str)])

# graph node names, including every name OSM/Wikidata attach to that node's own code
node_names = defaultdict(list)
for nid, nm in nname.items():
    node_names[nid].append(nm)
    for src in (osm_by_code, wd_by_code):
        if nid in src:
            node_names[nid].extend(src[nid]["names"])

# ----------------------------------------------------------------- the unknown codes
r24["seq"] = r24.stnSerialNumber.astype(int)
r24["dist"] = pd.to_numeric(r24.distance, errors="coerce")
r24["tno"] = r24.trainNumber.str.zfill(5)
r24 = r24.sort_values(["tno", "seq"])
codes_2024 = set(r24.station_code)
unknown = sorted(codes_2024 - ids)

uname, utrains, ustops = {}, defaultdict(set), defaultdict(int)
for r in r24.itertuples():
    if r.station_code in ids: continue
    uname.setdefault(r.station_code, r.station_name)
    utrains[r.station_code].add(r.tno)
    ustops[r.station_code] += 1

# route context: for each unknown code, the (prev known, km gap, next known, km gap) triples
ctx = defaultdict(list)
for tno, g in r24.groupby("tno", sort=False):
    rows = list(g.itertuples())
    known_idx = [i for i, x in enumerate(rows) if x.station_code in ids]
    present = {x.station_code for x in rows}
    for i, x in enumerate(rows):
        if x.station_code in ids or pd.isna(x.dist): continue
        prev = max((j for j in known_idx if j < i), default=None)
        nxt = min((j for j in known_idx if j > i), default=None)
        if prev is None or nxt is None: continue
        a, b = rows[prev], rows[nxt]
        if pd.isna(a.dist) or pd.isna(b.dist): continue
        ctx[x.station_code].append(dict(train=tno, a=a.station_code, b=b.station_code,
                                        ka=abs(x.dist - a.dist), kb=abs(b.dist - x.dist),
                                        present=present))

# ----------------------------------------------------------------- resolve
node_ids = list(pos)
node_lon = np.array([pos[n][0] for n in node_ids])
node_lat = np.array([pos[n][1] for n in node_ids])

def near(lon, lat, kmax):
    """Graph nodes within kmax of a point, nearest first."""
    dlat = (node_lat - lat) * 111.32
    dlon = (node_lon - lon) * 111.32 * math.cos(math.radians(lat))
    d = np.sqrt(dlat ** 2 + dlon ** 2)
    idx = np.where(d <= kmax)[0]
    return sorted(((node_ids[i], float(d[i])) for i in idx), key=lambda t: t[1])

def route_fit(code, cand):
    """Fraction of this code's route contexts that the candidate node reproduces,
    and how many of them rule it out by appearing in the same train."""
    ok = tot = excl = 0
    for c in ctx.get(code, [])[:12]:
        if cand in c["present"]: excl += 1; continue
        pa, pb = spkm(c["a"], cand), spkm(cand, c["b"])
        if pa is None or pb is None: continue
        tot += 1
        tol_a = max(TH["route_tol_km"], c["ka"] * TH["route_tol_frac"])
        tol_b = max(TH["route_tol_km"], c["kb"] * TH["route_tol_frac"])
        if abs(pa - c["ka"]) <= tol_a and abs(pb - c["kb"]) <= tol_b: ok += 1
    return (ok / tot if tot else None), tot, excl

rows = []
for code in unknown:
    nm = uname[code]
    src, anchor = None, None
    if code in osm_by_code and pd.notna(osm_by_code[code]["lon"]):
        src, anchor = "osm", (osm_by_code[code]["lon"], osm_by_code[code]["lat"])
    elif code in wd_by_code and wd_by_code[code]["lon"] is not None:
        src, anchor = "wikidata", (wd_by_code[code]["lon"], wd_by_code[code]["lat"])
    alias_names = [nm] + osm_by_code.get(code, {}).get("names", []) + \
                  wd_by_code.get(code, {}).get("names", [])

    cands = []
    if anchor:
        cands = [(n, d) for n, d in near(anchor[0], anchor[1], TH["anchor_search_km"])][:12]
    else:
        # no coordinate: fall back to name candidates nationally, then let route decide
        scored = sorted(((max(sim(a, x) for a in alias_names for x in node_names[n]), n)
                         for n in ids), reverse=True)[:8]
        cands = [(n, float("nan")) for s, n in scored if s >= TH["name_weak"]]

    best, vetoed = None, []
    for cand, dkm in cands:
        nsim = max((sim(a, x) for a in alias_names for x in node_names[cand]), default=0.0)
        rfit, rtot, rexcl = route_fit(code, cand)
        # hard veto 1: the train calls at both, so they are two different places
        if rexcl >= 2 or (rexcl == 1 and (rfit or 0) < 0.5):
            vetoed.append(cand); continue
        # hard veto 2: the candidate's own code is still running in 2024, so it was
        # never renamed away - the two are separate live stations (New Barauni / BJU)
        live = cand in codes_2024
        if live:
            vetoed.append(cand); continue
        score = 0.0
        if nsim >= TH["name_strong"]: score += 1.4
        elif nsim >= TH["name_weak"]: score += 0.7
        if not math.isnan(dkm):
            if dkm <= 1.0: score += 1.2
            elif dkm <= 3.0: score += 0.8
            elif dkm <= TH["alias_max_km"]: score += 0.3
        if rfit is not None and rtot >= 1:
            # a failing fit is weak evidence: the graph's own topology gaps cause many
            score += 1.3 * rfit if rfit >= 0.5 else -0.3
        rec = dict(cand=cand, cand_name=nname[cand], km=dkm, name_sim=round(nsim, 3),
                   route_fit=None if rfit is None else round(rfit, 2), route_n=rtot,
                   route_excluded=rexcl, code_live_2024=live, score=round(score, 2))
        if best is None or rec["score"] > best["score"]: best = rec

    # without name support, position has to be decisive on its own: either the two sit
    # on the same spot, or they are close and the timetable km agree repeatedly
    if best and best["name_sim"] < TH["name_weak"] and not math.isnan(best["km"]):
        tight = best["km"] <= 0.5 or (best["km"] <= 1.5 and best["route_n"] >= 2
                                      and (best["route_fit"] or 0) >= 0.5)
        if not tight: best["score"] = min(best["score"], TH["accept_score"] - 0.1)

    cls, why, review = "unresolved", "", ""
    if best and best["score"] >= TH["accept_score"]:
        cls = "alias"
        bits = []
        if best["name_sim"] >= TH["name_weak"]: bits.append(f"name {best['name_sim']:.2f}")
        if not math.isnan(best["km"]): bits.append(f"{best['km']:.2f} km apart")
        if best["route_fit"] is not None and best["route_n"]:
            bits.append(f"route fit {best['route_fit']:.0%} of {best['route_n']}")
        bits.append("old code retired" if not best["code_live_2024"] else "old code still live")
        why = "; ".join(bits)
        if best["name_sim"] < TH["name_weak"]:
            review = "accepted on position and route, not on name: confirm the rename"
    elif best and best["score"] >= TH["review_floor"]:
        why = (f"borderline: {best['cand']} ({best['cand_name']}) scored {best['score']}"
               f" < {TH['accept_score']}")
        review = "human review"
    elif anchor:
        cls = "missing_station"
        if not cands:
            why = f"anchored, no graph node within {TH['anchor_search_km']:.0f} km"
        else:
            nearest = min((d for _, d in cands if not math.isnan(d)), default=float("nan"))
            why = (f"anchored, but the nearest graph node is {nearest:.1f} km away and is a "
                   "different live station: this station is absent from the graph")
    else:
        why = "no coordinate and no name candidate"
    if vetoed:
        why += f"; ruled out by co-occurrence: {','.join(vetoed[:3])}"

    rows.append(dict(code=code, name=nm, stops_2024=ustops[code], trains_2024=len(utrains[code]),
                     anchor_source=src,
                     anchor_lon=anchor[0] if anchor else None,
                     anchor_lat=anchor[1] if anchor else None,
                     resolution=cls,
                     graph_node=best["cand"] if cls == "alias" else None,
                     graph_node_name=best["cand_name"] if cls == "alias" else None,
                     km_apart=None if (not best or math.isnan(best["km"])) else round(best["km"], 2),
                     name_sim=best["name_sim"] if best else None,
                     route_fit=best["route_fit"] if best else None,
                     route_contexts=best["route_n"] if best else 0,
                     route_excluded=best["route_excluded"] if best else 0,
                     old_code_retired=(not best["code_live_2024"]) if best else None,
                     score=best["score"] if best else None,
                     evidence=why, review=review))

cw = pd.DataFrame(rows)

# a rename is one-to-one: if two codes claim the same node, at most one can be right.
# Keep the better-supported claim (name first, then score) and send the rest to review.
contested = {}
for node, g in cw[cw.resolution == "alias"].groupby("graph_node"):
    if len(g) < 2: continue
    g = g.sort_values(["name_sim", "score"], ascending=False)
    winner = g.iloc[0]
    contested[node] = dict(kept=winner.code, demoted=g.code.tolist()[1:])
    for i in g.index[1:]:
        cw.loc[i, ["resolution", "graph_node", "graph_node_name"]] = ["unresolved", None, None]
        cw.loc[i, "review"] = "human review"
        cw.loc[i, "evidence"] = (f"also claimed {node}, which {winner.code} "
                                 f"({winner.name}) matches better: likely a separate "
                                 "station the graph lacks")

cw = cw.sort_values(["resolution", "stops_2024"], ascending=[True, False])
cw.to_csv(OUT / "crosswalk.csv", index=False)
dupe = contested

rep = dict(
    experiment="E-702 / gap G1", graph="graph_v1_3/open", thresholds=TH,
    unknown_codes=len(unknown),
    stops_2024_affected=int(cw.stops_2024.sum()),
    resolved_alias=int((cw.resolution == "alias").sum()),
    stops_recovered_by_alias=int(cw.loc[cw.resolution == "alias", "stops_2024"].sum()),
    missing_station=int((cw.resolution == "missing_station").sum()),
    unresolved=int((cw.resolution == "unresolved").sum()),
    stops_still_unresolved=int(cw.loc[cw.resolution != "alias", "stops_2024"].sum()),
    anchored={k: int(v) for k, v in cw.anchor_source.value_counts().items()},
    aliases_with_route_support=int(((cw.resolution == "alias") & (cw.route_fit.fillna(0) >= .5)).sum()),
    aliases_name_only=int(((cw.resolution == "alias") & (cw.route_contexts == 0)).sum()),
    aliases_old_code_retired=int(((cw.resolution == "alias") & (cw.old_code_retired == True)).sum()),
    aliases_flagged_for_review=int(((cw.resolution == "alias") & (cw.review != "")).sum()),
    borderline_for_review=int((cw.review == "human review").sum()),
    multiple_codes_per_node={k: v for k, v in dupe.items()},
    top_aliases=cw[cw.resolution == "alias"].head(25)[
        ["code", "name", "graph_node", "graph_node_name", "stops_2024", "evidence"]].to_dict("records"),
    biggest_unresolved=cw[cw.resolution != "alias"].head(20)[
        ["code", "name", "resolution", "stops_2024", "evidence"]].to_dict("records"))
json.dump(rep, open(OUT / "report.json", "w"), indent=2, default=str)

ov = cw[cw.resolution == "alias"].assign(
    audit_file="G1_station_code_crosswalk", field="node_id", action="recode",
    source_url="", reviewer="", review_date="",
    notes=lambda d: "2024 stops recovered: " + d.stops_2024.astype(str))
ov.rename(columns={"code": "item_id", "code_": "x"})[
    ["audit_file", "item_id", "field", "name", "graph_node", "action", "evidence",
     "source_url", "reviewer", "review_date", "notes"]].rename(
    columns={"name": "current_value", "graph_node": "new_value"}).to_csv(
    OUT / "OVERRIDES_G1.csv", index=False)

print(json.dumps({k: v for k, v in rep.items()
                  if k not in ("top_aliases", "biggest_unresolved", "multiple_codes_per_node")},
                 indent=1, default=str))
