"""Smooth the uploaded African height field, close the rift slit and restore a solid pyramid."""
import json,math
from pathlib import Path
from shapely.geometry import shape,mapping,Polygon,LineString,Point
from shapely.ops import unary_union,nearest_points,linemerge
from shapely import make_valid,set_precision,coverage_simplify
P=Path(__file__).resolve().parent.parent;R=json.load(open(P/'data/source/extracted.json'));W=[q for q in R if q['kind']=='wood'];C=json.load(open(P/'data/parameters.json'));NAMES=json.load(open(P/'data/source/region-names.json'));REF={k:shape(v)for k,v in json.load(open(P/'data/source/country-reference.json')).items()};WR={k:shape(v)for k,v in json.load(open(P/'data/source/water-reference.json')).items()};CANON=shape(json.load(open(P/'data/source/coast-reference.json')));PYRAMID=json.load(open(P/'data/source/pyramid-reference.json'));T=[shape(g)for g in PYRAMID['terraces']];BLOCK=T[0];RIFT=shape(json.load(open(P/'data/source/rift-reference.json')));report=[]
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty and g.area>1e-7 else[]
 return[p for a in getattr(g,'geoms',[])for p in ps(a)]
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[g]if not g.is_empty else[]
 return[p for a in getattr(g,'geoms',[])for p in lines(a)]
def valid(g):return set_precision(unary_union(ps(make_valid(g))),.001)
def fill_micro(g,minimum=.6):return valid(unary_union([Polygon(p.exterior.coords,[r.coords for r in p.interiors if Polygon(r).area>=minimum])for p in ps(g)]))
def smooth(g):
 g=set_precision(fill_micro(g),0).simplify(C['smoothing_simplify_mm'],preserve_topology=True);r=C['smoothing_closing_mm'];s=C['smoothing_opening_mm'];q=C['smoothing_arc_segments_per_quadrant'];return valid(g.buffer(r,quad_segs=q).buffer(-r,quad_segs=q).buffer(-s,quad_segs=q).buffer(s,quad_segs=q).simplify(.035,preserve_topology=True))
def vertices(g):return sum(len(r.coords)for p in ps(g)for r in [p.exterior,*p.interiors])
REF={k:valid(g)for k,g in REF.items()};WR={k:valid(g)for k,g in WR.items()};T=[valid(g)for g in T];BLOCK=T[0];RIFT=valid(RIFT);CANON=valid(CANON)
raw=[valid(unary_union([shape(q['geom'])for q in W if q['hi_mm']>=t*3-.05]))for t in range(1,7)];L=[];rift_roi=unary_union([REF['KEN'],REF['ETH']]);corridor=RIFT.buffer(1.15).intersection(rift_roi);rift_fills=[]
for i,g in enumerate(raw):
 # Restore water below the solid stepped square, including its lower supports.
 g=valid(g.union(WR['Нил'].intersection(BLOCK)))if i<2 else g
 if i>=2:g=valid(g.union(T[i-2]))
 if i>=2:
  candidate=valid(set_precision(g,0).buffer(2.25,quad_segs=8).buffer(-2.25,quad_segs=8).intersection(corridor));added=candidate.difference(g);rift_fills.append({'tier':i+1,'filled_area_mm2':added.area,'geom':mapping(added)});g=g.union(candidate)
 if i==0:g=g.union(unary_union(list(WR.values())).intersection(CANON))
 L.append(smooth(g))
for i in range(4,-1,-1):L[i]=valid(L[i].union(L[i+1]))
land=L[0];upper={};lower={}
river_width={'Нил':1.65,'Конго':1.7,'Замбези':1.2,'Водопад Виктория':1.3}
for name,width in river_width.items():
 g=valid(WR[name].simplify(.04,preserve_topology=True).buffer(.025,quad_segs=6).buffer(-.025,quad_segs=6).difference(BLOCK).intersection(land));narrow=valid(set_precision(g,0).buffer(-width/4,quad_segs=6));ext=[]
 for edge in [land.boundary,BLOCK.boundary]:
  for seg in lines(edge.intersection(g.buffer(.005))):
   if seg.length<.08:continue
   mid=seg.interpolate(.5,normalized=True);near=nearest_points(mid,narrow)[1]
   if near.distance(mid)<1.5:ext.append(LineString([near,mid]).buffer(width/4,quad_segs=6).intersection(g))
 narrow=valid(unary_union([narrow,*ext]).intersection(g));upper[name]=mapping(g);lower[name]=mapping(narrow);report.append({'feature':name,'type':'river','upper_nominal_width_mm':width,'lower_nominal_width_mm':width/2})
# The long narrow rift lakes retain their length. Local width profiles are computed separately.
for name,g in WR.items():
 if name in river_width:continue
 lake=set_precision(g,0).simplify(.14,preserve_topology=True).buffer(.20,quad_segs=6).buffer(-.20,quad_segs=6).buffer(-.16,quad_segs=6).buffer(.16,quad_segs=6).simplify(.035,preserve_topology=True);lake=max(ps(lake),key=lambda q:q.area);upper[name]=mapping(valid(lake.intersection(land)));lower[name]=upper[name]
UB=valid(unary_union([shape(g)for g in upper.values()]));BB=valid(unary_union([shape(g)for g in lower.values()]));L=[valid(g.difference(BB if i==0 else UB))for i,g in enumerate(L)]
removed=[]
for i,g in enumerate(L):
 minimum=C['minimum_base_island_area_mm2']if i==0 else C['minimum_upper_component_area_mm2'];keep=[]
 for q in ps(g):
  if q.area>=minimum:keep.append(q)
  else:removed.append({'tier':i+1,'area_mm2':q.area})
 L[i]=valid(unary_union(keep))
for i in range(1,6):L[i]=valid(L[i].intersection(L[i-1]))
# Full political footprints are independent of relief/water: no artificial river edges in borders.
regions={};occupied=Polygon()
for code in sorted(NAMES):
 g=valid(REF[code].intersection(land).difference(occupied));regions[code]=g;occupied=occupied.union(g)
for q in ps(land.difference(occupied)):
 code=min(regions,key=lambda c:regions[c].distance(q.representative_point()));regions[code]=valid(regions[code].union(q))
codes=list(regions)
try:
 cov=coverage_simplify([regions[c]for c in codes],.30,simplify_boundary=False);regions={c:valid(g)for c,g in zip(codes,cov)}
except Exception:pass
net=unary_union([g.boundary for g in regions.values()]);net=linemerge(net)if net.geom_type=='MultiLineString'else net;rounded=[]
for line in lines(net):
 coords=list(line.simplify(.25).coords)
 for iteration in range(2):
  if len(coords)<3:break
  cc=[coords[0]]
  for a,b in zip(coords,coords[1:]):cc.extend([(a[0]*.75+b[0]*.25,a[1]*.75+b[1]*.25),(a[0]*.25+b[0]*.75,a[1]*.25+b[1]*.75)])
  cc.append(coords[-1]);coords=cc
 rounded.append(LineString(coords))
network=unary_union(rounded);pieces=[]
for i,g in enumerate(L):
 for j,part in enumerate(sorted(ps(g),key=lambda q:-q.area),1):
  assert max(part.bounds[2]-part.bounds[0],part.bounds[3]-part.bounds[1])<725
  visible=valid(part.difference(L[i+1]))if i<5 else part;pieces.append({'id':f'L{i+1:02d}_P{j:03d}','tier':i+1,'geom':mapping(part),'visible':mapping(visible),'regions':[c for c,r in regions.items()if r.intersection(part).area>1],'paint':{},'engraving':mapping(Polygon()),'area_mm2':part.area})
summary=[{'tier':i+1,'pieces':sum(q['tier']==i+1 for q in pieces),'raw_vertices':vertices(raw[i]),'smoothed_vertices':vertices(L[i]),'raw_perimeter_mm':raw[i].length,'smoothed_perimeter_mm':L[i].length}for i in range(6)]
D={'layers':[mapping(g)for g in L],'visible':[mapping(valid(g.difference(L[i+1])))if i<5 else mapping(g)for i,g in enumerate(L)],'pieces':pieces,'regions':{c:mapping(g)for c,g in regions.items()},'region_names':NAMES,'political_network':mapping(network),'network_smoothing_version':'shared_chains_chaikin_2','upper_water':upper,'base_water':lower,'water_upper_union':mapping(UB),'water_base_union':mapping(BB),'water_steps':report,'rift_fills':rift_fills,'rift_repair_corridor':mapping(corridor),'pyramid_block':mapping(BLOCK),'pyramid_terraces':[mapping(g)for g in T],'stock_seams':[],'colors':{'NATURAL':[.72,.59,.40]},'summary':summary,'ply_mm':3,'levels_mm':[3,6,9,12,15,18],'parameters':C,'removed_micro_parts':removed}
(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));(P/'Проверка-сглаживания-и-воды.json').write_text(json.dumps({'layers':summary,'water_steps':report,'physical_parts':len(pieces),'rift_fills':[{'tier':q['tier'],'filled_area_mm2':q['filled_area_mm2']}for q in rift_fills],'pyramid_solid':True,'removed_micro_parts':removed,'parameters':C},ensure_ascii=False,indent=2));print('PLAN',summary,'PARTS',len(pieces),'RIFT FILL',[q['filled_area_mm2']for q in rift_fills],flush=True)
