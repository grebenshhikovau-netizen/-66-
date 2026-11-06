import bpy,bmesh,json,hashlib,array,struct
from pathlib import Path
P=Path(__file__).resolve().parent.parent
def unaffected(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));sc=bpy.context.scene;bpy.context.view_layer.update();result={}
 for o in sc.objects:
  if o.get('Role')!='PlywoodPiece'or o.get('WorldSource')=='01-Islands':continue
  h=hashlib.sha256();v=array.array('f',[0.])*(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',v);h.update(v.tobytes());h.update(struct.pack('16d',*[q for row in o.matrix_world for q in row]));h.update(str([tuple(m.diffuse_color)for m in o.data.materials]).encode());result[(o.get('WorldSource'),o.get('Piece_ID'))]=h.hexdigest()
 return result
before=unaffected(P.parent/'world-final-parts-740/04-Мир-общее-расположение.blend');after=unaffected(P/'Мир-исправленные-острова.blend');assert before==after and len(before)==192
results=[]
count=len(json.load(open(P/'01-Islands/data/production-plan.json'))['pieces'])
for file,expected in [(P/'01-Islands/Сборка.blend',count),(P/'Мир-исправленные-острова.blend',192+count)]:
 bpy.ops.wm.open_mainfile(filepath=str(file));sc=next(s for s in bpy.data.scenes if s.name.startswith('01'))if expected==count else bpy.context.scene
 bpy.context.window.scene=sc;bpy.context.view_layer.update();wood=[o for o in sc.objects if o.get('Role')=='PlywoodPiece'];assert len(wood)==expected
 for ob in wood:
  bm=bmesh.new();bm.from_mesh(ob.data);assert all(e.is_manifold for e in bm.edges),(ob.name,'non-manifold');assert bm.calc_volume(signed=False)>0;remaining=set(bm.verts);todo=[remaining.pop()]
  while todo:
   v=todo.pop()
   for edge in v.link_edges:
    q=edge.other_vert(v)
    if q in remaining:remaining.remove(q);todo.append(q)
  assert not remaining,(ob.name,'disconnected');bm.free();assert abs(min(v.co.z for v in ob.data.vertices))<1e-7;assert abs(max(v.co.z for v in ob.data.vertices)-.003)<1e-6
  assert abs(ob.matrix_world.translation.z-(ob['Tier']-1)*.003)<3e-6
 for factor in [2,3]:
  for ob in wood:
   if ob['Tier']==1:ob.scale.z=factor
  bpy.context.view_layer.update()
  for ob in wood:
   if ob['Tier']>1:assert abs(ob.matrix_world.translation.z-(factor+ob['Tier']-2)*.003)<3e-6,(ob.name,'height driver')
   top=ob.matrix_world.translation.z+.003*ob.matrix_world.to_scale().z
   for ch in ob.children:
    if ch.get('Role')in['Engraving','PaintMask']:assert ch.matrix_world.translation.z>=top-1e-7,(ch.name,'buried text')
 for ob in wood:
  if ob['Tier']==1:ob.scale.z=1
 assert sum(o.get('Role')=='AcrylicEngraving'for o in sc.objects)==1
 assert not any(o.library for o in sc.objects)
 results.append({'file':file.name,'physical_wood_parts':expected,'closed_manifold_single_component':True,'bottom_origins':True,'saved_height_tests_mm':[3,6,9],'engravings_follow_upper_surface':True,'acrylic_engraving_separate':True,'self_contained':True})
report={'native_files':results,'unchanged_other_continental_wood_parts':192,'other_meshes_transforms_and_colors_identical':True};(P/'Проверка-Blender-и-материков.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('ALL NATIVE CHECKS PASS',json.dumps(report,ensure_ascii=False),flush=True)
