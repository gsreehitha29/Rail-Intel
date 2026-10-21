# E-706 — gap G16: trains per day

**The gap.** The service layer counts distinct trains, so a weekly special and a daily express each count once. Every load figure in the project overstated daily traffic, and overstated it unevenly.

**Status: filled and verified.** Counting distinct trains overstates daily traffic **2.03× overall** and **2.5× on the median section**. More consequentially, **49 of the 100 busiest sections change** once traffic is counted per day.

## Measured, not asserted

No third-party list was needed. The September 2024 delay data records each train on each date it ran, 30 days of it, so frequency is observed:

```
trains_per_day = distinct dates the train was seen / 30
```

Across 3,892 trains the mean is 14.8 dates in 30. The population splits cleanly:

| Pattern | Trains | Median dates in 30 |
|---|---|---|
| daily | 1,251 | 30 |
| weekly or twice weekly | 1,745 | 4 |
| irregular | 896 | 16 |

## Two checks that it is real

**It matches an independent source.** Against the prasenjit27 weekly running days, the observed medians land almost exactly on what each listed frequency predicts:

| Listed days/week | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| expected dates in 30 | 4.3 | 8.6 | 12.9 | 17.1 | 21.4 | 25.7 | 30.0 |
| **observed median** | **4** | **8** | **12** | **17** | **21** | **24** | **29** |

That list covers only 43% of the 2024 trains, which is why it validates the measure rather than supplying it.

**Infrequent trains are genuinely weekly, not patchily tracked.** Of 1,491 trains seen on six dates or fewer, **1,336 ran on exactly one weekday** and 96.7% on two or fewer. Trains seen on 25+ dates use all seven weekdays. A tracking gap would scatter across the week; a weekly service does not.

## What the weighting changes

Overall ordering is broadly preserved (Spearman 0.972), but the top of the list is not:

- **Only 51 of the top 100 sections by distinct trains remain in the top 100 by trains per day.**
- Median overstatement factor **2.5**, 90th percentile **3.74**.
- Worst distortion: the Nagbhir narrow-gauge line in Maharashtra, 25 distinct trains but **3.3 a day** (factor 7.58).
- Least distorted: Mumbai CST suburban sections, where almost everything runs daily (factor 1.29).

Busiest sections per day, from the 2024 passenger data:

| Section | Trains/day | Distinct trains |
|---|---|---|
| Kanpur Central – Kanpur Goods Marshal | 238.6 | 576 |
| Allahabad Jn – Prayagraj Junction | 207.1 | 516 |
| Ghaziabad – Sahibabad | 196.6 | 374 |
| Kanpur Goods Marshal – Govindpuri | 158.2 | 379 |

These are passenger trains in the 2024 dataset only; freight and the local services the dataset omits are extra, so each figure is a lower bound.

## Why it matters for the objective

Load is one of the two candidate explanations for where trains lose time, and the delay pilot found the clearest gradient in the busiest load quartile. If nearly half the busiest sections are misidentified, that gradient is measured against the wrong sections. Any load-weighted result — criticality, congestion, the delay model — should use `trains_per_day_2024`.

## Files

- `trains_per_day.py` — derives frequency, validates it, re-weights the layer. `python trains_per_day.py <root> <E-705 out dir> out`
- `out/train_frequency_2024.csv` — per train: dates observed, weekdays used, trains per day, pattern, listed days/week
- `out/service_edges_directed_2024_weighted.csv` — the 2024 service layer with `trains_per_day`
- `out/edge_service_2024_weighted.csv` — per edge: distinct trains, trains per day, overstatement factor
- `out/E-706_report.json` — all figures and the verdicts
