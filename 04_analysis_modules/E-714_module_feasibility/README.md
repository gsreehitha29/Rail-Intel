# E-714 — measured feasibility of the downstream modules, and the timetable-versus-track comparison

    python feasibility.py <root> out      # ~40 s

## 1. What a timetable-built network gets wrong (contribution evidence)

IIT Kharagpur's IRN (RSTGCN, 2025): 4,735 stations, 9,336 "direct line" edges, built from
consecutive stops of 3,892 trains. Mapped through the v1.4 crosswalk, 8,877 edges have both ends
in our graph. Of those, **30.7% are a single physical section; 69.3% pass through one or more
stations; 43.3% through three or more** (median 4 when any). 4,627 of our nodes are not in IRN.

## 2. Sensitivity of each module to the dataset's uncertainties

Length: floor sections that also have an official distance are a median 1.49x short (p75 1.99x);
every floor was scaled by 1.49 and the analyses re-run.

| Analysis | Result under the length correction | Verdict |
|---|---|---|
| reach within 100 km (400 sampled stations) | Spearman 0.993; median -7.5%; 35.5% change >10% | ranks only |
| detour km, 100 busiest sections | Spearman 0.997; median +11.4%; severing set unchanged | ranks, km as lower bound |
| betweenness top 50 (k=300 samples) | 38/50 kept; noise floor between two samples only 21/50; E-707 repair 35/50 | not as a ranking |
| cut points, bridges, components, hop reach | length-free by construction | robust |
| giant-component decay | random: 1% -> 0.979, 2% -> 0.892, 5% -> 0.272; degree-targeted: 0.955, 0.640, 0.054 | robust (topological) |

Betweenness-targeted decay uses the sampled ranking and is not reliable.

Output: `out/E-714_feasibility.json`. Feeds the "contribution, feasibility and scope lock" doc.
