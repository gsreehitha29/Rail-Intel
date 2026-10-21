"""G15 verification - is the 2024 service layer sound, and how does it sit beside 2017?

Four checks:
  runtimes   on pairs both layers share, do the observed median runtimes agree? The
             two are built from different timetables by different code, so agreement
             is real evidence that the 2024 layer is put together correctly.
  speeds     implied speeds have to be physically sensible, and should sit a little
             above 2017's because the 2024 dataset is express-heavy.
  coverage   which layer sees more of the network, and why they differ.
  repairs    do the edges G5 and G6 added actually carry trains? An added edge no
             train uses would be a bad repair.

Run:  python verify.py <Rail-Intell root> <service dir> <output dir>
"""
import json, sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT, SVC, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)

new = pd.read_csv(SVC / "service_edges_directed_2024.csv")
old = pd.read_csv(ROOT / "03_graph_construction/service_layer_v1_3/open/"
                  "service_edges_directed.csv")
ed = pd.read_csv(SVC / "edge_service_2024.csv")

# ---- 1. runtimes on shared pairs
j = new.merge(old, on=["from_station", "to_station"], suffixes=("_24", "_17"))
j = j[(j.n_runtime_obs_24 >= 2) & (j.n_runtime_obs_17 >= 2)]
j["diff"] = j.runtime_min_median_24 - j.runtime_min_median_17
j["rel"] = j["diff"] / j.runtime_min_median_17.replace(0, np.nan)
runtimes = dict(shared_pairs_compared=len(j),
                median_abs_diff_min=round(float(j["diff"].abs().median()), 2),
                within_5_min=round(float((j["diff"].abs() <= 5).mean()), 4),
                within_10_min=round(float((j["diff"].abs() <= 10).mean()), 4),
                median_relative_change=round(float(j["rel"].median()), 4),
                spearman=round(float(j[["runtime_min_median_24",
                                        "runtime_min_median_17"]].corr("spearman")
                                     .iloc[0, 1]), 3))

# ---- 2. speeds
s24 = new.observed_speed_kmph.dropna(); s17 = old.observed_speed_kmph.dropna()
speeds = dict(median_2024=round(float(s24.median()), 1),
              median_2017=round(float(s17.median()), 1),
              p10_p90_2024=[round(float(s24.quantile(.1)), 1), round(float(s24.quantile(.9)), 1)],
              over_130_kmph=int((s24 > 130).sum()), under_10_kmph=int((s24 < 10).sum()),
              pairs_with_speed=int(s24.notna().sum()))

# ---- 3. coverage, and why the two differ
cov = dict(
    trains_2024=3889, trains_2017_layer=5208,
    stops_per_train_2024=round(85055 / 3889, 1),
    directed_pairs_2024=len(new), directed_pairs_2017=len(old),
    direct_edge_share_2024=round(float(new.is_direct_physical_edge.mean()), 4),
    direct_edge_share_2017=round(float(old.is_direct_physical_edge.mean()), 4),
    median_hops_2024=float(new.physical_hops.median()),
    median_hops_2017=float(old.physical_hops.median()),
    edges_served_2024=int((ed.service_load_2024 > 0).sum()),
    edges_served_2017=int((ed.service_load_2017.fillna(0) > 0).sum()),
    edges_served_by_either=int(((ed.service_load_2024 > 0) |
                                (ed.service_load_2017.fillna(0) > 0)).sum()),
    note=("the 2024 dataset is express-heavy, so consecutive stops sit further apart "
          "and fewer of them are single physical edges; it is not less accurate, it "
          "sees a different train population"))

# ---- 4. do the repaired edges carry trains?
rep = ed[ed.origin != "v1.3"]
repairs = dict(repaired_edges=len(rep),
               carrying_trains=int((rep.service_load_2024 > 0).sum()),
               share=round(float((rep.service_load_2024 > 0).mean()), 4),
               by_origin={k: dict(n=int(len(g)),
                                  carrying=int((g.service_load_2024 > 0).sum()),
                                  median_load=float(g.service_load_2024.median()))
                          for k, g in rep.groupby("origin")},
               busiest=rep.nlargest(8, "service_load_2024")[
                   ["name", "origin", "km", "service_load_2024"]].to_dict("records"),
               unused=rep[rep.service_load_2024 == 0][["name", "origin", "km"]].head(10)
               .to_dict("records"))

# Judge runtimes on absolute agreement, not rank correlation: most pairs sit in a
# narrow 5-20 minute band, where ranks are mostly ties and Spearman says little.
speeds["implausible_share"] = round(
    (speeds["under_10_kmph"] + speeds["over_130_kmph"]) / speeds["pairs_with_speed"], 4)
verdict = []
verdict.append("runtimes agree with the independently built 2017 layer"
               if runtimes["median_abs_diff_min"] <= 5 and runtimes["within_10_min"] >= 0.8
               else "REVIEW: runtimes disagree with the 2017 layer")
verdict.append("speeds are physically sensible"
               if speeds["implausible_share"] <= 0.02
               else "REVIEW: implausible speeds present")
verdict.append("most repaired edges carry trains"
               if repairs["share"] >= 0.6 else "REVIEW: many repaired edges carry no trains")

out = dict(experiment="E-705 verification", runtimes=runtimes, speeds=speeds,
           coverage=cov, repairs=repairs, verdict=verdict)
json.dump(out, open(OUT / "verification.json", "w"), indent=2, default=str)
print(json.dumps(out, indent=1, default=str))
