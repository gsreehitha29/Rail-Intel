# Application positioning — what this graph is for, and what it refuses to do

**Date:** 2026-10-03 · **Graph:** v1.0, spec `f9adf8ca9042`
**Supersedes nothing.** This document reconciles the four applications the team
now wants to claim against the explicit guardrails already written into
`CLAUDE_COWORK_PROJECT_CONTEXT.md` §2, §12 (Module 4), §13, §14 and §15 — the
original scoping doc — and against the measured capability of the shipped
graph. Where the new framing and the old doc disagree, the disagreement is
named rather than quietly resolved.

---

## 1. The positioning insight, and the evidence that it holds

**The claim:** prior Indian-railway network research works the *time* side of
the network — schedules, timetables, delays. This project works the
*infrastructure* side. Two sides of one coin, and only one of them has been
turned over.

This is correct, and the literature pass on 2026-10-03 (`docs/LITERATURE.md`
§1) makes it measurable rather than rhetorical:

| Work | Year | What it is built from | Side of the coin |
|---|---|---|---|
| `[SEN03]` Sen et al. | 2003 | printed timetable, 587 stations | time |
| `[BHA15]` Bhatia et al. | 2015 | origin–destination trains, 809 stations | time |
| `[DAS20]` zone network | 2020 | train counts between 17 zones | time |
| `[REG24]` SE-train connectivity | 2024 | SE timetables + census, 17-zone resolution | time |
| `[RST25]` RSTGCN | **2025** | timetable stop sequences, 4,735 stations, **delay prediction** | time |
| **Rail-Intell v1.0** | 2026 | **GIS infrastructure segments**, 9,095 nodes, track/gauge/geometry attributes | **infrastructure** |

Twenty-three years, five papers, every one of them time-side. The most recent
is a 2025 delay-prediction GNN that still derives its graph from stop
sequences and carries no infrastructure attribute at all. The infrastructure
side of the Indian network has not been built, which is why this project's
first contribution is the construction itself and not an analysis result.

**This reframes the paper's own framing.** `docs/PAPER_OUTLINE.md` §1 currently
states the gap as *prior IRN graphs are timetable-derived, smaller, and
externally unvalidatable* — all true, but stated as three independent
deficiencies. The sharper statement is one structural claim: **the field has
studied Indian Railways as a service system and never as a physical one**, and
the three deficiencies are consequences of that single choice. A timetable
graph is necessarily smaller (it only sees served stations), necessarily
unvalidatable (its source is its only reference), and necessarily
attribute-free (a timetable records no track). Recommend adopting this framing
in §1 and §2 of the paper.

---

## 2. The four applications, assessed honestly

Each application below is rated against two things: what the shipped graph
actually supports (measured, per `publication/QUALITY_NOVELTY_RELEVANCE_REPORT.md`),
and whether the old scoping doc permits the claim.

### A1 · Infrastructure connectivity insights and structural decisions
**Status: fully supported. This is the project's core strength, not an
extension of it.**

Already demonstrated on v1.0: 1,338 articulation points and 1,412 bridges
located and ranked; the Fakiragram–Kokrajhar–New Bongaigaon chain in Assam
rediscovered as the worst severance in the country **without being told about
it** (`GRAPH_HANDOFF_V2.md` §4.7); top-50 corridor criticality robust across
all nine open construction choices (`E-200`, Tier A, ≥0.82 overlap); geometry
independently validated against four UNESCO mountain railways (`F-029`).

Old doc agreement: §15 already lists exactly this — *network criticality,
connectivity gaps, redundancy, structural vulnerability, infrastructure-aware
network visualisation*. No tension. No new data needed.

**Safe claim language:** "identifies, locates and ranks structural
vulnerabilities and connectivity gaps in the physical network." Diagnostic,
not prescriptive.

### A2 · Rerouting special trains around regional festivals
**Status: weakest of the four as stated. The underlying need is real; the
claim as phrased is not supportable and must be narrowed.**

What rerouting-by-demand would require, and what we hold:

| Requirement | Held? |
|---|---|
| Demand signal at station × date granularity | **no** — `reference_data` has zone-level passengers/earnings aggregates only (`Table-19.2`), and `D-032` forbids using an aggregate to populate a finer attribute |
| Line capacity | **no** — `n_tracks` exists but is a corridor constant in 97.09% of corridors (`F-027`), and there is no block-section, headway or signalling data anywhere in the repo |
| Festival calendar mapped to regions | **no** — not in the repo |
| Directional capacity | **no** — the graph is undirected by decision (`D-033`); every capacity statement is direction-blind |
| Observed journey times | **partially** — `service_edges.runtime_min_median` exists; the declared `speed_kmph` must not be used (ratio 0.513, `F-036`) |

Old doc conflict: §14 explicitly lists *capacity saturation*, *headway
analysis* and *passenger demand* under "requires additional operational
data", and §2 says do not claim the project predicts congestion or capacity.
A rerouting recommendation is a capacity-and-demand claim. **As phrased, this
application contradicts the project's own scoping document.**

**What is supportable today, and it is genuinely useful:** not rerouting, but
**alternative-path screening**. Given an origin–destination pair, enumerate
the physically viable paths and report per path:

- route km, and how much of it sits on single-track corridors (`n_tracks` = 1)
- gauge continuity — whether the whole path is traversable without a break of
  gauge (60 non-BG corridors are genuinely not interoperable)
- bridge and articulation-point exposure along the path
- **existing service load** per edge (`service_load`) — how busy that track
  already is according to the timetable
- whether any edge on the path carries the `suspect_long_edge` flag, which
  means the path may be skipping real intermediate stations (`F-041`)

That output answers a real planner's question — *"of the three ways to get a
special train from here to there, which one is single-track, bridge-heavy and
already carrying 40 trains a day?"* — without claiming to know demand, to
schedule anything, or to compute capacity. It is a **screen, not a
recommendation**, and it is fully computable on v1.0.

**Safe claim language:** "screens physically viable alternative routes and
characterises each by infrastructure constraint and existing service load."
Never "recommends a reroute".

### A3 · Building and laying new railway lines
**Status: supported as scenario analysis only — which is exactly what the old
doc already decided, and the guardrail should stand.**

Supported: candidate links generated from real data rather than imagination
(the 607 service pairs with an endpoint missing from the graph, the 40
junctions whose name match was rejected on a spatial conflict, plus
low-redundancy regions surfaced by Module 3); structural impact scoring of
each candidate; a terrain-aware cost proxy via sinuosity (`D6`) instead of
naive great-circle distance.

Old doc conflict (partial): §12 Module 4 states in capitals that this is
*scenario analysis, NOT an automated system that tells Indian Railways where
to build*, and forbids claiming engineering, economic, land, demand or policy
feasibility without those datasets. §13 adds that link prediction must never
be described as predicting where IR should build.

That guardrail is correct and protective — a reviewer or a railway officer
will test it immediately. The useful move is not to weaken it but to be
precise about what *is* being computed: the structural consequence of a
hypothetical link, scored and ranked, with feasibility explicitly out of
scope.

**Safe claim language:** "evaluates and ranks the structural consequence of
hypothetical new links." Never "identifies where new lines should be built."

### A4 · What-if scenario feature with multi-aspect impact
**Status: the strongest product opportunity of the four, and the most
defensible, because it is descriptive by construction — it reports deltas, it
does not recommend.** Spec in §3 below.

---

## 3. The what-if feature — a concrete multi-aspect impact spec

"Multiple aspects" needs to mean specific computable columns, or it becomes a
dashboard of whatever was easy. Nine aspects worth reporting, and an honest
mark on each:

| # | Aspect | Metrics | On v1.0 today? |
|---|---|---|---|
| 1 | **Topology** | Δ components, Δ giant-component share, Δ independent cycles, Δ bridges, Δ articulation points | **yes** |
| 2 | **Distance / accessibility** | Δ mean shortest path, Δ circuity, Δ reachable route-km per station within a threshold | **yes** |
| 3 | **Criticality redistribution** | Δ betweenness, top-k overlap before/after, which stations gain and lose criticality | **yes** |
| 4 | **Resilience** | Δ robustness *R* under random, degree-targeted and **geographic** (`D10`) removal | **yes** |
| 5 | **Service exposure** | Δ `service_load` on affected edges; how many trains a removal strands | **yes** |
| 6 | **Regional / equity decomposition** | every row above, decomposed per zone | **yes**, after the 5-variant `railway_zone` typo cleanup |
| 7 | **Cost proxy** | route-km added; sinuosity-adjusted terrain cost (`D6`) | **yes** |
| 8 | **Journey time** | Δ travel time | **no** — needs `W2` observed run-times; the declared speed is out by ~2× (`F-036`) |
| 9 | **Budget allocation** | optimal vs. naive spend prioritisation under a constraint | **no** — needs `D11` implemented |

**Seven of nine ship on the graph as it stands.** The two that do not are
exactly the two that need v2 work already on the roadmap, which is a clean
story rather than an awkward gap.

Three design rules that fall out of the quality work and belong *in the
feature*, not only in a document:

1. **Every scenario result must carry its defect exposure.** If a scenario's
   affected paths route through `suspect_long_edge` edges, the output says so
   and how much — `F-041` showed those edges carry real route km but may be
   missing intermediate stations, so a path result through them is
   structurally less reliable while its length is fine.
2. **Scenario output must state which view it used.** The attributed-core
   filters inflate fragility ~2.5× (`GRAPH_HANDOFF_V2.md` §4.5). A resilience
   delta computed on the wrong view is not a smaller result, it is a wrong
   one.
3. **Direction-blind results must be labelled direction-blind** (`D-033`).

---

## 4. The one word to change

The team's framing says these insights give "better **operational**
functionality for the Indian Railways." *Operational* is precisely the word
§14 of the scoping doc warns against — it is the register of congestion,
capacity, headway and delay, which is the time side and is not what this
graph holds.

The accurate register is **structural and strategic planning support**:

> The graph supports infrastructure-layer planning questions — where the
> network is structurally vulnerable, where connectivity is missing, and what
> changes structurally if the physical network changes — and deliberately
> does not address scheduling, capacity or delay, which require operational
> data the project does not hold.

That sentence concedes nothing real and removes the single most likely line of
attack in a review or a stakeholder presentation. It is also *why* the
positioning in §1 is strong: being the only infrastructure-side work is only
a contribution if the boundary is stated with confidence rather than blurred.

---

## 5. Net position

| Application | Supported on v1.0 | Claim must be |
|---|---|---|
| A1 infrastructure connectivity insight | **fully** | diagnostic, not prescriptive |
| A2 festival special-train rerouting | **narrowed** to alternative-path screening | a screen, not a reroute |
| A3 new-line planning | **as scenario analysis** | structural consequence, not feasibility |
| A4 what-if, multi-aspect | **7 of 9 aspects** | deltas reported, not recommendations |

Recorded as `D-034` in `docs/DECISIONS.md`.
