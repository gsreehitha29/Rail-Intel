import pandas as pd
import json

root = "c:/Users/Sreehitha/OneDrive/Desktop/Major Project/Rail-Intel"

# 1. Check wikidata_stations.csv for BCT and MMCT
wd = pd.read_csv(f"{root}/external_data/wikidata_stations.csv")
wd_bct = wd[wd.code.isin(["BCT", "MMCT"])].to_dict(orient="records")
print("=== Wikidata Stations for BCT / MMCT ===")
print(json.dumps(wd_bct, indent=2))

# 2. Check 2017 timetable pairs
from pathlib import Path
import sys
sys.path.insert(0, f"{root}/03_graph_construction/experiments/E-716_osm_v2_build")
import osm_build as ob

pairs = ob.timetable_pairs(Path(root), ("2017",))
bct_pairs = pairs[(pairs.a.isin(["BCT", "MMCT"])) | (pairs.b.isin(["BCT", "MMCT"]))]
print(f"\n=== 2017 Timetable pairs mentioning BCT or MMCT ({len(bct_pairs)}) ===")
print(bct_pairs.to_string())

# 3. Check 2017 raw timetable (Train_details_22122017.csv) if present
tt_path = f"{root}/external_data/Train_details_22122017.csv"
try:
    tt = pd.read_csv(tt_path, low_memory=False)
    bct_trains = tt[tt["Station Code"].isin(["BCT", "MMCT"])]
    print(f"\nRaw 2017 timetable rows with BCT or MMCT: {len(bct_trains)}")
    print(bct_trains["Station Code"].value_counts().to_dict())
    print(bct_trains["Station Name"].value_counts().head(5).to_dict())
except Exception as e:
    print(f"Error reading raw timetable: {e}")

# 4. Save results to JSON
with open("audit_phase2d/results/task_e_bct_investigation.json", "w", encoding="utf-8") as f:
    json.dump({
        "wikidata": wd_bct,
        "pairs_2017_count": len(bct_pairs),
        "pairs_2017": bct_pairs.to_dict(orient="records")
    }, f, indent=2)
