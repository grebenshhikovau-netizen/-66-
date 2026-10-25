"""Build one portable Blender variant with identical bottom-plane political pivots."""
import bpy,bmesh,json,math,sys,os
sys.path.extend(p for p in os.environ.get('PYTHONPATH','').split(os.pathsep) if p and p not in sys.path)
from pathlib import Path
from mathutils import Vector,Quaternion

P=Path(__file__).resolve().parent.parent
D=json.load(open(P/'model-data.json'));REL=json.load(open(P/'model-relations.json'));G=json.load(open(P/'geometry.json'));LABELS=json.load(open(P/'labels.json'))['labels']
variant=sys.argv[sys.argv.index('--variant')+1] if '--variant' in sys.argv else 'relief'
assert variant in ['relief','political','political_water']
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.name={'relief':'Евразия — рельеф по политическим частям','political':'Евразия — политическая, сплошные части','political_water':'Евразия — политическая со сквозной водой'}[variant]
scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS';scale=D['mm_per_unit']/1000
def rgba(hex):
 rgb=[int(hex[i:i+2],16)/255 for i in [1,3,5]];return [c/12.92 if c<.04045 else ((c+.055)/1.055)**2.4 for c in rgb]+[1]
def material(name,color,grain=False):
 m=bpy.data.materials.new(name);m.diffuse_color=rgba(color);m.use_nodes=True;n=m.node_tree.nodes;p=n.get('Principled BSDF');p.inputs['Base Color'].default_value=rgba(color);p.inputs['Roughness'].default_value=.62
 if grain:
  geom=n.new('ShaderNodeTexCoord');vec=n.new('ShaderNodeVectorMath');vec.operation='MULTIPLY';vec.inputs[1].default_value=(6,550,20);noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=2;noise.inputs['Detail'].default_value=1.2;ramp=n.new('ShaderNodeValToRGB');col=rgba(color)
  ramp.color_ramp.elements[0].position=.05;ramp.color_ramp.elements[0].color=[c*.84 for c in col[:3]]+[1];ramp.color_ramp.elements[1].position=.95;ramp.color_ramp.elements[1].color=[min(1,c*1.08) for c in col[:3]]+[1]
  m.node_tree.links.new(geom.outputs['UV'],vec.inputs[0]);m.node_tree.links.new(vec.outputs[0],noise.inputs['Vector']);m.node_tree.links.new(noise.outputs['Fac'],ramp.inputs[0]);m.node_tree.links.new(ramp.outputs[0],p.inputs['Base Color'])
 return m
coat={c:material('ПОКРЫТИЕ_'+c+' — '+r['coating_name'],r['color'],True) for c,r in D['countries'].items()}
for c,m in coat.items():m['Country_ID']=c;m['HEX']=D['countries'][c]['color']
refmats={i:material('Россия — исходный слой '+str(i),D['russia_palette'][f'L{i}'][1],True) for i in range(1,7)}
edge=material('Обожжённая кромка','#30251d');floorburn=material('Дно гравированного кратера','#4c3827');lighttext=material('Гравировка — вскрытая светлая фанера','#e7d9bd');darktext=material('Гравировка — тёмный след','#493929')
countries={};regions={};regioncols={};objects={};descs={o['id']:o for o in D['objects']};checks=[];fail=[]
work=bpy.data.collections.new('01_Политические_модули');scene.collection.children.link(work)
for country,row in D['countries'].items():
 col=bpy.data.collections.new('COUNTRY_'+country+'__'+row['name']);work.children.link(col);ob=bpy.data.objects.new('СТРАНА_'+country+'__'+row['name'],None);col.objects.link(ob);ob.location=row['origin'];ob.empty_display_type='PLAIN_AXES';ob.empty_display_size=.005;ob['Role']='CountryRoot';ob['Country_ID']=country;ob['Начало отсчёта']='Нижняя плоскость Z=0';ob['Покрытие']=row['coating_name'];countries[country]=(ob,col)
for code,row in D['regions'].items():
 parent,col=countries[row['country']];rc=bpy.data.collections.new('REG_'+code+'__'+row['name']);col.children.link(rc);rc['Region_ID']=code;rc['Country_ID']=row['country'];rc.objects.link(parent)
 ob=bpy.data.objects.new('ЧАСТЬ_'+code+'__'+row['name'],None);rc.objects.link(ob);ob.parent=parent;ob.location=Vector(row['origin'])-Vector(D['countries'][row['country']]['origin']);ob.empty_display_type='PLAIN_AXES';ob.empty_display_size=.003
 ob['Role']='RegionRoot';ob['Region_ID']=code;ob['Country_ID']=row['country'];ob['Вариант']=variant;ob['Начало отсчёта']='Нижняя плоскость, общий центр для всех вариантов';regions[code]=ob;regioncols[code]=rc
refcol=bpy.data.collections.new('70_Россия_готовая_геометрия_СПРАВОЧНО');scene.collection.children.link(refcol)
selected=[o for o in D['objects'] if o['variant']==variant or o['variant']=='reference' and (variant=='relief' or o['tier']==1)]
for d in selected:
 mesh=bpy.data.meshes.new(d['id']);mesh.from_pydata(d['vertices'],[],d['faces']);mesh.update();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-9);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bad=sum(not e.is_manifold for e in bm.edges)
 if bad:fail.append({'id':d['id'],'edges':bad})
 bm.to_mesh(mesh);bm.free();ob=bpy.data.objects.new(d['id'],mesh);isref=d['variant']=='reference';(refcol if isref else regioncols[d['region']]).objects.link(ob)
 uv=mesh.uv_layers.new(name='Непрерывное направление фанеры');uv.data.foreach_set('uv',[v for loop in mesh.loops for v in [mesh.vertices[loop.vertex_index].co.x+d['origin'][0],mesh.vertices[loop.vertex_index].co.y+d['origin'][1]]])
 if isref:ob.location=d['origin'];ob.hide_select=True
 else:
  ob.parent=regions[d['region']];ob.location=Vector(d['origin'])-Vector(D['regions'][d['region']]['origin'])
 ob['Role']='RussianReference' if isref else 'PlywoodPiece';ob['Region_ID']=d['region'];ob['Country_ID']=d['country'];ob['Tier']=d['tier'];ob['BaseHeight_m']=d['height'];ob['Area_mm2']=d['area_mm2'];ob['Начало отсчёта']='Нижняя плоскость: изменение размеров Z растит деталь вверх.'
 mesh.materials.append(refmats[d['tier']] if isref else coat[d['country']]);mesh.materials.append(edge);mesh.materials.append(floorburn)
 for f,i in zip(mesh.polygons,d['material_indices']):f.material_index=i
 if not isref and d['area_mm2']>3:
  mod=ob.modifiers.new('Визуальная фаска кромки — можно отключить','BEVEL');mod.width=.000055;mod.segments=1;mod.material=1;mod.affect='EDGES';mod.limit_method='ANGLE';mod.angle_limit=.6;mod.use_clamp_overlap=True
 objects[d['id']]=ob
print('SOURCE SOLIDS',len(selected),'ERRORS',fail[:20],flush=True)
assert not fail,fail[:20]
for name,owners in REL['stack'].items():
 if name not in objects:continue
 dr=objects[name].driver_add('location',2).driver;terms=[]
 for i,key in enumerate(owners):
  for prefix,path in [('z','location[2]'),('s','scale[2]'),('h','["BaseHeight_m"]')]:
   v=dr.variables.new();v.name=prefix+str(i);v.type='SINGLE_PROP';v.targets[0].id=objects[key];v.targets[0].data_path=path
  terms.append(f'z{i}+s{i}*h{i}')
 dr.expression='max('+','.join(terms)+')' if len(terms)>1 else terms[0]
bpy.context.view_layer.update()

# Lettering is a closed filled vector curve, parented directly to its wood piece.
# Rotation, scaling and a 3 / 6 / 9 mm height change all keep it on that surface.
from shapely.geometry import shape,Polygon
from shapely.ops import unary_union
def ps(g):
 if g.geom_type=='Polygon':return [g] if not g.is_empty and g.area>1e-6 else []
 return [p for q in getattr(g,'geoms',[]) for p in ps(q)]
visible=[shape(x) for x in G['visible']];geo={o['id']:shape(o['geom']) for o in selected if o['variant']==variant};label_objects=[];label_area=0;label_expected=0
for lab in LABELS:
 whole=shape(lab['geom']);label_expected+=whole.area;fragments=[]
 for d in selected:
  if d['variant']!=variant or d['country']!=lab['country']:continue
  g=geo[d['id']]
  if variant=='relief':g=g.intersection(visible[d['tier']-1])
  g=g.intersection(whole)
  if g.area<1e-6:continue
  fragments.append(g);x0,y0,x1,y1=g.bounds;cx,cy=(x0+x1)/2,(y0+y1)/2;curve=bpy.data.curves.new('Подпись_'+d['id'],'CURVE');curve.dimensions='2D';curve.fill_mode='BOTH';curve.resolution_u=1
  from shapely.geometry.polygon import orient
  for p in ps(g):
   pp=orient(p,-1)
   for ring in [pp.exterior,*pp.interiors]:
    coords=list(ring.coords)[:-1];spl=curve.splines.new('POLY');spl.points.add(len(coords)-1)
    for pt,(x,y) in zip(spl.points,coords):pt.co=((x-cx)*scale,-(y-cy)*scale,0,1)
    spl.use_cyclic_u=True
  ob=bpy.data.objects.new('ТЕКСТ_'+d['id'],curve);regioncols[d['region']].objects.link(ob);owner=objects[d['id']];ob.parent=owner
  ob.location=((cx*scale-d['origin'][0]),((2657.4803125-cy)*scale-d['origin'][1]),d['height']+.000025)
  col=D['countries'][d['country']]['color'];lum=sum(int(col[i:i+2],16) for i in [1,3,5])/3;curve.materials.append(darktext if lum>170 else lighttext)
  ob['Role']='Engraving';ob['Region_ID']=d['region'];ob['Country_ID']=d['country'];ob['Текст']=lab['name'];label_objects.append((ob,owner));label_area+=g.area
 if fragments:
  lost=whole.difference(unary_union(fragments)).area/max(whole.area,1e-12)
  assert lost<.002,('cropped country lettering',lab['country'],lost)

woods=[o for n,o in objects.items() if descs[n]['variant']==variant];references=[o for n,o in objects.items() if descs[n]['variant']=='reference'];bevel_disabled=[]
deps=bpy.context.evaluated_depsgraph_get()
for ob in woods:
 assert abs(min(v.co.z for v in ob.data.vertices))<1e-8,ob.name
 ev=ob.evaluated_get(deps);me=ev.to_mesh();bm=bmesh.new();bm.from_mesh(me);bad=sum(not e.is_manifold for e in bm.edges);bm.free();ev.to_mesh_clear()
 if bad:
  for mod in ob.modifiers:mod.show_viewport=False;mod.show_render=False
  bevel_disabled.append(ob.name)
# Verify the real height editing behavior, not only the written origin flag.
for factor in [1,2,3]:
 for ob in woods:
  if variant!='relief' or ob['Tier']==1:ob.scale.z=factor
 bpy.context.view_layer.update()
 if variant=='relief':
  for ob in woods:
   if ob['Tier']>1:assert abs(ob.location.z-(factor+ob['Tier']-2)*.003)<2e-6,ob.name
 for text,owner in label_objects:
  top=owner.matrix_world@Vector((0,0,owner['BaseHeight_m']));p=text.matrix_world.translation
  assert p.z>top.z-1e-7,('buried label',text.name,p.z,top.z)
for ob in woods:
 if variant!='relief' or ob['Tier']==1:ob.scale.z=1
bpy.context.view_layer.update()

# Presentation fixtures do not participate in the cut geometry.
presentation=bpy.data.collections.new('90_Презентация_только_рендер');scene.collection.children.link(presentation)
points=[o.matrix_world@Vector(p) for o in woods+references for p in o.bound_box];lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)));center=(lo+hi)/2
camera=bpy.data.objects.new('Камера',bpy.data.cameras.new('Камера'));presentation.objects.link(camera);camera.data.type='ORTHO';camera.data.clip_start=.001;camera.location=center+Vector((.07,-.31,.95));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=1.21;scene.camera=camera
for name,delta,power,size in [('Основной',(-.28,-.27,.75),12,.50),('Заполняющий',(.38,.25,.60),5,.55)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;ob=bpy.data.objects.new(name,data);presentation.objects.link(ob);ob.location=center+Vector(delta);ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
mesh=bpy.data.meshes.new('Фон');mesh.from_pydata([(-20,-20,-.0034),(20,-20,-.0034),(20,20,-.0034),(-20,20,-.0034)],[],[(0,1,2,3)]);ob=bpy.data.objects.new('Фон',mesh);presentation.objects.link(ob);mesh.materials.append(material('Тёплый фон','#ede9df'))
acrylic=bpy.data.collections.new('85_Оргстекло_условный_лист_НЕ_контур_резки');scene.collection.children.link(acrylic);pad=.008;pts=[(x,y,z) for z in [-.003,0] for y in [lo.y-pad,hi.y+pad] for x in [lo.x-pad,hi.x+pad]];me=bpy.data.meshes.new('Оргстекло');me.from_pydata(pts,[],[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]);ob=bpy.data.objects.new('REFERENCE_Оргстекло_справочно',me);acrylic.objects.link(ob);ob.display_type='WIRE';mat=material('Прозрачное оргстекло','#f4f8f8');n=mat.node_tree.nodes;tr=n.new('ShaderNodeBsdfTransparent');tr.inputs['Color'].default_value=rgba('#f4f8f8');mat.node_tree.links.new(tr.outputs[0],n.get('Material Output').inputs['Surface']);me.materials.append(mat)
scene.world=bpy.data.worlds.new('Мир');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.5,.5,.5,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.18
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=64;scene.cycles.use_denoising=False;scene.render.resolution_x=2800;scene.render.resolution_y=1800;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
try:scene.view_settings.look='AgX - Medium High Contrast'
except:pass
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   sp=area.spaces.active;sp.shading.type='MATERIAL';sp.clip_start=.0001;sp.region_3d.view_rotation=Quaternion((1,0,0,0));sp.region_3d.view_location=center;sp.region_3d.view_distance=.85;sp.region_3d.view_perspective='ORTHO';sp.overlay.show_floor=False
bpy.context.view_layer.layer_collection.children[presentation.name].hide_viewport=True
if variant!='relief':bpy.context.view_layer.layer_collection.children[refcol.name].hide_viewport=True
script=bpy.data.texts.new('ЗАМЕНИТЬ_ВЫБРАННУЮ_ЧАСТЬ.py');script.write((P/'tools'/'swap_region.py').read_text())
scene['Инструкция']='Страна / провинция: контейнер ЧАСТЬ_. Начало отсчёта снизу. Для замены выбранной части откройте текст ЗАМЕНИТЬ_ВЫБРАННУЮ_ЧАСТЬ.py.'
scene['Высоты']='Толщина 3 мм, уровни 3 / 6 / 9 / 12 / 15 / 18 мм. X/Y и центры совпадают во всех вариантах.'
bpy.ops.object.select_all(action='DESELECT');active=next((o for o in woods if o['Country_ID']=='FRA'),woods[0]);active.select_set(True);bpy.context.view_layer.objects.active=active
files={'relief':'Евразия-рельеф-по-регионам.blend','political':'Евразия-политическая.blend','political_water':'Евразия-политическая-с-водой.blend'}
report={'variant':variant,'wood_objects':len(woods),'russian_reference_objects':len(references),'all_source_solids_manifold':True,'bottom_origins':True,'height_tests_mm':[3,6,9],'upper_stacks_follow_base':True,'labels_follow_actual_piece':True,'closed_outline_label_objects':len(label_objects),'same_region_roots_all_variants':True,'render_bevel_disabled_for_robustness':bevel_disabled,'region_ids':list(regions)}
(P/('Проверка-Blender-'+variant+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(P/files[variant]),compress=True);print('SAVED',files[variant],report['wood_objects'],'wood solids',flush=True)
if '--no-render' in sys.argv:sys.exit(0)
png={'relief':'Евразия-Россия-рельеф-3D.png','political':'Евразия-политическая-3D.png','political_water':'Евразия-политическая-с-водой-3D.png'};scene.render.filepath=str(P/png[variant]);bpy.ops.render.render(write_still=True)
if variant=='relief' and '--no-details' not in sys.argv:
 # Camera targets are in the same world-coordinate system as the frozen map.
 from math import log,tan,pi,radians
 cfg=json.load(open(P/'data'/'config.json'));pr=cfg['projection'];mc=log(tan(pi/4+radians(pr['latmin'])/2))
 for name,lon,lat,span in [('Европа-Альпы-3D.png',10,47,.38),('Гималаи-Тибет-3D.png',85,31,.34),('Аравия-Иран-3D.png',47,27,.32),('Япония-Фудзи-3D.png',138,36,.16),('Индонезия-3D.png',112,-4,.31),('Тянь-Шань-Памир-3D.png',76,41,.25)]:
  x=pr['source_xmin']+(lon-pr['lonmin'])*pr['kx_per_degree'];y=pr['source_ymax']-(log(tan(pi/4+radians(lat)/2))-mc)*pr['ky_per_mercator'];target=Vector((x*scale,(2657.4803125-y)*scale,.007));camera.location=target+Vector((.025,-.09,.23));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=span;scene.render.resolution_x=1700;scene.render.resolution_y=1350;scene.render.filepath=str(P/name);bpy.ops.render.render(write_still=True)
print('RENDER COMPLETE',variant,flush=True)
