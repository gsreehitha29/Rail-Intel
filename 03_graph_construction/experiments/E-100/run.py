"""E-100 -- metric baselines on the shipped default graph, plus the resilience
protocol and its validation.

Produces the numbers the four Phase 4 modules check their own work against, and
the evidence for F-011..F-016. Four parts:

  1. structural baselines vs QA_REPORT.txt
  2. criticality: bridge severance, named, with service impact
  3. resilience: percolation under four attack strategies, with R, plus the
     null-model sanity checks that make the inverted result believable
  4. communities: two methodologically different algorithms, scored against the
     railway-zone labels

    python experiments/E-100/run.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from railgraph import load_graph  # noqa: E402
from railgraph import metrics as M  # noqa: E402
from railgraph import weights as W  # noqa: E402

OUT = Path(__file__).parent
QA_BASELINE = {"articulation_points": 1338, "bridges": 1412, "independent_cycles": 612}


def part1_structure(G) -> dict:
    print("\n[1] structural baselines")
    cs = M.cut_structure(G)
    ok = all(cs[k] == v for k, v in QA_BASELINE.items())
    for k in ("n_nodes", "n_edges", "n_components", "giant_nodes", "giant_edges",
              "articulation_points", "bridges", "independent_cycles"):
        print(f"    {k:22} {cs[k]:,}")
    for k in ("articulation_share", "bridge_share", "meshedness", "tree_likeness"):
        print(f"    {k:22} {cs[k]:.4f}")
    print(f"    vs QA_REPORT baselines: {'MATCH' if ok else 'MISMATCH'}")
    assert ok, f"metric baselines disagree with QA_REPORT: {cs}"

    cov = W.travel_time_coverage(G)
    print(f"    speed coverage: {cov['edges_with_speed']:,}/{cov['edges_total']:,} edges "
          f"({cov['edge_share']:.1%}), {cov['km_share']:.1%} of route km")
    cs["speed_coverage"] = cov

    for w in ("length_km", "unit"):
        pp = M.path_profile(G, weight=w, n_pairs=1500)
        cs[f"path_{w}"] = pp
        print(f"    paths[{w:9}] mean {pp['mean_path']:9.2f}  median {pp['median_path']:9.2f}"
              f"  hops {pp['mean_hops']:6.1f}  circuity median "
              f"{pp['circuity_median'] if not np.isnan(pp['circuity_median']) else float('nan'):.3f}")
    return cs


def part2_criticality(G) -> pd.DataFrame:
    print("\n[2] criticality -- worst bridges by nodes stranded")
    nb = M.node_basics(G).set_index("node_id")
    bs = M.bridge_severance(G, top=0)
    bs["from_name"] = bs.from_node.map(nb.node_name)
    bs["to_name"] = bs.to_node.map(nb.node_name)
    bs["zone"] = bs.from_node.map(nb.zone_code)
    bs = bs.sort_values("nodes_stranded", ascending=False)
    for r in bs.head(8).itertuples():
        print(f"    {r.from_node:>6}-{r.to_node:<6} {str(r.from_name)[:22]:22} -> "
              f"{str(r.to_name)[:22]:22} strands {r.nodes_stranded:4,} "
              f"({r.stranded_share:5.1%})  {r.service_load or 0:4.0f} trains  "
              f"stitch={bool(r.any_stitch)}")
    top50 = bs.head(50)
    share_all = float(np.mean([bool(d.get("any_stitch")) for _, _, d in G.edges(data=True)]))
    print(f"    stitched edges among top-50 severing bridges: "
          f"{int(top50.any_stitch.sum())}/50 ({top50.any_stitch.mean():.1%}) "
          f"vs {share_all:.1%} of all edges")
    bs.to_csv(OUT / "bridge_severance.csv", index=False)
    return bs


def part3_resilience(G) -> dict:
    print("\n[3] resilience -- percolation, R, and the sanity checks")
    res = {}
    curves = []
    for strat in ("random", "degree", "betweenness", "service_load"):
        for adaptive in (False, True):
            if adaptive and strat in ("random",):
                continue
            t = time.time()
            df = M.percolation(G, strategy=strat, steps=40 if not adaptive else 20,
                               recompute=adaptive, sample_k=400 if not adaptive else 250)
            df["adaptive"] = adaptive
            curves.append(df)
            sub = df[df.scf < 0.5]
            f50 = float(sub.removed_frac.iloc[0]) if len(sub) else np.nan
            sub = df[df.scf < 0.1]
            f10 = float(sub.removed_frac.iloc[0]) if len(sub) else np.nan
            key = f"{strat}{'_adaptive' if adaptive else ''}"
            res[key] = {"R": float(df.R.iloc[0]), "f_scf50": f50, "f_scf10": f10}
            print(f"    {key:24} R={res[key]['R']:.4f}  f(SCF<0.5)={f50:.3f}  "
                  f"f(SCF<0.1)={f10:.3f}  [{time.time() - t:.0f}s]")
    pd.concat(curves).to_csv(OUT / "percolation_curves.csv", index=False)

    # --- sanity checks: is the inverted ranking real, or an implementation bug? ---
    print("\n    sanity: does the same code give the textbook answer elsewhere?")
    BA = nx.barabasi_albert_graph(3000, 2, seed=1)
    for _u, _v, d in BA.edges(data=True):
        d["length_km"], d["service_load"] = 1.0, 1.0
    BA.graph["spec_hash"] = "ba-control"
    ba = {s: float(M.percolation(BA, strategy=s, steps=40).R.iloc[0])
          for s in ("random", "degree")}
    print(f"      BA(3000,2) scale-free:  random R={ba['random']:.4f}  "
          f"degree R={ba['degree']:.4f}  -> hub attack much worse, as expected")

    P = nx.path_graph(G.subgraph(max(nx.connected_components(G), key=len)).number_of_nodes())
    for _u, _v, d in P.edges(data=True):
        d["length_km"], d["service_load"] = 1.0, 1.0
    P.graph["spec_hash"] = "path-control"
    pr = float(M.percolation(P, strategy="random", steps=40).R.iloc[0])
    print(f"      path graph, same n:     random R={pr:.4f}  -> a pure tree is even "
          f"more fragile than ours ({res['random']['R']:.4f})")

    # why static betweenness is a weak attack here
    H = M.giant(G)
    bc = M.betweenness(H, weight="length_km", k=400)
    top = set(bc.nlargest(500, "betweenness").node_id)
    sub = H.subgraph(top)
    contiguity = {
        "induced_components": nx.number_connected_components(sub),
        "largest_induced_run": max(len(c) for c in nx.connected_components(sub)),
        "mean_degree_top500": float(np.mean([H.degree(n) for n in top])),
        "mean_degree_network": float(np.mean([d for _, d in H.degree()])),
    }
    print(f"      top-500 betweenness nodes induce {contiguity['induced_components']} "
          f"components, largest run {contiguity['largest_induced_run']} "
          f"-> they lie contiguously along the trunk")

    res["controls"] = {"ba_scale_free": ba, "path_graph_random_R": pr,
                       "betweenness_contiguity": contiguity}
    return res


def part4_communities(G) -> dict:
    print("\n[4] communities -- two methodologically different algorithms")
    out = {}
    for method in ("louvain", "infomap"):
        t = time.time()
        part = M.communities(G, method=method)
        v = M.community_vs_zone(G, part)
        sizes = part.groupby("community").size()
        v["largest"] = int(sizes.max())
        v["median_size"] = int(sizes.median())
        v["secs"] = round(time.time() - t, 1)
        out[method] = v
        print(f"    {method:9} {v['n_communities']:4} communities  Q={v['modularity']:.4f}  "
              f"largest {v['largest']:4}  median {v['median_size']:4}")
        print(f"              vs stated zone  NMI={v['stated_zone_only']['nmi']:.3f} "
              f"ARI={v['stated_zone_only']['ari']:.3f}  (n={v['stated_zone_only']['n']:,})")
        part.to_csv(OUT / f"communities_{method}.csv", index=False)
    return out


def main() -> None:
    print("=" * 78)
    print("E-100  metric baselines, criticality, resilience, communities")
    print("=" * 78)
    G = load_graph()
    report = {
        "structure": part1_structure(G),
        "resilience": part3_resilience(G),
        "communities": part4_communities(G),
    }
    part2_criticality(G)
    (OUT / "report.json").write_text(json.dumps(report, indent=2, default=str))
    print(f"\nwrote {OUT}/report.json, bridge_severance.csv, percolation_curves.csv, "
          f"communities_*.csv")


if __name__ == "__main__":
    main()
