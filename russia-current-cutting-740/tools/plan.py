"""Smooth the user's actual height field, add stepped water and minimize part count."""
import json,math
from pathlib import Path
from collections import Counter
from shapely.geometry import shape,mapping,Polygon,LineString,Point,box
from shapely.ops import unary_union,polylabel,nearest_points,linemerge
from shapely.affinity import rotate,scale
from shapely import make_valid,set_precision,coverage_simplify
P=Path(__file__).resolve().parent.parent;R=json.load(open(P/'data/source/extracted.json'));W=[q for q in R if q['kind']=='wood'];C=json.load(open(P/'data/parameters.json'));NAMES=json.load(open(P/'data/source/region-names.json'));WREF={k:shape(v)for k,v in json.load(open(P/'data/source/water-reference.json')).items()};CANON=shape(json.load(open(P/'data/source/coast-reference.json')));report=[]
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty and g.area>1e-7 else[]
 return[p for a in getattr(g,'geoms',[])for p in ps(a)]
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[g]if not g.is_empty else[]
 return[p for a in getattr(g,'geoms',[])for p in lines(a)]
def valid(g):return set_precision(unary_union(ps(make_valid(g))),.001)
def fill_micro(g,minimum=1,exclude=None):
 result=[]
 for p in ps(g):
  holes=[]
  for ring in p.interiors:
   h=Polygon(ring)
   if h.area<minimum or exclude is not None and h.intersection(exclude).area>.6*h.area:continue
   holes.append(ring.coords)
  result.append(Polygon(p.exterior.coords,holes))
 return valid(unary_union(result))
def smooth(g):
 g=fill_micro(g,.4,WREF['Ладожское'].union(WREF['Онежское']));g=g.simplify(C['smoothing_simplify_mm'],preserve_topology=True);r=C['smoothing_closing_mm'];s=C['smoothing_opening_mm'];q=C['smoothing_arc_segments_per_quadrant'];g=g.buffer(r,quad_segs=q).buffer(-r,quad_segs=q).buffer(-s,quad_segs=q).buffer(s,quad_segs=q);return valid(g)
def vertices(g):return sum(len(r.coords)for p in ps(g)for r in [p.exterior,*p.interiors])
raw=[valid(unary_union([shape(q['geom'])for q in W if q['hi_mm']>=3*t-.05]))for t in [1,2,3]]
L=[smooth(g)for g in raw]
# Keep the four levels nested; small smoothing displacements cannot leave floating plywood.
for i in [1,0]:L[i]=valid(L[i].union(L[i+1]))
land=L[0];allOldWater=unary_union(list(WREF.values()));river_names=[k for k in WREF if k not in ['Байкал','Таймыр','Ладожское','Онежское','Телецкое']];upperwater={};basewater={}
# Current upper cut profiles are retained and rounded; lower slots are approximately half width.
for name in river_names:
 g=WREF[name].simplify(.045,preserve_topology=True).buffer(.03,quad_segs=6).buffer(-.03,quad_segs=6)
 # Extend old outlets by fractions of a millimetre if smoothing moved the coastline.
 coast=CANON.boundary.intersection(g.buffer(.015));extra=[]
 width=1.8 if name in ['Обь','Енисей','Лена']else 1.6
 for segment in lines(coast):
  if segment.length<.1:continue
  mid=segment.interpolate(.5,normalized=True);near=nearest_points(mid,land.boundary)[1]
  if mid.distance(near)<1.2:extra.append(LineString([mid,near]).buffer(width/2,quad_segs=6))
 g=valid(unary_union([g,*extra]).intersection(land));narrow=valid(g.buffer(-width/4,quad_segs=6));mouths=land.boundary.intersection(g.buffer(.002));ext=[]
 for segment in lines(mouths):
  if segment.length<.1:continue
  mid=segment.interpolate(.5,normalized=True);near=nearest_points(mid,narrow)[1]
  if mid.distance(near)<1.8:ext.append(LineString([near,mid]).buffer(width/4,quad_segs=6).intersection(g))
 narrow=valid(unary_union([narrow,*ext]).intersection(g));upperwater[name]=mapping(g);basewater[name]=mapping(narrow);report.append({'feature':name,'type':'river','upper_nominal_width_mm':width,'lower_nominal_width_mm':width/2,'lower_is_subset_of_upper':narrow.difference(g).area<.001})
for name in C['required_lakes']:
 g=smooth(WREF[name]).intersection(land);rect=list(g.minimum_rotated_rectangle.exterior.coords);_,a,b=max((math.dist(a,b),a,b)for a,b in zip(rect,rect[1:]));angle=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]));center=g.centroid;narrow=rotate(scale(rotate(g,-angle,origin=center),xfact=1,yfact=C['lake_first_layer_width_factor'],origin=center),angle,origin=center).intersection(g.buffer(-.15));narrow=valid(unary_union(sorted(ps(narrow),key=lambda q:-q.area)[:1]));upperwater[name]=mapping(g);basewater[name]=mapping(narrow);report.append({'feature':name,'type':'lake','lower_width_factor':C['lake_first_layer_width_factor'],'lower_is_subset_of_upper':narrow.difference(g).area<.001})
UB=valid(unary_union([shape(g)for g in upperwater.values()]));BB=valid(unary_union([shape(g)for g in basewater.values()]));assert BB.difference(UB.buffer(.0001)).area<.001
# Layer 1 has narrow through-water; layer 2 and above open to the wider bank profile.
L=[valid(g.difference(BB if i==0 else UB))for i,g in enumerate(L)]
# Tiny water-isolated delta specks are omitted rather than supplied as loose glue dots.
for i in range(3):
 minimum=C['minimum_base_island_area_mm2']if i==0 else C['minimum_upper_component_area_mm2'];kept=[]
 for q in ps(L[i]):
  if q.area>=minimum:kept.append(q)
  else:report.append({'feature':'tiny isolated relief/delta component','tier':i+1,'removed_area_mm2':q.area})
 L[i]=valid(unary_union(kept))
for i in [1,2]:L[i]=valid(L[i].intersection(L[i-1]))
# Regional coverage is used for labels, border engraving and inconspicuous stock-size seams.
regions={};occupied=Polygon()
for code in sorted(NAMES):
 g=valid(unary_union([shape(q['geom'])for q in W if q['region']==code]));g=fill_micro(g,.3).buffer(.01,quad_segs=4).intersection(land).difference(occupied);regions[code]=valid(g);occupied=occupied.union(g)
for q in ps(land.difference(occupied)):
 code=min(regions,key=lambda c:regions[c].distance(q.representative_point()));regions[code]=valid(regions[code].union(q))
# Simplify shared borders consistently, then round individual shared chains while holding junctions.
regioncodes=list(regions)
try:
 cov=coverage_simplify([regions[c]for c in regioncodes],.32,simplify_boundary=False);regions={c:valid(g)for c,g in zip(regioncodes,cov)}
except Exception:pass
network=unary_union([g.boundary for g in regions.values()]);network=linemerge(network)if network.geom_type=='MultiLineString'else network;chains=lines(network);rounded=[]
for line in chains:
 line=line.simplify(.28,preserve_topology=True);coords=list(line.coords)
 if len(coords)<3:rounded.append(line);continue
 for iteration in range(2):
  out=[coords[0]]
  for a,b in zip(coords,coords[1:]):out.extend([(a[0]*.75+b[0]*.25,a[1]*.75+b[1]*.25),(a[0]*.25+b[0]*.75,a[1]*.25+b[1]*.75)])
  out.append(coords[-1]);coords=out
 rounded.append(LineString(coords))
network=unary_union(rounded)
# A mainland wider than the bed is divided along existing regional outlines.
pieces=[];seams=[]
for i,g in enumerate(L):
 pending=list(ps(g));out=[]
 while pending:
  part=pending.pop();x0,y0,x1,y1=part.bounds
  if x1-x0<=C['maximum_part_extent_mm']and y1-y0<=C['maximum_part_extent_mm']:out.append(part);continue
  # Choose a broad east/west regional division close to the middle of the continent.
  candidates=[]
  for cutx in [(x0+x1)/2,x0+200,x0+280,x0+380]:
   leftcodes=[c for c,r in regions.items()if r.centroid.x<cutx];leftmask=unary_union([regions[c]for c in leftcodes]);a=valid(part.intersection(leftmask));b=valid(part.difference(leftmask))
   if a.area<1000 or b.area<1000:continue
   aa=ps(a)+ps(b)
   if all(q.bounds[2]-q.bounds[0]<=725 and q.bounds[3]-q.bounds[1]<=725 for q in aa):
    seam=a.boundary.intersection(b.boundary.buffer(.002));upper=L[i+1]if i<2 else Polygon();visible_length=seam.difference(upper.buffer(-.2)).length;candidates.append((visible_length+len(aa)*10,aa,seam))
  if not candidates:
   cutx=(x0+x1)/2;a=valid(part.intersection(box(x0-1,y0-1,cutx,y1+1)));b=valid(part.difference(a));candidates=[(0,ps(a)+ps(b),a.boundary.intersection(b.boundary))]
  _,parts,seam=min(candidates,key=lambda q:q[0]);pending.extend(parts);seams.append({'tier':i+1,'geom':mapping(seam)})
 for j,part in enumerate(sorted(out,key=lambda q:-q.area),1):
  id=f'L{i+1:02d}_P{j:03d}';visible=valid(part.difference(L[i+1]))if i<2 else part;codes=[c for c,r in regions.items()if r.intersection(part).area>1];pieces.append({'id':id,'tier':i+1,'geom':mapping(part),'visible':mapping(visible),'regions':codes,'paint':{},'engraving':mapping(Polygon()),'area_mm2':part.area})
summary=[{'tier':i+1,'pieces':sum(q['tier']==i+1 for q in pieces),'raw_vertices':vertices(raw[i]),'smoothed_vertices':vertices(L[i]),'raw_perimeter_mm':raw[i].length,'smoothed_perimeter_mm':L[i].length}for i in range(3)]
D={'layers':[mapping(g)for g in L],'visible':[mapping(valid(g.difference(L[i+1])))if i<2 else mapping(g)for i,g in enumerate(L)],'pieces':pieces,'regions':{c:mapping(g)for c,g in regions.items()},'region_names':NAMES,'political_network':mapping(network),'upper_water':upperwater,'base_water':basewater,'water_upper_union':mapping(UB),'water_base_union':mapping(BB),'water_steps':report,'stock_seams':seams,'colors':{'NATURAL':[.72,.59,.40]},'summary':summary,'ply_mm':3,'levels_mm':[3,6,9],'parameters':C}
(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));(P/'Проверка-сглаживания-и-воды.json').write_text(json.dumps({'layers':summary,'water_steps':report,'required_lakes':['Байкал','Таймыр'],'no_new_karelian_lake_cuts':True,'physical_parts':len(pieces),'stock_seams':len(seams),'smoothing_parameters':C},ensure_ascii=False,indent=2));print('PLAN',summary,'PARTS',len(pieces),'SEAMS',len(seams),flush=True)
