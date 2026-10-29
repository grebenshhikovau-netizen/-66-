import bpy,bmesh,json,os,sys,math
sys.path.extend(p for p in os.environ.get('PYTHONPATH','').split(os.pathsep)if p and p not in sys.path)
from pathlib import Path
from shapely.geometry import shape,Polygon
from shapely.ops import unary_union
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));plan={q['id']:q for q in D['pieces']};bpy.ops.wm.open_mainfile(filepath=str(P/'Евразия-производственная-сборка.blend'));scene=bpy.data.scenes['01 — Собранная карта'];wood={o['Piece_ID']:o for o in scene.objects if o.get('Role')=='PlywoodPiece'};assert set(wood)==set(plan);report=[]
for id,o in wood.items():
 bm=bmesh.new();bm.from_mesh(o.data);assert all(e.is_manifold for e in bm.edges),(id,'non-manifold');volume=bm.calc_volume(signed=False)*1e9;bm.free();assert abs(min(v.co.z for v in o.data.vertices))<1e-8;assert abs(max(v.co.z for v in o.data.vertices)-.003)<1e-8;assert abs(o.matrix_world.translation.z*1000-(plan[id]['tier']-1)*3)<.0001
 vertices=[o.matrix_world@v.co for v in o.data.vertices];parts=[]
 for face in o.data.polygons:
  pts=[(vertices[i].x*1000,-vertices[i].y*1000)for i in face.vertices];g=Polygon(pts)
  if g.is_valid and g.area>1e-7:parts.append(g)
 footprint=unary_union(parts);expected=shape(plan[id]['geom']);err=footprint.symmetric_difference(expected).area;assert err<expected.length*.0002+.01,(id,'world footprint changed',err);assert abs(volume-expected.area*3)<expected.area*3*.00001,(id,'volume changed')
 # Every actual physical part is one connected mesh, not a joined object of islands.
 parent=list(range(len(o.data.vertices)))
 def find(q):
  while parent[q]!=q:parent[q]=parent[parent[q]];q=parent[q]
  return q
 for edge in o.data.edges:a,b=edge.vertices;parent[find(a)]=find(b)
 components=len(set(find(i)for i in range(len(parent))));assert components==1,(id,components)
 report.append({'id':id,'tier':plan[id]['tier'],'closed_manifold':True,'connected_components':components,'bottom_origin':True,'footprint_error_mm2':err,'volume_mm3':volume})
material_groups={}
for id,o in wood.items():
 key=(o['Tier'],plan[id].get('paint_group','Основной массив'));mat=o.data.materials[0];material_groups.setdefault(key,set()).add(mat.name);assert mat.get('PlywoodLayer')==key[0];assert mat.get('PaintGroup')==key[1]
assert all(len(v)==1 for v in material_groups.values());assert len({next(iter(v))for v in material_groups.values()})==len(material_groups)
# Exercise saved drivers and parenting, then restore; the checked file is not rewritten.
for factor in [1,2,3]:
 for o in wood.values():
  if o['Tier']==1:o.scale.z=factor
 bpy.context.view_layer.update()
 for o in wood.values():
  expected=(factor+o['Tier']-2)*3 if o['Tier']>1 else 0;assert abs(o.matrix_world.translation.z*1000-expected)<.001,(o.name,'support driver')
  for child in o.children:assert child.matrix_world.translation.z>=o.matrix_world.translation.z+.003*o.scale.z-1e-7,(child.name,'buried label')
for o in wood.values():
 if o['Tier']==1:o.scale.z=1
r={'passed':True,'wood_parts':len(wood),'layers':[s['pieces']for s in D['summary']],'all_parts_one_connected_manifold_solid':True,'bottom_origins':True,'height_driver_tests_mm':[3,6,9],'labels_follow_top':True,'independent_material_per_layer_and_paint_group':True,'checks':report};(P/'Проверка-сохранённого-Blender.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print('SAVED BLENDER VERIFIED',len(wood),'parts',flush=True)
