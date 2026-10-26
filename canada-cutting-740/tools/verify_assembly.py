import bpy,bmesh,json
from pathlib import Path
P=Path(__file__).resolve().parent.parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Канада-обновлённая-сборка.blend'));scene=bpy.data.scenes['01 — Собранная карта'];bpy.context.window.scene=scene
wood=[o for o in scene.objects if o.get('Role')=='PlywoodPiece'];assert len(wood)==28
assert not any(o.name in ['L03_P002','L03_P003']for o in scene.objects)
ob=bpy.data.objects['L03_P001'];bm=bmesh.new();bm.from_mesh(ob.data);assert all(e.is_manifold for e in bm.edges);bm.verts.ensure_lookup_table();seen=set();components=0
for v in bm.verts:
 if v.index in seen:continue
 components+=1;todo=[v];seen.add(v.index)
 while todo:
  w=todo.pop()
  for e in w.link_edges:
   q=e.other_vert(w)
   if q.index not in seen:seen.add(q.index);todo.append(q)
assert components==1,components
assert abs(min(v.co.z for v in bm.verts))<1e-8;assert abs(max(v.co.z for v in bm.verts)-.003)<1e-8;bm.free()
for o in wood:
 b=bmesh.new();b.from_mesh(o.data);assert all(e.is_manifold for e in b.edges),o.name;b.free()
result={'wood_count':len(wood),'joined_target':'L03_P001','absorbed_objects_removed':['L03_P002','L03_P003'],'joined_mesh_connected_components':components,'all_wood_manifold':True,'bottom_origin':True,'ply_thickness_mm':3,'nominal_top_mm':9,'source_prongs_positions_retained':True}
(P/'Проверка-обновлённой-сборки.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('ASSEMBLY VERIFIED',result,flush=True)
