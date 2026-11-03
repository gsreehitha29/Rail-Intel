"""E-722 Step 1b: classify 2017 timetable codes that resolve to no v2.0-open node.

Read-only. Resolution mirrors v14._resolver (node id, else crosswalk alias).
Candidate sources, in order: E-702 crosswalk (2024 code -> 2017-era code, used in
reverse), then exact normalised-name match to a v2.0 station.
"""
import csv, json, pathlib, re, collections

ROOT = pathlib.Path(__file__).resolve().parents[3]
REL = ROOT / "03_graph_construction/release/rail-intel-v2.0-open/graph"
OUT = pathlib.Path(__file__).resolve().parent / "out"
TT = ROOT / "external_data/timetable_2017_datagovin/Train_details_22122017.csv"
E702 = ROOT / "04_analysis_modules/E-702_station_code_crosswalk/out/crosswalk.csv"

nodes = list(csv.DictReader(open(REL/"nodes.csv", encoding="utf-8")))
ids = {r["node_id"] for r in nodes}
st = {r["node_id"]: r for r in nodes if r["node_type"] == "station"}
cw = {r["code"]: r["graph_node"] for r in csv.DictReader(open(REL/"station_code_crosswalk.csv", encoding="utf-8")) if r["resolution"] == "alias"}
resolve = lambda c: c if c in ids else cw.get(c)

def norm(s):
    s = (s or "").upper()
    s = re.sub(r"\b(JN|JN\.|JUNCTION|JNC|RLY|RAILWAY|STATION|HALT|CANTT|ROAD|RD|TERMINUS|TERMINAL)\b", " ", s)
    return re.sub(r"[^A-Z]", "", s)
by_name = collections.defaultdict(list)
for nid, r in st.items(): by_name[norm(r["node_name"])].append(nid)

old2new = collections.defaultdict(set)
for r in csv.DictReader(open(E702, encoding="utf-8")):
    if r["resolution"] == "alias" and r["graph_node"]:
        old2new[r["graph_node"]].add(r["code"])

rows = list(csv.DictReader(open(TT, encoding="utf-8", errors="ignore")))
trains, stops, name = collections.defaultdict(set), collections.Counter(), {}
for r in rows:
    c = r["Station Code"].strip()
    trains[c].add(r["Train No"]); stops[c] += 1; name.setdefault(c, r["Station Name"].strip())

out = []
for c in trains:
    if resolve(c): continue
    cand_e702 = sorted(n for n in old2new.get(c, ()) if n in ids)
    cand_name = sorted(by_name.get(norm(name[c]), [])) if norm(name[c]) else []
    if len(cand_e702) == 1:
        cls, tgt, ev = "rename", cand_e702[0], "E-702 crosswalk (2024 code -> this 2017 code)"
    elif len(cand_name) == 1:
        cls, tgt, ev = "name_match", cand_name[0], "exact normalised name"
    elif cand_e702 or len(cand_name) > 1:
        cls, tgt, ev = "ambiguous", "|".join(cand_e702 or cand_name), "several candidates"
    else:
        cls, tgt, ev = "no_candidate", "", ""
    t = st.get(tgt) if tgt in st else None
    out.append(dict(code=c, name_2017=name[c], trains_2017=len(trains[c]), stop_rows=stops[c],
                    class_=cls, candidate=tgt, candidate_name=t["node_name"] if t else "",
                    candidate_scheduled_2017=t["scheduled_2017"] if t else "", evidence=ev))
out.sort(key=lambda r: -r["trains_2017"])
with open(OUT/"unresolved_codes_2017.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)

unsched = [r for r in st.values() if r["scheduled_2017"] != "True"]
cand = {r["candidate"] for r in out if r["class_"] in ("rename", "name_match")}
summary = dict(
    timetable_codes=len(trains), unresolved=len(out),
    unresolved_trains_stops=sum(r["stop_rows"] for r in out),
    by_class={k: dict(codes=sum(1 for r in out if r["class_"] == k), stop_rows=sum(r["stop_rows"] for r in out if r["class_"] == k)) for k in ("rename", "name_match", "ambiguous", "no_candidate")},
    unscheduled_stations=len(unsched),
    unscheduled_explained_by_unresolved_code=sum(1 for r in unsched if r["node_id"] in cand),
    unscheduled_station_code_not_in_timetable=sum(1 for r in unsched if r["node_id"] not in trains and r["node_id"] not in cand),
)
json.dump(summary, open(OUT/"unresolved_codes_2017_summary.json", "w"), indent=2)
print(json.dumps(summary, indent=2))
