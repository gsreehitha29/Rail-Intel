# E-711 — do E-709's conclusions survive the choices that produced them?

Claim C3, applied to the conclusions actually going into the pitch rather than to the
v1.2-era conclusions `E-200` and `E-401` tested.

**Status: run. Four conclusions robust, one conditional, two must be withdrawn as stated.**

## The design

Twelve cells, every combination of three choices:

| choice | values | what it tests |
|---|---|---|
| `release` | v1_3, v1_4 | whether the five repair modules made the conclusions |
| `contracted` | the 82 known duplicate pairs merged, or as shipped | whether duplicate nodes made them |
| `artifact_km` | 0.5, 1.0, 2.0 | whether the intra-station classification threshold made them |

Severance is purely topological, so no cell varies edge length — length choices cannot
move these conclusions by construction, which is worth stating rather than testing.

## Verdicts

| conclusion | verdict | evidence |
|---|---|---|
| the Lumding corridor isolates 84 stations | **ROBUST** | **identical — 84 — in all 12 cells** |
| the worst bridge isolates the whole Northeast | **ROBUST** | 326–327 NE-state stations |
| the worst corridor isolates >450 stations | **ROBUST** | 455–459 |
| junction cut points (degree ≥ 3) | **ROBUST** | 372–385, within 10% |
| number of severance corridors | **CONDITIONAL** | 258–306; 283 only at `artifact_km` = 1.0 |
| share of sections with no alternative route | **WITHDRAW as a point figure** | 11.4%–14.9% across cells, 26.5% of the median |
| "82 intra-station artifacts" | **WITHDRAW as a finding** | 33–126 by threshold; it is a parameter output, not a measurement |

## What this changes in the pitch

**Say this.** The Siliguri corridor isolates the whole Northeast; the Lumding–Badarpur
corridor isolates 84 stations and the July 2025 landslide confirmed it. Both are
invariant to every construction choice tested — the Lumding figure does not move by a
single station across twelve different ways of building and classifying the graph. That
is a far stronger statement than the number alone.

**Say this with its condition.** "283 severance corridors" becomes *"283 corridors at a
1 km intra-station threshold; 258–306 across 0.5–2 km."* The corridor concept is sound;
its count is a function of where you draw the duplicate line.

**Stop saying this.** "11.9% of sections have no alternative route" is not a defensible
point estimate — it ranges 11.4% to 14.9%, driven mostly by the repairs (v1.3 14.4% →
v1.4 11.9%). The honest form is directional: *roughly an eighth of sections have no
alternative route, and repairing the graph reduced the estimate from 14.4% to 11.9%,*
which is itself evidence the repairs removed false fragility rather than adding it.

**And this.** The count of intra-station artifacts is set by the threshold, so it is not
a finding. What *is* robust is that the class exists and contains the four high-traffic
station renames — Allahabad Jn / Prayagraj Junction, Vishakapatnam / Waltair, Cheoki /
Prayagraj Chheoki, Daraganj / Prayagraj Sangam. All four are under 0.5 km and sever
exactly one station, so all four are caught at every threshold tested. The *mechanism* is
robust; the *count* is a dial.

## Repair sensitivity, holding the rest fixed

| | v1.3 | v1.4 |
|---|---|---|
| share with no alternative route | 0.1439 | 0.1191 |
| severance corridors | 282 | 283 |
| worst corridor severs | 455 | 455 |
| NE stations severed by the worst bridge | 326 | 326 |
| junction cut points | 384 | 372 |

The headline domain findings are **identical before and after five modules of repair**.
What the repairs changed is the *level* of fragility, downward — consistent with D-055's
nesting result, where repairs only ever removed false cut points.

Note on definitions: `junction_cut_points` here counts cut points of degree ≥ 3 (372),
where E-709 reports the stricter set that also severs more than one station (200). The
numbers are not in conflict.

## Files

- `sweep.py` — `python sweep.py <root> out` (~47 s for all twelve cells)
- `out/sweep_cells.csv` — every cell's full result
- `out/E-711_sweep.json` — the verdicts and the v1.3/v1.4 comparison
