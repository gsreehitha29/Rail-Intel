# Scope, objectives and deliverables — LOCKED

Date: 2026-10-15 · Supersedes every earlier scope statement in this repository
Status: this is the definition of done. Changes to it are decisions, recorded in `DECISIONS.md`.

The scope was ambiguous for months because it was being written forward from intentions.
Everything below is written backward from evidence that now exists.

---

## 1. The objective, in one sentence

> Build a validated, reproducible, station-level **physical** graph of the Indian railway
> network, and establish **which network conclusions about it are robust to how it was
> built** — then use the robust ones to answer a real operational question: which
> corridors have no alternative route.

Three parts, each with its evidence already in hand:

| | Claim | Evidence | Status |
|---|---|---|---|
| **C1** | the artifact — a 9,095-node geolocated, attributed, provenance-carrying physical graph with a derived service layer | `graph_v1_4/`, nine gates, 30 regression tests, manifest | **done** |
| **C2** | the method — GIS → corridor → chain → **junction-stitched**, with the timetable held back as validation | giant component 59.4% → 99.6%; `OVERRIDES.csv`, 179 evidence-carrying decisions | **done** |
| **C3** | the evaluation — which conclusions survive the construction choices | E-711 (12 cells), D-055 (nesting), E-710 (theory check) | **done** |

C3 is the scientific core, and it is the part no prior Indian-railway study could attempt:
each had one source, so it could only check itself. Ours has two independent kinds of
source and the timetable was never used in construction.

---

## 2. What is in scope

**The dataset.** 9,095 stations and junctions, 9,759 physical track sections, 74,849.7
route km, 18 components with 99.59% in the giant one. A service layer of 16,703 directed
station pairs with observed running times and trains per day. Frozen as v1.4.

**The build.** One command, deterministic, gated. `make repairs` derives decisions from
evidence; `make v14` applies them, gates and freezes. Nine gates must pass or the build
fails. `make test` holds 30 tests against reviewed golden values.

**The analysis.** Only the metric class certified stable by D-055: connectivity,
reachability, route distance, cut points, bridges, corridor load. Delivered as E-709
(severance criticality), E-710 (degree distribution), E-711 (conclusion robustness).

**The documentation.** `FITNESS.md` (what it supports and never will), `SCHEMA.md`
(generated per-column reference), `DATASHEET.md` (Gebru et al.), `docs/STABILITY.md` (the
contract), plus 57 ADRs and an experiment registry where every claim resolves to an ID.

---

## 3. What is out of scope, and why

Named, with the reason, so none of these reads as an oversight.

| Excluded | Why | Could it ever be done? |
|---|---|---|
| **Open redistribution of the dataset** | the base GIS source is an Esri India Living Atlas export whose terms forbid offline export (D-057) | yes — rebuild from the OSM extracts already held. Weeks of work; roadmap item R1 |
| **Node-level criticality ranking** ("the 10 most critical stations") | 228 absent stations and 82 duplicate node pairs understate exactly the junctions a ranking is about; betweenness moved 15 of its top 50 under one round of repair | only with a station register that does not exist in any held source |
| **Absolute path kilometres** | 25.3% of route km is a straight-line floor | partially, by adjudicating the 823 deferred length disagreements |
| **Capacity, congestion, delay as a mechanism** | no capacity, no signalling, no turn restrictions, undirected | no — out of scope for a space-of-stations representation |
| **Freight** | the 2024 dataset is passenger-only | only with a freight source |
| **Real-time or predictive operation** | no live feed, and the delay data is one month of 2024 | not in this project |
| **Reproducing Sen (2003) and Bhatia (2015) from our data** | needs a service-space projection and a multi-layer build; deliberately deferred, not forgotten | yes, as a follow-on paper |
| **Two-rater validation audit** | needs a second rater, who does not exist on this team | report single-rater agreement with the limitation stated |

---

## 4. The product built on the dataset

The fitness classification narrows this to one coherent product rather than a menu,
because the product can only promise what the stable class supports:

> **A corridor-level vulnerability and contingency tool for the Indian rail network:**
> which corridors have no alternative route, what each one isolates, how much daily
> traffic depends on it, and what a named blockage would cut off.

**Why this one.** It is the only product idea where every input metric is in the robust
class, it answers a question Indian Railways demonstrably faces — section blockages are
routine, not exceptional — and it already has two retrodictive validations: the Siliguri
corridor recovered from geometry alone, and the July 2025 Lumding–Badarpur landslide's
blast radius predicted correctly before the event was looked up.

**What it will say, and how strongly** — straight from E-711, because overclaiming here
is the main risk:

| Output | Strength |
|---|---|
| the corridors with no alternative route, each with what it isolates | **robust** — invariant across all 12 construction cells |
| a named section's blast radius (stations, states, services) | **robust** — the Lumding figure does not move by one station across 12 cells |
| the corridor count | **conditional** — 283 at a 1 km threshold, 258–306 across 0.5–2 km; always quoted with the threshold |
| the share of the network with no alternative | **directional only** — roughly an eighth; never a point estimate |
| trains per day dependent on a corridor | **lower bound** — passenger only, suburban under-recorded |

---

## 5. Deliverables, with acceptance criteria

| # | Deliverable | Accepted when | Status |
|---|---|---|---|
| **D1** | Frozen dataset release v1.4 | nine gates pass; 30 tests pass; manifest hashes match; `FITNESS`, `SCHEMA`, `DATASHEET`, `STABILITY` all present and current | ✅ **done 2026-10-15** |
| **D2** | Reproducible build | `make v14` rebuilds byte-identically in one environment; cross-machine differences limited to parquet and declared in the manifest | ✅ done |
| **D3** | Severance criticality analysis | corridors ranked, with external validation against at least one real disruption | ✅ done (E-709) |
| **D4** | Theory validation | the degree claim is a fit test with a reported p-value, not a caption | ✅ done (E-710) |
| **D5** | Conclusion robustness | every headline conclusion carries a robust / conditional / withdrawn verdict | ✅ done (E-711) |
| **D6** | Documentation set | a reader who was not in the room can load the data, know what it supports, and rebuild it | ✅ done |
| **D7** | The pitch | every claim on every slide resolves to an experiment ID | **next** |
| **D8** | The product (phase 4) | corridor vulnerability tool over the v1.4 release, using only robust-class metrics, with the strength of each output shown on screen | **specified, not built** |

### Roadmap, explicitly not in this scope

| | Item | Cost | Unlocks |
|---|---|---|---|
| **R1** | rebuild the topology from the OSM extracts in `external_data/` | weeks | an openly licensable dataset (C1 deposit, DOI) |
| **R2** | adjudicate the 823 deferred length disagreements | days | absolute kilometres |
| **R3** | merge the 82 duplicate node pairs against a real station register | blocked on the register | node-level ranking |
| **R4** | service-space projection and multi-layer build | weeks | Sen/Bhatia reproduction, a second paper |

---

## 6. The one-line honest summary

A physical graph of Indian Railways that is 11× larger than any published predecessor,
validated against sources never used to build it, frozen and test-guarded, with an
explicit account of which of its own conclusions can be trusted — and one real finding
produced from it that an outside event confirmed.

What it is not: an open dataset (yet), a capacity model, or a station ranking.
