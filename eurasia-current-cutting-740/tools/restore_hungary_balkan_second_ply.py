"""Join Hungary to the Balkan second-ply carrier; retain the Austrian seam."""
import json
from pathlib import Path
from shapely.geometry import shape,mapping,Polygon
from shapely.ops import unary_union
from shapely import set_precision
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));parts={p['id']:p for p in D['pieces']};a=parts['L02_P007'];b=parts['L02_P012'];before3={p['id']:p['geom']for p in D['pieces']if p['tier']==3};g=set_precision(unary_union([set_precision(shape(a['geom']),.001),set_precision(shape(b['geom']),.001)]),.001);assert g.geom_type=='Polygon'and g.is_valid
a.update({'geom':mapping(g),'area_mm2':g.area,'visible':mapping(g.difference(shape(D['layers'][2]))),'regions':sorted(set(a['regions']+b['regions'])),'paint_group':'Венгрия и балканский массив','engraving':mapping(Polygon())});D['pieces']=[p for p in D['pieces']if p['id']!='L02_P012']
for k in ['labels','city_markers']:
 for q in D.get(k,[]):
  if q['piece']=='L02_P012':q['piece']='L02_P007'
for s in D['summary']:s['pieces']=sum(p['tier']==s['tier']for p in D['pieces'])
assert before3=={p['id']:p['geom']for p in D['pieces']if p['tier']==3}
D['Hungary_second_ply_correction']={'carrier':'L02_P007','with':['ROU','SRB','BIH'],'separate_from_Austria':True,'all_third_ply_shapes_unchanged':True};(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));print('HUNGARY JOINED',len(D['pieces']),[s['pieces']for s in D['summary']])
