# Literature — annotated bibliography and gap analysis

> Maintained from Phase 3 onward. Every entry: what it did, what we take from it,
> how we differ. Entries are cited by key (e.g. `[SEN03]`) from `DECISIONS.md`,
> `FINDINGS.md` and `PAPER_OUTLINE.md`.
>
> Last updated: 2026-10-03

---

## 1. Prior work on the Indian railway network

### `[SEN03]` Sen, Dasgupta, Chatterjee, Sreeram, Mukherjee & Manna (2003)
*Small-world properties of the Indian railway network.* Physical Review E 67, 036106.
arXiv:cond-mat/0208535

**What it did.** Built a *space-of-changes* (P-space) graph: stations are nodes,
two stations share an edge if at least one train stops at both. Data: 579 trains
over **587 stations** from the printed IR timetable.

**Published figures.**

| Quantity | Value |
|---|---|
| mean distance ⟨d⟩ | ≈ 2.16, fitting A + B·log N with A ≈ 1.33, B ≈ 0.13 |
| clustering C | ≈ 0.69 (random-graph prediction 0.113) |
| degree distribution | exponential, F(k) ∼ exp(−αk), α = 0.0085 |
| degree correlation r | −0.033 (essentially uncorrelated) |

**What we take.** The reproduction target for `g04`/V4, and the canonical citation
for "the Indian railway network has been studied as a complex network."

**How we differ.** P-space makes every train's stop list a clique, so its high
clustering and short path lengths are properties of *the representation*, not of
the railway. Two stations served by different trains that never meet are
nonetheless neighbours. Our graph is physical: 9,095 nodes (15.5×), geolocated,
infrastructure-attributed. We reproduce their statistics and then show the
divergence explicitly rather than asserting it.

---

### `[BHA15]` Bhatia, Kumar, Kodra & Ganguly (2015)
*Network science based quantification of resilience demonstrated on the Indian
Railways Network.* PLOS ONE 10(11):e0141890. arXiv:1508.03542

**What it did.** Origin–destination network of **809 stations** / 7,066 trains
(Oct 2014), edges weighted by train count, 752 stations in the giant component.
Source: IR websites plus Ixigo. Percolation framework with
**SCF = FF / TF** (fraction of stations remaining in the giant component).
Compared removal and recovery sequences by degree, strength, betweenness,
eigenvector and closeness centrality against a random baseline. Simulated three
hazards (tsunami, cascading blackout, cyber-attack).

**Published figures.** Targeted attack on high-degree stations collapses the
network after removing ~**25%** of stations, versus ~**95%** for random failure.
Betweenness-based recovery was most efficient; random recovery's impact area was
250% larger.

**What we take.** The strongest prior art for Module 3, the SCF formulation, and
the attack/recovery sequence protocol. Reproduction target for `g04`/V4.

**How we differ — and this is the key point.** Their network is a *service*
network, and the paper states that it does not distinguish physical
infrastructure damage from service disruption; node removal is treated uniformly
regardless of cause. We have a physical layer and a service layer as separate,
independently sourced objects, so we can ask what they cannot: does cutting
*track* fragment the network the same way as losing *service*? Expect a different
answer, and that difference is Module 3's contribution.

---

### `[DAS20]` Complex Network Analysis of Indian Railway Zones (2020)
arXiv:2004.04146

**What it did.** Zone-level graph: **17 nodes** (the zones themselves), edges
weighted by train count between zone pairs. In-degree/out-degree, "degree
passenger correlation," betweenness, clustering, clique detection. The authors
themselves note the limitation: this is "a network of complex networks" — each
zone is a complex system in its own right, collapsed to a single node.

**What we take.** Confirms the pattern across all Indian-railway network
literature found so far: analysis has stayed at zone granularity (17 nodes)
or timetable-station granularity (587–1,620 stations, `[SEN03], [BHA15]`
and the SE-train study below). Nobody has reached infrastructure-level,
station-population scale for India specifically — our 9,095 nodes is not
just bigger than the two headline comparisons, it is a different *tier* of
granularity than anything in the India-specific literature, zone studies
included.

---

### `[REG24]` Connectivity evaluations of Indian Railways zones with superfast
express (SE) trains (2024), ScienceDirect

**What it did.** 1,620 stations across 17 zones, SE-train timetables joined to
2011 census, employment and investment data. Degree centrality and
accessibility as connectivity indicators, Theil's T to decompose between-zone
vs. within-zone inequality, a spatial Durbin regression linking investment to
employment. Finding: between-zone inequality in centrality/accessibility
exceeds within-zone inequality, and daytime (7am–9pm) service correlates with
job growth where night service does not.

**What we take.** The first Indian-railway paper found that connects network
position to a real socioeconomic outcome (employment), rather than stopping at
a structural statistic — and the precedent that "friendly hours" (not just
frequency) is a connectivity variable worth separating out.

**How we differ — and this is a genuine opening.** Their accessibility measure
is computed at **zone** granularity (17 units); ours would be computable at
**station** granularity (9,095 nodes) if we can join population/employment
data at that resolution. Nobody has done an equity/accessibility analysis
below zone level for Indian Railways. This is `D17` below.

---

### `[RST25]` RSTGCN — Railway-centric Spatio-Temporal Graph Convolutional
Network for Train Delay Prediction (2025), arXiv:2510.01262

**What it did.** States explicitly it is "the first work to study delay
prediction in the entire IRN." Builds a station graph from **3,892
long-distance trains across 4,735 stations, 9,336 edges** (consecutive stops
only — a space-of-stops graph in `[KUR06]`'s terms, not space-of-stations).
Features: hourly average arrival/departure delay and a novel "hourly
headway" metric. Architecture: three parallel spatio-temporal GCN branches
(recent/daily/weekly), Chebyshev graph convolution, train-frequency-weighted
spatial attention. Data: September 2024, one month of real observed delays.

**What we take.** This is the most current Indian-railway-specific network
paper found (2025) and it is decisive confirmation of the gap: even a
state-of-the-art GNN built specifically for Indian Railways **this year**
still derives its graph purely from timetables (no GIS, no infrastructure
attributes, no true geometry), and at roughly half our node count because it
only includes stations touched by long-distance trains. Our physical layer —
real track count, gauge, sinuosity-validated geometry — is exactly the
missing ingredient their spatial-attention mechanism would want but does not
have. This is `D16` below: a concrete, direct extension of a paper published
months before this one.

---

### `[GHO]` Ghosh et al.
*Statistical analysis of the Indian Railway Network: a complex network approach.*

Same family as `[SEN03]` — timetable-derived, comparable scale. Cited for
completeness of the prior-art table. **To obtain in full.**

---

## 2. The methodological ancestor

### `[KUR06]` Kurant & Thiran (2006)
*Extraction and analysis of traffic and topologies of transportation networks*
("Trainspotting"). Physical Review E 74, 036114. arXiv:physics/0510151

**What it did.** Defines the three representations the whole field now uses:

- **space-of-changes** — stations on one vehicle form a clique; path length =
  number of transfers. (= `[SEN03]`'s graph.)
- **space-of-stops** — consecutive *stops* linked. Introduces **shortcuts**:
  edges with no infrastructure behind them, created because express services skip
  intermediate stations.
- **space-of-stations** — only physically adjacent stations linked. *"This graph
  reflects the topology of the real-life infrastructure."*

Two-layer model: physical graph **G^φ** (space-of-stations) and logical/traffic
graph **G^λ** whose weighted edges each map to a *path* through G^φ. A three-phase
algorithm extracts physical topology from timetables by detecting and eliminating
shortcuts.

**Published figures.** Including shortcuts collapsed their EU-dataset diameter
from **184 to 48** nodes. Space-of-stations degree distributions are
**exponential**; space-of-changes distributions are not.

**What we take.** (a) The vocabulary — our physical layer *is* space-of-stations,
and saying so locates the artifact precisely. (b) The two-layer
physical/logical model, which is exactly our `edges.csv` / `service_edges.csv`
split, and the path-projection idea behind `service_load`. (c) The exponential
degree prediction as a **falsifiable check** on our construction (`g04`/V2) —
if we fit a power law, we built it wrong. (d) The shortcut problem, which is our
express-skip artifact (the 30/67 alternation on corridor C00786).

**How we differ.** Direction of travel. They go **timetable → physical by
removing shortcuts**. We go **GIS → physical by building ordered station chains
and stitching them at junctions**, which leaves the timetable unconsumed and
therefore available as an independent validation set. That inversion is only
available to someone who has done the Phase 1–2 data engineering, and it is
claim **C2**.

---

## 3. Construction method and simplification

### `[KAR16]` Karduni, Kermanshah & Derrible (2016)
*A protocol to convert spatial polyline data to network formats and applications
to world urban road networks.* Scientific Data 3, 160046.

**What it did.** A five-step protocol: separate by crossing category using
bridge/tunnel tags, split lines at intersections and create nodes at endpoints,
merge edges, merge nodes, remove duplicates. Key insight: naive tools create a
node at *every* polyline vertex, inflating node counts; the protocol creates nodes
*only where intersections exist*. Shipped as ArcGIS tools plus networks for 80
cities. Validation was topological (ArcGIS overlap/connectivity checks) plus
re-import cross-checks.

**What we take.** The **publication template** — a protocol plus a dataset is a
legitimate, citable contribution in a data journal. Also independent
confirmation of our founding premise that GIS segment records are not graph
edges (our 119,446 segments → 2,279 corridors).

**How we differ.** Road networks are already topologically connected at
intersections; the problem is *over*-segmentation. Rail GIS corridors terminate
at junctions that may carry no station, so our problem is chains that *fail to
meet* — the opposite failure mode, and the reason junction stitching exists.
Our validation is also external (cross-source) rather than internal.

---

### `[BOE25]` Boeing (2025)
*Topological graph simplification solutions to the street intersection miscount
problem.* Transactions in GIS. doi:10.1111/tgis.70037, arXiv:2407.00258

**What it did.** Names three causes of node over-counting — non-planarity
(overpasses counted as junctions), intersection complexity (divided roads,
roundabouts producing multiple nodes for one junction), and curve digitisation
(vertices treated as nodes). Two algorithms in OSMnx: **edge simplification**
(remove interstitial nodes between true endpoints, preserving geometry) and
**node consolidation**, in a *geometric* variant (buffer and merge) and a
**topological** variant (merge by **network** distance, so spatially close but
topologically remote nodes — a surface street under a flyover — are not merged).

**Published figures.** Without consolidation, median urban intersection count is
overestimated by **~14%**. Simplification reduced nodes ~77% and edges ~83%
across 8,910 urban areas. Validation: stratified manual review of 32 urban areas
against Street View and satellite imagery, reporting **98% TP among consolidated
nodes, 87% TN among unconsolidated, 13% FN**, with the FN rate read as evidence
the conservative parameterisation *understates* the problem.

**What we take.** Three things, all load-bearing. (a) Our `is_dissolvable`
degree-2 question is his edge-simplification problem, and his framing settles that
retaining-with-a-flag is defensible. (b) **Topological, not geometric,
consolidation** is the right method for our 249 co-located pairs — merge by
network distance, never by Euclidean proximity alone. (c) His **validation
protocol** is the template for `g04`/V5: stratified sampling, independent
reference imagery, TP/TN/FP/FN reported **per stratum**, and honesty about which
direction the residual error points. A single global accuracy number is not worth
having.

**How we differ.** Street networks; our failure mode is disconnection, not
over-counting. And he reports FN rate as a limitation — we intend to report
per-stratum agreement as a *result*, specifically for the stitched edges, because
those are the novel operator and therefore the ones a reviewer will distrust.

---

### `[UIC16]` UIC (2016)
*RailTopoModel — railway infrastructure topological model.* International Railway
Standard **IRS 30100**. Basis of the railML 3 topology core.

**What it is.** The standard conceptual model for describing railway
infrastructure topology, built on connexity graph theory, with four aggregation
levels: **nano** (switch interiors), **micro** (switches, buffer stops), **meso**
(operation points), **macro** (main operation points and corridors).

**What we take.** Vocabulary alignment. Our station-level graph sits at
**meso–macro**: nodes are operation points (stations) and corridor endpoints
(junctions). Declaring that is cheap and positions the artifact against an
international standard instead of inventing terms. Our `node_type` distinction
(`station` vs `operational_junction`) maps cleanly onto the operation-point /
topology-point distinction the standard already makes.

**How we differ.** RailTopoModel is a schema for infrastructure managers with
authoritative data. We are reconstructing a meso-level topology from incomplete
open data, so we additionally carry matching confidence and provenance per
element, which the standard does not model.

---

### `[MAT17]` MatchingLand (2017)
*A geospatial data testbed for the assessment of matching methods.* Scientific
Data 3/4.

Precedent for publishing *matching evaluation* as a first-class result. Supports
treating our 1,555 tiered junction matches — each carrying method, name score,
spatial gap and confidence class — as a reportable artifact rather than an
internal detail.

---

## 4. Analysis-side literature

### `[BAR11]` Barthélemy (2011)
*Spatial networks.* Physics Reports 499(1–3), 1–101.

The reference review for spatially embedded networks. Key points we rely on:
degree is **bounded** in spatial networks (ours: max 7, 82.8% of nodes at degree
2), there are no hubs, and betweenness structure is governed by geometry rather
than by degree heterogeneity. Cite this so our degree distribution is reported as
the *expected signature* of a spatial network, not defended as a non-defect.

### `[TR20]` *Resilience in railway transport systems: a literature review* (2020)
Transport Reviews 40(4).

Framing and terminology for Module 3; distinguishes robustness, vulnerability,
resilience and recoverability, which we must not use interchangeably.

### `[SCH]` Schneider et al. — robustness measure **R**; robustness envelopes
Standard scalar summary of a percolation curve, so attack sequences can be
compared by one number rather than by eyeballing curves. Module 3 reports R per
sequence against a random baseline.

### `[ZHA19]` Zhao et al. (2019)
*Circuity in China's high-speed-rail network.* Journal of Transport Geography 77.

Direct precedent for circuity — network distance ÷ great-circle distance — as a
rail accessibility measure. Computable from our node coordinates and `length_km`
alone, which keeps Module 2 inside scope without population data (blueprint §6).

### Community detection — resolution limit
Modularity maximisation has a known resolution limit and degenerate near-optimal
solutions. Module 1 therefore runs **at least two methods** (Louvain/Leiden and
Infomap) and validates against `zone_code` as an independent label via NMI/ARI.
Never cluster *on* zone.

---

## 5. The closest competitor

### `[PAL26]` Palk et al. (2026)
*Robustness assessment of public transport networks in various graph
representations: systematic review, decision support, and case study.* Networks
(Wiley). doi:10.1002/net.70021

**Status: NOT YET READ — paywalled, 403s to automated retrieval.**
**Blocking for the C3 novelty claim. Obtain via institutional access.**

**What it appears to do, from title and indexing.** Systematic review of how the
choice of graph *representation* changes robustness-assessment conclusions, plus
decision support for choosing one, plus a case study.

**Why it matters both ways.** It is independent support for our handoff §4.5
finding (filtering to the attributed core pushes bridge share from 14.6% past
30%, overstating fragility ~2.5×) — and it is the nearest existing claim to our
C3.

**Our intended distinction.** Palk et al. vary the **representation** of an
already-constructed network. We vary the **construction** — placement tolerance,
junction stitching, node model, degree-2 dissolution, match confidence — which is
upstream of representation. On current evidence that is unexamined. **This
distinction must be verified against the actual text before it appears in a
submission.**

---

## 6. Data and documentation standards

### `[WIL16]` Wilkinson et al. (2016)
*The FAIR Guiding Principles for scientific data management and stewardship.*
Scientific Data 3, 160018. — Findable, Accessible, Interoperable, Reusable.
Drives the `g07` release checklist: persistent identifier, rich metadata,
standard formats, explicit licence, provenance.

### `[GEB21]` Gebru et al. (2021)
*Datasheets for datasets.* Communications of the ACM 64(12), 86–92. — The
format for `graph_v1/DATASHEET.md`: motivation, composition, collection process,
preprocessing, uses, distribution, maintenance.

---

## 7. The gap, as it will be stated in the paper

> Published graphs of the Indian railway network are derived from timetables
> `[SEN03, GHO, BHA15]`, are an order of magnitude smaller than the station
> population, carry no geographic or infrastructure attributes, and cannot be
> externally validated because the timetable is both their source and their only
> available reference. The construction literature for spatial networks has
> concentrated on street networks `[KAR16, BOE25]`, where the characteristic
> problems are over-counting and over-segmentation. Segment-oriented national
> rail GIS presents the opposite failure mode: ordered station chains that fail
> to meet, because corridors terminate at junctions carrying no station. No
> published work quantifies how sensitive downstream criticality, accessibility
> and resilience conclusions are to the construction choices that resolve it
> `[PAL26 — to verify]`.

### Claims

| | Claim | Supported by |
|---|---|---|
| **C1** | A 9,095-node geolocated, infrastructure-attributed, provenance-carrying **physical** station graph of Indian Railways with a derived service layer, released FAIR with a datasheet | 15.5× `[SEN03]`, 11.2× `[BHA15]`; `[KAR16]` precedent; `[WIL16, GEB21]` |
| **C2** | A reproducible GIS→corridor→ordered-chain→**junction-stitched** transformation, with stitching as the named operator resolving rail-specific chain fragmentation (59.4%→99.6%), and the timetable retained as validation rather than consumed as input | Inverts `[KUR06]`; distinct failure mode from `[KAR16, BOE25]` |
| **C3** | Cross-source external validation plus a **construction-choice sensitivity study** reporting which downstream conclusions survive the construction choices and which are artifacts | Extends `[PAL26]` upstream; protocol from `[BOE25]` |

---

## To obtain

| | Why | Priority |
|---|---|---|
| `[PAL26]` Palk et al. 2026, *Networks* | Blocking for the C3 novelty claim | **High** |
| `[GHO]` Ghosh et al. | Completes the prior-art table | Medium |
| `[SCH]` Schneider et al., R index (original) | Module 3 protocol | Medium |
| `[TR20]` Transport Reviews 2020 review, full text | Module 3 framing | Low |
