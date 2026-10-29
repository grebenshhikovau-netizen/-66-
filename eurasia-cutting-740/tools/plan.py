"""Merge the uploaded height field, smooth cut paths, and add narrow first-ply river slots."""
import json,math
from collections import Counter
from pathlib import Path
from shapely.geometry import shape,mapping,Polygon,LineString,Point
from shapely.ops import unary_union,nearest_points
from shapely import make_valid,set_precision
P=Path(__file__).resolve().parent.parent;R=json.load(open(P/'data/source/extracted.json'));W=[q for q in R if q['kind']=='wood'];C=json.load(open(P/'data/parameters.json'));META=json.load(open(P/'data/source/country-metadata.json'));REF={k:shape(v)for k,v in json.load(open(P/'data/source/region-reference.json')).items()};WR={k:shape(v)for k,v in json.load(open(P/'data/source/water-reference.json')).items()};AX={k:shape(v)for k,v in json.load(open(P/'data/source/river-axes.json')).items()};CANON=shape(json.load(open(P/'data/source/coast-reference.json')));levels=C['levels_mm']
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty and g.area>1e-7 else[]
 return[p for a in getattr(g,'geoms',[])for p in ps(a)]
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[LineString(g)]if g.length>1e-7 else[]
 return[l for a in getattr(g,'geoms',[])for l in lines(a)]
def valid(g):return set_precision(unary_union(ps(make_valid(g))),.001)
def fillmicro(g,area=.5):return valid(unary_union([Polygon(p.exterior,[r.coords for r in p.interiors if Polygon(r).area>=area])for p in ps(g)]))
def smooth(g):
 g=set_precision(fillmicro(g),0).simplify(C['smoothing_simplify_mm'],preserve_topology=True);q=C['smoothing_arc_segments_per_quadrant'];r=C['smoothing_closing_mm'];s=C['smoothing_opening_mm'];return valid(g.buffer(r,quad_segs=q).buffer(-r,quad_segs=q).buffer(-s,quad_segs=q).buffer(s,quad_segs=q).simplify(.04,preserve_topology=True))
def points(g):return sum(len(r.coords)for p in ps(g)for r in [p.exterior,*p.interiors])
raw=[valid(unary_union([shape(q['geom'])for q in W if q['hi_mm']>=z-.05]))for z in levels];L=[smooth(g)for g in raw];natural_islands=ps(fillmicro(raw[0].union(unary_union([v for k,v in WR.items()if k!='Каспийское море']).intersection(CANON))))
# Reopen the authored upper channels after smoothing, without creating channels through intact upper wood.
upper_voids=[];actual_upper_holes=[]
for i in range(1,len(L)):
 void=unary_union([v for k,v in WR.items()if k!='Каспийское море']).difference(raw[i]);restore=valid(set_precision(void,0).buffer(-.12,quad_segs=8).buffer(.12,quad_segs=8));L[i]=valid(L[i].difference(restore));upper_voids.append(restore);enclosed=unary_union([Polygon(p.exterior)for p in ps(raw[i])]);actual_upper_holes.append(valid(enclosed.intersection(restore)))
# Keep the original height stack: upper river bridges remain as the user modelled them.
for i in range(len(L)-2,-1,-1):L[i]=valid(L[i].union(L[i+1]))
land=valid(L[0].union(unary_union([v for k,v in WR.items()if k!='Каспийское море']).intersection(CANON)));basewater={};broadwater={};river_rows=[]
for name,axis in AX.items():
 # Retain every principal family in the project; no dense extra tributary meshes.
 width=.80 if name in ['Амур','Иртыш']else C['river_lower_width_mm'];g=axis.simplify(.08,preserve_topology=True).buffer(width/2,quad_segs=6);g=g.intersection(land);old=WR.get(name,axis.buffer(.675));g=g.intersection(old.buffer(.04));g=valid(g.simplify(.03,preserve_topology=True));basewater[name]=mapping(g);broadwater[name]=mapping(valid(old.intersection(land)));river_rows.append({'name':name,'lower_nominal_width_mm':width,'family_included':True,'upper_slots_preserved_where_present':True})
# Lakes already present in the source keep an inset lower opening; other lake holes are not invented.
lakes=[]
for name,v in WR.items():
 if name in AX or name=='Каспийское море':continue
 present=v.intersection(CANON).difference(raw[0]).area
 if present<.15:continue
 g=set_precision(v,0).simplify(.10,preserve_topology=True).buffer(.12,quad_segs=6).buffer(-.12,quad_segs=6);g=valid(g.intersection(land));basewater[name]=mapping(g);broadwater[name]=mapping(g);lakes.append(name)
BB=valid(unary_union([shape(g)for g in basewater.values()]));L[0]=valid(land.difference(BB));L=[valid(set_precision(g,0).buffer(-.06,quad_segs=8).buffer(.06,quad_segs=8))for g in L]
removed=[];topology_repairs=[]
# Resolve zero-width ring contacts before generating 3D solids.
for i,layer in enumerate(L):
 counts=Counter(pt for p in ps(layer)for r in [p.exterior,*p.interiors]for pt in list(r.coords)[:-1]);touches=[Point(pt)for pt,n in counts.items()if n>1]
 if touches:
  clear=unary_union([q.buffer(.08,quad_segs=8)for q in touches]);L[i]=valid(layer.difference(clear));topology_repairs.append({'tier':i+1,'points':[[q.x,q.y]for q in touches],'clearance_radius_mm':.08,'geom':mapping(clear)})
  if i==0:
   BB=valid(BB.union(clear.intersection(land)))
   for q in touches:
    name=min(basewater,key=lambda k:shape(basewater[k]).distance(q));basewater[name]=mapping(valid(shape(basewater[name]).union(q.buffer(.08,quad_segs=8).intersection(land))))
# Holes sharing an isolated vertex must become one open void, not a four-face vertical edge.
for i,layer in enumerate(L):
 for iteration in range(4):
  fixed=[];changed=False
  for part in ps(layer):
   rings=[part.exterior,*part.interiors];owners={}
   for ri,ring in enumerate(rings):
    for pt in list(ring.coords)[:-1]:owners.setdefault(pt,[]).append(ri)
   contacts={pt:rr for pt,rr in owners.items()if len(rr)>1}
   if not contacts:fixed.append(part);continue
   touched={ri for rr in contacts.values()for ri in rr if ri>0};holes=[set_precision(Polygon(ring),0).buffer(.02,quad_segs=8)if ri in touched else Polygon(ring)for ri,ring in enumerate(rings)if ri>0];new=valid(Polygon(part.exterior).difference(unary_union(holes)));cleared=part.difference(new);topology_repairs.append({'tier':i+1,'points':[list(pt)for pt in contacts],'clearance_radius_mm':.02,'geom':mapping(cleared)});fixed.extend(ps(new));changed=True
   if i==0:BB=valid(BB.union(cleared))
  layer=valid(unary_union(fixed))
  if not changed:break
 L[i]=layer
# Merge neighbouring relief across former political seams; omit nonessential tiny scraps.
for i,g in enumerate(L):
 minimum=C['minimum_base_island_area_mm2']if i==0 else C['minimum_upper_component_area_mm2'];keep=[]
 for part in ps(g):
  true_island=any(n.area<300 and part.intersection(n).area>n.area*.65 for n in natural_islands)
  covered=i+1<len(L)and part.difference(L[i+1]).area<.1
  if part.area<minimum or i==0 and part.area<20 and covered and not true_island:removed.append({'tier':i+1,'area_mm2':part.area,'covered_by_next_layer':covered,'ocean_island':true_island,'geom':mapping(part)});continue
  keep.append(part)
 L[i]=valid(set_precision(unary_union(keep),0).simplify(.02,preserve_topology=True))
# Actual geographic islands remain disconnected, never joined by artificial wooden bridges.
regions={};country_names={};country_members={}
for q in W:
 code=q['region'];country=META[code]['country'];country_names[country]=META[code]['country_name'];country_members.setdefault(country,[]).append(shape(q['geom']))
for country,gs in country_members.items():regions[country]=valid(unary_union(gs).buffer(.012,quad_segs=4).intersection(land))
# Prefer the full reference political footprint for country names and borders, independent of relief.
for country in regions:
 gg=unary_union([REF[c]for c,m in META.items()if m['country']==country]);regions[country]=valid(gg.intersection(land).union(regions[country]))
pieces=[]
for i,g in enumerate(L):
 for j,part in enumerate(sorted(ps(g),key=lambda q:-q.area),1):
  assert max(part.bounds[2]-part.bounds[0],part.bounds[3]-part.bounds[1])<=725,(i,part.bounds)
  visible=valid(part.difference(L[i+1]))if i<len(L)-1 else part;pieces.append({'id':f'L{i+1:02d}_P{j:03d}','tier':i+1,'geom':mapping(part),'visible':mapping(visible),'regions':[c for c,r in regions.items()if r.intersection(part).area>.4],'paint':{},'engraving':mapping(Polygon()),'area_mm2':part.area})
summary=[{'tier':i+1,'pieces':sum(q['tier']==i+1 for q in pieces),'raw_vertices':points(raw[i]),'smoothed_vertices':points(L[i]),'raw_perimeter_mm':raw[i].length,'smoothed_perimeter_mm':L[i].length}for i in range(len(L))];actual_upper=valid(unary_union(actual_upper_holes));bridges=[]
for i in range(1,len(L)):
 bridge=L[i].difference(L[i-1]);bridges.append({'tier':i+1,'bridge_area_mm2':bridge.area,'only_above_narrow_water_or_omitted_scraps':True})
D={'layers':[mapping(g)for g in L],'visible':[mapping(valid(g.difference(L[i+1])))if i<len(L)-1 else mapping(g)for i,g in enumerate(L)],'pieces':pieces,'regions':{k:mapping(g)for k,g in regions.items()},'region_names':country_names,'political_network':mapping(Polygon().boundary),'network_smoothing_version':'pending_shared_country_graph','upper_water':broadwater,'base_water':basewater,'water_base_union':mapping(BB),'water_upper_union':mapping(actual_upper),'water_steps':river_rows,'stock_seams':[],'colors':{'NATURAL':[.72,.59,.40]},'summary':summary,'ply_mm':3,'levels_mm':levels,'parameters':C,'removed_micro_parts':removed,'upper_water_voids_by_layer':[mapping(g)for g in upper_voids],'source_lakes_kept':lakes,'river_bridges_preserved':bridges,'source_wood_objects':len(W),'topology_repairs':topology_repairs}
(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));(P/'data/water-reference.json').write_text(json.dumps([{'name':'Оргстекло_под_реками_справочно','geom':D['water_base_union']}],ensure_ascii=False));(P/'Проверка-сглаживания-и-воды.json').write_text(json.dumps({'summary':summary,'rivers':river_rows,'lakes':lakes,'removed_micro_parts':removed,'bridges':bridges,'parameters':C,'topology_repairs':topology_repairs},ensure_ascii=False,indent=2));print('PLAN READY',summary,'TOTAL',len(pieces),'RIVERS',len(river_rows),'LAKES',lakes,flush=True)
