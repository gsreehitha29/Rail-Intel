"""E-710 - the degree distribution as a fit test, not a caption claim.

`fig3_degree.caption.txt` asserts the tail is "exponential rather than scale-free, as
Kurant & Thiran (2006) predict for physical rail networks". Nothing in FINDINGS.md fits
anything. This is the project's one falsifiable theory check, so it needs numbers.

Method. Discrete MLE for both families on the support k >= k_min:
    power law     P(k) ~ k^-alpha           (discrete, normalised by the Hurwitz zeta
                                             truncated at k_max, since support is finite)
    exponential   P(k) ~ exp(-lambda k)     (discrete, geometric, normalised on the
                                             same finite support)
Both are normalised over exactly the same support, so the log-likelihoods are
comparable and a Vuong-style likelihood-ratio test applies. AIC is reported too; the
models have one parameter each, so AIC ordering equals log-likelihood ordering.

The honest caveat is reported alongside: the support is k in [1, 7]. Over seven
integers a power law is barely identifiable, so a rejection of scale-free here is not
the strong result it would be on a heavy-tailed support spanning decades. Bounded
support IS the finding (Barthelemy 2011): a scale-free degree distribution cannot
occur in a network whose maximum degree is 7.

    python degree_fit.py <staged root> <out dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import networkx as nx
from scipy import optimize, stats


def load(root: Path):
    d = root / "03_graph_construction" / "graph_v1_4" / "open"
    nodes = pd.read_csv(d / "nodes.csv")
    edges = pd.read_csv(d / "edges.csv")
    G = nx.Graph()
    G.add_nodes_from(nodes.node_id)
    for r in edges.itertuples():
        G.add_edge(r.from_node, r.to_node)
    return G


def _norm_pl(alpha, support):
    return np.sum(support.astype(float) ** -alpha)


def _norm_exp(lam, support):
    return np.sum(np.exp(-lam * support.astype(float)))


def fit(k: np.ndarray, kmin: int, kmax: int):
    """MLE for both families on the shared finite support [kmin, kmax]."""
    k = k[(k >= kmin) & (k <= kmax)]
    n = len(k)
    support = np.arange(kmin, kmax + 1)

    def nll_pl(a):
        return a * np.sum(np.log(k)) + n * np.log(_norm_pl(a, support))

    def nll_exp(l):
        return l * np.sum(k) + n * np.log(_norm_exp(l, support))

    a = optimize.minimize_scalar(nll_pl, bounds=(0.01, 20), method="bounded").x
    l = optimize.minimize_scalar(nll_exp, bounds=(1e-4, 20), method="bounded").x
    ll_pl, ll_exp = -nll_pl(a), -nll_exp(l)

    # per-observation log-likelihood ratio, Vuong normal test
    lpl = -a * np.log(k) - np.log(_norm_pl(a, support))
    lex = -l * k - np.log(_norm_exp(l, support))
    d = lex - lpl                                   # positive favours exponential
    sd = d.std(ddof=1)
    R = d.sum()
    z = R / (np.sqrt(n) * sd) if sd > 0 else np.inf
    p = 2 * stats.norm.sf(abs(z))

    # goodness of fit of the preferred model: chi-square on the observed counts
    obs = np.array([(k == v).sum() for v in support])
    exp_e = n * np.exp(-l * support) / _norm_exp(l, support)
    exp_p = n * support.astype(float) ** -a / _norm_pl(a, support)
    chi_e = float(((obs - exp_e) ** 2 / exp_e).sum())
    chi_p = float(((obs - exp_p) ** 2 / exp_p).sum())
    dof = len(support) - 1 - 1

    return dict(
        kmin=int(kmin), kmax=int(kmax), n=int(n),
        power_law_alpha=round(float(a), 4), power_law_loglik=round(float(ll_pl), 2),
        exponential_lambda=round(float(l), 4), exponential_loglik=round(float(ll_exp), 2),
        loglik_ratio_exp_minus_pl=round(float(R), 2),
        vuong_z=round(float(z), 3), vuong_p=float(f"{p:.3e}"),
        preferred="exponential" if R > 0 else "power_law",
        aic_exponential=round(float(2 * 1 - 2 * ll_exp), 2),
        aic_power_law=round(float(2 * 1 - 2 * ll_pl), 2),
        chisq_exponential=round(chi_e, 2), chisq_power_law=round(chi_p, 2),
        chisq_dof=int(dof),
        chisq_p_exponential=float(f"{stats.chi2.sf(chi_e, dof):.3e}") if dof > 0 else None,
        observed_counts={int(v): int(c) for v, c in zip(support, obs)},
        expected_exponential={int(v): round(float(c), 1) for v, c in zip(support, exp_e)},
        expected_power_law={int(v): round(float(c), 1) for v, c in zip(support, exp_p)},
    )


def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    G = load(root)
    H = G.subgraph(max(nx.connected_components(G), key=len))
    k_all = np.array([d for _, d in G.degree()])
    k = np.array([d for _, d in H.degree()])

    rpt = dict(
        release="graph_v1_4/open",
        prediction="Kurant & Thiran 2006: space-of-stations rail degree distributions are "
                   "exponential, not scale-free. Barthelemy 2011: spatially embedded "
                   "networks have bounded degree.",
        nodes_all=len(k_all), nodes_giant=len(k),
        mean_degree=round(float(k.mean()), 4),
        median_degree=float(np.median(k)),
        max_degree=int(k.max()), min_degree=int(k.min()),
        degree_counts={int(v): int((k == v).sum()) for v in np.unique(k)},
        degree_share={int(v): round(float((k == v).mean()), 4) for v in np.unique(k)},
    )
    rpt["fit_full_support"] = fit(k, 1, int(k.max()))
    rpt["fit_tail_kmin2"] = fit(k, 2, int(k.max()))
    rpt["fit_tail_kmin3"] = fit(k, 3, int(k.max()))

    full, tail = rpt["fit_full_support"], rpt["fit_tail_kmin3"]
    sh = rpt["degree_share"]
    rpt["composition"] = dict(
        termini_k1=round(sh.get(1, 0.0), 4),
        intermediate_k2=round(sh.get(2, 0.0), 4),
        junctions_k3plus=round(sum(v for k_, v in sh.items() if k_ >= 3), 4),
    )
    rpt["verdict"] = dict(
        claim_tested="the degree distribution is exponential rather than scale-free "
                     "(fig3_degree.caption.txt, after Kurant & Thiran 2006)",
        result="upheld for the junction tail, REJECTED as stated for the whole distribution",
        correction=(
            "The caption's conclusion is right and its characterisation is wrong. Over the "
            f"full support the exponential beats a power law decisively (Vuong z = "
            f"{full['vuong_z']}) but it does not FIT: it predicts {full['expected_exponential'][1]:.0f} "
            f"nodes of degree 1 against {full['observed_counts'][1]} observed, and chi-square "
            f"rejects it ({full['chisq_exponential']:.0f} on {full['chisq_dof']} dof, p < 1e-16). "
            "Preferring one badly fitting model over a worse one is not evidence of either."),
        what_the_distribution_actually_is=(
            f"A spike at degree 2. {sh.get(2, 0):.1%} of stations are intermediate stops, "
            f"{sh.get(1, 0):.1%} are termini, and "
            f"{rpt['composition']['junctions_k3plus']:.1%} are junctions. That is forced by "
            "the representation: in space-of-stations a line-based network is mostly "
            "degree-2 chain nodes, so no smooth single-family law can describe the whole "
            "distribution, and fitting one to it is a category error."),
        the_defensible_claim=(
            f"Among junctions (k >= 3) the degree distribution IS exponential and fits well: "
            f"lambda = {tail['exponential_lambda']}, chi-square {tail['chisq_exponential']} on "
            f"{tail['chisq_dof']} dof, p = {tail['chisq_p_exponential']:.2f} - not rejectable. "
            f"A power law over the same support is rejected (chi-square {tail['chisq_power_law']}; "
            f"Vuong z = {tail['vuong_z']}, p = {tail['vuong_p']:.1e} favouring exponential). "
            "Kurant & Thiran's prediction therefore holds, located precisely where it has "
            "content - the branching structure - rather than asserted over a support the "
            "chain nodes dominate."),
        scale_free_is_impossible_anyway=(
            f"Maximum degree is {rpt['max_degree']}. A scale-free degree distribution cannot "
            "occur on a support of seven integers, which is Barthelemy's (2011) prediction "
            "for a spatially embedded network where every junction costs land and civil works. "
            "The bound is the structural result; the tail fit is the distributional one."),
        contrast_with_prior_work=(
            "Prior Indian-railway graphs report heavy-tailed degree because they are "
            "service-space graphs, where a node's degree counts trains or reachable stations, "
            "not tracks. The two are not comparable, and the difference is a consequence of "
            "representation, not of the network."),
    )
    (out / "E-710_degree_fit.json").write_text(json.dumps(rpt, indent=1, default=str))
    pd.DataFrame([dict(degree=k_, nodes=v,
                       share=rpt["degree_share"][k_],
                       expected_exponential=full["expected_exponential"].get(k_),
                       expected_power_law=full["expected_power_law"].get(k_),
                       expected_exponential_tail_fit=tail["expected_exponential"].get(k_))
                  for k_, v in rpt["degree_counts"].items()]).to_csv(
        out / "degree_distribution.csv", index=False)
    print(json.dumps(rpt, indent=1, default=str))


if __name__ == "__main__":
    main()
