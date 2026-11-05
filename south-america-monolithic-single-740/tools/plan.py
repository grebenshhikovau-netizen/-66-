"""Exact connected paint-compatible partition; narrow base water slots under approved upper relief."""
import json,gzip,math,functools,copy
from pathlib import Path
import numpy as np
from scipy.interpolate import RBFInterpolator
from shapely.geometry import shape,mapping,Polygon,Point,box,LineString
from shapely.ops import unary_union,transform
from shapely import make_valid,set_precision
P=Path(__file__).resolve().parent.parent;S=json.load(gzip.open(P/'data/source/approved-plan.json.gz','rt'));D=copy.deepcopy(S)
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty and g.area>1e-7 else[]
 return[p for q in getattr(g,'geoms',[])for p in ps(q)]
def valid(g):return unary_union(ps(make_valid(g)))
C=json.load(open(P/'data/source/geographic-controls.json'));F=json.load(open(P/'data/source/geographic-features.json'));MM=1600/4251.9685
warp=RBFInterpolator(np.array([[c[1],c[2]]for c in C]),np.array([[c[3],c[4]]for c in C]),kernel='thin_plate_spline',smoothing=1.8)
def project(g):
 def f(x,y,z=None):
  a=warp(np.column_stack([x,y]));return a[:,0]*MM,a[:,1]*MM-1000
 return transform(f,g)
river_lines=[];base_profiles=[]
for f in F['rivers']:
 name=f['name'];geo=shape(f['geom'])
 if name not in ['Amazonas','Madeira','Tapajós','Xingu','Ucayali','Marañón','Negro']:continue
 if name=='Negro'and not(geo.centroid.y>-5 and geo.centroid.x<-55):continue
 g=project(geo).simplify(.06);width=.65 if name=='Amazonas'else .45
 river_lines.append({'name':name,'geom':mapping(g),'base_width_mm':width})
 base_profiles.append(g.buffer(width/2,quad_segs=8))
# Preserve accepted second/third plies. The new lower cut stays inside their open
# river valley, leaving >=0.15 mm of bank ledge and avoiding buried unsupported slots.
base=shape(S['layers'][0]);upper=shape(S['layers'][1]);raw_water=unary_union(base_profiles)
base_water=valid(raw_water.intersection(base).difference(upper.buffer(.15)))
base_water=valid(base_water.buffer(-.08,quad_segs=6).buffer(.08,quad_segs=6).intersection(base_water))
base_water=unary_union([p for p in ps(base_water)if p.area>=.3])
parts=[];partition_report=[];bridges=[]
for tier in [1,2,3]:
 visible=shape(S['visible'][tier-1]);nodes=[]
 for code,raw in S['layer_country_masks'][tier-1].items():
  for g in ps(shape(raw)):
   if g.area>.01:nodes.append({'code':code,'geom':g,'visible':g.intersection(visible).buffer(-.02)})
 n=len(nodes);conf=[0]*n;adj=[0]*n
 for i,a in enumerate(nodes):
  for j,b in enumerate(nodes[:i]):
   if S['country_coat'][a['code']]!=S['country_coat'][b['code']]and not a['visible'].is_empty and not b['visible'].is_empty and a['visible'].distance(b['visible'])<.75:
    conf[i]|=1<<j;conf[j]|=1<<i
   if a['geom'].boundary.intersection(b['geom'].boundary.buffer(.00001)).length>.75:
    adj[i]|=1<<j;adj[j]|=1<<i
 feasible=[]
 for m in range(1,1<<n):
  if any(m>>i&1 and conf[i]&m for i in range(n)):continue
  seen=m&-m;front=seen
  while front:
   bit=front&-front;front-=bit;i=bit.bit_length()-1;new=adj[i]&m&~seen;seen|=new;front|=new
  if seen==m:feasible.append(m)
 lookup={i:sorted([m for m in feasible if m>>i&1],key=lambda m:-m.bit_count())for i in range(n)}
 @functools.lru_cache(None)
 def solve(m):
  if not m:return(0,0,())
  i=(m&-m).bit_length()-1;best=(n+1,float('inf'),())
  for a in lookup[i]:
   if a&m!=a:continue
   c,penalty,groups=solve(m^a);area=sum(nodes[j]['geom'].area for j in range(n)if a>>j&1)
   # First minimize count; among equal counts avoid tiny separate glue pieces.
   candidate=(c+1,penalty+1/max(area,1),(a,)+groups)
   if candidate[:2]<best[:2]:best=candidate
  return best
 count,penalty,groups=solve((1<<n)-1)
 partition_report.append({'tier':tier,'atomic_nodes':n,'feasible_connected_groups':len(feasible),'minimum_groups':count,'groups':[[nodes[j]['code']for j in range(n)if m>>j&1]for m in groups]})
 for k,m in enumerate(groups,1):
  original=valid(unary_union([nodes[j]['geom']for j in range(n)if m>>j&1]));assert len(ps(original))==1,(tier,k,'not physically connected')
  g=valid(original.difference(base_water))if tier==1 else original
  # Add only local base bridges if the new slot would split a monolithic part.
  if len(ps(g))>1:
   candidates=[]
   for river in river_lines:
    line=shape(river['geom'])
    segments=[line]if line.geom_type=='LineString'else list(line.geoms)
    for seg in segments:
     for s in np.arange(.5,seg.length,.65):
      center=seg.interpolate(s)
      if not original.buffer(-.03).covers(center)or not base_water.covers(center):continue
      a=seg.interpolate(max(0,s-.2));b=seg.interpolate(min(seg.length,s+.2));vx,vy=b.x-a.x,b.y-a.y;length=math.hypot(vx,vy)
      if length<1e-6:continue
      nx,ny=-vy/length,vx/length
      cross=LineString([(center.x-nx*1.2,center.y-ny*1.2),(center.x+nx*1.2,center.y+ny*1.2)])
      footprint=cross.buffer(1.1,cap_style=2).intersection(original);addition=footprint.intersection(base_water)
      if addition.area>.01:candidates.append((addition.area,center,footprint,river['name']))
   while len(ps(g))>1:
    before=len(ps(g));chosen=None
    for area,pt,footprint,name in sorted(candidates,key=lambda q:q[0]):
     nextg=valid(g.union(footprint))
     if len(ps(nextg))<before:chosen=(nextg,pt,footprint,name);break
    if chosen is None:raise RuntimeError(('Cannot reconnect base part with local river bridge',tier,k,before))
    nextg,pt,fp,name=chosen;added=nextg.difference(g);bridges.append({'tier':tier,'part':f'L{tier:02d}_P{k:03d}','river':name,'width_mm':2.2,'point':[pt.x,pt.y],'footprint':mapping(fp),'restored_wood':mapping(added),'area_mm2':added.area});g=nextg
  assert len(ps(g))==1 and g.is_valid
  codes=[c for c,mask in S['layer_country_masks'][tier-1].items()if g.intersection(shape(mask)).area>.005]
  parts.append({'id':f'L{tier:02d}_P{k:03d}','tier':tier,'geom':mapping(g),'regions':codes,'area_mm2':g.area})
 print('OPTIMAL PARTITION',tier,count,partition_report[-1]['groups'],flush=True)

layers=[unary_union([shape(r['geom'])for r in parts if r['tier']==i+1])for i in range(3)]
vis=[layers[i].difference(layers[i+1])if i<2 else layers[i]for i in range(3)]
for row in parts:
 g=shape(row['geom']);tier=row['tier'];exposed=valid(g.intersection(vis[tier-1]));upper=layers[tier]if tier<3 else Polygon();paint={}
 for coat in S['colors']:
  mask=unary_union([valid(shape(S['layer_country_masks'][tier-1].get(c,mapping(Polygon()))))for c in S['country_names']if S['country_coat'][c]==coat]);v=valid(mask.intersection(exposed,grid_size=.000001))
  if v.area>.0001:
   bleed=valid(v.buffer(2).intersection(upper,grid_size=.000001));bleed=valid(bleed.intersection(g,grid_size=.000001))
   paint[coat]={'visible':mapping(v),'with_overlap':mapping(valid(v.union(bleed))),'paint':coat!='NATURAL'}
 for i,(coat,mask)in enumerate(paint.items()):
  a=shape(mask['visible']).buffer(-.02)
  for c,bmask in list(paint.items())[:i]:
   b=shape(bmask['visible']).buffer(-.02);assert a.is_empty or b.is_empty or a.distance(b)>=.75-1e-5,(row['id'],coat,c,'visible paint contact')
 row.update({'visible':mapping(exposed),'paint':paint,'engraving':mapping(Polygon())})
for i in [1,2]:assert layers[i].symmetric_difference(shape(S['layers'][i])).area<.0001
assert layers[0].difference(base).area<.0001
actual_water=base.difference(layers[0]);assert actual_water.difference(base_water.buffer(.000001)).area<.0001
D.update({'pieces':parts,'layers':[mapping(g)for g in layers],'visible':[mapping(g)for g in vis],'summary':[{'tier':i+1,'pieces':sum(r['tier']==i+1 for r in parts)}for i in range(3)],'river_lines':river_lines,'base_water_union':mapping(actual_water),'river_bridges':bridges,'optimization':partition_report})
D['original_raw_height_field_error_before_river_slots_mm2']=D.pop('source_height_field_error_mm2',None)
D['height_field_changes_vs_approved_mm2']=[layers[i].symmetric_difference(shape(S['layers'][i])).area for i in range(3)]
D['layer_country_masks']=[{c:mapping(shape(g).intersection(layers[i],grid_size=.000001))for c,g in masks.items()}for i,masks in enumerate(S['layer_country_masks'])]
labels=[]
for a in S['labels']:
 if a.get('kind')!='country':continue
 bb=box(*shape(a['geometry']).bounds);matches=[r for r in parts if r['tier']==a['tier']and shape(r['visible']).buffer(.00001).covers(bb)]
 assert matches,(a['text'],'country title cut by base river')
 labels.append({**a,'piece':matches[0]['id']})
D['labels']=labels;D['city_markers']=[]
(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False))
(P/'data/water-reference.json').write_text(json.dumps([{'name':'Оргстекло — реки, справочно','geom':mapping(base_water)}],ensure_ascii=False))
(P/'Проверка-плана.json').write_text(json.dumps({'passed':True,'before_parts':len(S['pieces']),'after_parts':len(parts),'layers':D['summary'],'connected_partition_exact_within_existing_country_atoms':partition_report,'base_river_cut_area_mm2':actual_water.area,'river_bridge_count':len(bridges),'river_bridges':bridges,'approved_upper_plies_unchanged':True,'all_parts_single_connected_polygon':True,'painting_conflicts':0},ensure_ascii=False,indent=2))
print('PLAN DONE',len(parts),'parts',len(bridges),'bridges','base water area',actual_water.area,flush=True)
