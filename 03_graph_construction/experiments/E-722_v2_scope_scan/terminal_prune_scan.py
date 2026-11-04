"""E-722 Step 1a: nationwide scan for station footprints that lost track in O4 prune.

Read-only. Rebuilds the C2 pre-prune vertex graph from Stage C1 work files
(network_edges + station snaps + throat links + joins), replays prune(), and
reports every pruned piece whose buffer-stop end lies within R metres of a
released station that the piece does not attach to.
"""
import csv, json, math, pathlib, collections, sys
import pyarrow.parquet as pq
import networkx as nx

ROOT = pathlib.Path(__file__).resolve().parents[3]
WORK = ROOT / "03_graph_construction/graph_v2_0_open/work"
REL = ROOT / "03_graph_construction/release/rail-intel-v2.0-open"
OUT = pathlib.Path(__file__).resolve().parent / "out"
R_M = float(sys.argv[1]) if len(sys.argv) > 1 else 100.0

def hav(lon1, lat1, lon2, lat2):
    p = math.pi / 180
    a = math.sin((lat2-lat1)*p/2)**2 + math.cos(lat1*p)*math.cos(lat2*p)*math.sin((lon2-lon1)*p/2)**2
    return 2 * 6371008.8 * math.asin(math.sqrt(a))

nodes = list(csv.DictReader(open(REL/"graph/nodes.csv", encoding="utf-8")))
st = {r["node_id"]: r for r in nodes if r["node_type"] == "station"}
osm2node = {}
for r in nodes:
    if r["osm_node_id"]:
        osm2node[str(int(float(r["osm_node_id"])))] = r["node_id"]

vmap = {}
for r in csv.DictReader(open(WORK/"station_snaps.csv", encoding="utf-8")):
    nid = osm2node.get(r["node_id"])
    if nid and r["vertex"]:
        vmap.setdefault(r["vertex"], nid)

V = pq.read_table(WORK/"network_vertices.parquet").to_pydict()
vxy = {v: (lo, la) for v, lo, la in zip(V["vertex"], V["lon"], V["lat"])}
E = pq.read_table(WORK/"network_edges.parquet").to_pydict()

G = nx.Graph()
G.add_nodes_from(set(vmap.values()))
def add(a, b, km, src):
    a, b = vmap.get(a, a), vmap.get(b, b)
    if a == b: return
    if G.has_edge(a, b) and G[a][b]["km"] <= km: return
    G.add_edge(a, b, km=float(km), src=src)
for a, b, km, ch in zip(E["a"], E["b"], E["km"], E["chain"]):
    add(a, b, km, f"chain{ch}")
for r in csv.DictReader(open(WORK/"c2_throat_links.csv", encoding="utf-8")):
    add(r["a"], r["b"], float(r["km"]), "throat")
for r in csv.DictReader(open(WORK/"c2_joins.csv", encoding="utf-8")):
    add(r["a"], r["b"], float(r["km"]), "join_" + r["stage"])

G0 = G.copy()
protect = set(st) | {n for n in G if not str(n).startswith(("n", "s"))}
rnd = {}
k = 0
while True:
    d1 = [n for n, d in G.degree() if d <= 1 and n not in protect]
    if not d1: break
    k += 1
    for n in d1: rnd[n] = k
    G.remove_nodes_from(d1)
P = set(rnd)

# station points (both OSM point and track point)
spts = []
for nid, r in st.items():
    for lo, la in ((r["longitude"], r["latitude"]), (r["track_lon"], r["track_lat"])):
        if lo and la: spts.append((nid, float(lo), float(la)))
grid = collections.defaultdict(list)
for nid, lo, la in spts:
    grid[(int(lo*100), int(la*100))].append((nid, lo, la))
def near(lo, la):
    out = {}
    gx, gy = int(lo*100), int(la*100)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for nid, slo, sla in grid[(gx+dx, gy+dy)]:
                d = hav(lo, la, slo, sla)
                if d <= R_M and d < out.get(nid, 1e9): out[nid] = d
    return out

rows = []
for comp in nx.connected_components(G0.subgraph(P)):
    attach = {m for n in comp for m in G0.neighbors(n) if m not in P}
    km = sum(d["km"] for u, v, d in G0.edges(comp, data=True))
    leaves = [n for n in comp if G0.degree(n) == 1]
    foot = {}
    for n in leaves:
        if n in vxy:
            for nid, d in near(*vxy[n]).items():
                if nid not in attach and d < foot.get(nid, 1e9): foot[nid] = d
    if not foot or not attach: continue
    att_st = sorted(a for a in attach if a in st)
    for nid, d in foot.items():
        rows.append({
            "station": nid, "station_name": st[nid]["node_name"],
            "station_degree": st[nid]["degree"],
            "buffer_stop_m": round(d, 1),
            "pruned_km": round(km, 4), "pruned_vertices": len(comp),
            "max_round": max(rnd[n] for n in comp),
            "attaches_to_stations": "|".join(att_st),
            "attaches_to_other": len(attach) - len(att_st),
        })

rows.sort(key=lambda r: (r["station"], -r["pruned_km"]))
with open(OUT/f"terminal_prune_scan_r{int(R_M)}.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
summary = {
    "pre_prune_nodes": G0.number_of_nodes(), "pre_prune_edges": G0.number_of_edges(),
    "pruned_vertices": len(P), "prune_rounds": k, "radius_m": R_M,
    "rows": len(rows), "stations_affected": len({r["station"] for r in rows}),
    "stations_affected_degree1": len({r["station"] for r in rows if r["station_degree"] == "1"}),
    "rows_attaching_to_another_station": sum(1 for r in rows if r["attaches_to_stations"]),
}
json.dump(summary, open(OUT/f"terminal_prune_scan_r{int(R_M)}_summary.json", "w"), indent=2)
print(json.dumps(summary, indent=2))
