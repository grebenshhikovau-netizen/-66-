"""Fill manufacturing slivers; retain real openings and the accepted 28 parts."""
import json
from pathlib import Path
from shapely.geometry import shape, mapping, Polygon
from shapely.ops import unary_union, polylabel
from shapely import set_precision
P=Path(__file__).resolve().parent.parent
F=P/'data/source/production-plan.json'; backup=P/'data/source/plan-before-slit-repair.json'
if not backup.exists(): backup.write_bytes(F.read_bytes())
D=json.loads(backup.read_text()); report=[]
def polygons(g):
 if g.geom_type=='Polygon': return [g] if not g.is_empty else []
 return [p for a in getattr(g,'geoms',[]) for p in polygons(a)]
for row in D['pieces']:
 g=shape(row['geom']); old=g; removed=[]; keep=[]
 for h in g.interiors:
  hole=Polygon(h); center=polylabel(hole,tolerance=.005);radius=center.distance(hole.boundary)
  if radius<.31:
   removed.append({'area_mm2':hole.area,'max_inradius_mm':radius,'bounds':hole.bounds})
  else: keep.append(h.coords)
 g=Polygon(g.exterior.coords,keep)
 # Repair only long narrow exterior slits. Do not smooth coastlines globally.
 closed=g.buffer(.16,quad_segs=8).buffer(-.16,quad_segs=8).union(g)
 patches=[q for q in polygons(closed.difference(g)) if q.area>.15 and q.length>3]
 g=set_precision(unary_union([g,*patches]),.000001)
 assert g.geom_type=='Polygon' and g.is_valid
 row['geom']=mapping(g);row['area_mm2']=g.area
 report.append({'id':row['id'],'removed_sliver_holes':removed,'closed_exterior_slits':len(patches),'added_area_mm2':g.difference(old).area,'removed_area_mm2':old.difference(g).area})
# Give filled top slits continuous support on the lower ply as well.
for tier in [3,2]:
 upper=unary_union([shape(q['geom']) for q in D['pieces'] if q['tier']==tier]);lower=unary_union([shape(q['geom']) for q in D['pieces'] if q['tier']==tier-1]);missing=upper.difference(lower)
 if missing.area<.001: continue
 for patch in polygons(missing):
  candidates=[q for q in D['pieces'] if q['tier']==tier-1]
  target=max(candidates,key=lambda q:shape(q['geom']).intersection(patch.buffer(.02)).area)
  merged=unary_union([shape(target['geom']),patch.buffer(.000002)]).intersection(upper.union(lower))
  assert merged.geom_type=='Polygon',(target['id'],merged.geom_type)
  target['geom']=mapping(merged);target['area_mm2']=merged.area
D['layers']=[mapping(unary_union([shape(q['geom'])for q in D['pieces']if q['tier']==i]))for i in [1,2,3]]
D['visible']=[mapping(shape(D['layers'][i]).difference(shape(D['layers'][i+1])))if i<2 else D['layers'][i]for i in range(3)]
for row in D['pieces']:
 g=shape(row['geom']);row['visible']=mapping(g.intersection(shape(D['visible'][row['tier']-1])))
 oldrow=next(q for q in json.loads(backup.read_text())['pieces']if q['id']==row['id']);added=g.difference(shape(oldrow['geom']))
 # Only tiny repairs are new; inherit coating from the adjacent original mask.
 for name,mask in row['paint'].items():
  h=shape(mask['with_overlap']);extra=added.intersection(h.buffer(.4));mask['with_overlap']=mapping(h.union(extra).intersection(g));mask['visible']=mapping(shape(mask['visible']).union(extra).intersection(shape(row['visible'])))
 assert shape(row['engraving']).difference(shape(row['visible']).buffer(.00001)).area<.03
for tier in [2,3]:
 assert shape(D['layers'][tier-1]).difference(shape(D['layers'][tier-2]).buffer(.00001)).area<.001
for q in report:
 row=next(r for r in D['pieces']if r['id']==q['id']);before=next(r for r in json.loads(backup.read_text())['pieces']if r['id']==q['id']);q['final_added_area_including_support_mm2']=shape(row['geom']).difference(shape(before['geom'])).area
F.write_text(json.dumps(D,ensure_ascii=False))
(P/'Исправление-щелей.json').write_text(json.dumps({'parts':report,'physical_parts':len(D['pieces']),'real_holes_preserved':True},ensure_ascii=False,indent=2))
print('REPAIRED',[(q['id'],len(q['removed_sliver_holes']),q['closed_exterior_slits'],round(q['added_area_mm2'],3))for q in report if q['added_area_mm2']>.001],flush=True)
