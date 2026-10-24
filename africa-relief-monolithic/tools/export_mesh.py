import json,sys
from pathlib import Path
from collections import Counter
from shapely.geometry import shape,mapping
from shapely.geometry.polygon import orient
from shapely import constrained_delaunay_triangles
from shapely.ops import unary_union
P=Path(__file__).resolve().parent
if P.name=='tools':P=P.parent
D=json.load(open(P/'terrain-geometry.json'));scale=D['mm_per_unit']/1000;objects=[]
def polys(g):
 if g.geom_type=='Polygon':return [g] if g.area>1e-8 else []
 return [p for c in getattr(g,'geoms',[]) for p in polys(c)]
def solid(g,name,z,h,kind,tier,country):
 if kind=="cutter":g=g.buffer(-.002).buffer(.002).simplify(.001,preserve_topology=True)
 parts=sorted(polys(g),key=lambda p:-p.area)
 for num,p in enumerate(parts,1):
  p=orient(p,1);lookup={};xy=[]
  def idx(c):
   key=(round(c[0],8),round(c[1],8))
   if key not in lookup:lookup[key]=len(xy);xy.append(key)
   return lookup[key]
  triangles=[]
  for t in constrained_delaunay_triangles(p).geoms:
   ids=[idx(c) for c in list(t.exterior.coords)[:3]]
   if len(set(ids))==3:triangles.append(ids[::-1])
  triangles=list({tuple(sorted(t)):t for t in triangles}.values());edges=Counter()
  for t in triangles:
   for a,b in zip(t,t[1:]+t[:1]):edges[tuple(sorted((a,b)))]+=1
  boundary=[e for e,n in edges.items() if n==1];n=len(xy)
  if n<3:continue
  cx=(min(x for x,y in xy)+max(x for x,y in xy))/2;cy=(min(y for x,y in xy)+max(y for x,y in xy))/2;v=[[(x-cx)*scale,-(y-cy)*scale,height] for height in [0,h] for x,y in xy];f=[];m=[]
  for t in triangles:f.extend([t[::-1],[k+n for k in t]]);m.extend([1,0])
  for a,b in boundary:f.append([a,b,b+n,a+n]);m.append(1)
  objects.append({'id':name+(f'_P{num:02d}' if len(parts)>1 else ''),'logical_id':name,'kind':kind,'tier':tier,'country':country,'origin':[cx*scale,(2657.4803125-cy)*scale,z],'height':h,'vertices':v,'faces':f,'material_indices':m,'geom':mapping(p)})

for i,l in enumerate(D['layers'],1):
 for code,key in [('AFR','mainland'),('MAD','madagascar')]:
  g=shape(l).intersection(shape(D[key]));solid(g,f'L{i:02d}_{code}',(i-1)*.003,.003,'wood',i,code)
 for kind,key in [('texture','texture')]:
  g=shape(D[key]).intersection(shape(D['visible'][i-1]))
  if g.area>.00001:solid(g,f'{kind.upper()}_L{i:02d}',i*.003+.00001,.00002,kind,i,'AFR')
merged=[];groups={}
for ob in objects:
 if ob['kind']=='wood':merged.append(ob)
 else:groups.setdefault(ob['logical_id'],[]).append(ob)
for name,items in groups.items():
 first=items[0];origin=first['origin'];v=[];f=[];m=[]
 for ob in items:
  off=len(v);delta=[ob['origin'][i]-origin[i] for i in range(3)];v.extend([[p[i]+delta[i] for i in range(3)] for p in ob['vertices']]);f.extend([[a+off for a in face] for face in ob['faces']]);m+=ob['material_indices']
 merged.append({**first,'id':name,'vertices':v,'faces':f,'material_indices':m,'geom':mapping(unary_union([shape(o['geom']) for o in items]))})
objects=merged;geo={o['id']:shape(o['geom']) for o in objects};wood=[o for o in objects if o['kind']=='wood'];rel={'stack':{},'markings':{}}
for ob in objects:
 if ob['kind']=='wood' and ob['tier']>1:
  owners=[a['id'] for a in wood if a['country']==ob['country'] and a['tier']==ob['tier']-1 and geo[a['id']].intersection(geo[ob['id']]).area>1e-8];assert owners,ob['id'];rel['stack'][ob['id']]=owners
 elif ob['kind']!='wood':
  owners=[a['id'] for a in wood if a['country']=='AFR' and a['tier']==ob['tier'] and geo[a['id']].intersection(geo[ob['id']]).area>1e-8];assert owners,ob['id'];rel['markings'][ob['id']]=owners
(P/'model-data.json').write_text(json.dumps({'objects':objects,'palette':D['palette'],'places':D['places'],'mm_per_unit':D['mm_per_unit']},ensure_ascii=False));(P/'model-relations.json').write_text(json.dumps(rel));print('EXPORTED',len(wood),'wood pieces',len(groups),'marking groups',flush=True)

# Reproducible vertical-ray samples for the Blender through-hole checks.
from shapely.geometry import Point
ray_points=[]
for name,g in D['waters'].items():
 g=shape(g);parts=polys(g);points=[p.representative_point() for p in parts]
 xmin,ymin,xmax,ymax=g.bounds
 for i in range(31):
  for j in range(31):
   q=Point(xmin+(xmax-xmin)*(i+.5)/31,ymin+(ymax-ymin)*(j+.5)/31)
   if g.contains(q):points.append(q)
 for q in points:ray_points.append({'water':name,'point':[q.x,q.y]})
(P/'through-ray-points.json').write_text(json.dumps(ray_points,ensure_ascii=False))
