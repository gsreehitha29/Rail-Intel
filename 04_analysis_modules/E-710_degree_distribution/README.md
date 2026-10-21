# E-710 — the degree distribution as a test, not a caption

**The problem.** `publication/figures/fig3_degree.caption.txt` asserted that the tail is
"exponential rather than scale-free, as Kurant & Thiran (2006) predict". Nothing in
`FINDINGS.md` fitted anything. This is the project's one *falsifiable* theory check, so
it has to be a test.

**Status: run. The claim's conclusion is right and its characterisation was wrong.**

## What the distribution actually is

| degree | stations | share | what it is |
|---|---|---|---|
| 1 | 394 | 4.3% | termini |
| 2 | 7,393 | 81.6% | intermediate stops |
| 3 | 904 | 10.0% | junctions |
| 4 | 274 | 3.0% | |
| 5 | 71 | 0.8% | |
| 6 | 19 | 0.2% | |
| 7 | 3 | 0.03% | the maximum |

Mean 2.15, median 2, max 7, on the 9,058-node giant component.

## Three results

**1. The whole distribution is not exponential.** The exponential beats a power law
decisively (Vuong z = 164.4) but it does not *fit*: it predicts 4,054 nodes of degree 1
against 394 observed, and chi-square rejects it (15,809 on 5 dof, p < 1e-16). Preferring
one badly fitting model over a worse one is not evidence for either. The distribution is
a **spike at degree 2**, which the representation forces — in space-of-stations a
line-based network is mostly degree-2 chain nodes, so no smooth single-family law can
describe it and fitting one is a category error.

**2. Among junctions (k ≥ 3) it is exponential, and it fits well.**

| k | observed | expected under exponential (λ = 1.270) |
|---|---|---|
| 3 | 904 | 915.8 |
| 4 | 274 | 257.1 |
| 5 | 71 | 72.2 |
| 6 | 19 | 20.3 |
| 7 | 3 | 5.7 |

χ² = 2.63 on 3 dof, **p = 0.45 — not rejectable.** A power law on the same support is
rejected (χ² = 25.41; Vuong z = 3.81, p = 1.4e-4 favouring exponential). So Kurant &
Thiran's prediction **holds, located where it has content** — the branching structure —
rather than asserted over a support the chain nodes dominate.

**3. Scale-free is impossible anyway.** Maximum degree is 7. A scale-free degree
distribution cannot occur on a support of seven integers. That is Barthélemy's (2011)
prediction for a spatially embedded network where every junction costs land and civil
works: the bound is the structural result, the tail fit is the distributional one.

## Why prior work reports heavy tails

Earlier Indian-railway graphs are *service-space* graphs, where a node's degree counts
trains or reachable stations, not tracks. The two quantities are not comparable, and the
difference is a consequence of representation, not of the network. This is the clearest
single illustration of the project's central argument.

## Method

Discrete MLE for both families, normalised over exactly the same finite support so the
log-likelihoods are comparable; Vuong normal test on the per-observation log-likelihood
ratio; chi-square goodness of fit against observed counts. Fitted at k_min = 1, 2 and 3.

## Files

- `degree_fit.py` — `python degree_fit.py <root> out`
- `out/E-710_degree_fit.json` — every figure above, all three fits, and the verdict
- `out/degree_distribution.csv` — observed vs expected under each model
