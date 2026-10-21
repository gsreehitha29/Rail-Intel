exec(open('tune.py').read().split("base=test")[0])
n=pd.read_parquet(v13.OUT/'full/nodes.parquet'); ins=set(n.node_id[n.node_origin=='osm_inserted_station'])
E=pd.read_parquet(v13.OUT/'full/edges.parquet'); Eo=pd.read_parquet(v13.OUT/'open/edges.parquet')
def errs(E,keys):
    G=nx.Graph(); G.add_weighted_edges_from(zip(E.from_node,E.to_node,E.length_km)); out={}
    for s in keys:
        st=[x for x in stops[s][0] if x in G]
        if len(st)<2 or st[0]!=stops[s][0][0] or st[-1]!=stops[s][0][-1] or stops[s][1]<=20: continue
        try: tot=sum(nx.shortest_path_length(G,x,y,weight='weight') for x,y in zip(st[:-1],st[1:]) if x!=y)
        except nx.NetworkXNoPath: continue
        out[s]=(tot-stops[s][1])/stops[s][1]*100
    return pd.Series(out)
keys=tune+hold; ef=errs(E,keys); eo=errs(Eo,keys)
hit=pd.Series({s: any(x in ins for x in stops[s][0]) for s in ef.index})
for lab,m in [('trains stopping at an inserted station',hit),('trains not stopping at one',~hit)]:
    print(lab,int(m.sum()),'| full median abs',round(ef[m].abs().median(),2),'| open median abs',round(eo.reindex(ef.index)[m].abs().median(),2),'| full worse by >2pts on',int(((ef[m].abs()-eo.reindex(ef.index)[m].abs())>2).sum()))
# per inserted station: excess when routing through it
