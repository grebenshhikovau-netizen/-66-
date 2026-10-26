"""Join the two Nevada bars to Boise–Helena in assembly coordinates, before nesting."""
from pathlib import Path
import json,copy
from shapely.geometry import shape,mapping,LineString,Polygon
from shapely.ops import unary_union
P=Path(__file__).resolve().parent.parent;f=P/'data'/'source'/'production-plan.json';backup=P/'data'/'source'/'plan-before-joining.json'
if not backup.exists():backup.write_bytes(f.read_bytes())
D=json.load(open(backup));parts={p['id']:p for p in D['pieces']};target='L03_P001';absorbed=['L03_P002','L03_P003'];old=unary_union([shape(parts[id]['geom'])for id in [target,*absorbed]])
paths=[[(751,-263),(750,-258),(749.7,-252)],[(742.4,-252.8),(749.7,-252.8)]];width=3.2;bridges=[LineString(q).buffer(width/2,quad_segs=12,join_style=1)for q in paths];new=unary_union([old,*bridges]);assert new.is_valid and new.geom_type=='Polygon'
added=new.difference(old);support=shape(D['layers'][1]);assert new.difference(support).area<.000001,'unsupported bridge';assert old.difference(new).area<.000001
for p in D['pieces']:
 if p['tier']==3 and p['id']not in [target,*absorbed]:assert shape(p['geom']).intersection(added).area<.000001,'overlaps another upper part'
root=parts[target];root['geom']=mapping(new);root['area_mm2']=new.area;root['visible']=mapping(new);root['engraving']=mapping(unary_union([shape(parts[k]['engraving'])for k in [target,*absorbed]]));root['regions']=sorted(set(r for k in [target,*absorbed]for r in parts[k]['regions']))
# All joined material belongs to the unpainted USA surface.
root['paint']={'NATURAL':{'visible':mapping(new),'with_overlap':mapping(new),'paint':False}}
D['pieces']=[p for p in D['pieces']if p['id']not in absorbed];D['layers'][2]=mapping(unary_union([shape(p['geom'])for p in D['pieces']if p['tier']==3]));D['visible']=[mapping(shape(D['layers'][i]).difference(shape(D['layers'][i+1])))if i<2 else D['layers'][2]for i in range(3)]
for p in D['pieces']:
 if p['id']==target:continue
 exposed=shape(p['geom']).intersection(shape(D['visible'][p['tier']-1]));p['visible']=mapping(exposed)
 for c,m in p['paint'].items():m['visible']=mapping(shape(m['visible']).intersection(exposed))
 # New bridges must not cover any existing engraving.
 assert shape(p['engraving']).difference(exposed).area<.03,(p['id'],'engraving covered')
for i,s in enumerate(D['summary']):s['pieces']=sum(p['tier']==i+1 for p in D['pieces'])
report={'target_part':target,'target_description':'Бойсе — Хелена','absorbed_parts':absorbed,'prongs_original_position_preserved':True,'single_connected_polygon':True,'bridge_width_mm':width,'centerlines':paths,'added_material_area_mm2':added.area,'full_support_on_layer_2':True,'engraving_covered_by_bridges':False,'original_piece_count':len(parts),'new_piece_count':len(D['pieces']),'levels':[s['pieces']for s in D['summary']],'added_geom':mapping(added),'before_geom':mapping(old),'after_geom':mapping(new)}
D['joined_prongs']= {k:v for k,v in report.items()if not k.endswith('_geom')};f.write_text(json.dumps(D,ensure_ascii=False));(P/'Соединение-палочек.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('JOINED PRONGS', {k:v for k,v in report.items()if not k.endswith('_geom')},flush=True)
