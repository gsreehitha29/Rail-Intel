# E-720 — robustness of the severance conclusions on v2.x-open (remediation Step 9)

E-711's sweep. Choices: release (v2.0, v2.1) × view (physical, places; D-066) × intra-station artifact threshold (0.5, 1, 2 km). The duplicate contraction is dropped (V2-25), and severance counts stations only. It reads the released packages, because the working build's places view has no `state`. `python sweep_v2.py` writes `out/sweep_cells.csv` and `out/E-720_sweep.json`.

| Conclusion | All 12 cells | v2.1 only (6 cells) |
|---|---|---|
| Worst corridor severs 109 stations (Lumding–Badarpur hill line: Assam, Manipur, Mizoram) | **ROBUST** | **ROBUST** |
| The worst bridge severs 109 Northeast stations | **ROBUST** | **ROBUST** |
| Junction cut points | CONDITIONAL (260–312) | **ROBUST** (260–286) |
| Number of severance corridors | CONDITIONAL (208–240) | CONDITIONAL (209–234) |
| Share of sections with no alternative route | ARTIFACT (12.5–16.9%) | CONDITIONAL: 12.5–12.7% physical, 15.6–15.9% places. Quote with the view |
| Number of intra-station artifact bridges | ARTIFACT | ARTIFACT: do not quote |

- **Superseded v1.4 conclusions:** E-711's "worst corridor isolates > 450 stations" and "worst bridge isolates the whole Northeast" no longer hold. The Araria–Galgalia line (commissioned 2024–25; E-718, E-725) gives a second route past Barsoi.
- **What replaces them:** a 109-station Lumding–Badarpur exposure, robust in every cell.
