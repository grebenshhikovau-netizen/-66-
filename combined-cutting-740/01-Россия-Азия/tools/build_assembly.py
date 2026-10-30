"""Editable plywood production model. All geometry is in original world coordinates."""
import bpy,bmesh,sys,os,json,math
sys.path.extend(p for p in os.environ.get('PYTHONPATH','').split(os.pathsep) if p and p not in sys.path)
from pathlib import Path
from collections import Counter
from mathutils import Vector,Quaternion
from shapely.geometry import shape
from shapely.geometry.polygon import orient
from shapely import constrained_delaunay_triangles,set_precision
from shapely.ops import unary_union
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data'/'production-plan.json'))
bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene;sc.name='01 — Собранная карта';sc.unit_settings.system='METRIC';sc.unit_settings.length_unit='MILLIMETERS'
def polys(g):
 if g.geom_type=='Polygon':return [g] if not g.is_empty and g.area>1e-8 else []
 return [p for q in getattr(g,'geoms',[]) for p in polys(q)]
def mat(name,col,grain=False):
 m=bpy.data.materials.new(name);m.diffuse_color=tuple(col)+ (1,);m.use_nodes=True;n=m.node_tree.nodes;bs=n.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*col,1);bs.inputs['Roughness'].default_value=.72;bs.inputs['Specular IOR Level'].default_value=.05
 if grain:
  tex=n.new('ShaderNodeTexCoord');vec=n.new('ShaderNodeVectorMath');vec.operation='MULTIPLY';vec.inputs[1].default_value=(6,460,20);noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=2;noise.inputs['Detail'].default_value=1.2;ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=tuple(c*(.91/.975) for c in col)+(1,);ramp.color_ramp.elements[1].color=tuple(min(c*(1.04/.975),1) for c in col)+(1,);links=m.node_tree.links;links.new(tex.outputs['UV'],vec.inputs[0]);links.new(vec.outputs[0],noise.inputs['Vector']);links.new(noise.outputs['Fac'],ramp.inputs[0]);links.new(ramp.outputs[0],bs.inputs['Base Color'])
 return m
base=mat('Фанера без покраски',D['colors']['NATURAL'],True);edge=mat('Обожжённый торец',[.055,.022,.009]);burn=mat('Гравировка',[.018,.008,.003]);coats={c:mat('ПОКРЫТИЕ — '+c,rgb,True)for c,rgb in D['colors'].items()};lightburn=mat('Гравировка — светлая фанера после окраски',[.65,.47,.25])
layer_bases={}
for tier in range(1,len(D['layers'])+1):
 layer_bases[tier]=base.copy();layer_bases[tier].name=f'ФАНЕРА — слой {tier:02d}, цвет всего слоя';layer_bases[tier]['PlywoodLayer']=tier
paint_materials={}
cols={};objects={};checks=[];glookup={p['id']:shape(p['geom'])for p in D['pieces']}
for tier in range(1,len(D['layers'])+1):
 c=bpy.data.collections.new(f'СЛОЙ {tier:02d} — толщина 3 мм');sc.collection.children.link(c);cols[tier]=c

def curve(g,name,owner,material,level):
 if not polys(g):return
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='2D';cu.fill_mode='BOTH';cu.resolution_u=1
 ox,oy=owner.location.x,owner.location.y
 for p in polys(g):
  p=orient(p,-1)
  for ring in [p.exterior,*p.interiors]:
   coords=list(ring.coords)[:-1]
   if len(coords)<3:continue
   sp=cu.splines.new('POLY');sp.points.add(len(coords)-1)
   for pt,(x,y) in zip(sp.points,coords):pt.co=(x/1000-ox,-y/1000-oy,0,1)
   sp.use_cyclic_u=True
 ob=bpy.data.objects.new(name,cu);cols[owner['Tier']].objects.link(ob);ob.parent=owner;ob.location=(0,0,level);cu.materials.append(material);ob['Role']='Engraving' if name.startswith('ГРАВИРОВКА') else 'PaintMask';ob['Piece_ID']=owner.name
 return ob
for row in D['pieces']:
 name=row['id'];original_geom=shape(row['geom']);g=set_precision(original_geom,.000001);x0,y0,x1,y1=g.bounds;cx,cy=(x0+x1)/2,(y0+y1)/2;vertices=[];faces=[];mi=[];index={};edges=Counter()
 def vertex(q,z):
  key=(round(q[0],8),round(q[1],8),z)
  if key not in index:index[key]=len(vertices);vertices.append(((key[0]-cx)/1000,-(key[1]-cy)/1000,z))
  return index[key]
 for tri in constrained_delaunay_triangles(g).geoms:
  q=[tuple(round(x,8)for x in p)for p in list(tri.exterior.coords)[:3]]
  if len(set(q))<3:continue
  ids=[vertex(p,.003)for p in q];bot=[vertex(p,0)for p in q];faces.extend([ids,bot[::-1]]);mi.extend([0,1])
  for a,b in zip(q,q[1:]+q[:1]):edges[tuple(sorted((a,b)))]+=1
 for (a,b),count in edges.items():
  if count==1:faces.append([vertex(a,0),vertex(b,0),vertex(b,.003),vertex(a,.003)]);mi.append(1)
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bad=sum(not e.is_manifold for e in bm.edges);volume=bm.calc_volume(signed=False);
 if bad:
  print('BAD EDGES DETAIL',name,[(list(e.verts[0].co),list(e.verts[1].co),len(e.link_faces))for e in bm.edges if not e.is_manifold],flush=True)
 bm.to_mesh(mesh);bm.free();assert bad==0,(name,bad)
 ob=bpy.data.objects.new(name,mesh);cols[row['tier']].objects.link(ob);ob.location=(cx/1000,-cy/1000,(row['tier']-1)*.003);group=row.get('paint_group','Основной массив');key=(row['tier'],group)
 if key not in paint_materials:
  paint_materials[key]=layer_bases[row['tier']].copy();paint_materials[key].name=f'КРАСКА — слой {row["tier"]:02d} — {group}';paint_materials[key]['PaintGroup']=group
 mesh.materials.append(paint_materials[key]);mesh.materials.append(edge);ob['Группа покраски']=group
 for f,i in zip(mesh.polygons,mi):f.material_index=i
 uv=mesh.uv_layers.new(name='Волокна в мировых координатах');uv.data.foreach_set('uv',[v for lp in mesh.loops for v in [mesh.vertices[lp.vertex_index].co.x+ob.location.x,mesh.vertices[lp.vertex_index].co.y+ob.location.y]])
 ob['Блок']=row.get('block','MAIN');ob['Role']='PlywoodPiece';ob['Tier']=row['tier'];ob['Piece_ID']=name;ob['BaseHeight_m']=.003;ob['Площадь, мм²']=g.area;ob['Политические части']=', '.join(row['regions']);ob['Начало отсчёта']='Нижняя плоскость';ob['Покраска']='Отдельные группы покраски по ТЗ; у каждой группы свой материал';objects[name]=ob
 for coat,mask in row['paint'].items():
  if mask['paint']:curve(shape(mask['with_overlap']),f'КРАСКА_{name}__{coat}',ob,coats[coat],.003008)
 eng=shape(row['engraving']);dark=unary_union([shape(v['visible'])for c,v in row['paint'].items()if sum(a*b for a,b in zip(D['colors'][c],[.2126,.7152,.0722]))<.1]);curve(eng.difference(dark),'ГРАВИРОВКА_'+name,ob,burn,.003028);curve(eng.intersection(dark),'ГРАВИРОВКА_СВЕТЛАЯ_'+name,ob,lightburn,.003028)
 checks.append({'id':name,'nonmanifold_edges':bad,'closed_solid':True,'precision_grid_mm':.000001,'footprint_difference_mm2':g.symmetric_difference(original_geom).area,'volume_mm3':volume*1e9,'expected_mm3':g.area*3,'local_bottom_mm':min(v.co.z for v in mesh.vertices)*1000})
 print('SOLID',name,'verts',len(vertices),'closed',bad==0,flush=True)
# A single controller moves Scandinavia independently from the main assembly.
if any(row.get('block')=='SCAND'for row in D['pieces']):
 control=bpy.data.objects.new('СКАНДИНАВИЯ — отдельный блок',None);sc.collection.objects.link(control);control.empty_display_type='PLAIN_AXES';control.empty_display_size=.025;control['Role']='IndependentScandinaviaController'
 for row in D['pieces']:
  if row.get('block')=='SCAND':objects[row['id']].parent=control

# Upper plies follow the top of their supporting lower ply if its height changes.
for row in D['pieces']:
 if row['tier']==1:continue
 ob=objects[row['id']];owners=[objects[q['id']]for q in D['pieces']if q['tier']==row['tier']-1 and glookup[q['id']].intersection(glookup[row['id']]).area>.01];assert owners,row['id'];driver=ob.driver_add('location',2).driver;terms=[]
 for j,owner in enumerate(owners):
  for prefix,path in [('z','location[2]'),('s','scale[2]'),('h','["BaseHeight_m"]')]:
   var=driver.variables.new();var.name=prefix+str(j);var.type='SINGLE_PROP';var.targets[0].id=owner;var.targets[0].data_path=path
  terms.append(f'z{j}+s{j}*h{j}')
 driver.expression='max('+','.join(terms)+')'if len(terms)>1 else terms[0]
bpy.context.view_layer.update()
# Verify actual editing and label attachment, then restore nominal 3 mm.
for factor in [1,2,3]:
 for ob in objects.values():
  if ob['Tier']==1:ob.scale.z=factor
 bpy.context.view_layer.update()
 for ob in objects.values():
  assert abs(ob.location.z-(factor+ob['Tier']-2)*.003)<2e-6 if ob['Tier']>1 else abs(ob.location.z)<1e-8
  for child in ob.children:
   assert child.matrix_world.translation.z >= ob.location.z+.003*ob.scale.z-1e-7,(child.name,'buried')
for ob in objects.values():
 if ob['Tier']==1:ob.scale.z=1
bpy.context.view_layer.update()
# Create acrylic under the actual through-water reference as optional acrylic references.
if (P/'data'/'water-reference.json').exists():
 water=bpy.data.collections.new('СПРАВОЧНО — оргстекло под водой, не фанера');sc.collection.children.link(water);watermat=mat('Вода / оргстекло',[.025,.42,.57])
 for row in json.load(open(P/'data'/'water-reference.json')):
  g=shape(row['geom']);cu=bpy.data.curves.new(row['name'],'CURVE');cu.dimensions='2D';cu.fill_mode='BOTH';cu.extrude=.0015
  for poly in polys(g):
   pp=orient(poly,-1)
   for ring in [pp.exterior,*pp.interiors]:
    cc=list(ring.coords)[:-1];sp=cu.splines.new('POLY');sp.points.add(len(cc)-1)
    for pt,(x,y)in zip(sp.points,cc):pt.co=(x/1000,-y/1000,0,1)
    sp.use_cyclic_u=True
  ob=bpy.data.objects.new(row['name'],cu);water.objects.link(ob);ob.location.z=-.0015;cu.materials.append(watermat);ob['Role']='ReferenceWater'
# Presentation helpers.
minx,miny,maxx,maxy=shape(D['layers'][0]).bounds;center=Vector(((minx+maxx)/2000,-(miny+maxy)/2000,.003));width=(maxx-minx)/1000;height=(maxy-miny)/1000

def setup(scene,target,ortho,angled=False):
 col=bpy.data.collections.new('ПРЕЗЕНТАЦИЯ — не резать');scene.collection.children.link(col)
 cam=bpy.data.objects.new('Камера',bpy.data.cameras.new('Камера'));col.objects.link(cam);cam.data.type='ORTHO';cam.data.clip_start=.001;cam.location=target+Vector((.035,-.23,.78)if angled else (0,0,1));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=ortho;scene.camera=cam
 for name,delta,power,size in [('Основной',(-.25,-.35,.65),10,.5),('Заполняющий',(.3,.3,.6),6,.6)]:
  data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;ob=bpy.data.objects.new(name,data);col.objects.link(ob);ob.location=target+Vector(delta);ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
 floor=bpy.data.meshes.new('Фон');floor.from_pydata([(-5,-5,-.0035),(5,-5,-.0035),(5,5,-.0035),(-5,5,-.0035)],[],[(0,1,2,3)]);ob=bpy.data.objects.new('Фон',floor);col.objects.link(ob);floor.materials.append(mat('Тёплый фон',[.82,.80,.75]));scene.world=bpy.data.worlds.new('Свет');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.3
 scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=False;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.3;scene.render.image_settings.file_format='PNG'
 return col
rw,rh=(2400,1850)if D['batch']=='EAST'else(1800,2400);fixtures=setup(sc,center,(max(width,height*rw/rh)if rw>=rh else max(height,width*rh/rw))*1.15,True);sc.render.resolution_x=rw;sc.render.resolution_y=rh;sc.cycles.samples=20
# Second scene: actual separate layers, all lying on the table.
expl=bpy.data.scenes.new('02 — Слои отдельно');expl.unit_settings.system='METRIC';expl.unit_settings.length_unit='MILLIMETERS'
for i in range(len(D['layers'])):
 ob=bpy.data.objects.new(f'Слой {i+1} — отдельная раскладка',None);expl.collection.objects.link(ob);ob.instance_type='COLLECTION';ob.instance_collection=cols[i+1];ob.location=(i*(width+.05),0,-i*.003)
font=bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
for i,count in enumerate([s['pieces']for s in D['summary']]):
 cu=bpy.data.curves.new('Слой','FONT');cu.body=f'СЛОЙ {i+1}  /  {count} '+('деталь' if count==1 else 'деталей');cu.size=.009;cu.font=font;cu.align_x='CENTER';ob=bpy.data.objects.new(cu.body,cu);expl.collection.objects.link(ob);ob.location=(center.x+i*(width+.05),-miny/1000+.016,.001);cu.materials.append(burn)
explfixtures=setup(expl,center+Vector((((len(D['layers'])-1)/2)*(width+.05),.012,0)),(len(D['layers'])*width+(len(D['layers'])-1)*.05)*1.035,False);expl.render.resolution_x=2400;expl.render.resolution_y=900;expl.cycles.samples=16
sc['Слои']=' / '.join(str(z)for z in D['levels_mm'])+' мм. Каждая физическая деталь толщиной 3 мм.';sc['Окраска']='Отдельный материал на каждый слой; цвет можно изменять сразу для всего слоя. Политические границы не разрезают общие детали.';sc['Коррекции']='Соседние части объединены по фактической высоте; мелкие зубцы сглажены. В первом слое прорези всех основных рек. Верхние русла открыты; согласованные перемычки на Меконге и Дунае и пирамида Египта остаются цельными.';sc['Контуры']='Чёрный — замкнутая резка, красный — города, фактура и сборка, синий — названия стран. Все надписи SVG/PDF редактируются как текст.'
text=bpy.data.texts.new('ПРОЧТИ-МЕНЯ');text.write((P/'ПРОЧТИ-МЕНЯ.txt').read_text())
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   sp=area.spaces.active;sp.shading.type='MATERIAL';sp.clip_start=.0001;sp.overlay.show_floor=False;sp.region_3d.view_location=center;sp.region_3d.view_distance=.65;sp.region_3d.view_rotation=Quaternion((1,0,0,0));sp.region_3d.view_perspective='ORTHO'
# Hide render fixtures in viewport only, without disabling renders.
sc.view_layers[0].layer_collection.children[fixtures.name].hide_viewport=True
expl.view_layers[0].layer_collection.children[explfixtures.name].hide_viewport=True
bpy.ops.object.select_all(action='DESELECT');ob=objects['L01_P001'];ob.select_set(True);bpy.context.view_layer.objects.active=ob
report={'pieces':checks,'all_closed_manifold':True,'bottom_origins':True,'labels_follow_height':True,'upper_plies_follow_base':True,'height_test_mm':[3,6,9],'wood_count':len(objects)};(P/'Проверка-Blender.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'Сборка-комплекта.blend'),compress=True);print('BLEND SAVED',flush=True)
if '--no-render' in sys.argv:sys.exit(0)
sc.render.filepath=str(P/'Сборка-комплекта.png');bpy.ops.render.render(write_still=True,scene=sc.name)
expl.render.filepath=str(P/'Слои-отдельно.png');bpy.ops.render.render(write_still=True,scene=expl.name)
print('RENDERS COMPLETE',flush=True)
