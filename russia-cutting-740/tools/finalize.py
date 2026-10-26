import json
from pathlib import Path
from shapely.geometry import shape,Polygon,LineString,mapping
from shapely.ops import unary_union,linemerge
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'))
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[g]if not g.is_empty and g.length>1e-6 else[]
 return[p for a in getattr(g,'geoms',[])for p in lines(a)]
network=shape(D['political_network'])
if not D.get('network_smoothing_version'):
 merged=linemerge(network)if network.geom_type=='MultiLineString'else network;rr=[]
 for g in lines(merged):
  coords=list(g.simplify(.25).coords)
  for iteration in range(2):
   if len(coords)<3:break
   out=[coords[0]]
   for a,b in zip(coords,coords[1:]):out.extend([(a[0]*.75+b[0]*.25,a[1]*.75+b[1]*.25),(a[0]*.25+b[0]*.75,a[1]*.25+b[1]*.75)])
   out.append(coords[-1]);coords=out
  rr.append(LineString(coords))
 network=unary_union(rr);D['political_network']=mapping(network);D['network_smoothing_version']='shared_chains_chaikin_2'
sources=json.load(open(P/'data/source/extracted.json'));craters={}
for tier in [1,2,3,4]:
 craters[tier]=unary_union([shape(q['recess'])for q in sources if q.get('kind')=='wood'and not shape(q['recess']).is_empty and abs(q['hi_mm']-tier*3)<.05])
labelboxes=unary_union([shape(q['bbox']).buffer(.18)for q in D['labels']]);markerMask=unary_union([shape(q['geom']).buffer(.08)for q in D['city_markers']]);leaders=unary_union([shape(q['leader'])for q in D['labels']if q.get('leader')])
for row in D['pieces']:
 g=shape(row['geom']);visible=shape(row['visible']);uppers=[shape(q['geom'])for q in D['pieces']if q['tier']==row['tier']+1];upper=unary_union(uppers);upper=upper if not upper.is_empty else Polygon();political=network.intersection(visible).difference(upper.buffer(.04)).difference(g.boundary.buffer(.28)).difference(labelboxes).difference(markerMask);guide=unary_union([q.boundary for q in uppers]).intersection(g.buffer(-.12)).difference(g.boundary.buffer(.22)).difference(labelboxes)if uppers else Polygon().boundary;leader=leaders.intersection(visible).difference(labelboxes).difference(markerMask).difference(g.boundary.buffer(.15));recess=craters[row['tier']].boundary.intersection(visible).difference(labelboxes).difference(g.boundary.buffer(.15))if not craters[row['tier']].is_empty else Polygon().boundary;row['source_recess_engraving']=mapping(recess);red=unary_union(lines(unary_union([political,guide,leader,recess])))
 if red.geom_type=='MultiLineString':red=linemerge(red)
 row['red_political']=mapping(political);row['placement_guides']=mapping(guide);row['red_leaders']=mapping(leader);row['red_internal']=mapping(red.simplify(.001));ink=unary_union([shape(q['geometry'])for q in D['labels']if q['piece']==row['id']]+[shape(q['geom'])for q in D['city_markers']if q['piece']==row['id']]);row['engraving']=mapping(ink.union(red.buffer(.022,cap_style=2,join_style=2)).intersection(g))
 assert political.intersection(upper.buffer(-.001)).length<.001
D['source_existing_region_labels']=37;D['source_region_aliases']=D['label_notes'];D['no_paint_separation']=True;(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));print('FINALIZED',len(D['pieces']),len(D['labels']),len(D['city_markers']),flush=True)
