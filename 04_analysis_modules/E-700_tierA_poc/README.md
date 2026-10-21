# E-700: Tier A proof of concept (one region of graph v1.3 open)

**Question.** Do the Tier A applications work on the data we have, or only on paper?

**Region.** Delhi – Agra – Kanpur – Lucknow – Moradabad (bbox 77.0–81.2°E, 26.3–29.0°N):
704 nodes, 759 edges, 4,708 km, one connected component. 1,421 trains from the 2017 timetable.

**Run.** `python run.py <Rail-Intell root> <this folder>/out`. Takes about 20 s and needs pandas and networkx.
Inputs are read-only: `graph_v1_3/open/{nodes,edges}.csv`, `service_layer_v1_3/open/service_edges_directed.csv`,
and `external_data/timetable_2017_datagovin/Train_details_22122017.csv`.

## Verdicts

| Test | Verdict | Key number |
|---|---|---|
| 1 Routing trains on track | works | 100% routed; median length error 3.3%; 75% of trains within 5% |
| 2 Trains per section | works | 91% of sections carry trains; Spearman 0.82 against the build's `service_load` |
| 3 Criticality (section and junction removal) | works, after fixes | 36 sections strand trains (all single-line branches); top-20 overlap with plain betweenness = 0 |
| 4 Accessibility to hubs | works | median 74 min; 43% of stations within 60 min; Delhi 6 min, UP 79, MP 154 |
| 5 Circuity | works | median 1.19; outliers come from the missing Ganga crossing at Farrukhabad, a real gap |
| 6 Observed running times | works | 69% of edges and 73% of km covered; modelled times are about 0.49× observed |

## Defects found by using the graph

- **Aligarh Jn is off the trunk.** The spine runs Daud Khan → Mandrak, with Aligarh as a side stub off Daud Khan. This is an instance of LIMITATIONS §1.1 and needs an override.
- **27 missing-link candidates** are listed in `out/missing_link_candidates.csv`: graph route > 1.25 × timetable and more than 5 km longer. The top case is Dhaulpur–Morena.
- **Ghaziabad–Kanpur is 4% long** (421.6 vs 405 km) and **New Delhi–Agra Cantt is 4% long** (197.6 vs 190). Suspects: the Tundla approach via Etmadpur, the Somna–Daud Khan lower-bound chord, and the Hathras Jn–Hathras Road link.
- **Boundary effect.** 165 sections strand trains inside the box, but only 36 do on the national graph. Always recheck nationally.

## Outputs (`out/`)

`report.json` (all numbers) · `routing_segments.csv` · `edge_load.csv` · `criticality_edges.csv` ·
`criticality_junctions.csv` · `accessibility_stations.csv` · `circuity_pairs.csv` · `edge_runtime.csv` ·
`missing_link_candidates.csv` · `map_data.json` · `tierA_poc.html` (results page)

## Caveats

- The service layer is from 2017 and runs on current track, so sections built after 2017 show zero trains.
- Load counts distinct passenger trains. It is not utilisation: there is no capacity or freight data.
- Junction removal leaves out trains whose run inside the box starts or ends at that junction (this matters for CNB and LKO).
- The licence of `Railway_Network_.csv` is unresolved, so treat these results as internal.
