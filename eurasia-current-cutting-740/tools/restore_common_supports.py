"""Keep common supporting plies; separate only the visible third-ply paint pieces."""
import json
from pathlib import Path
from shapely.geometry import shape,mapping,Polygon
from shapely.ops import unary_union
from shapely import set_precision
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));original=json.loads(json.dumps(D))
def merge(ids,name):
 by={p['id']:p for p in D['pieces']};parent=by[ids[0]];g=set_precision(unary_union([set_precision(shape(by[k]['geom']),.001)for k in ids]),.001);assert g.geom_type=='Polygon'and g.is_valid,(ids,g.geom_type)
 parent.update({'geom':mapping(g),'area_mm2':g.area,'visible':mapping(g.difference(shape(D['layers'][parent['tier']]))if parent['tier']<len(D['layers'])else g),'regions':sorted(set(c for k in ids for c in by[k]['regions'])),'paint_group':name,'engraving':mapping(Polygon())})
 D['pieces']=[p for p in D['pieces']if p['id']not in ids[1:]]
 for key in ['labels','city_markers']:
  for a in D.get(key,[]):
   if a['piece']in ids[1:]:a['piece']=ids[0]
merge(['L02_P001','L02_P002','L02_P008','L02_P009','L02_P011'],'Общий второй слой — восточный массив')
merge(['L03_P014','L03_P015'],'Лаос-Камбоджа')
for s in D['summary']:s['pieces']=sum(p['tier']==s['tier']for p in D['pieces'])
assert D['layers']==original['layers']
old=next(p for p in original['pieces']if p['id']=='L03_P005');assert old['geom']==next(p for p in D['pieces']if p['id']=='L03_P005')['geom']
D['visible_paint_corrections']={'common_second_ply':['TUR','IRN','SYR','TKM','KAZ','LAO','KHM','THA','CHN'],'third_ply_Laos_Cambodia_one_part':'L03_P014','third_ply_Turkmenistan_separate':True,'Turkey_third_ply_unchanged':True};(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));print('CORRECTED',len(D['pieces']),[s['pieces']for s in D['summary']])
