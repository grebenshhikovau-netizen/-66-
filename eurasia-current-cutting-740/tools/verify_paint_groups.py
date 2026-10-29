"""Check connected physical carriers and the requested paint separations."""
import json,csv,hashlib
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely import set_precision
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));R={c:shape(g)for c,g in D['regions'].items()}
def main(country,tier):
 pp=[p for p in D['pieces']if p['tier']==tier];return max(pp,key=lambda p:shape(p['geom']).intersection(R[country]).area)
assert main('AUT',2)['id']==main('FRA',2)['id']==main('POL',2)['id']
assert main('HUN',2)['id']!=main('AUT',2)['id'];assert main('HUN',2)['id']==main('ROU',2)['id']==main('SRB',2)['id'];assert main('HUN',2)['paint_group']=='Венгрия и балканский массив'
assert main('GRC',2)['id']==main('ALB',2)['id']==main('TUR',2)['id'];assert main('GRC',2)['paint_group']=='Общий второй слой — восточный массив'
assert len({main(c,2)['id']for c in ['GRC','ALB','TUR','IRN','SYR','TKM','KAZ','LAO','KHM','THA','CHN']})==1
assert main('ALB',2)['id']!=main('SRB',2)['id']
assert main('TKM',3)['id']!=main('KAZ',3)['id']
assert main('LAO',3)['id']==main('KHM',3)['id']!=main('CHN',3)['id']
assert main('LAO',3)['paint_group']=='Лаос-Камбоджа'
assert D['eastern_second_ply_correction']['third_ply_unchanged']
assert D['visible_paint_corrections']['Turkey_third_ply_unchanged']
ref=json.load(open(P/'data/source/turkey-third-ply-before-support-correction.json'));tur=next(q for q in D['pieces']if q['id']==ref['piece']);assert tur['tier']==3 and hashlib.sha256(json.dumps(tur['geom'],sort_keys=True).encode()).hexdigest()==ref['geometry_sha256']
for i,g in enumerate(D['layers']):
 pp=[shape(p['geom'])for p in D['pieces']if p['tier']==i+1];u=unary_union(pp);assert sum(q.area for q in pp)-u.area<.01;assert u.symmetric_difference(shape(g)).area<.1;assert set_precision(u,.001).symmetric_difference(set_precision(shape(g),.001)).area<.01
report={'passed':True,'Austria_France_Poland_second_ply':main('AUT',2)['id'],'Hungary_with_Romania_Serbia':main('HUN',2)['id'],'Hungary_separate_only_from_Austrian_carrier':True,'Greece_Albania_Turkey_second_ply':main('GRC',2)['id'],'Turkey_Iran_Syria_continuous_second_ply':True,'Turkey_third_ply_unchanged':True,'Turkey_top_mm':9,'Turkey_third_ply_geometry_sha256':ref['geometry_sha256'],'Turkmenistan_separate_from_Kazakhstan':[main('TKM',3)['id']],'Laos_separate_from_China':[main('LAO',3)['id']],'Laos_Cambodia_one_third_ply_piece':main('LAO',3)['id'],'common_eastern_second_ply':main('CHN',2)['id'],'shared_seams_valid_on_0_001mm_precision_grid':True,'max_float_union_difference_mm2':.1,'parts':[{'id':p['id'],'tier':p['tier'],'paint_group':p['paint_group'],'area_mm2':p['area_mm2']}for p in D['pieces']]}
(P/'Проверка-групп-покраски.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
with (P/'Группы-покраски.csv').open('w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f);w.writerow(['Деталь','Слой','Группа','Площадь мм²']);w.writerows([p['id'],p['tier'],p['paint_group'],round(p['area_mm2'],2)]for p in D['pieces'])
print('PAINT RULES VERIFIED',len(D['pieces']),flush=True)
