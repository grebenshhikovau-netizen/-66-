"""Union the uploaded height field; join only paint-compatible adjacent territories."""
import json,math
from pathlib import Path
from collections import defaultdict,Counter
from shapely.geometry import Polygon,Point,shape,mapping
from shapely.ops import unary_union,polylabel
from shapely import make_valid,set_precision
P=Path(__file__).resolve().parent.parent;R=json.load(open(P/'data/source/extracted.json'));wood=[q for q in R if q['kind']=='wood'];GRID=.001;BLEED=2;PAINT_GAP=.75
NAMES={'BRA':'БРАЗИЛИЯ','ARG':'АРГЕНТИНА','CHL':'ЧИЛИ','BOL':'БОЛИВИЯ','PER':'ПЕРУ','COL':'КОЛУМБИЯ','VEN':'ВЕНЕСУЭЛА','ECU':'ЭКВАДОР','PRY':'ПАРАГВАЙ','URY':'УРУГВАЙ','GUY':'ГАЙАНА','SUR':'СУРИНАМ','GUF':'ФРАНЦУЗСКАЯ ГВИАНА'}
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty and g.area>1e-9 else[]
 return[p for a in getattr(g,'geoms',[])for p in ps(a)]
def valid(g):return unary_union(ps(make_valid(g)))
rawcountries={c:valid(unary_union([shape(q['geom'])for q in wood if q['country']==c]))for c in NAMES};network=unary_union([g.boundary for g in rawcountries.values()]);repairs=[]
def repair(g,tier):
 filled=[]
 for p in ps(g):
  holes=[]
  for ring in p.interiors:
   h=Polygon(ring);center=polylabel(h,tolerance=.0005)
   if center.distance(h.boundary)<.02:repairs.append({'tier':tier,'type':'parasitic_seam_hole','area_mm2':h.area,'bounds':h.bounds})
   else:holes.append(ring.coords)
  filled.append(Polygon(p.exterior.coords,holes))
 new=unary_union(filled);closed=new.buffer(.004,quad_segs=4).buffer(-.004,quad_segs=4).union(new);extra=closed.difference(new).intersection(network.buffer(.02))
 if extra.area>1e-7:repairs.append({'tier':tier,'type':'open_seam_slits','area_mm2':extra.area})
 return valid(new.union(extra))
rawL=[valid(unary_union([shape(q['geom'])for q in wood if q['hi_mm']>=3*t-.05]))for t in [1,2,3]];L=[repair(g,i+1)for i,g in enumerate(rawL)]
# Full source coastline is preserved; shared country edges are partitioned once.
base=L[0];territories={};occupied=Polygon()
for c,g in sorted(rawcountries.items()):
 part=g.buffer(.004,quad_segs=4).intersection(base).difference(occupied);territories[c]=valid(part);occupied=occupied.union(part)
missing=base.difference(occupied)
for patch in ps(missing):
 owner=min(territories,key=lambda c:territories[c].distance(patch.representative_point()));territories[owner]=territories[owner].union(patch)
for i in [2,1]:L[i-1]=valid(L[i-1].union(L[i]))
# Resolve any sub-grid perturbations at the coastline without inventing islands.
base=L[0];coverage=unary_union(list(territories.values()));missing=base.difference(coverage)
for patch in ps(missing):
 owner=min(territories,key=lambda c:territories[c].distance(patch.representative_point()));territories[owner]=valid(territories[owner].union(patch))
# Partition every actual height separately. Legacy flat objects were stretched
# by the user; source Tier properties must not invent material at another height.
layer_countries=[]
for i,layer in enumerate(L):
 masks={};occupied=Polygon()
 for c in sorted(NAMES):
  raw=valid(unary_union([shape(q['geom'])for q in wood if q['country']==c and q['hi_mm']>=3*(i+1)-.05]))
  if raw.is_empty:continue
  part=valid(raw.buffer(.004,quad_segs=4).intersection(layer).difference(occupied));masks[c]=part;occupied=occupied.union(part)
 for patch in ps(layer.difference(occupied)):
  owner=min(masks,key=lambda c:masks[c].distance(patch.representative_point()));masks[owner]=valid(masks[owner].union(patch))
 layer_countries.append(masks)
territories=layer_countries[0]
colors={};country_coat={};country_colors={}
for c in NAMES:
 rows=[q for q in wood if q['country']==c];col=rows[0]['color_linear'];assert all(max(abs(a-b)for a,b in zip(col,q['color_linear']))<1e-5 for q in rows),(c,'varying source color')
 country_colors[c]=col;match=next((k for k,v in colors.items()if max(abs(a-b)for a,b in zip(col,v))<1e-5),None)
 if match is None:match='NATURAL'if c=='BRA'else c;colors[match]=col
 country_coat[c]=match
visible=[L[i].difference(L[i+1])if i<2 else L[i]for i in range(3)];pieces=[];contacts=[];summary=[]
for i in range(3):
 upper=L[i+1]if i<2 else Polygon();nodes=[]
 for c in NAMES:
  g=layer_countries[i].get(c,Polygon())
  for component in ps(g):
   v=valid(component.intersection(visible[i]));core=v.buffer(-.02)
   nodes.append({'country':c,'g':component,'v':v,'core':core,'coat':country_coat[c]})
 forbidden=set();edges=[]
 for a,A in enumerate(nodes):
  for b,B in enumerate(nodes[:a]):
   if A['coat']!=B['coat']and not A['core'].is_empty and not B['core'].is_empty and A['core'].distance(B['core'])<PAINT_GAP:
    forbidden.add((b,a));contacts.append({'tier':i+1,'a':B['country'],'b':A['country'],'exposed_gap_mm':A['core'].distance(B['core'])})
   boundary=A['g'].boundary.intersection(B['g'].boundary.buffer(.00001));length=boundary.length
   if length>.75:edges.append((length,a,b))
 groups=[{j}for j in range(len(nodes))]
 def owner(j):return next(k for k,v in enumerate(groups)if j in v)
 for length,a,b in sorted(edges,reverse=True):
  u,v=owner(a),owner(b)
  if u==v:continue
  if any(tuple(sorted((x,y)))in forbidden for x in groups[u]for y in groups[v]):continue
  groups[u]|=groups[v];groups[v]=set()
 index=0
 for group in groups:
  if not group:continue
  g=valid(unary_union([nodes[j]['g']for j in group]))
  for part in sorted(ps(g),key=lambda q:-q.area):
   if part.area<.01:
    repairs.append({'tier':i+1,'type':'subpixel_component_omitted','area_mm2':part.area});continue
   index+=1;id=f'L{i+1:02d}_P{index:03d}';exposed=valid(part.intersection(visible[i]));paints={};regions=[]
   for j in group:
    node=nodes[j]
    if node['g'].intersection(part).area>.005:regions.append(node['country'])
   for coat in colors:
    countrymask=unary_union([layer_countries[i].get(c,Polygon())for c in NAMES if country_coat[c]==coat]);v=valid(countrymask.intersection(exposed))
    if v.area<.0001:continue
    expanded=valid(v.union(v.buffer(BLEED).intersection(upper).intersection(part)));paints[coat]={'visible':mapping(v),'with_overlap':mapping(expanded),'paint':coat!='NATURAL'}
   pieces.append({'id':id,'tier':i+1,'geom':mapping(part),'visible':mapping(exposed),'engraving':mapping(Polygon()),'paint':paints,'regions':sorted(set(regions)),'area_mm2':part.area})
 summary.append({'tier':i+1,'pieces':index,'paint_conflicts_separated':sum(q['tier']==i+1 for q in contacts)})
for i in range(3):
 actual=unary_union([shape(q['geom'])for q in pieces if q['tier']==i+1]);err=actual.symmetric_difference(L[i]).area;assert err<.05,(i,err);L[i]=actual
for i in [1,2]:assert L[i].difference(L[i-1].buffer(.00002)).area<.001
# Confirm every joined piece can be painted without an exposed two-color seam.
for row in pieces:
 masks=[(c,shape(v['visible']).buffer(-.02))for c,v in row['paint'].items()]
 for j,(c,a)in enumerate(masks):
  for c2,b in masks[:j]:
   assert a.is_empty or b.is_empty or a.distance(b)>=PAINT_GAP-.0001,(row['id'],'paint conflict',c,c2,a.distance(b))
D={'layers':[mapping(g)for g in L],'visible':[mapping(g)for g in visible],'pieces':pieces,'colors':colors,'country_colors':country_colors,'country_coat':country_coat,'country_names':NAMES,'territories':{c:mapping(g)for c,g in territories.items()},'layer_country_masks':[{c:mapping(g)for c,g in v.items()}for v in layer_countries],'summary':summary,'paint_overlap_mm':BLEED,'minimum_exposed_color_gap_for_join_mm':PAINT_GAP,'contact_warnings':contacts,'source_wood_objects':len(wood),'source_actual_top_levels_mm':[3,6,9],'source_labels_found':0,'source_cities_found':0,'country_labels_to_add':13,'source_geometry_rounding_mm':GRID,'repairs':repairs,'source_height_field_error_mm2':[L[i].symmetric_difference(rawL[i]).area for i in range(3)]}
(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));(P/'Проверка-плана.json').write_text(json.dumps({'layers':summary,'physical_parts':len(pieces),'paint_conflicts_separated':contacts,'source_height_field_error_mm2':D['source_height_field_error_mm2'],'subpixel_seam_repairs':len(repairs),'max_height_mm':9,'no_country_color_changes':True},ensure_ascii=False,indent=2));print('PLAN',summary,'PARTS',len(pieces),'ERROR',D['source_height_field_error_mm2'],flush=True)
