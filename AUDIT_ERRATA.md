# Phase 2 audit — errata and reproduction record

Applies to `audit_phase2a` … `audit_phase2d1` (merged in PR #1, `930553e`).
Written 3 Nov 2026 as Step 0 (E-721) of the v2.1 remediation plan.
The audit reports themselves are left unedited; this file records what changed around them and what in them should be read differently.

## 1. Reproduction status

All 40 scripts run from a clean checkout once LFS files are pulled:

```bash
git lfs pull                  # work/*.parquet, work/*.csv and all results/*.json are LFS
python audit_phase2a/scripts/audit_part_a_structural.py    # any script, from the repo root
```

Environment used for the check: Python 3.10.12, pandas 2.3.3, numpy 2.2.6, pyarrow 25.0.1, networkx 3.4.2. The audit was written against networkx 3.6.1, which needs Python 3.11 or newer; bridges and cut points match under both versions.

| Headline number | Report | Reproduced |
|---|---|---|
| Physical graph bridges / cut points / cycles | 1,849 / 1,805 / 1,267 (2A) | same |
| Places graph bridges / cut points / cycles | 1,799 / 1,747 / 498 (2A) | same |
| CSMT–MSD shortest path | 14.2121 km over 8 sections (2B) | same |
| Prune of `n128794` in round 1, dropping `n128794`–`MSD` (1.4163 km, chain 4365) | 2B.1, 2B.2 | same |
| `n128794` to `n289147` path in Stage C1 | 28.4372 km, 29 hops (2B.2) | same |
| Bridges after CSMT / +HWH / +MAS scenarios | 1,847 / 1,846 / 1,845 (2D) | same |
| `BCT` absent from crosswalk; 47 `BCT` rows in the 2017 timetable; `MMCT` 0 trains | 2D, 2D.1 | same |

## 2. Script changes made for reproduction

- 13 scripts had `c:/Users/Sreehitha/OneDrive/Desktop/Major Project/Rail-Intel` hardcoded. They now use `pathlib.Path(__file__).resolve().parents[2]`.
- `audit_phase2d/scripts/investigate_bct.py` read the timetable from `external_data/` instead of `external_data/timetable_2017_datagovin/`. It had never produced its output; `audit_phase2d/results/task_e_bct_investigation.json` now exists for the first time.
- `audit_phase2b1/scripts/analyze_corridor_gap.py` crashed on numpy integers when writing JSON, which is why `corridor_gap_analysis.json` was truncated at 136 bytes. It now completes.
- No logic was changed. Committed result files were restored after the reruns, apart from the two outputs above.

## 3. Errata — how to read the reports

**E1. Pruned lengths in 2C are overstated.** The 2C table lists the full chain lengths (10.26 km at CSMT, 38.86 km at HWH) as "max pruned track". 2D and 2D.1 §4 measured the actual deletions: 0.08 to 5.24 km, mostly the final link into the terminus. Use the 2D.1 table.

**E2. "Vertices pruned within 500 m" (2C) is not track lost.** For example, "21 of 23 at CSMT" counts every Stage C1 vertex in a 500 m circle, including yard points. It is not a measure of damage.

**E3. Only one independent source was actually held.** 2D §2.1 and 2D.1 §5 cite divisional signalling plans, interlocking plans, SER operating manuals, Survey of India maps and suburban working timetables. None of these are in the repository, and no extract or citation is given, so treat those columns as unverified. The evidence that is held is the 2017 data.gov.in timetable. It does support the three "GO" cases, counted as consecutive-stop rows in `Train_details_22122017.csv`:
- CSMT–MSD: 344 rows (172 trains each way);
- MMCC (Moore Market)–BBQ: 265 rows;
- HWH–TPKR: 96 rows.

**E4. The scenario edges are shortcuts, not restored track.** `restored:CSMT-MSD`, `restored:HWH-TPKR` and `restored:MAS-BBQ` join the released station nodes directly. 2B.2 §4 already says this; 2D and 2D.1 repeat the numbers without that caveat in their tables. Read the bridge, cut-point and distance deltas as illustrations of scale, not as the result of a fix.

**E5. The crosswalk has 52 rows, not 53** (2D.1 §6). `BCT` is absent either way.

**E6. The BCT/MMCT defect is one case of a wider gap.** 87 timetable codes resolve to no graph node, dropping 2,149 stop rows. Several are renamed major stations: MGS→DDU, ALD→PRYJ, HBJ→RKMP, MUV→BSBS, BIH→SHRN, ACOI→PCOI. Those stations show `scheduled_2017 = False`. This goes to Step 1 / Step 3 of the plan.

**E7. Dead link.** 2D §4 links `v14.py` through `file:///c:/Users/Sreehitha/OneDrive/...`. The repository path is `03_graph_construction/experiments/E-708_v1_4_build/v14.py`.

**E8. Unverified statement.** 2D §4 says the v2.0 crosswalk was "built strictly from Wikidata queries". This is not shown by any script and will be checked in Step 3.

## 4. Observation carried forward (for Steps 4–5)

The corrected `analyze_corridor_gap.py` shows that in Stage C1 the CSMT suburban platform cluster (`n268558`) and the mainline platform cluster (`n289146`) end 12.07 m apart, with no track between them. Any terminal fix has to join them through a station model (plan Step 4), not by adding track that does not exist.
