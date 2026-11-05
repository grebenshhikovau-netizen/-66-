"""Visible country borders and immediate next-ply guides for the new physical parts."""
import json
from pathlib import Path
from shapely.geometry import shape,mapping,Polygon,LineString,box
from shapely.ops import unary_union,linemerge
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'))
net=unary_union([shape(q).boundary for q in D['territories'].values()])
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[LineString(g)]if g.length>.002 else[]
 return[l for q in getattr(g,'geoms',[])for l in lines(q)]
for row in D['pieces']:
 g=shape(row['geom']);v=shape(row['visible']);ink=unary_union([shape(a['geometry'])for a in D['labels']if a['piece']==row['id']]);upperparts=[shape(r['geom'])for r in D['pieces']if r['tier']==row['tier']+1];upper=unary_union(upperparts)
 political=net.intersection(v).difference(upper.buffer(.04)).difference(g.boundary.buffer(.2)).difference(ink.buffer(.3))
 guides=unary_union([q.boundary for q in upperparts]).intersection(g.buffer(-.1)).difference(g.boundary.buffer(.2)).difference(ink.buffer(.3))if upperparts else Polygon().boundary
 red=unary_union(lines(unary_union([political,guides])))
 if red.geom_type=='MultiLineString':red=linemerge(red)
 row.update({'red_political':mapping(political),'placement_guides':mapping(guides),'red_internal':mapping(red.simplify(.001)),
             'engraving':mapping(unary_union([ink,red.buffer(.025,cap_style=2,join_style=2)]))})
(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));print('RED LINES READY',len(D['pieces']),flush=True)
