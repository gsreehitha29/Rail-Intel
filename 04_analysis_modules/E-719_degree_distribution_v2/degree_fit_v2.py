"""E-719 - E-710's degree-distribution test, rerun on v2.x-open (remediation Step 9).

Reuses E-710's fit() unchanged (discrete MLE, power law vs exponential on the same finite support,
Vuong test, chi-square). Reports the numbers and the outcome of E-710's two claims instead of its
v1.4 narrative text:
  claim A  over the full support, exponential is preferred but does not fit (a spike at k = 2);
  claim B  among junctions (k >= 3) the exponential fits (chi-square not rejected at 5%) and a
           power law is rejected (Vuong favours exponential).
Views: places (D-066, the stable-class view, comparable with v1.4's station graph) and physical.

    python degree_fit_v2.py
"""
import json, sys
from pathlib import Path
import numpy as np
import networkx as nx
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "04_analysis_modules/E-710_degree_distribution"))
from degree_fit import fit                                    # noqa: E402


def degrees(ver, view):
    d = ROOT / "03_graph_construction" / f"graph_{ver}" / "open"
    if view == "places": d = d / "places"
    n = pd.read_csv(d / "nodes.csv", low_memory=False); e = pd.read_csv(d / "edges.csv")
    G = nx.Graph(); G.add_nodes_from(n.node_id); G.add_edges_from(zip(e.from_node, e.to_node))
    H = G.subgraph(max(nx.connected_components(G), key=len))
    return np.array([d for _, d in H.degree()])


rows, rep = [], {}
for ver in ("v2_0_open", "v2_1_open"):
    for view in ("places", "physical"):
        k = degrees(ver, view)
        full, tail = fit(k, 1, int(k.max())), fit(k, 3, int(k.max()))
        sh = {int(v): round(float((k == v).mean()), 4) for v in np.unique(k)}
        r = dict(nodes_giant=len(k), mean_degree=round(float(k.mean()), 4), max_degree=int(k.max()), degree_share=sh,
                 full=dict(preferred=full["preferred"], vuong_z=full["vuong_z"], chisq_exp=full["chisq_exponential"],
                           dof=full["chisq_dof"], p_exp=full["chisq_p_exponential"]),
                 tail_k3=dict(preferred=tail["preferred"], lam=tail["exponential_lambda"], vuong_z=tail["vuong_z"],
                              vuong_p=tail["vuong_p"], chisq_exp=tail["chisq_exponential"], dof=tail["chisq_dof"],
                              p_exp=tail["chisq_p_exponential"], chisq_pl=tail["chisq_power_law"]))
        r["claim_A_holds"] = bool(full["preferred"] == "exponential" and (full["chisq_p_exponential"] or 0) < 0.05)
        r["claim_B_holds"] = bool(tail["preferred"] == "exponential" and tail["chisq_p_exponential"] is not None
                                  and tail["chisq_p_exponential"] >= 0.05)
        rep[f"{ver}/{view}"] = r
        rows.append(dict(release=ver, view=view, nodes=len(k), max_degree=int(k.max()), share_k1=sh.get(1, 0), share_k2=sh.get(2, 0),
                         share_k3plus=round(sum(v for kk, v in sh.items() if kk >= 3), 4),
                         tail_lambda=tail["exponential_lambda"], tail_chisq_p=tail["chisq_p_exponential"], tail_vuong_z=tail["vuong_z"],
                         claim_A=r["claim_A_holds"], claim_B=r["claim_B_holds"]))
v14 = json.loads((ROOT / "04_analysis_modules/E-710_degree_distribution/out/E-710_degree_fit.json").read_text())
rows.insert(0, dict(release="v1_4", view="station", nodes=v14["nodes_giant"], max_degree=v14["max_degree"],
                    share_k1=v14["degree_share"]["1"], share_k2=v14["degree_share"]["2"],
                    share_k3plus=v14["composition"]["junctions_k3plus"], tail_lambda=v14["fit_tail_kmin3"]["exponential_lambda"],
                    tail_chisq_p=v14["fit_tail_kmin3"]["chisq_p_exponential"], tail_vuong_z=v14["fit_tail_kmin3"]["vuong_z"],
                    claim_A=True, claim_B=True))
out = HERE / "out"; out.mkdir(exist_ok=True)
(out / "E-719_degree_fit.json").write_text(json.dumps(rep, indent=1, default=str))
t = pd.DataFrame(rows); t.to_csv(out / "summary.csv", index=False)
print(t.to_string(index=False))
