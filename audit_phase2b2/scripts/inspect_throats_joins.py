import csv
import json
import math

def haversine(lon1, lat1, lon2, lat2):
    R = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# Load network_vertices to get coords of throat link endpoints
import pyarrow.parquet as pq
table = pq.read_table("03_graph_construction/graph_v2_0_open/work/network_vertices.parquet").to_pydict()
v_coords = {v: (table["lon"][i], table["lat"][i]) for i, v in enumerate(table["vertex"])}

csmt_lon, csmt_lat = 72.8357856, 18.9404925

# 1. Throat links within 10 km of CSMT
nearby_throats = []
with open("03_graph_construction/graph_v2_0_open/work/c2_throat_links.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        a, b = row["a"], row["b"]
        if a in v_coords and b in v_coords:
            ca = v_coords[a]
            cb = v_coords[b]
            d = haversine(csmt_lon, csmt_lat, ca[0], ca[1])
            if d <= 15.0:
                nearby_throats.append({
                    "a": a, "b": b, "km": float(row["km"]),
                    "dist_from_csmt_km": round(d, 2),
                    "coords_a": ca, "coords_b": cb,
                    "osm_a": row["osm_a"], "osm_b": row["osm_b"]
                })

print(f"Total throat links within 15 km of CSMT: {len(nearby_throats)}")
nearby_throats.sort(key=lambda x: x["dist_from_csmt_km"])
print("Closest 10 throat links to CSMT:")
print(json.dumps(nearby_throats[:10], indent=2))

# 2. Joins in c2_joins.csv
nearby_joins = []
with open("03_graph_construction/graph_v2_0_open/work/c2_joins.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        a, b = row["a"], row["b"]
        # get coords if available
        ca = v_coords.get(a)
        if ca:
            d = haversine(csmt_lon, csmt_lat, ca[0], ca[1])
            if d <= 15.0:
                nearby_joins.append({
                    "row": row,
                    "dist_from_csmt_km": round(d, 2)
                })

print(f"\nTotal joins within 15 km of CSMT: {len(nearby_joins)}")
print(json.dumps(nearby_joins[:10], indent=2))
