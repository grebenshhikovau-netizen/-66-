"""Partition authored upper plies for the requested paint groups, with shared seams."""
import json
from pathlib import Path
from shapely.geometry import shape,mapping,Polygon
from shapely.ops import unary_union
from shapely import make_valid,set_precision
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));R={c:shape(g)for c,g in D['regions'].items()};L=[shape(g)for g in D['layers']]
def ps(g):
 if g.geom_type=='Polygon':return [g]if not g.is_empty and g.area>1e-8 else []
 return [p for q in getattr(g,'geoms',[])for p in ps(q)]
def valid(g):return set_precision(unary_union(ps(make_valid(g))),.001)
groups={'Венгрия':['HUN'],'Греция-Албания-Турция':['GRC','ALB','TUR'],'Туркмения':['TKM'],'Лаос':['LAO']}
masks={name:valid(unary_union([R[c]for c in codes]).buffer(.18,quad_segs=8).buffer(-.18,quad_segs=8).simplify(.06,preserve_topology=True))for name,codes in groups.items()}
pieces=[];checks=[]
for i,layer in enumerate(L):
 batches=[]
 if i==0:batches=[('Общий слой',layer)]
 else:
  rest=layer
  for name,mask in masks.items():
   cut=valid(rest.intersection(mask));batches.append((name,cut));rest=valid(rest.difference(cut))
  batches.append(('Основной массив',rest))
 candidates=[{'group':name,'g':g}for name,ge in batches for g in ps(ge)]
 # Numerical scraps at smoothed three-way borders join their actual adjacent carrier.
 for q in list(candidates):
  if q not in candidates:continue
  if q['g'].area>=2:continue
  adjacent=[b for b in candidates if b is not q and b['g'].distance(q['g'])<.002 and b['g'].intersection(q['g'].boundary.buffer(.002)).area>.00001]
  if not adjacent:continue
  target=max(adjacent,key=lambda b:b['g'].intersection(q['g'].boundary.buffer(.002)).area)
  merged=valid(target['g'].union(q['g']))
  if merged.geom_type=='Polygon':target['g']=merged;candidates.remove(q)
 for j,q in enumerate(sorted(candidates,key=lambda q:-q['g'].area),1):
  g=q['g'];vis=valid(g.difference(L[i+1]))if i+1<len(L)else g
  pieces.append({'id':f'L{i+1:02d}_P{j:03d}','tier':i+1,'geom':mapping(g),'visible':mapping(vis),'regions':[c for c,r in R.items()if r.intersection(g).area>.4],'paint':{},'engraving':mapping(Polygon()),'area_mm2':g.area,'paint_group':q['group']})
 union=unary_union([q['g']for q in candidates]);err=union.symmetric_difference(layer).area;assert err<.01,err
 assert sum(q['g'].area for q in candidates)-union.area<.01
 checks.append({'tier':i+1,'pieces':len(candidates),'union_error_mm2':err,'zero_width_shared_seams':True})
D['pieces']=pieces
for s in D['summary']:s['pieces']=sum(p['tier']==s['tier']for p in pieces)
D['paint_partition_rules']=groups;D['paint_partition_checks']=checks
(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));print('PAINT PARTITIONS',checks,flush=True)
