"""Restore Turkey's continuous second ply into Iran and Syria; retain the Serbian seam."""
import json
from pathlib import Path
from shapely.geometry import shape,mapping,Polygon
from shapely.ops import unary_union
from shapely import set_precision
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));before=json.loads(json.dumps(D));byid={p['id']:p for p in D['pieces']};ids=['L02_P001','L02_P006','L02_P010'];parent=byid[ids[0]]
g=set_precision(unary_union([set_precision(shape(byid[i]['geom']),.001)for i in ids]),.001)
assert g.geom_type=='Polygon'and g.is_valid,(g.geom_type,g.is_valid)
parent['geom']=mapping(g);parent['visible']=mapping(g.difference(shape(D['layers'][2])));parent['area_mm2']=g.area;parent['regions']=sorted(set(c for i in ids for c in byid[i]['regions']));parent['paint_group']='Греция-Албания-Турция и восточный массив';parent['engraving']=mapping(Polygon())
D['pieces']=[p for p in D['pieces']if p['id']not in ids[1:]]
for key in ['labels','city_markers']:
 for a in D.get(key,[]):
  if a['piece']in ids[1:]:a['piece']=ids[0]
for s in D['summary']:s['pieces']=sum(p['tier']==s['tier']for p in D['pieces'])
assert all(a==b for a,b in zip(before['layers'],D['layers']))
for p in D['pieces']:
 if p['tier']==3:assert p['geom']==next(q['geom']for q in before['pieces']if q['id']==p['id'])
D['eastern_second_ply_correction']={'merged':ids,'result':'L02_P001','third_ply_unchanged':True,'Greek_Albanian_seam_to_Serbia_retained':True}
(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));print('SECOND PLY RESTORED',len(D['pieces']),'all upper shapes unchanged',flush=True)
