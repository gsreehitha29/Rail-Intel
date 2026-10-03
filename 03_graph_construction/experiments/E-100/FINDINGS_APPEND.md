
---

## F-011 — Random failure is more damaging than betweenness-targeted attack
**Class:** publishable · **Evidence:** `E-100` (with controls) · **Module 3**

Robustness measure **R** (normalised area under the SCF curve; `R = 0.5` is a
network that never fragments until the last node):

| Attack strategy | R | f(SCF<0.5) | f(SCF<0.1) |
|---|---|---|---|
| degree, static | **0.0227** | 0.025 | 0.050 |
| degree, adaptive | 0.0287 | 0.050 | 0.050 |
| **random** | **0.0435** | 0.050 | 0.100 |
| betweenness, adaptive | 0.0803 | 0.100 | 0.200 |
| service_load, adaptive | 0.0983 | 0.050 | 0.299 |
| service_load, static | 0.1056 | 0.050 | 0.324 |
| betweenness, static | **0.1241** | 0.100 | 0.299 |

**Only degree-targeted attack beats random.** Betweenness-targeted removal — the
strategy `[BHA15]` found most effective on the Indian *service* network — is
**2.9× less damaging than random failure** here.

This inverts the standard complex-network result, so it was validated three ways
before being believed:

1. **Control on a hub network.** The same code on `BA(3000, 2)`: random
   `R = 0.4128`, degree `R = 0.1010`. The textbook result is reproduced exactly,
   so the implementation is sound.
2. **Control on a pure tree.** A path graph of the same 9,058 nodes gives random
   `R = 0.0157` — *more* fragile than ours (0.0435), which is where a 94%
   tree-like network should sit.
3. **Mechanism identified.** The top-500 betweenness nodes induce only **27
   connected components, largest run 123 nodes** — they lie *contiguously* along
   the trunk. Removing them in rank order excises one connected stretch and
   leaves a few large pieces; random removal scatters cuts and shatters the
   network into many small ones.

**Why it matters.** Hub-attack intuitions come from scale-free networks. This
network has bounded degree and no hubs, exactly as `[BAR11]` describes for
spatially embedded networks, so the intuition does not transfer. Module 3 must
report the full strategy set against a random baseline and **must not** assume
targeted attack is the worst case. For a near-tree infrastructure network, broad
scattered damage — a flood, a strike, a region-wide power failure — is the
threat model that matters, not the loss of a few important stations.

---

## F-012 — The physical network is far more fragile than its service representation implies
**Class:** publishable — **a headline Module 3 result** · **Evidence:** `E-100`
**Status: provisional** pending the like-for-like reproduction in `E-104`

`[BHA15]` report that their 809-station Indian Railways **service** network needs
**~95% random node removal** to collapse, versus ~25% for targeted attack.

On our **physical** graph, random removal of **5%** of nodes takes the giant
component to 18.5%, and **10%** takes it to **6.1%**.

| removed | SCF (giant share), random removal |
|---|---|
| 2.5% | 0.718 |
| 5.0% | 0.185 |
| 10.0% | **0.061** |
| 20.0% | 0.010 |

The service representation overstates robustness by roughly an order of
magnitude in the removal fraction required. The reason is structural, not a
disagreement about data: a service-network edge means *a train runs between these
two stations*, which creates an edge wherever a through train exists and so
manufactures redundancy that **no track provides**. Cut the physical line and
every service that used it fails together; the service graph cannot represent
that because it has already abstracted the line away.

**This is the mirror image of our own `D-013` warning.** Filtering to the
attributed core overstates *fragility* by ~2.5× because it deletes real
alternative routes; using a service representation overstates *robustness* by
~10× because it invents routes that do not exist. Both errors come from the same
root cause — the graph not being the infrastructure — and together they are the
quantified argument for the physical-graph thesis.

**Why provisional.** This is not yet like-for-like: different node counts,
different representations, different vintages. `E-104` must rebuild `[BHA15]`'s
representation *from our own data* and re-run both percolations on the same
station set. Only then does the comparison carry its full weight. The direction
and rough magnitude are not in doubt; the exact factor is.

---

## F-013 — Edge-level speed coverage is 64.4%, not 49.8%
**Class:** diagnostic — **improves what Module 2 can do** · **Evidence:** `E-100`

The handoff's "speed is present on only 49.8% of corridors" (`D-012`) is correct
but is a **corridor-level** figure. At the level that matters for routing:

| Level | Coverage |
|---|---|
| corridors with speed | 1,135 / 2,279 = **49.8%** |
| **edges** with speed | 6,238 / 9,689 = **64.4%** |
| **route km** with speed | 43,296 / 72,201 = **60.0%** |

Speed-bearing corridors carry more edges than average, so the usable share is
materially higher than the corridor figure suggests. `travel_time_proxy` is
therefore more defensible than `D-012` implied — though `D-012`'s core ruling
stands unchanged: speed must stay **nullable and never a filter**, because the
corridors that have it are scattered and filtering on it still collapses the
graph to 771 nodes.

`railgraph.weights.travel_time_coverage()` returns these numbers for any graph,
and any result using `travel_time_proxy` must report them.

---

## F-014 — Community count is not robust across methods; high modularity is a near-tree artifact
**Class:** publishable (methodological caution) · **Evidence:** `E-100` · **Module 1**

| Method | Communities | Q | Largest | Median | NMI vs stated zone | ARI |
|---|---|---|---|---|---|---|
| Louvain (modularity) | **78** | 0.9646 | 211 | 108 | **0.689** | 0.269 |
| Infomap (flow) | **865** | 0.8789 | 29 | 10 | 0.593 | 0.042 |

Two things follow, and both are cautions rather than results.

**The number of communities is not a property of the network.** Louvain and
Infomap disagree by a factor of 11. Module 1 must never report "the Indian
railway network has N communities"; it must report both partitions and the scale
each one describes.

**Q = 0.96 is not evidence of strong community structure.** The network is 94%
tree-like with meshedness 0.034, and modularity is near-degenerate on sparse
near-trees: almost any spatial partition of a tree scores highly, because there
are so few edges to cut. Quoting Q as a quality score here would be a mistake.
This is the resolution-limit problem of modularity maximisation in its most
acute form.

**What is genuinely informative** is the agreement with the *independent*
administrative label: NMI 0.689 against stated railway zone, on the 4,123 nodes
whose zone comes from the station master rather than from corridor inference.
That is external corroboration that detected structure is real, and it is
computed on stated zones only — including inferred zones would leak, because
inferred zone derives from the same corridors that built the edges.

---

## F-015 — Stitched edges are under-represented among the most critical bridges
**Class:** publishable (validates the novel operator) · **Evidence:** `E-100`

Junction stitching (`D-005`) creates 2,252 of 9,689 edges — **23.2%**. The
obvious worry is that the novel operator manufactures artifactual criticality.
It does not:

| | stitched share |
|---|---|
| all edges | 23.2% |
| **top-50 bridges by nodes stranded** | **14.0%** (7 of 50) |
| top-10 bridges by nodes stranded | 30% (3 of 10) |

Stitched edges are **less** likely than average to appear among the most
severing bridges, which is the opposite of what an artifact-generating operator
would produce.

**But the single most critical edge in the network is a stitched edge** (`F-016`,
BOE–MFA). So the headline criticality result depends on one application of the
novel operator. `E-105` must audit that edge specifically and by name, not rely
on the aggregate being reassuring. A 14% aggregate does not license a claim about
the one edge that matters most.

---

## F-016 — The graph independently identifies the Siliguri Corridor as India's worst rail chokepoint
**Class:** publishable (face validity) · **Evidence:** `E-100`
**Supersedes and sharpens `F-005`**

Ranking every bridge in the giant component by how many nodes it strands, the
worst is **BOE–MFA: Barsoi Jn – Makuria** (87.92°E, 25.65°N), length 4.34 km,
double-tracked, carrying **136 trains**.

Cutting it strands **459 nodes (5.1% of the network)**:

| | |
|---|---|
| zones | NFR 458, NER 1 |
| states | Assam 187, West Bengal 49, Tripura 16, Nagaland 4, Mizoram 1, Bihar 1 |
| extent | 87.84–95.78°E, 23.00–28.04°N |

That is the **entire rail network of Northeast India**. The cut point sits on the
approach to the Siliguri Corridor — the "Chicken's Neck" — which is India's
best-known strategic infrastructure bottleneck.

The next seven worst bridges are the Fakiragram – Kokrajhar – Salakati – Basugaon
– Dangtal – New Bongaigaon chain (93 trains each, 304–310 nodes stranded), i.e.
the continuation of the same single-threaded corridor into Assam. The handoff's
`F-005` named this chain; the ranked analysis shows the true chokepoint is one
step further west, and more severe.

**Nothing in the construction pipeline encodes any of this.** No geography, no
strategic designation, no prior. The graph recovers a known structural fact it
was never told, and attaches a service-impact figure to it. This is the cheapest
and most persuasive face-validity evidence the project has, and it belongs in the
paper beside the quantitative validation — not instead of it.

---

## F-017 — "Top-k central stations" is not k stations
**Class:** publishable (methodological caution) · **Evidence:** `E-100` · **Module 1**

Taking the exact distance-weighted betweenness ranking and asking how many
*distinct places* the top k covers:

| | distinct localities (connected runs) | largest run | degree-2 pass-throughs |
|---|---|---|---|
| top-10 | 6 | 4 | 10% |
| top-50 | **11** | 17 | 60% |
| top-100 | 14 | 35 | 64% |
| top-200 | **15** | 42 | **78%** |

**The top 200 nodes by betweenness are 15 localities.** In a network where 82.8%
of nodes are degree 2, every node on a through-chain carries essentially the same
traffic, so betweenness cannot discriminate within a chain. The Mughal Sarai
cluster makes it concrete — four adjacent nodes spanning degrees 2 to 6:

| node | degree | betweenness |
|---|---|---|
| MGS (Mughal Sarai Jn) | 6 | 0.140518 |
| XCBN | 5 | 0.140515 |
| MGMY (Mughal Sarai Marshalling Yard) | 2 | 0.140353 |
| ICBN | 4 | 0.140252 |

The spread across all four is **2.65 × 10⁻⁴**, i.e. they are indistinguishable.

**Consequence for Module 1.** A "top-50 critical stations" table would be a list
of 11 places with duplicates, and would read as a result when it is an artifact
of chain topology. Module 1 must either report **corridor-level** criticality
(edge betweenness aggregated by `corridor_id`) or deduplicate the node ranking by
locality before presenting it. This also means top-k overlap — the summary
statistic the `g05` sweep relies on — is measuring locality stability, not station
stability, and must be described that way.

**Data-quality flag for `E-105`.** Five of the top 20 betweenness nodes have
`node_name` equal to `node_id`, i.e. no real station name: **NWBV** (the
single highest-betweenness node in the network, 0.1532), **RAU**, **XCBN**,
**ICBN**, **HATI**. The most structurally central node in the graph being
unnamed is exactly the kind of thing the stratified audit exists to catch.

---

## F-018 — Cross-source validation: 0 contradictions, and the stitching deficit is 71% definitional artifact
**Class:** publishable — **the direct test of claim C2** · **Evidence:** `E-101`

Two directions, because one alone proves nothing.

### Completeness — does the timetable find holes in the physical graph?

| Check | Result |
|---|---|
| service pairs with both endpoints in the graph | 9,586 / 10,193 = **94.04%** |
| of those, already a direct physical edge | **80.89%** |
| resolving within 3 physical hops (skip-stop signature) | **97.81%** |
| **whose endpoints fall in different physical components** | **0** |
| median hops when indirect | 2 |

**Zero cross-component contradictions out of 9,586 resolvable pairs.** Two
networks built from genuinely independent sources — 119,446 GIS segments and
416,970 timetable stop records, neither used to construct the other — and the
timetable never once asserts a connection the physical graph says is impossible.
That is the strongest single validation statement the project has.

### Soundness — do physical edges carry service? And is stitching the weak spot?

The raw stratification looks damning for the novel operator:

| stratum | n | direct service | projected load |
|---|---|---|---|
| ALL | 9,689 | 80.0% | 89.9% |
| `any_stitch=True` | 2,252 | **57.9%** | 66.4% |
| `any_stitch=False` | 7,437 | **86.7%** | 97.0% |
| endpoints = both_station | 9,100 | 85.2% | 94.8% |
| endpoints = mixed | 493 | **0.0%** | 16.6% |
| endpoints = both_junction | 96 | **0.0%** | 1.0% |

A 28.8 pp gap — except the two 0.0% rows give the game away. **`service_edges.csv`
contains only station codes** (8,539 distinct, zero `JN::` ids), because a
junction is not a station and cannot appear in a timetable. So an edge with a
junction endpoint *cannot* have direct service **by definition** — and all 589
such edges are stitched (26.2% of stitched edges; 0% of unstitched).

Conditioning on station-to-station edges, where the test is meaningful:

| | n | direct service | projected load |
|---|---|---|---|
| stitched | 1,663 | **78.5%** | 85.0% |
| unstitched | 7,437 | **86.7%** | 97.0% |
| gap | | **8.2 pp** | 12.0 pp |

**71% of the apparent gap was a definitional artifact. The remaining 8.2 pp is
real** — Fisher exact odds ratio **0.558**, p = 2.0 × 10⁻¹⁶.

**How to report this.** Stitched edges are genuinely less likely to carry
scheduled service, by a modest but unambiguous margin. That is partly expected
rather than erroneous: a stitch connects a junction to the first *placed* station
on a corridor, which is disproportionately a short stub, a yard approach or a
low-traffic branch. But "partly expected" is not "validated", and an 8.2 pp
deficit at p ≈ 10⁻¹⁶ is exactly why `E-105` must audit stitched edges as their
own stratum — which `F-015` already demanded for a different reason.

**Methodological note worth the paper's space.** Three analyses of the same data
give three different answers: the aggregate says "80% of edges carry service,
fine"; the naive stratification says "stitching is broken, 57.9% vs 86.7%"; the
correct conditioning says "71% definitional, 8.2 pp real and significant." Only
the third is defensible. This is the concrete argument for `[BOE25]`'s
per-stratum reporting discipline over a single global figure.

---

## F-019 — Route-km reconciles to −0.06% of the published national figure, but the mechanism is not established
**Class:** diagnostic — **do not present as validation yet** · **Evidence:** `E-101`
**Supersedes the expected explanation in `F-004`**

| | km | gap vs Year Book 2024–25 (69,439) |
|---|---|---|
| all graph edges | 72,201 | **+3.98%** |
| excluding the 126 edges from zero-station corridors | **69,401** | **−0.06%** |
| also excluding parallel-corridor edges | 68,324 | −1.61% |

A 38 km miss on 69,439 km is striking. **It is also probably a coincidence, and
must not be reported as a reconciliation until the mechanism is established.**

`F-004` predicted the gap would be explained by parallel chords and loops counted
separately. It is not: parallel edges account for only 1,076 km of the 2,762 km
gap — **39%**. Excluding zero-station corridors closes the rest, but inspecting
those corridors shows they are *not* the yard and siding links the hypothesis
requires. The longest are:

| corridor | endpoints | km |
|---|---|---|
| C00325 | Balipara – Harmuti Junction | 132.6 |
| C00682 | Bogibeel Bridge – Harmuti Junction | 116.0 |
| C00315 | Balangir – Puranakatak | 94.9 |
| C00906 | Darsi – Vki Venkatagiri | 90.2 |

These are genuine route — Bogibeel is a major Brahmaputra rail bridge. Their
length distribution (median 12.9 km, mean 20.2 km, max 132.6 km) is a mixture of
short yard links and real lines whose stations simply failed to place. Excluding
them is therefore not defensible as "excluding non-route track", and the near-exact
agreement has no established cause.

**Resolution.** Compare **per zone** against
`reference_data/Table-19.2-Zone-wise.csv`. One national total can reconcile by
luck; seventeen zone totals cannot. Our zone totals are already computed
(NR 7,429 · WR 6,673 · SCR 6,208 · NWR 6,028 · SR 5,202 · NFR 4,621 km). This is
the single highest-value remaining validation check and it needs one reference
file. Registered as `E-102`.

---

## F-020 — The network's near-tree fragility comes from its degree sequence, not its geography
**Class:** publishable · **Evidence:** `E-101` (12 rewiring replicates)

Against a degree-preserving (double-edge-swap) null, on the giant component:

| measure | observed | null mean | z |
|---|---|---|---|
| bridges | 1,412 | 1,754 | **−3.8** |
| bridge share | **0.1460** | **0.1833** | **−3.9** |
| articulation points | 1,338 | 1,708 | **−4.1** |
| independent cycles | 612 | 632 | −5.7 |

The real network has **fewer** single points of failure than a random graph with
the same degree sequence — not more. So the 14.6% bridge share is not evidence
that the spatial embedding makes the network fragile; the fragility is almost
entirely a consequence of the degree distribution (87.6% of nodes at degree ≤ 2,
`F-011`), and the actual geography adds a modest amount of redundancy on top,
presumably because real alternative routes cluster locally where traffic
justifies them.

**Why this matters for Module 3.** It reframes the question. "Why is the Indian
railway network fragile?" has the answer "because it is built as a near-tree, and
a near-tree is fragile" — which is almost tautological. The non-trivial question
is where the network has *more* redundancy than its degree sequence predicts, and
why. That is a better Module 3 thesis than a percolation curve.

**Caveat to state.** Double-edge-swap rewiring breaks the graph into ~21
components (observed: 1), so observed and null giant components differ slightly
(9,058 vs 8,939) and the comparison is approximate. A spatially constrained null
— rewiring only between geographically plausible pairs — would be a stronger
test and is not yet implemented.

---

## F-021 — One edge's length is not a measurement, and the integrity suite cannot see it
**Class:** defect — **fix before freeze** · **Evidence:** `E-007` · **Action:** `D-024`

Exporting GeoJSON silently produced 9,688 edge features for 9,689 edges. Chasing
the missing one found a genuine latent defect.

**Edge `E005897`, `JN::Alirajpur` – `JN::Khandala`:**

| field | value |
|---|---|
| `length_km` | **0.05** |
| `is_colocated` | **True** |
| `any_stitch` | True |
| `reconstruction_status` | `degenerate_no_edges` |
| `service_load` | 0 |
| `JN::Khandala` coordinates | **null** |
| `JN::Khandala` match | `rejected_name_spatial_conflict` / `exact_name_no_coord` |

`JN::Khandala` is the single node of 9,095 with no coordinate. A stitch edge's
length is the haversine between its endpoints, so with one endpoint missing the
haversine is **undefined** — and the undefined value then passed through
`clip(lower=0.05)` and emerged as a plausible-looking 50 metres, flagged
`is_colocated = True` as though two stations sat on top of each other.

**Three consequences.**

1. **`VERIFICATION.txt`'s "no null edge lengths" check passes for the wrong
   reason.** It is satisfied by an undefined quantity having been converted into
   a number. This is precisely the failure mode the project's own engineering
   principle forbids — *"Unknown is a valid state. Do not silently impute
   unsupported railway facts."* The check verifies the absence of nulls, not the
   presence of measurements, and those are different things.
2. **There are 248 genuinely co-located edges, not 249.** Every reported count
   of co-located station pairs is off by one.
3. **It compounds `F-002`.** `is_colocated` now conflates *three* distinct
   states: truly co-located stations, edges floored because they were short, and
   this edge, floored because its length could not be computed at all.

**Scale:** exactly one edge, because exactly one node lacks a coordinate and it
has degree 1. The magnitude is negligible; the fact that the integrity suite
cannot distinguish "measured 50 m" from "unmeasurable" is not — the same
mechanism would hide a thousand such edges just as effectively.

**How it surfaced is the lesson.** No internal check caught it. It surfaced
because an export to a format that *cannot represent a missing coordinate*
refused to invent one. Round-tripping through a stricter format is a validation
technique in its own right, and `verify_roundtrip()` now requires every omitted
feature to be explicitly accounted for rather than merely counted.

---

## D-024 — Add `length_source` and make the verification suite assert measurement, not non-nullity
**Date:** 2026-10-03 · **Status:** proposed · **Evidence:** `F-021`
**Reversible:** yes, additive column

**Problem.** `length_km` currently conflates three provenances, and nothing in
the shipped schema distinguishes them:

| provenance | n | how produced |
|---|---|---|
| `measured` | 9,440 | `measure_km` difference along a corridor spine, or haversine between two known coordinates |
| `floored` | 248 | raw length below the 0.05 km floor (`D-007`) |
| `undefined` | **1** | haversine undefined — an endpoint has no coordinate (`F-021`) |

**Proposed.** Add a `length_source` column with exactly those three values, and
extend `s10_verify_dataset.py` with two checks: that no edge has
`length_source = undefined` while presenting a finite `length_km` without the
flag set, and that `is_colocated` is true only where `length_source = floored`.

**Why this and not simply dropping the edge.** `JN::Khandala` is degree 1 and
carries no service, so dropping it would change nothing measurable — which is
exactly why dropping it is the wrong instinct. The edge is a *record that the
data has a hole*, and the hole is in the station master, not in the graph. Making
the hole visible in the schema is worth more than a cosmetically cleaner edge
list, and it generalises: the same column makes any future unmeasurable edge
self-announcing instead of self-concealing.

**Cost.** One column, two verification checks, a one-line note in the data
dictionary. Implemented in `s09`/`s10` by whoever next touches the pipeline —
this is a Phase 2 change, so it belongs to Bhuvanesh, not to the Phase 3 builder.

---

## F-022 — Construction-choice sensitivity: the tiered verdict
**Class:** publishable — **this is claim C3** · **Evidence:** `E-200` (16 distinct cells)

A single sweep verdict is useless, because the sweep necessarily contains
configurations the decision register already rejected on measured grounds. Run
over everything, *every* conclusion is an artifact — which only restates that
`D-001` and `D-005` mattered. The informative question is conditional: **given
the decisions, how much do the remaining reasonable choices move the answer?**

So the verdict is computed over three nested tiers.

### Tier A — the nine defensible construction choices
*(default, tolerance 1.0/2.0, parallel=mean, dissolve_degree2, prune_degree1,
merge_colocated, match_conf=high-only, gauge_constrained)*

| Conclusion | Verdict | Max deviation | Range |
|---|---|---|---|
| giant component share | **robust** | 0.004 | 0.9918 – 0.9995 |
| mean shortest path | **robust** | 2.5% | 1,266 – 1,308 km |
| circuity (median) | **robust** | 1.6% | 1.249 – 1.270 |
| R, random attack | **robust** | 11.2% | 0.0433 – 0.0541 |
| R, degree attack | **robust** | 19.5% | 0.0206 – 0.0269 |
| top-50 corridor criticality | **robust** | 0.18 | ≥ **0.82** overlap |
| bridge share | *conditional* | 0.025 | 0.1206 – 0.1645 |
| meshedness | *conditional* | 0.006 | 0.0275 – 0.0398 |
| | **artifact: none** | | |

**This is the result Phase 4 needs.** Given the decision register, every headline
conclusion survives the choices that remain genuinely open. Corridor criticality
holds at 82% or better overlap; the worst case is `gauge_constrained`, which is
an opt-in routing mode rather than a default. The two conditional verdicts are
marginal — `bridge_share` exceeds its 2 pp band by half a point, driven by
`prune_degree1`, which mechanically removes 313 degree-1 stubs and so *lowers*
the bridge count by construction.

### Tier B — adding the attributed-core views

| Conclusion | Verdict | Worst cell | Movement |
|---|---|---|---|
| top-50 corridor criticality | **artifact** | `core_v2` | overlap falls to **0.34** |
| mean shortest path | **artifact** | `core_v4` | **+47%** (1,275 → 1,871 km) |
| circuity (median) | **artifact** | `core_v4` | **+31%** (1.251 → 1.639) |
| bridge share | **artifact** | `core_v4` | **0.146 → 0.324** (2.2×) |
| R, random attack | *conditional* | `core_v4` | −43% |

This is `D-013`'s warning, measured far more sharply than the handoff stated it.
The handoff said filtering to the core "would overstate fragility by roughly
2.5×". It does (2.2× here) — **and it also destroys two thirds of the criticality
ranking, inflates mean path by 47% and circuity by 31%.** A module that ran on
the attributed core would not merely overstate fragility; it would identify
largely different critical corridors.

Note the direction of the path inflation matters for the honesty of the claim:
`core_v4` has a *smaller* giant component (93.7%), which on its own would make
paths *shorter*. Paths get 47% longer anyway, because filtering removes real
shortcuts. The effect is therefore understated by this measurement, not inflated.

### Tier C — adding the rejected construction options
*(no stitching at any tolerance, junction-only, station-only)*

Every conclusion is an artifact; `top50_corridor_overlap` falls to **0.08** at
`tol=1.0, stitch=OFF`, and `giant_share` spans 0.176 – 0.9995. This tier is not
a finding about the network, it is a measurement of how much `D-001` and `D-005`
mattered — and the answer is that without them nothing downstream would mean
anything.

### A measurement caveat that must travel with this table

`mean_path` is computed **within** the giant component, so for a fragmented cell
it measures paths inside a fragment and is not comparable to the default. The
clearest case is `tol=1.0, stitch=OFF`: mean path 604 km, *shorter* than the
default's 1,275 km, purely because its giant component is 17.6% of the network.
Path comparisons are therefore valid only among cells with a comparable giant
component. All nine Tier A cells sit at giant share ≥ 0.9918, so Tier A's
robustness verdict for `mean_path` is sound; Tier C's artifact verdict for it is
confounded and should be read from `top50_corridor_overlap` instead.

---

## F-023 — Junction stitching's damping effect is measure-specific, not universal
**Class:** publishable — **the precise version of `F-001`/`F-007`** · **Evidence:** `E-200`

`F-007` established a 322× damping factor on connectivity from `E-002`. `E-200`
measured the same tolerance × stitching grid across the **full battery**, which
is what the roadmap required before generalising the claim:

| Conclusion | Range, stitched | Range, unstitched | **Damping factor** |
|---|---|---|---|
| giant component share | 0.0023 | 0.7461 | **322×** |
| mean shortest path | 32.4 km | 967.5 km | **30×** |
| bridge share | 0.0079 | 0.1950 | **25×** |
| top-50 corridor criticality | 0.12 | 0.40 | **3.3×** |
| R, random attack | 0.0094 | 0.0220 | **2.3×** |
| independent cycles | 200 | 360 | 1.8× |
| meshedness | 0.0109 | 0.0138 | **1.3×** |

**The claim must be stated per measure, not as a single number.** Stitching
near-eliminates tolerance sensitivity for connectivity (322×), distance (30×)
and fragility (25×); it helps moderately for criticality rankings (3.3×) and
resilience (2.3×); and it barely helps at all for cycle structure (1.3–1.8×).

That last row is the honest limit of the claim. Independent cycles and meshedness
are counts of redundancy, and stitching *adds* edges — so it adds cycles roughly
in proportion to the tolerance, rather than stabilising them. Anyone computing a
redundancy measure still has to justify their placement tolerance.

**Why this is the right form for the paper.** "Our operator makes the result
insensitive to a free parameter" would be an overclaim. "Our operator removes
tolerance sensitivity from connectivity, distance and fragility measures by one
to two orders of magnitude, and does not remove it from cycle counts" is both
true and more useful, because it tells a reader exactly which of their own
results the technique would protect.

---

## F-024 — The inverted attack ordering is robust to construction choices
**Class:** publishable · **Evidence:** `E-200` · **confirms `F-011`**

`F-011` found that random failure is more damaging than betweenness-targeted
attack — inverting the standard result. Across all 20 sweep cells:

- **Degree-targeted attack is the worst strategy in 20 of 20 cells.**
- **Random is worse than betweenness-targeted in 19 of 20 cells.**

The single exception is `node_model=junction_only`, which is a 2,274-edge
corridor-endpoint graph rather than a station-level one — a different object, not
a different parameterisation of the same one.

So the inversion is a property of the network, not of how the graph was built.
That matters: it means Module 3 can state it as a finding about Indian Railways
rather than as a caveat about methodology, and `[BAR11]`'s account of spatial
networks (bounded degree, no hubs) is the explanation rather than an excuse.

---

## F-025 — Export format choice: parquet for analysis, GraphML for archive
**Class:** housekeeping — **decides `D-016`** · **Evidence:** `E-007`

| Format | Round-trip | Size | Load time |
|---|---|---|---|
| GraphML | exact (Δ length sum 0.0) | 7.51 MB | 0.83 s |
| **parquet** | exact (Δ length sum 0.0) | **0.81 MB** | **0.02 s** |
| GeoJSON | 1 edge / 1 node omitted, fully accounted (`F-021`) | 7.95 MB | — |
| (source CSV) | — | 2.8 MB | 0.05 s |

**Decision for `D-016`: ship all three, none exclusively.** Parquet is 9× smaller
than GraphML and **42× faster to load** than it, so it is the format the Phase 4
modules should use. GraphML is the citable graph-native archive format and the
one an outside tool will accept. GeoJSON is for maps only, and carries the
caveat that its edge geometry is the straight chord between endpoints, **not the
true track alignment** — the corridor spine is not retained per edge by `s09`.

Pickle is rejected: version-fragile, Python-only, fails `[WIL16]`
Interoperability. A graph database is rejected: operational burden with no
analytical gain at 9,095 nodes.
