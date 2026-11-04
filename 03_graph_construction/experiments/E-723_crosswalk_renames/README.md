# E-723 — 2017 timetable renames in the crosswalk (V2-28, remediation Step 3)

Read-only on the release. Builds the 2017 service layer twice, once with the v2.0 crosswalk and once with
`aliases_v2_1.csv` added, and writes only to `out/`.

```bash
python run_service17.py
```

- **Baseline:** reproduces the release exactly (same 27,952 station pairs and train counts, and identical
  `trains_2017` on all 13,560 edges).
- **Aliases:** 19 accepted (`aliases_v2_1.csv`, each with its source) and 3 rejected (`rejected.csv`: BRY, SLTP, 142).
  A name match was accepted only where the target has no 2017 code of its own, or where both codes share the
  same timetable neighbours.

| Measure | v2.0 | with aliases |
|---|---|---|
| Station pairs | 27,952 | 27,997 (308 new, 263 replaced) |
| Unroutable station pairs | 121 | 93 |
| Stations with 2017 service | 8,049 | 8,065 |
| Max trains on an edge at MMCT / DDU / PRYJ / MBDP / PRRB | 0 / 109 / 30 / 0 / 0 | 45 / 272 / 193 / 71 / 33 |
| New pairs within 2 km or 5% of the timetable distance | — | 90.5% (median error 2.1%) |

- **Edges that lose trains:** 91 edges lose trains, all in the DDU and Prayagraj junction areas. Trains that used to skip an unresolved stop were routed over yard bypasses; they now pass through the station.
- **Long non-stop hops:** the 14 new pairs with no path are non-stop hops over the 400 km routing cutoff (e.g. ADI–MMCT), the same rule the release applies.

**Gate (plan Step 3): passed.** MMCT, DDU, PRYJ and RKMP carry trains. No code that already resolved changes target (asserted). Unroutable pairs fall. Route agreement on the new pairs is in line with the release.
