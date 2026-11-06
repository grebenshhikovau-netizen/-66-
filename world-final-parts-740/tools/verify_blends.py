"""Open the saved native files and validate solid topology and editable Z behavior."""
import bpy,bmesh,sys,os,json
from pathlib import Path
P=Path(__file__).resolve().parent.parent
results=[]
for key in ['01-Islands','02-Greenland','03-Australia','WORLD']:
 path=P/key/'Сборка.blend'if key!='WORLD'else P/'04-Мир-общее-расположение.blend'
 bpy.ops.wm.open_mainfile(filepath=str(path));sc=bpy.context.scene;wood=[o for o in sc.objects if o.get('Role')=='PlywoodPiece'];assert wood
 if key!='WORLD':expected=len(json.load(open(P/key/'data/production-plan.json'))['pieces']);assert len(wood)==expected
 else:assert len({(o.get('WorldSource'),o.get('Piece_ID'))for o in wood})==len(wood)
 totalverts=0
 for ob in wood:
  bm=bmesh.new();bm.from_mesh(ob.data);assert all(e.is_manifold for e in bm.edges),(key,ob.name,'non-manifold');assert bm.calc_volume(signed=False)>1e-12
  # Each physical cutting part is a single connected closed mesh.
  unseen=set(bm.verts);todo=[unseen.pop()]
  while todo:
   v=todo.pop()
   for e in v.link_edges:
    q=e.other_vert(v)
    if q in unseen:unseen.remove(q);todo.append(q)
  assert not unseen,(key,ob.name,'disconnected mesh');totalverts+=len(bm.verts);bm.free()
  assert abs(min(v.co.z for v in ob.data.vertices))<1e-7
  assert abs(max(v.co.z for v in ob.data.vertices)-.003)<1e-6
  assert abs(ob.matrix_world.translation.z-(ob['Tier']-1)*.003)<2e-6,(key,ob.name,'stack height')
  if ob.animation_data:
   for fc in ob.animation_data.drivers:
    assert fc.driver.is_valid,(key,ob.name,'invalid driver')
    for var in fc.driver.variables:
     for target in var.targets:assert target.id in sc.objects.values(),(key,ob.name,'orphan driver target')
 # Test changing the first plywood sheet from 3 to 6 and 9 mm after reopening.
 for factor in [2,3]:
  for ob in wood:
   if ob['Tier']==1:ob.scale.z=factor
  bpy.context.view_layer.update()
  for ob in wood:
   if ob['Tier']>1:assert abs(ob.matrix_world.translation.z-(factor+ob['Tier']-2)*.003)<3e-6,(key,ob.name,'does not follow base')
   top=ob.matrix_world.translation.z+.003*ob.matrix_world.to_scale().z
   for ch in ob.children:
    if ch.get('Role')in ['Engraving','PaintMask']:assert ch.matrix_world.translation.z>=top-1e-7,(key,ch.name,'buried engraving')
 for ob in wood:
  if ob['Tier']==1:ob.scale.z=1
 bpy.context.view_layer.update()
 assert not any(x.library for x in bpy.data.objects)
 results.append({'file':key,'wood_pieces':len(wood),'vertices':totalverts,'closed_manifold_single_components':True,'bottom_origins':True,'driver_targets_in_current_scene':True,'saved_height_edit_tests_mm':[3,6,9],'engravings_follow_upper_surface':True,'external_linked_objects':0})
(P/'Проверка-нативных-файлов.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print('ALL SAVED NATIVE FILES VERIFIED',json.dumps(results,ensure_ascii=False),flush=True)
