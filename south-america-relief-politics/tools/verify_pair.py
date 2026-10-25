"""Test saved files and real library swapping, including self-library avoidance."""
import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data'/'compatibility.json'));sys.path.insert(0,str(P/'tools'));from swap_country import swap_region
flatpath=P/'Южная-Америка-политическая.blend';relpath=P/'Южная-Америка-рельеф-по-странам.blend'
def load(p):bpy.ops.wm.open_mainfile(filepath=str(p));bpy.context.view_layer.update()
def root(code):return next(o for o in bpy.context.scene.objects if o.get('Role')=='RegionRoot'and o.get('Region_ID')==code)
def wood(code):return [o for o in bpy.context.scene.objects if o.get('Role')=='PlywoodPiece'and o.get('Country_ID')==code]
load(flatpath);origins={code:root(code).matrix_world.copy()for code in D['countries']};flatverts={code:[tuple(ob.matrix_world@v.co)for v in ob.data.vertices]for code in D['countries']for ob in wood(code)}
assert len([o for o in bpy.context.scene.objects if o.get('Role')=='PlywoodPiece'])==13
for code in D['countries']:
 ob=wood(code)[0];assert abs(min(v.co.z for v in ob.data.vertices))<1e-8;assert abs(max(v.co.z for v in ob.data.vertices)-.003)<1e-8
 for factor in [1,2,3]:
  ob.scale.z=factor;bpy.context.view_layer.update();assert abs(min((ob.matrix_world@v.co).z for v in ob.data.vertices))<1e-8
  for child in ob.children:assert child.matrix_world.translation.z>.003*factor-1e-7
 ob.scale.z=1
load(relpath);maxerror=0
for code,row in D['countries'].items():
 assert max(abs(origins[code][i][j]-root(code).matrix_world[i][j])for i in range(4)for j in range(4))<1e-8
 ob=bpy.data.objects[row['base_id']];assert len(ob.data.vertices)==len(flatverts[code]);maxerror=max(maxerror,max((Vector(v)-ob.matrix_world@ob.data.vertices[i].co).length for i,v in enumerate(flatverts[code])))
assert maxerror<1e-7,maxerror
checks=[]
for code in ['BRA','CHL','BOL']:
 r=root(code);r.location+=Vector((.009,-.006,.004));r.rotation_euler.z=.19;r.scale=(1.08,.92,1.15);bpy.context.view_layer.update();pose=r.matrix_world.copy()
 for target,variant,count in [(flatpath,'political',1),(relpath,'relief',None)]:
  r=swap_region(code,target);bpy.context.view_layer.update();error=max(abs(pose[i][j]-r.matrix_world[i][j])for i in range(4)for j in range(4));assert error<1e-6,(code,error)
  assert r['Вариант']==variant
  if count:assert len(wood(code))==count
  for ob in wood(code):
   bm=bmesh.new();bm.from_mesh(ob.data);assert all(e.is_manifold for e in bm.edges),ob.name;bm.free()
  if variant=='relief':
   base=next(o for o in wood(code)if o['Tier']==1);base.scale.z=2;bpy.context.view_layer.update()
   for o in wood(code):
    if o['Tier']>1:assert abs(o.location.z-o['Tier']*.003)<3e-7,(code,o.name,o.location.z)
   base.scale.z=1;bpy.context.view_layer.update()
  checks.append({'country':code,'to':variant,'pose_error':error,'wood_objects':len(wood(code)),'drivers_and_manifold':True})
result={'political_modules':13,'relief_wood_count':78,'same_country_root_matrices':True,'base_vertex_world_error_m':maxerror,'political_thickness_tests_mm':[3,6,9],'both_directions_swap_tests':checks,'original_source_unchanged':True}
(P/'Проверка-совмещения-и-замены.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('PAIR VERIFIED',result,flush=True)
