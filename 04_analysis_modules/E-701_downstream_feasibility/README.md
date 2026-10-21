# E-701: Downstream feasibility (what each dataset adds to graph v1.3)

**Question.** Which analytics are feasible on graph v1.3 now, and what do the datasets fetched on 5 Oct add?

**Run.** `python feas.py <Rail-Intell root> <this folder>/out` (about 10 s; needs pandas and networkx).
**Write-up.** The "Rail-Intel downstream feasibility" doc (a Claude doc, linked from the chat of 11 Oct).

## Key numbers (`out/report.json`)

- **2024 routes (IIT KGP), never used in construction.** 3,885 of 3,892 trains route on v1.3 open. Median length error is 0.92%; 90.4% are within 5%. This is the cleanest independent validation.
- **2024 vs 2017 service.** 267 sections (4,584 km) carry trains in 2024 but none in 2017. Section loads correlate with 2017 at Spearman 0.88.
- **Running days.** 5,208 trains, 84% daily. A days ÷ 7 weight turns distinct trains into trains per day, which is about 11% lower overall.
- **Delays (Sept 2024).** 11,964 stop-to-stop sections (1.06 M runs) map onto track. On double lines, the busiest quartile loses 5.1 min per 100 km (95% CI 2.7–7.7), against 0.7–2.1 on quieter ones. Busy single track shows 10.1 min per 100 km, but the CI of −2.1 to 22.4 means this is not yet significant. Arrival delay equals departure delay in every row.
- **2015 timetable.** 1,969 trains appear in 2015, 2017 and 2024.
- **OSM (full variant).** Electrification is tagged on 84% of edges; 2,375 km of route is mostly not electrified.

## Outputs

`out/report.json` · `out/delay_hops.csv` (per stop-to-stop section: runs, km, minutes lost, single-track share, load)

## Caveats

The IIT KGP data has no licence, so it is for internal research only until the authors agree. The licence of `Railway_Network_.csv` is unresolved.
