"""Freeze source annotation identity and create actual one-stroke red lettering."""
import json,re
from pathlib import Path
from collections import defaultdict
from shapely.geometry import shape,mapping
from shapely.ops import unary_union
from shapely.affinity import scale,rotate,translate
from shapely import make_valid,set_precision
from centerlines import centerline,polys
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/source/production-plan.json'));R=json.load(open(P/'data/source/extracted.json'));groups=defaultdict(list)
BLUE={'TEXT_043':'США','TEXT_050':'Канада','TEXT_063':'Мексика','TEXT_081':'Аляска'}
for row in R:
 if row['kind']=='engraving':groups[re.sub(r'\.\d+$','',row['name'])].append(shape(row['geom']))
moves={q['source_id']:q for q in D['annotation_moves']};out=[]
for id,gg in sorted(groups.items()):
 raw=unary_union(gg);g=set_precision(set_precision(unary_union(polys(make_valid(raw))),.01),0);m=moves.get(id)
 if m:
  if 'rotation_degrees'in m:
   g=scale(raw,xfact=m['scale'],yfact=m['scale'],origin='centroid');g=rotate(g,m['rotation_degrees'],origin='centroid')
  else:g=scale(g,xfact=m['scale'],yfact=m['scale'],origin='centroid')
  g=translate(g,m['dx_mm'],m['dy_mm'])
 coverage,owner=max((shape(p['engraving']).intersection(g).area/max(g.area,1e-12),p['id'])for p in D['pieces'])
 assert coverage>.999,(id,coverage)
 ink=shape(next(q for q in D['pieces']if q['id']==owner)['engraving']);g=g.intersection(ink.buffer(.00001))
 kind='blue_fill'if id in BLUE else 'red_stroke'if id.startswith('TEXT_')else 'red_mark'
 stroke=centerline(g)if kind=='red_stroke'else None
 if stroke is not None:
  assert not stroke.is_empty,(id,'empty centerline')
  outside=stroke.difference(g.buffer(.025)).length;assert outside<.03,(id,'stroke outside glyph',outside)
 out.append({'id':id,'name':BLUE.get(id,''),'piece':owner,'kind':kind,'source_outline':mapping(g),'geometry':mapping(stroke if stroke is not None else g),'glyph_components':len(polys(g))})
 print('ANNOTATION',id,kind,owner,flush=True)
assert len(out)==158
(P/'data/annotations.json').write_text(json.dumps(out,ensure_ascii=False));print('ANNOTATIONS READY',len(out),'singleline',sum(q['kind']=='red_stroke'for q in out),flush=True)
