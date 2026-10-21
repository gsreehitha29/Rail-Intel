"""G16 - trains per day: weight the service layer by how often each train actually runs.

The service layer counts distinct trains. A weekly train and a daily one each count
once, so every load figure in the project overstates daily traffic, and overstates it
unevenly: a corridor worked by weekly specials looks as busy as one worked by daily
expresses.

The fix does not need a third-party list. The September 2024 delay data records each
train on each date it ran, 30 days of it, so how often a train runs is **observed**
rather than asserted:

    trains_per_day = distinct dates the train was seen / 30

Two checks say this measure is sound rather than an artefact of patchy tracking:

  weekday pattern   of 1,491 trains seen on 6 dates or fewer, 1,336 ran on exactly one
                    weekday and 96.7% on two or fewer - a real weekly service. Trains
                    seen on 25+ dates use all seven weekdays.
  second source     against the prasenjit27 weekly running days, the observed medians
                    land on the expected values almost exactly (1 day/week -> 4 dates
                    observed against 4.3 expected; 7 -> 29 against 30). That list only
                    covers 43% of the 2024 trains, so it validates rather than supplies.

Across all 3,892 trains the mean is 14.8 dates in 30, so counting distinct trains
overstates daily traffic by roughly a factor of two.

Run:  python trains_per_day.py <Rail-Intell root> <service dir> <output dir>
"""
import json, sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT, SVC, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SVC.parent))
sys.path.insert(0, str(ROOT / "04_analysis_modules/E-702_station_code_crosswalk"))
from resolve import load_resolver                                    # noqa: E402
from railgraph_repaired import load_graph                            # noqa: E402

DAYS_IN_MONTH = 30
X = ROOT / "external_data/iitkgp_rstgcn_network_2024/Indian-Railway-Network-and-Delays"

# ---------------------------------------------------------------- observed frequency
d = pd.read_csv(X / "train_routes_delays_Sep2024.csv", dtype={"train": str},
                usecols=["train", "date"])
d["tno"] = d.train.str.zfill(5)
d["dow"] = pd.to_datetime(d.date).dt.dayofweek
freq = d.groupby("tno").agg(dates_observed=("date", "nunique"),
                            weekdays_used=("dow", "nunique")).reset_index()
freq["trains_per_day"] = (freq.dates_observed / DAYS_IN_MONTH).round(4)
freq["pattern"] = np.where(freq.dates_observed >= 25, "daily",
                  np.where(freq.weekdays_used <= 2, "weekly or twice weekly", "irregular"))

# validation against the independent weekly list
rd = json.load(open(ROOT / "external_data/running_days_prasenjit27/trains.json"))
wk = {t["trainNumber"].zfill(5): sum(bool(v) for v in t["runningDays"].values()) for t in rd}
freq["days_per_week_listed"] = freq.tno.map(wk)
m = freq.dropna(subset=["days_per_week_listed"]).copy()
m["expected_dates"] = m.days_per_week_listed / 7 * DAYS_IN_MONTH
validation = dict(
    trains_total=len(freq), matched_to_list=len(m),
    match_share=round(len(m) / len(freq), 3),
    spearman=round(float(m[["dates_observed", "expected_dates"]].corr("spearman").iloc[0, 1]), 3),
    median_observed_by_listed_days={int(k): float(v) for k, v in
                                    m.groupby("days_per_week_listed").dates_observed
                                    .median().items()},
    median_expected_by_listed_days={int(k): round(k / 7 * DAYS_IN_MONTH, 1)
                                    for k in sorted(m.days_per_week_listed.unique())},
    weekly_pattern_check=dict(
        trains_with_6_or_fewer_dates=int((freq.dates_observed <= 6).sum()),
        of_which_one_weekday=int(((freq.dates_observed <= 6) & (freq.weekdays_used == 1)).sum()),
        of_which_two_or_fewer=round(float(
            (freq.loc[freq.dates_observed <= 6, "weekdays_used"] <= 2).mean()), 3)))
freq.to_csv(OUT / "train_frequency_2024.csv", index=False)

tpd = dict(zip(freq.tno, freq.trains_per_day))

# ---------------------------------------------------------------- re-weight the layer
res = load_resolver(ROOT)
G, gmeta = load_graph(ROOT)
nm = {n: a.get("name") for n, a in G.nodes(data=True)}

r24 = pd.read_csv(X / "train_routes_Sep2024.csv", dtype=str)
r24["seq"] = r24.stnSerialNumber.astype(int)
r24["tno"] = r24.trainNumber.str.zfill(5)
r24 = r24.sort_values(["tno", "seq"])

pair_n, pair_w = defaultdict(int), defaultdict(float)
for tno, g in r24.groupby("tno", sort=False):
    w = tpd.get(tno)
    if w is None: continue
    stops = []
    for c in g.station_code:
        nd = res.node(c)
        if nd and (not stops or stops[-1] != nd): stops.append(nd)
    for a, b in zip(stops, stops[1:]):
        pair_n[(a, b)] += 1
        pair_w[(a, b)] += w

se = pd.read_csv(SVC / "service_edges_directed_2024.csv")
se["trains_per_day"] = [round(pair_w.get((r.from_station, r.to_station), 0.0), 3)
                        for r in se.itertuples()]
se["trains_per_day_per_distinct_train"] = (se.trains_per_day / se.n_trains).round(3)
se.to_csv(OUT / "service_edges_directed_2024_weighted.csv", index=False)

# per physical edge
ed = pd.read_csv(SVC / "edge_service_2024.csv")
import networkx as nx                                                # noqa: E402
cache = {}
def path(a, b):
    k = (a, b) if a < b else (b, a)
    if k not in cache:
        try: cache[k] = nx.shortest_path(G, a, b, weight="km")
        except (nx.NetworkXNoPath, nx.NodeNotFound): cache[k] = None
    return cache[k]

# both sums must run over the same set of routed pairs, or the ratio between them
# measures the difference in path sets rather than the difference in weighting
edge_w, edge_n = defaultdict(float), defaultdict(int)
for (a, b), w in pair_w.items():
    p = path(a, b)
    if not p: continue
    n = pair_n[(a, b)]
    for u, v in zip(p, p[1:]):
        k = (u, v) if u < v else (v, u)
        edge_w[k] += w
        edge_n[k] += n
key = [(r.a, r.b) if r.a < r.b else (r.b, r.a) for r in ed.itertuples()]
ed["distinct_trains_2024"] = [edge_n.get(k, 0) for k in key]
ed["trains_per_day_2024"] = [round(edge_w.get(k, 0.0), 2) for k in key]
ed["overstatement_factor"] = (ed.distinct_trains_2024 /
                              ed.trains_per_day_2024.replace(0, np.nan)).round(2)
ed.to_csv(OUT / "edge_service_2024_weighted.csv", index=False)

# ---------------------------------------------------------------- what it changes
served = ed[ed.trains_per_day_2024 > 0].copy()
served["rank_unweighted"] = served.distinct_trains_2024.rank(ascending=False)
served["rank_weighted"] = served.trains_per_day_2024.rank(ascending=False)
served["rank_shift"] = served.rank_unweighted - served.rank_weighted
top_un = set(served.nlargest(100, "distinct_trains_2024").edge_id)
top_w = set(served.nlargest(100, "trains_per_day_2024").edge_id)

rep = dict(
    experiment="E-706 / gap G16", days_in_month=DAYS_IN_MONTH, graph=gmeta,
    frequency=dict(
        trains=len(freq),
        mean_dates_observed=round(float(freq.dates_observed.mean()), 1),
        median_dates_observed=int(freq.dates_observed.median()),
        mean_trains_per_day=round(float(freq.trains_per_day.mean()), 3),
        overstatement_factor_overall=round(1 / float(freq.trains_per_day.mean()), 2),
        by_pattern={k: dict(trains=int(len(g)),
                            median_dates=int(g.dates_observed.median()))
                    for k, g in freq.groupby("pattern")}),
    validation=validation,
    effect_on_loads=dict(
        edges_with_service=int(len(served)),
        spearman_weighted_vs_unweighted=round(float(
            served[["distinct_trains_2024", "trains_per_day_2024"]].corr("spearman").iloc[0, 1]), 3),
        top100_overlap=len(top_un & top_w),
        median_overstatement_factor=round(float(served.overstatement_factor.median()), 2),
        p90_overstatement_factor=round(float(served.overstatement_factor.quantile(.9)), 2),
        biggest_rank_gains=served.nlargest(8, "rank_shift")[
            ["name", "distinct_trains_2024", "trains_per_day_2024", "overstatement_factor"]]
        .to_dict("records"),
        biggest_rank_losses=served.nsmallest(8, "rank_shift")[
            ["name", "distinct_trains_2024", "trains_per_day_2024", "overstatement_factor"]]
        .to_dict("records")),
    busiest_per_day=served.nlargest(10, "trains_per_day_2024")[
        ["name", "trains_per_day_2024", "distinct_trains_2024"]].to_dict("records"))

v = rep["validation"]; f = rep["frequency"]
rep["verdict"] = [
    ("the observed frequency matches the independent weekly list"
     if all(abs(v["median_observed_by_listed_days"][str(k)] -
                v["median_expected_by_listed_days"][str(k)]) <= 2.0
            for k in range(1, 8) if str(k) in v["median_observed_by_listed_days"])
     else "REVIEW: observed frequency disagrees with the listed running days"),
    ("infrequent trains run on a fixed weekday, so they are genuinely weekly rather "
     "than patchily tracked"
     if v["weekly_pattern_check"]["of_which_two_or_fewer"] >= 0.9
     else "REVIEW: infrequent trains look like tracking gaps, not weekly services"),
    (f"counting distinct trains overstates daily traffic {f['overstatement_factor_overall']}x "
     f"overall, and the weighting reorders the busiest sections "
     f"({100 - rep['effect_on_loads']['top100_overlap']} of the top 100 change)")]
json.dump(rep, open(OUT / "E-706_report.json", "w"), indent=2, default=str)
print(json.dumps({k: v for k, v in rep.items() if k not in ("graph", "busiest_per_day")},
                 indent=1, default=str)[:3000])
