"""Use full lake holes for audit and acrylic rendering, rather than their shoreline bands."""
import json
from pathlib import Path
from shapely.geometry import shape,mapping,Polygon
from shapely.ops import unary_union
P=Path(__file__).resolve().parent.parent
for O in sorted(q for q in P.iterdir()if q.is_dir()and q.name[:2]in ['01','02']):
 D=json.load(open(O/'data/production-plan.json'));oldledge=shape(D['water_upper_union']).difference(shape(D['water_base_union']));bb=unary_union([shape(g)for g in D['base_water'].values()]);ub=unary_union([shape(g)for g in D['upper_water'].values()]);newledge=ub.difference(bb);allwood=unary_union([shape(g)for g in D['layers']]);effect=oldledge.symmetric_difference(newledge).intersection(allwood).area;assert effect<.03,(O.name,effect)
 D['water_base_union']=mapping(bb);D['water_upper_union']=mapping(ub);(O/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));g=shape(D['layers'][0]).buffer(1.2);pp=list(g.geoms)if hasattr(g,'geoms')else[g];envelope=unary_union([Polygon(q.exterior)for q in pp]);ref=bb.intersection(envelope);(O/'data/water-reference.json').write_text(json.dumps([{'name':'Оргстекло под всеми речными и озёрными отверстиями — справочно','geom':mapping(ref)}],ensure_ascii=False));print('FULL WATER ENVELOPES',O.name,'engraving material impact mm2',effect,flush=True)
