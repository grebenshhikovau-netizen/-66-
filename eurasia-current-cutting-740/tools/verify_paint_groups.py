"""Check connected physical carriers and the requested paint separations."""
import json,csv
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely import set_precision
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));R={c:shape(g)for c,g in D['regions'].items()}
def main(country,tier):
 pp=[p for p in D['pieces']if p['tier']==tier];return max(pp,key=lambda p:shape(p['geom']).intersection(R[country]).area)
assert main('AUT',2)['id']==main('FRA',2)['id']==main('POL',2)['id']
assert main('HUN',2)['id']!=main('AUT',2)['id'];assert main('HUN',2)['paint_group']=='Венгрия'
assert main('GRC',2)['id']==main('ALB',2)['id']==main('TUR',2)['id'];assert main('GRC',2)['paint_group']=='Греция-Албания-Турция'
for tier in [2,3]:
 assert main('TKM',tier)['id']!=main('KAZ',tier)['id'];assert main('TKM',tier)['paint_group']=='Туркмения'
 assert main('LAO',tier)['id']!=main('CHN',tier)['id'];assert main('LAO',tier)['paint_group']=='Лаос'
for i,g in enumerate(D['layers']):
 pp=[shape(p['geom'])for p in D['pieces']if p['tier']==i+1];u=unary_union(pp);assert sum(q.area for q in pp)-u.area<.01;assert u.symmetric_difference(shape(g)).area<.1;assert set_precision(u,.001).symmetric_difference(set_precision(shape(g),.001)).area<.01
report={'passed':True,'Austria_France_Poland_second_ply':main('AUT',2)['id'],'Hungary_separate':main('HUN',2)['id'],'Greece_Albania_Turkey_second_ply':main('GRC',2)['id'],'Turkmenistan_separate_from_Kazakhstan':[main('TKM',i)['id']for i in [2,3]],'Laos_separate_from_China':[main('LAO',i)['id']for i in [2,3]],'shared_seams_valid_on_0_001mm_precision_grid':True,'max_float_union_difference_mm2':.1,'parts':[{'id':p['id'],'tier':p['tier'],'paint_group':p['paint_group'],'area_mm2':p['area_mm2']}for p in D['pieces']]}
(P/'Проверка-групп-покраски.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
with (P/'Группы-покраски.csv').open('w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f);w.writerow(['Деталь','Слой','Группа','Площадь мм²']);w.writerows([p['id'],p['tier'],p['paint_group'],round(p['area_mm2'],2)]for p in D['pieces'])
print('PAINT RULES VERIFIED',len(D['pieces']),flush=True)
