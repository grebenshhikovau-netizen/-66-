"""Build a portable Blender scene from closed laser-contour solids."""
import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Vector,Quaternion
P=Path(__file__).resolve().parent
if P.name=='tools':P=P.parent
D=json.load(open(P/'model-data.json'));R=json.load(open(P/'model-relations.json'));bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS'
def rgba(h):
 rgb=[int(h[i:i+2],16)/255 for i in [1,3,5]];return [v/12.92 if v<.04045 else ((v+.055)/1.055)**2.4 for v in rgb]+[1]
def material(name,h,grain=False):
 m=bpy.data.materials.new(name);m.diffuse_color=rgba(h);m.use_nodes=True;n=m.node_tree.nodes;bs=n.get('Principled BSDF');bs.inputs['Base Color'].default_value=rgba(h);bs.inputs['Roughness'].default_value=.64
 if grain:
  geom=n.new('ShaderNodeNewGeometry');vec=n.new('ShaderNodeVectorMath');vec.operation='MULTIPLY';vec.inputs[1].default_value=(6,550,20);noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=2;noise.inputs['Detail'].default_value=1.2
  ramp=n.new('ShaderNodeValToRGB');col=rgba(h);ramp.color_ramp.elements[0].position=.05;ramp.color_ramp.elements[0].color=[v*.84 for v in col[:3]]+[1];ramp.color_ramp.elements[1].position=.95;ramp.color_ramp.elements[1].color=[min(1,v*1.08) for v in col[:3]]+[1]
  lk=m.node_tree.links;lk.new(geom.outputs['Position'],vec.inputs[0]);lk.new(vec.outputs[0],noise.inputs['Vector']);lk.new(noise.outputs['Fac'],ramp.inputs[0]);lk.new(ramp.outputs[0],bs.inputs['Base Color'])
 return m
mats={code:material(code+' — '+name,h,True) for code,(name,h,desc) in D['palette'].items()};edge=material('Лазерный торец','#4b3226');burn=material('Лёгкая гравировка пустынь','#795c3d');watermat=material('Окраска деревянного дна рек и озёр','#317b80');objects={};descs={d['id']:d for d in D['objects']};cols={};source_bad=[]
for i in range(1,7):
 c=bpy.data.collections.new(f'{i:02d}_Слой_{i}_верх_{i*3}мм');scene.collection.children.link(c);cols[i]=c
cutcol=bpy.data.collections.new('80_Фактура_гравировка');scene.collection.children.link(cutcol)
watercol=bpy.data.collections.new('70_Маска_окраски_воды');scene.collection.children.link(watercol)
madcol=bpy.data.collections.new('60_Опция_Мадагаскар');scene.collection.children.link(madcol)
for d in D['objects']:
 mesh=bpy.data.meshes.new(d['id']);mesh.from_pydata(d['vertices'],[],d['faces']);mesh.update();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bad=sum(not e.is_manifold for e in bm.edges)
 if bad:source_bad.append({'id':d['id'],'edges':bad})
 bm.to_mesh(mesh);bm.free();ob=bpy.data.objects.new(d['id'],mesh);(madcol if d['kind']=='wood' and d['country']=='MAD' else cols[d['tier']] if d['kind']=='wood' else watercol if d['kind']=='water' else cutcol).objects.link(ob);ob.location=d['origin'];ob['Tier']=d['tier'];ob['BaseHeight_m']=d['height'];ob['Country_ID']=d['country'];ob['Описание']='Начало координат на нижней плоскости. Рельеф 6 ступеней; толщина листа 3 мм.';mesh.materials.append(mats[f'L{d["tier"]}'] if d['kind']=='wood' else watermat if d['kind']=='water' else burn);mesh.materials.append(edge if d['kind']=='wood' else watermat if d['kind']=='water' else burn)
 for face,idx in zip(mesh.polygons,d['material_indices']):face.material_index=idx
 if d['kind']!='wood':ob['Описание']='Визуальная маска окраски / гравировки 0.02 мм; не дополнительный слой фанеры.'
 objects[d['id']]=ob
assert not source_bad,source_bad[:10]
def driver(ob,owners,gap):
 dr=ob.driver_add('location',2).driver;terms=[]
 for i,name in enumerate(owners):
  for prefix,path in [('z','location[2]'),('s','scale[2]'),('h','["BaseHeight_m"]')]:
   v=dr.variables.new();v.name=prefix+str(i);v.type='SINGLE_PROP';v.targets[0].id=objects[name];v.targets[0].data_path=path
  terms.append(f'z{i}+s{i}*h{i}')
 dr.expression=('max('+','.join(terms)+')' if len(terms)>1 else terms[0])+f'+({gap})'
for name,owners in R['stack'].items():driver(objects[name],owners,0)
for name,owners in R['markings'].items():driver(objects[name],owners,.00001)
bpy.context.view_layer.update()
checks=[];deps=bpy.context.evaluated_depsgraph_get()
for name,d in descs.items():
 if d['kind']!='wood':continue
 ob=objects[name];ev=ob.evaluated_get(deps);mesh=ev.to_mesh();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8);bad=sum(not e.is_manifold for e in bm.edges);checks.append({'id':name,'non_manifold_edges':bad});bm.free();ev.to_mesh_clear()
print('EVALUATED ERRORS',[c for c in checks if c['non_manifold_edges']],flush=True)
assert not [c for c in checks if c['non_manifold_edges']],[c for c in checks if c['non_manifold_edges']][:10]
# Verify bottom origin and the entire dependent stack at multiple base heights.
for name,d in descs.items():
 if d['kind']=='wood':assert abs(min(v.co.z for v in objects[name].data.vertices))<1e-9,name
height_tests=[]
for scale in [1,2,3]:
 for name,d in descs.items():
  if d['kind']=='wood' and d['tier']==1:objects[name].scale.z=scale
 bpy.context.view_layer.update()
 for name,d in descs.items():
  if d['kind']=='wood' and d['tier']>1:assert abs(objects[name].location.z-(scale+d['tier']-2)*.003)<3e-7,name
 height_tests.append({'base_mm':scale*3,'passed':True})
for name,d in descs.items():
 if d['kind']=='wood' and d['tier']==1:objects[name].scale.z=1
bpy.context.view_layer.update()
# Rendering equipment is hidden from editing; no external textures are needed.
presentation=bpy.data.collections.new('90_Презентация_только_рендер');scene.collection.children.link(presentation)
woods=[ob for name,ob in objects.items() if descs[name]['kind']=='wood'];pts=[ob.matrix_world@Vector(v) for ob in woods for v in ob.bound_box];lo=Vector(tuple(min(v[i] for v in pts) for i in range(3)));hi=Vector(tuple(max(v[i] for v in pts) for i in range(3)));center=(lo+hi)/2
camera=bpy.data.objects.new('Камера',bpy.data.cameras.new('Камера'));presentation.objects.link(camera);camera.data.type='ORTHO';camera.data.clip_start=.001;scene.camera=camera
camera.location=center+Vector((.045,-.24,.68));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=.49
for name,delta,power,size in [('Key',(-.18,-.20,.65),8,.4),('Fill',(.35,.20,.5),3,.45)]:
 light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size;ob=bpy.data.objects.new(name,light);presentation.objects.link(ob);ob.location=center+Vector(delta);ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
mesh=bpy.data.meshes.new('Фон');mesh.from_pydata([(-20,-20,-.0003),(20,-20,-.0003),(20,20,-.0003),(-20,20,-.0003)],[],[(0,1,2,3)]);floor=bpy.data.objects.new('Фон',mesh);presentation.objects.link(floor);mesh.materials.append(material('Фон','#ede9df'))
scene.world=bpy.data.worlds.new('Мир');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.5,.5,.5,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.15
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32;scene.cycles.use_denoising=False;scene.render.resolution_x=1600;scene.render.resolution_y=1700;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
try:scene.view_settings.look='AgX - Medium High Contrast'
except:pass
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   sp=area.spaces.active;sp.clip_start=.0001;sp.shading.type='MATERIAL';sp.region_3d.view_rotation=Quaternion((1,0,0,0));sp.region_3d.view_location=center;sp.region_3d.view_distance=.5;sp.region_3d.view_perspective='ORTHO';sp.overlay.show_floor=False
bpy.context.view_layer.layer_collection.children[presentation.name].hide_viewport=True
bpy.ops.object.select_all(action='DESELECT');bpy.context.view_layer.objects.active=woods[0]
report={'all_source_solids_manifold':True,'all_evaluated_wood_solids_manifold':True,'bottom_origins':True,'height_follow_tests':height_tests,'wood_meshes':len(woods),'water_and_texture_markings':len(R['markings']),'marking_representation':'20 micrometre surface colour, production masks in SVG','main_level_count':6,'heights_mm':[3,6,9,12,15,18],'madagascar_separate_collection':True,'checks':checks}
(P/'Проверка-Blender.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(P/'Африка-рельеф.blend'));print('SAVED AFRICA ALL CHECKS PASS',len(woods),'wood meshes',flush=True)
if '--no-render' in sys.argv:sys.exit(0)
scene.render.filepath=str(P/'Африка-3D.png');bpy.ops.render.render(write_still=True)
mm=D['mm_per_unit']/1000
for name,file,span,offset in [('Великий рифт','Озёра-и-рифт-3D.png',.175,(-.018,-.012,0)),('Водопад Виктория','Замбези-Виктория-3D.png',.073,(0,0,0))]:
 p=next(v for v in D['places'] if v['name']==name);target=Vector((p['x']*mm,(2657.4803125-p['y'])*mm,.006))+Vector(offset);camera.location=target+Vector((.025,-.10,.21));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=span;scene.render.resolution_x=1500;scene.render.resolution_y=1400;scene.render.filepath=str(P/file);bpy.ops.render.render(write_still=True)
print('AFRICA RENDERS COMPLETE',flush=True)
