# Validation Report — Data Quality & Graph Feasibility

> ## ✅ CLOSED — all seven gaps resolved, retained for provenance
>
> **Status as of 2026-09-30: no gap in this report is still open.** Each was
> closed by the pipeline under `02_graph_inputs/pipeline/`, and the resulting
> dataset ships in `02_graph_inputs/graph_dataset/`. The resolution table is
> in the addendum at the end of this document.
>
> This report is kept because it is the evidence that the preprocessing layer
> was independently checked rather than assumed — not because anything in it
> still needs action. **Read the addendum before acting on anything above it.**
>
> Two headline claims in the original body are now known to be wrong, and are
> corrected in the addendum:
> * The "**corridor geometry is usable for only ~15% of corridors**" finding
>   measured endpoint degree globally across all 118k segments, which is the
>   wrong question. Measured inside each corridor's own geometry — which is
>   what ordering stations along it actually requires — **95% reconstruct as a
>   clean end-to-end path** and 2,278 of 2,279 yield a usable spine.
> * The "no single authoritative corridor count" problem is settled:
>   **2,279** canonical corridors, one rule, one script.


**Prepared by:** Claude Cowork technical validation pass
**Date:** 2026-09-29
**Scope:** Independent re-verification of every "processed" / "initial graph" artifact currently in the repository, plus a feasibility check on the core Month-2 task (station-level graph construction), by reading and re-executing the actual notebook logic — not by trusting the prose in README.md / docs/GRAPH_HANDOFF.md / docs/DATA_DICTIONARY.md at face value.

**Bottom line:** The three "clean" tabular datasets (`cleaned_stations.csv`, `cleaned_trains.csv`, `cleaned_schedules.csv`) are genuinely solid — every documented QA number reproduced exactly, zero referential-integrity failures. The junction-level graph artifacts (`rail_edges_initial.csv`, `junction_nodes_initial.csv`, `railway_components_initial.csv`) are internally self-consistent (edges ↔ nodes ↔ components all reproduce exactly from each other), but they were built from **unstripped raw junction-name strings**, so ~2% of nodes/edges are whitespace/newline duplicates of each other — a bug the notebooks already diagnose but never fix in the saved files. Most importantly: **the geometry needed to order stations along a corridor — the actual Month-2 deliverable — is usable for only ~15% of corridors**; the other ~85% are topologically messy MultiLineStrings with more than 2 loose ends, which naive line-projection will not handle. Full detail below.

---

## 1. Reconciling the conflicting EDA counts

Three different documents/notebooks report three different counts for "how many corridors/edges exist," because two notebooks independently re-implemented the same aggregation step without sharing code, and neither one strips whitespace from junction names before grouping:

| Source | Valid segment rows | Distinct corridors/edges reported |
|---|---|---|
| Blueprint doc (project brief) | 118,442 | 2,305 |
| `01_Final_Data_Preprocessing_and_Validation.ipynb` cell 161 (re-verified, exact match) | 118,442 | **2,305** (confirmed — includes 5 self-loops, 192 with attribute conflicts) |
| `docs/DATA_DICTIONARY.md` / `rail_edges_initial.csv` (from `Railway_networks_EDA.ipynb`) | "116,218 filtered" (unverified — does not match either notebook's actual valid-row count) | **2,257** |
| My independent re-derivation from `Railway_Network_.csv` with `.strip()` applied | 118,442 | 2,290 directed / 2,282 undirected |

**Finding:** The blueprint's 118,442 and the 01_Final notebook's 2,305 agree exactly and are traceable to executed code. The DATA_DICTIONARY's "116,218" does not match anything I can reproduce from the raw file with any filter I tried — it looks like stale/incorrect documentation, not a different valid pipeline run. The 2,257 in `rail_edges_initial.csv` differs from 2,305 for a diagnosable reason (see §2). **There is currently no single authoritative corridor count** — three code paths, three answers, off by 1–2%.

## 2. Whitespace/newline contamination in the shipped junction graph

`rail_edges_initial.csv` and `junction_nodes_initial.csv` were built (in `Railway_networks_EDA.ipynb`, cell 139) by grouping on the **raw, unstripped** `fromjunction`/`tojunction` strings. A `normalize_junction_name()` function is defined afterward (cell 143) purely to *flag* duplicates — it is never used to actually merge them before the files are saved (cell 145).

Verified effect, by rebuilding the graph with normalization applied:

| Metric | Shipped (uncleaned) | After merging whitespace/newline duplicates |
|---|---|---|
| Nodes | 2,024 | 1,987 |
| Edges | 2,257 (2,249 after de-duplication) | 2,226 |
| Connected components | 113 | **100** |
| Largest component | 1,758 nodes | 1,761 nodes |
| Self-loops | 5 | 5 (unaffected — these are genuine, not whitespace artifacts) |

This confirms `docs/GRAPH_HANDOFF.md` §12.2's qualitative claim that the 36 normalization groups (I independently found the same number, 36 groups / 73 raw rows) are real duplicates — but **corrects its quantitative claim**. The doc says merging them will "seamlessly reconnect dozens of disjoint components into the main network graph." Actually measured: components drop by only 13 (113→100), and the main component grows by only 3 nodes. The other ~23 collision groups are already in the same component as their duplicate (they're just spurious low-degree twins, not bridges to isolated pieces). **Do not assume this merge meaningfully improves connectivity — it mostly just removes noise.**

Independent cross-check performed: I rebuilt the full graph from the shipped `rail_edges_initial.csv` and recomputed connected components with NetworkX from scratch. Result: 113 components, largest = 1,758 nodes, and the **full component-size distribution matches `railway_components_initial.csv` exactly, element for element**. So whatever bug exists is upstream in the raw grouping — the node/edge/component files are perfectly consistent *with each other*, they're just consistent-but-uncleaned.

## 3. `01_data_engineering/processed_data/*` — clean, verified, no issues found

Every check below reproduced the documented figures exactly:

- **cleaned_stations.csv** (8,990 rows): 0 duplicate `station_code`, 8,697/8,990 with coordinates, all coordinates inside a plausible India bounding box, `data_quality_status` counts match docs exactly (complete 4,270 / missing_metadata 4,427 / missing_geometry 188 / missing_geometry_and_metadata 105). One minor unflagged issue: 11 stations share exact identical lat/lon with another station (docs mention this as "4 groups," consistent).
- **cleaned_trains.csv** (5,208 rows): 0 duplicate `train_number`, **0** `from_station_code`/`to_station_code` values missing from the station master (full referential integrity).
- **cleaned_schedules.csv** (416,970 rows): 0 duplicate `(train_number, station_code, stop_sequence)` keys, 0 station codes missing from the station master, 0 train numbers missing from `cleaned_trains.csv`, and **0 trains have a gap or non-1-start in their `stop_sequence`** (I independently re-verified every one of 5,208 trains).

**This layer is solid and ready to use as-is.** It is the strongest part of the pipeline.

## 4. The haversine spatial validation: documentation is stale, but the actual result is good news

`docs/GRAPH_HANDOFF.md` §1 and §7, and `README.md`, both say the haversine coordinate-distance validation "was not executed" and point to notebook cell 210. **This is now false.** I inspected the notebook's stored cell outputs directly: cells 211–218 have `execution_count` values and saved outputs. The validation *was* run, and its results are saved in the notebook file right now:

- 270 corridors evaluated (both endpoints name-matched to the station master)
- Best-of-two-orientations total gap: min 0.025 km, median 0.850 km, mean 6.6 km, max 1,068.8 km
- ≤0.1 km: 31/270 · ≤0.5 km: 92/270 · ≤1 km: 148/270 · ≤2 km: 201/270 · (per-endpoint, not combined — see note below)

These numbers **do not exactly match** the "combined both-endpoints" figures quoted in `docs/GRAPH_HANDOFF.md` §12.1 (31/114/172/219/249 for ≤0.1/0.5/1/2/5 km). I traced this: §12.1's numbers come from cell 218, which sums `from_best_distance_km` and `to_best_distance_km` **separately per endpoint, both must pass** — I reproduced cell 218's output exactly (31, 114, 172, 219, 249). The cell 211 numbers I quoted above (`best_total_km`) are the **sum of both endpoints' gap combined**, a different (looser) metric. Both are legitimately in the notebook; the two docs referencing this work should cite the same metric consistently. **Net finding: the validation is real, reproducible, and both metrics agree with each other once you know which one you're looking at — the only actual bug is that README.md and GRAPH_HANDOFF §1/§7 haven't been updated to remove the "not executed" claim.**

One outlier worth flagging by name: **Manabar ↔ "Maligura\n"** — the tojunction string literally contains an embedded newline in the raw source, and it is also one of the 36 whitespace-duplicate junctions from §2. It appears in the "good" match list (0.048 km) purely by luck of which variant matched.

## 5. Junction ↔ station-master name matching: the 727 vs 747 discrepancy is resolved

`docs/GRAPH_HANDOFF.md` §4 says 727 of 2,066 junctions matched; §12.3 (added later) says 747 of 2,024 matched. I traced both numbers directly from notebook cell outputs:

- Cell 188/196: **"Known junctions: 727"**, out of junction names derived from `network_lines` (2,066 distinct names, matches §4)
- No cell anywhere produces "747" — I could not find a code path that yields that number.

**Conclusion: 727 is correct and reproducible; 747 in §12.3 is a documentation typo** (most likely a transposition of 727). Treat 747 as wrong wherever it appears.

Separately, there is an **earlier, different matching pass** (cell 162, matching against `station_name` text directly rather than junction geometry) that gets 716/2,026 matched, rising to 719/2,026 after basic punctuation normalization. This is a *third* matching number, from a different method, on a slightly different universe of endpoint names (2,026 vs. 2,066). **Three different "how many junctions matched" numbers exist in the notebook from three different attempts, and only one (727) made it into the docs.** Worth deciding which method the team actually wants to standardize on before building the real pipeline.

## 6. An already-built but undocumented fallback: nearest-neighbour matching for the 1,339 unmatched junctions

Cells 194–198 of `01_Final_Data_Preprocessing_and_Validation.ipynb` already attempt to resolve the 1,339 name-unmatched junctions by pure spatial nearest-neighbour (`geopandas.sjoin_nearest`) against all 8,697 coordinate-bearing stations, with **no name constraint and no distance threshold**. This work exists, is executed, and is **not mentioned in README.md, DATA_DICTIONARY.md, or GRAPH_HANDOFF.md at all**. Its results, verified:

- 1,339 candidate matches produced (100% coverage, by construction)
- Distance to nearest station: mean 6.14 km, median 2.30 km, max 78.7 km
- Only 26/1,339 (1.9%) within 100 m; only 321/1,339 (24%) within 1 km; 758/1,339 (57%) are **more than 2 km** from their nearest station

**This confirms the blueprint's own warning almost exactly** ("a nearest station... should not automatically become an edge without evidence and validation" — §4 of the blueprint doc). This candidate table is a reasonable *starting point* for manual/threshold-based resolution of the 1,339 gap, but as-is it would silently introduce hundreds of wrong station assignments if merged in without a confidence cutoff. It is currently sitting only in notebook cell output — it was never exported to a CSV, so it isn't reusable without re-running the notebook.

## 7. Graph feasibility: is the corridor geometry actually usable for station-ordering? — **this is the main risk**

The blueprint's required Month-2 step is: *"project candidate station points onto the corridor geometry and order them along the physical line."* This assumes each corridor's geometry is (or can be reduced to) a single continuous line you can walk from one end to the other. I checked this directly using the notebook's own already-executed topology analysis (cells 176–183), which the docs do **not** surface:

| Corridor geometry shape | Count | % of 2,305 |
|---|---|---|
| Already a single clean `LineString` (2 endpoints, no branching) | 289 | 12.5% |
| `MultiLineString` with exactly 2 true topological loose ends (walkable after reassembly) | 37 | 1.6% |
| `MultiLineString` with exactly 1 loose end | 312 | 13.5% |
| `MultiLineString` with **0 or >2 loose ends** — i.e. not a simple path; contains branches, spurs, or disconnected fragments | **1,951 + 5 = 1,956** | **~85%** |

In other words: **only about 15% of corridors have geometry that a simple "sort points along the line" algorithm can handle.** The remaining 85% are topologically ambiguous — either they have no clear start/end (0 boundary points, usually meaning the corridor geometry forms one or more closed-ish loops or is one continuous mesh with the neighboring corridor) or more than 2 (meaning the corridor's segments branch, e.g. at a junction internal to the corridor, or contain siding/yard spurs).

Separately, a **looser** definition of "clean corridor" was used later in the same notebook (cells 199–208, based on *locally* unique segment endpoints rather than global topological boundary count) and produced 2,210/2,305 "clean" corridors (96%) — this is the number `docs/GRAPH_HANDOFF.md` §7 quotes. **These two "clean corridor" numbers (349 vs. 2,210) come from genuinely different definitions of "clean" and give a very different picture of feasibility.** The stricter topological check (§7 here) is the one that actually matters for "can I order stations along this line," and it says the problem is much harder than the 2,210 figure suggests. This inconsistency should be resolved before committing to a station-ordering algorithm design.

## 8. Everything not yet checked / out of scope of this pass

- I did not attempt to actually build a station-level graph (that's the next phase, not a validation task).
- I did not validate `01_data_engineering/railways-master/schedules.json` → `cleaned_schedules.csv` transformation logic line-by-line (only the output's integrity), nor `cleaned_trains.csv`'s geometry-quality fields.
- Reference-only files (`archive (5)/list_of_stations.json`, `Indian_Railway_Stations_JSON-master/...`, historical CSVs) were not touched — docs already correctly mark them as unused.
- I did not re-verify the blueprint's "203 corridors with conflicting attributes" figure against the notebook's own "192" (cell 161) — both exist, neither matches, low priority to resolve but noted.

---

## Summary gap list (actionable)

1. **No single authoritative corridor/edge count** — 2,305 vs 2,290/2,282 vs 2,257 vs "116,218 filtered" all currently coexist. Pick one pipeline, one script, and freeze it.
2. **Whitespace/newline duplicates are diagnosed but not fixed** in the shipped `rail_edges_initial.csv`/`junction_nodes_initial.csv` — 36 groups, 73 raw name-variants, real but modest effect (113→100 components).
3. **Corridor geometry is only cleanly "walkable" for ~15% of corridors**, not 96% as the "2,210 clean corridors" figure in GRAPH_HANDOFF implies — the two "clean" definitions disagree by a wide margin and this is the single biggest risk to the Month-2 station-ordering task.
4. **README.md / GRAPH_HANDOFF.md §1 and §7 are stale**: they say the haversine validation "was not executed"; it was, and results are saved in the notebook (just never exported to a file or copied into the docs consistently — two different metrics from cells 211 vs 218 are both floating around).
5. **727 is the correct junction-match count; 747 in GRAPH_HANDOFF §12.3 is a typo.** A third, different matching method (text-based, cell 162) gives 716–719 on a slightly different universe — three matching methods exist, none chosen as canonical.
6. **The nearest-neighbour fallback for the 1,339 unmatched junctions already exists (cells 194–198) but is undocumented and unexported**, and its quality is poor unmatched (only ~24% within 1 km) — needs a confidence threshold before use, per the blueprint's own validation principles.
7. **None of the exploratory matching/validation tables (clean corridor endpoints, 727-match table, 1,339-candidate table, haversine results) are exported as CSVs.** They only exist as notebook cell output. This violates the blueprint's own reproducibility requirement (§12: "deterministic and rerunnable from versioned input tables") — if the notebook kernel is lost or cells are re-run out of order, this work has to be redone from scratch.


---

# Addendum — Gap Resolution (same day)

All seven gaps above were closed by building `02_graph_inputs/pipeline/` and the `02_graph_inputs/graph_inputs/`
package. Status of each:

| # | Gap | Resolution |
|---|---|---|
| 1 | No authoritative corridor count | One rule, one script (`s02_corridors.py`), one number: **2,279** canonical unordered corridors. The 2,305 / 2,290 / 2,257 variants were all artefacts of inconsistent whitespace handling and direction treatment across two notebooks. |
| 2 | Whitespace duplicates diagnosed but not fixed | `s01_canonical_junctions.py` merges them (36 groups, 57 raw strings repaired, 8 with embedded newlines) and emits a full raw→canonical crosswalk. 2,066 raw strings → 2,029 canonical junctions. |
| 3 | Corridor geometry thought usable for only ~15% | **Resolved — the original measurement asked the wrong question.** Measuring endpoint degree *within* each corridor rather than globally, and snapping endpoints at 10 m, gives **2,166 / 2,279 (95%) clean end-to-end paths** and a usable ordered spine for 2,278 / 2,279. Total spine 70,958 km vs 801 km of spurs. |
| 4 | Stale docs ("haversine not executed", two conflicting metrics) | `README.md` corrected; `docs/GRAPH_HANDOFF.md` carries a superseded banner naming both errors; `docs/GRAPH_HANDOFF_V2.md` replaces it. |
| 5 | 727 vs 747 matching discrepancy, three competing methods | 727 confirmed correct, 747 confirmed a typo. Replaced by one spatially-constrained tiered matcher (`s06`): **1,555 high/medium-confidence matches**, every one carrying method, name score, spatial gap and confidence. |
| 6 | 1,339 junctions with no coordinates; nearest-neighbour fallback poor (24% within 1 km) | Replaced with coordinates derived from corridor-spine endpoint consensus (`s05`): **2,028 / 2,029 junctions (100%) now have coordinates**, median consensus spread 154 m, no dependence on the station master. This also solves coordinates for the ~337 operational nodes (cabins, yards, block huts) that can never appear in a passenger station master. |
| 7 | Intermediate tables trapped in notebook cell output | Twelve CSVs exported to `02_graph_inputs/graph_inputs/`, all regenerable by `python 02_graph_inputs/pipeline/run_all.py` in ~30 s with no kernel state. |

## Additional findings made while closing the gaps

**The source length field is inflated by ~9%.** `st_lengthshape` summed over all
segments gives 78,126 km; the true geodesic length of the same geometry is
71,759 km (median ratio 1.0902). The inflation is consistent with a length
computed in a projected CRS at Indian latitudes. The Year Book 2024–25 reports
69,439 route km, which the geodesic figure is far closer to. **Any edge weight
taken from `st_lengthshape` — including `geometry_length_km` in the old
`rail_edges_initial.csv` — is systematically ~9% too long.**

**Zeros were being absorbed into modal attribute values.** Treating `0` in
speed / tracklength / noofstations / nooflanes as UNKNOWN rather than as a real
value (blueprint §12: "unknown attributes should remain unknown") raises missing
`speed` from 815 corridors to 1,144. The higher number is the honest one.

**An unconstrained fuzzy matcher is actively dangerous here.** A first pass with
rapidfuzz over all 8,697 stations produced matches such as "Thiruvananthapuram
Central" → "PURA HALT" 2,017 km away, and 287 spatial conflicts. Constraining
candidates to a 15 km radius around the junction's geometry coordinate first
reduced conflicts to 40 while *increasing* usable matches.

**Station placement independently corroborates the geometry.** The GIS
`noofstations` attribute had never been used for anything. Comparing it against
the stations this pipeline places on each corridor gives r = 0.49, with 65% of
corridors agreeing within ±3. Moderate corroboration from two sources that
share no lineage — and the median perpendicular offset of a placed station from
its corridor line is **41 m**, which is strong evidence the station coordinates
and the rail geometry describe the same physical network.
