import pandas as pd, numpy as np, os, networkx as nx, sys, itertools, json
sys.path.insert(0, os.path.expanduser('~/mnt/Rail-Intell/03_graph_construction')); from railgraph import v13
STG=v13.STG; e12=pd.read_parquet(v13.V12/'edges.parquet')
sn=pd.read_parquet(STG/'s2b_snap.parquet').set_index('node_id').snap_km
X=v13.EXT; t=pd.read_csv(X/'timetable_2017_datagovin/Train_details_22122017.csv',dtype=str)
t['Distance']=pd.to_numeric(t.Distance,errors='coerce'); t['SEQ']=pd.to_numeric(t.SEQ,errors='coerce'); t['Station Code']=t['Station Code'].str.strip()
t=t.sort_values(['Train No','SEQ']); stops={k:(g['Station Code'].tolist(),g.Distance.max()) for k,g in t.groupby('Train No')}
allk=pd.Series(sorted(stops)); tune=allk.sample(n=700,random_state=7).tolist(); hold=allk.drop(allk.sample(n=700,random_state=7).index).sample(n=700,random_state=99).tolist()
def lengths(v,cap,floor_rule):
    d=pd.read_parquet(STG/f's3_edges_{v}.parquet').merge(e12[['edge_id','from_node','to_node','length_source']],on='edge_id')
    ch=d.length_chord_v13.fillna(0); off=d.official_km; L12=d.length_km_v12; spine=d.length_source.eq('spine')
    agree=lambda x,o:(x-o).abs()<=np.maximum(1,0.05*o)
    off_ok=off.notna()&(off>=0.9*ch-1)&(off<=cap*ch+1)
    osm=d.osm_km if 'osm_km' in d else pd.Series(np.nan,index=d.index)
    osm_ok=osm.notna()&(osm>=0.98*ch)&(osm<=cap*ch+0.5)&~(off_ok&~agree(osm,off))
    o_sp=osm.notna()&agree(osm,L12); o_of=osm.notna()&agree(osm,off)
    to_off=off_ok&spine&~agree(L12,off)&o_of&~o_sp
    out=np.where(off_ok&spine&~to_off,L12,np.where(off_ok&osm_ok&agree(osm,off),osm,np.where(off_ok,off,np.where(spine,L12,np.where(osm_ok,osm,L12)))))
    out=pd.Series(out,index=d.index)
    trust=lambda x: (~x.str.startswith('JN::'))|(x.map(sn).fillna(9)<=0.5)
    fl=(trust(d.from_node)&trust(d.to_node)) if floor_rule=='trusted_only' else pd.Series(True,index=d.index)
    out=np.where(fl,np.maximum(out,ch),out); return d.from_node,d.to_node,np.maximum(out,0.05)
def test(a,b,L,keys):
    G=nx.Graph(); G.add_weighted_edges_from(zip(a,b,L)); err=[]
    for s in keys:
        st=[x for x in stops[s][0] if x in G]
        if len(st)<2 or st[0]!=stops[s][0][0] or st[-1]!=stops[s][0][-1] or stops[s][1]<=20: continue
        try: tot=sum(nx.shortest_path_length(G,x,y,weight='weight') for x,y in zip(st[:-1],st[1:]) if x!=y)
        except nx.NetworkXNoPath: continue
        err.append((tot-stops[s][1])/stops[s][1]*100)
    e=np.array(err); return round(float(np.median(e)),2),round(float(np.median(np.abs(e))),2),round(float((np.abs(e)<=2).mean()*100),1)
base=test(e12.from_node,e12.to_node,e12.length_km,tune); print('v1.2 tune',base)
res=[]
for v,cap,fr in itertools.product(sys.argv[1].split(','),[1.15,1.25,1.35,1.6],['all','trusted_only']):
    a,b,L=lengths(v,cap,fr); r=test(a,b,L,tune); res.append((v,cap,fr,r)); print(v,cap,fr,r,flush=True)
