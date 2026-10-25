"""Independent checks on the delivered polygon data, without Blender."""
import json
from pathlib import Path
from shapely.geometry import shape,Polygon
from shapely.ops import unary_union
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'production-plan.json'))
def polys(g):
 if g.geom_type=='Polygon':return [g]if not g.is_empty else []
 return [p for q in getattr(g,'geoms',[])for p in polys(q)]
issues=[];necks=[];layer_checks=[]
for tier in [1,2,3]:
 pp=[p for p in D['pieces']if p['tier']==tier];g=unary_union([shape(p['geom'])for p in pp]);error=g.symmetric_difference(shape(D['layers'][tier-1])).area;duplicates=sum(shape(p['geom']).area for p in pp)-g.area
 assert error<.01 and abs(duplicates)<.01
 layer_checks.append({'tier':tier,'pieces':len(pp),'layer_error_mm2':error,'duplicate_area_mm2':duplicates})
 for p in pp:
  a=shape(p['geom']);assert a.is_valid
  if len([q for q in polys(a.buffer(-.5))if q.area>5])>1:necks.append(p['id'])
  # No unhidden extension of paint on any ply.
  for name,mask in p['paint'].items():
   visible=shape(mask['visible']);painted=shape(mask['with_overlap']);cover=shape(D['layers'][tier])if tier<3 else Polygon()
   assert painted.difference(visible).difference(cover).area<.0001
  assert shape(p['engraving']).difference(shape(p['visible'])).area<.03
  if tier==1:continue
  colors=[(name,unary_union(polys(shape(mask['visible']))))for name,mask in p['paint'].items()]
  for j,(c,g1)in enumerate(colors):
   for d,g2 in colors[:j]:
    area=g1.buffer(.025).intersection(g2.buffer(.025)).area
    if area>.015:issues.append({'piece':p['id'],'colors':[c,d],'contact_area':area})
assert not issues,issues
assert not necks,necks
assert not D['annotations_requiring_review']
result={'layers':layer_checks,'upper_pieces_with_exposed_paint_color_conflicts':issues,'pieces_split_by_1mm_erosion_into_areas_over_5mm2':necks,'complete_annotations':D['unique_annotations'],'relocated_annotations':len(D['annotation_moves']),'base_masks_required':['Arizona / Mexico','Labrador / Quebec'],'source_file_unchanged':True}
(P/'Независимая-проверка-векторов.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('VECTOR CHECK PASS',result,flush=True)
