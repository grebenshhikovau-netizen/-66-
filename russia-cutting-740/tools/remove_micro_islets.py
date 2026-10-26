"""Omit only unsupported, unlabelled tiny river islets; keep separate real islands."""
import json
from pathlib import Path
from shapely.geometry import shape,mapping
from shapely.ops import unary_union
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));BB=shape(D['water_base_union']);UB=shape(D['water_upper_union']);removed=[];upper=shape(D['layers'][1])
for q in D['pieces']:
 if q['tier']!=1 or q['area_mm2']>=D['parameters']['small_unsupported_island_removal_mm2']:continue
 g=shape(q['geom'])
 if g.distance(BB)>.002 or g.intersection(upper).area>.001:continue
 assert not any(a['piece']==q['id']for a in D['labels']+D['city_markers']);removed.append(q)
if removed:
 ids={q['id']for q in removed};void=unary_union([shape(q['geom'])for q in removed]);D['pieces']=[q for q in D['pieces']if q['id']not in ids];D['layers'][0]=mapping(shape(D['layers'][0]).difference(void));D['visible'][0]=mapping(shape(D['visible'][0]).difference(void));D['water_base_union']=mapping(BB.union(void));D['water_upper_union']=mapping(UB.union(void));D['removed_river_islets']=[{'id':q['id'],'area_mm2':q['area_mm2'],'no_label_or_city':True,'no_upper_support':True}for q in removed]
 for s in D['summary']:s['pieces']=sum(q['tier']==s['tier']for q in D['pieces'])
 (P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));N=json.load(open(P/'data/layout.json'));N['placements']=[q for q in N['placements']if q['id']not in ids];N['part_count']=N['parts_per_kit']=len(D['pieces']);N['checks'][0]['parts']=len(D['pieces']);(P/'data/layout.json').write_text(json.dumps(N,ensure_ascii=False,indent=2));r=json.load(open(P/'Проверка-сглаживания-и-воды.json'));r['physical_parts']=len(D['pieces']);r['removed_river_islets']=D['removed_river_islets'];r['layers']=D['summary'];(P/'Проверка-сглаживания-и-воды.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));(P/'data/water-reference.json').write_text(json.dumps([{'name':'Оргстекло_под_водой_СПРАВОЧНО','geom':D['water_base_union']}],ensure_ascii=False));print('OMITTED',[(q['id'],round(q['area_mm2'],2))for q in removed],'remaining',len(D['pieces']),flush=True)
else:print('No further tiny unlabelled river islets',flush=True)
