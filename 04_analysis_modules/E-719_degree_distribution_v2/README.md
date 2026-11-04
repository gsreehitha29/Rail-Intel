# E-719 — degree distribution on v2.x-open (remediation Step 9)

E-710's fit (`degree_fit.fit`, unchanged), rerun on v2.0 and v2.1. `python degree_fit_v2.py` writes `out/summary.csv` and `out/E-719_degree_fit.json`. Read the **places** view (D-066); the physical view keeps junction areas and is not comparable with v1.4's station graph.

| | v1.4 station graph | v2.0 places | **v2.1 places** |
|---|---|---|---|
| Max degree | 7 | 8 | **6** |
| Degree 1 / 2 / ≥ 3 | 4.4% / 81.6% / 14.0% | 2.9% / 86.2% / 10.9% | **2.6% / 87.6% / 9.8%** |
| Claim A: over the full support, exponential is preferred but does not fit | holds | holds | **holds** |
| Claim B: junction tail (k ≥ 3) is exponential, chi-square p | 0.45 (holds) | 1.9e-5 (fails; power law preferred) | **0.14 (holds)** |
| Vuong z, exponential vs power law on the tail | 3.8 (p < 0.001) | −1.7 | **0.87 (p = 0.38)** |

- **v2.0's artifacts flipped claim B.** The degree-1 terminal stubs and the extra junction structure made a power law fit the tail better. v2.1 restores the exponential fit.
- **The likelihood-ratio test no longer separates the two families on v2.1** (p = 0.38), so claim B holds as "exponential fits; power law rejected by chi-square (6.65 on 2 dof)", not as a decisive model choice.
- **Bounded degree (max 6) and the spike at degree 2 stay the structural results.**
