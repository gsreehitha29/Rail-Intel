"""E-601 — do the paper's conclusions survive v1.3? Same battery and bands as E-501 B
(sensitivity.measure_graph / BANDS), measured on graph_v1_3/<variant>, compared with
v1.0 (E-200 default cell) and v1.2 (E-501 B). usage: run.py open|full|report"""
import json, sys
from pathlib import Path
import networkx as nx, numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; PHASE3 = HERE.parents[1]
sys.path.insert(0, str(PHASE3))
from railgraph import sensitivity as S

def measure(v):
    n = pd.read_parquet(PHASE3/'graph_v1_3'/v/'nodes.parquet'); e = pd.read_parquet(PHASE3/'graph_v1_3'/v/'edges.parquet')
    G = nx.Graph()
    for r in n.itertuples(index=False):
        G.add_node(r.node_id, longitude=r.longitude, latitude=r.latitude, node_type=r.node_type)
    for r in e.itertuples(index=False):
        G.add_edge(r.from_node, r.to_node, length_km=float(r.length_km), corridor_id=r.corridor_id,
                   service_load=float(r.service_load) if pd.notna(r.service_load) else 0.0, edge_id=r.edge_id)
    rk = json.loads((PHASE3/'experiments'/'E-401_derivation_sweep'/'rankings.json').read_text())
    ref = rk.get('default') or rk['length=asis']
    row = S.measure_graph(G, {'cell': f'v1.3-{v}'}, ref_corridors=ref.get('top_corridors'), ref_nodes=ref.get('top_nodes'))
    row = {k: (x if not isinstance(x, (np.floating, np.integer)) else x.item()) for k, x in row.items()}
    (HERE/f'measure_{v}.json').write_text(json.dumps(row, default=str, indent=1))
    return row

def report():
    c200 = pd.read_csv(PHASE3/'experiments'/'E-200'/'cells.csv').set_index('cell').loc['default']
    v12 = pd.read_csv(PHASE3/'experiments'/'E-501_v1_2_audit'/'conclusions_v1_2.csv')
    v12 = v12[v12.vs == 'v1.0'].set_index('conclusion').v1_2
    out = []
    for v in ('open', 'full'):
        row = json.loads((HERE/f'measure_{v}.json').read_text())
        for k, band in S.BANDS.items():
            x = row.get(k)
            if k.endswith('_overlap'):
                out.append(dict(variant=v, conclusion=k, value=x, vs='v1.0', reference=None, deviation=1-float(x), band=band, within_band=(1-float(x)) <= band)); continue
            for refname, rv in (('v1.0', float(c200[k])), ('v1.2', float(v12[k]))):
                dev = abs(float(x)-rv)/abs(rv) if k in S.RELATIVE else abs(float(x)-rv)
                out.append(dict(variant=v, conclusion=k, value=float(x), vs=refname, reference=rv, deviation=dev, band=band, within_band=dev <= band))
    t = pd.DataFrame(out); t.to_csv(HERE/'conclusions_v1_3.csv', index=False)
    rep = {v: dict(all_within_band=bool(t[t.variant == v].within_band.all()),
                   failures=t[(t.variant == v) & ~t.within_band][['conclusion', 'vs', 'value', 'reference', 'deviation', 'band']].to_dict('records'))
           for v in ('open', 'full')}
    (HERE/'report.json').write_text(json.dumps(rep, indent=1, default=str)); return rep

if __name__ == '__main__':
    a = sys.argv[1]
    print(json.dumps(report() if a == 'report' else {k: v for k, v in measure(a).items() if not isinstance(v, list)}, default=str)[:1500])
