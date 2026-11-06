"""Self-contained world overview, reusing approved physical assemblies unchanged.
Only XY similarity registration is applied to continental roots; plywood Z is unchanged.
"""
import bpy,sys,os,json,math
from pathlib import Path
from mathutils import Vector,Quaternion
sys.path.extend(x for x in os.environ.get('PYTHONPATH','').split(os.pathsep)if x and x not in sys.path)
from shapely.geometry import shape,Polygon,mapping
from shapely.geometry.polygon import orient
from shapely import constrained_delaunay_triangles
P=Path(__file__).resolve().parent.parent;R=Path(os.environ.get('MAP_REPO',str(P.parent if (P.parent/'.git').exists() else '/workspace/-66-')))
bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene;sc.name='МИР — общее расположение';sc.unit_settings.system='METRIC';sc.unit_settings.length_unit='MILLIMETERS'
T=json.load(open(P/'data/world-registration.json'));roles={'PlywoodPiece','PaintMask','Engraving','ReferenceWater'};report=[]
names={'north-america':'01 — Северная Америка','south-america':'02 — Южная Америка','russia-asia':'03 — Россия и Азия','africa-europe':'04 — Африка, Европа, Ближний Восток','01-Islands':'05 — Недостающие острова','02-Greenland':'06 — Гренландия','03-Australia':'07 — Австралия'}
def import_assembly(key,path,affine):
 before=set(bpy.data.objects)
 with bpy.data.libraries.load(str(path),link=False)as(src,dst):dst.scenes=[next(n for n in src.scenes if n.startswith('01'))]
 source=dst.scenes[0];selected={o for o in source.objects if o.get('Role')in roles}
 for o in list(selected):
  par=o.parent
  while par:selected.add(par);par=par.parent
 col=bpy.data.collections.new(names[key]);sc.collection.children.link(col);tiers={}
 root=bpy.data.objects.new(names[key]+' — ПЕРЕМЕЩАТЬ БЛОК',None);col.objects.link(root);root.empty_display_type='PLAIN_AXES';root.empty_display_size=.04;root['Role']='WorldBlockController';root['Source']=str(path.relative_to(R))if path.is_relative_to(R)else str(path.relative_to(P));root['Registration']='Приблизительное географическое размещение; исходная геометрия сохранена.'
 for o in selected:
  tier=o.get('Tier',o.parent.get('Tier',0)if o.parent else 0)
  if tier not in tiers:
   tiers[tier]=bpy.data.collections.new(f'{key} / '+(f'СЛОЙ {tier}'if tier else 'Прочее'));col.children.link(tiers[tier])
  tiers[tier].objects.link(o);o.name=key+' / '+o.name;o['WorldSource']=key
 for o in selected:
  if o.parent not in selected:o.parent=root
 a,b,c,d,tx,ty=affine;ss=math.hypot(a,c);angle=math.atan2(c,a)
 assert abs(a-d)<1e-6 and abs(b+c)<1e-6
 root.location=(tx/1000,-ty/1000,0);root.scale=(ss,ss,1);root.rotation_euler.z=-angle
 wood=[o for o in selected if o.get('Role')=='PlywoodPiece'];report.append({'block':key,'wood_pieces':len(wood),'objects':len(selected),'transform_xy':affine,'z_scale':1,'original_mesh_data_preserved':True})
 bpy.data.scenes.remove(source)
 # Unlink orphan presentation objects that came along with the library scene.
 for o in set(bpy.data.objects)-before:
  if o!=root and o not in selected and o.users==0:bpy.data.objects.remove(o)
 print('IMPORTED',key,len(wood),'wood pieces',flush=True)
for key,t in T.items():import_assembly(key,R/t['blend_relative'],t['affine'])
for key in ['01-Islands','02-Greenland','03-Australia']:import_assembly(key,P/key/'Сборка.blend',T['russia-asia']['affine'])
# The original decorative Antarctic silhouette is retained as a flat geographic reference.
# No unsupported Antarctic terrain is substituted for approved data.
C={x['code']:x for x in json.load(open(P/'data/source/master-countries.json'))};g=shape(C['ATA']['geom']).simplify(.3)
col=bpy.data.collections.new('08 — Антарктида — исходный силуэт');sc.collection.children.link(col)
def polys(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in polys(q)]
m=bpy.data.materials.new('Антарктида — натуральная фанера');m.diffuse_color=(.77,.62,.41,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.77,.62,.41,1)
for j,p in enumerate(polys(g)):
 verts=[];faces=[];idx={};cx,cy=p.centroid.coords[0]
 def v(q,z):
  k=(round(q[0],6),round(q[1],6),z)
  if k not in idx:idx[k]=len(verts);verts.append(((k[0]-cx)/1000,-(k[1]-cy)/1000,z))
  return idx[k]
 for tr in constrained_delaunay_triangles(p).geoms:
  q=list(tr.exterior.coords)[:3];faces.append([v(a,.003)for a in q]);faces.append([v(a,0)for a in q[::-1]])
 for ring in [p.exterior,*p.interiors]:
  for a,b in zip(list(ring.coords)[:-1],list(ring.coords)[1:]):faces.append([v(a,0),v(b,0),v(b,.003),v(a,.003)])
 mesh=bpy.data.meshes.new('Антарктида');mesh.from_pydata(verts,[],faces);mesh.update();ob=bpy.data.objects.new('Антарктида — исходный плоский ориентир',mesh);col.objects.link(ob);ob.location=(cx/1000,-cy/1000,0);mesh.materials.append(m);ob['Role']='AntarcticReference';ob['NotProductionRelief']=True
fontpath=str(P/'Шрифт/OpenSans-Light.ttf');font=bpy.data.fonts.load(fontpath)
cu=bpy.data.curves.new('Название Антарктиды','FONT');cu.body='АНТАРКТИДА';cu.font=font;cu.size=.010;cu.align_x='CENTER';ob=bpy.data.objects.new(cu.body,cu);col.objects.link(ob);ob.location=(1.10,-1.31,.00303);ob['Role']='ReferenceCaption';dark=bpy.data.materials.new('Гравировка названия Антарктиды');dark.diffuse_color=(.03,.015,.005,1);cu.materials.append(dark)
# Presentation fixtures are separate and hidden in the modeling viewport.
fx=bpy.data.collections.new('ПРЕЗЕНТАЦИЯ — не часть карты');sc.collection.children.link(fx);center=Vector((.95,-.67,.003))
def camera(name,angled=False):
 cam=bpy.data.objects.new(name,bpy.data.cameras.new(name));fx.objects.link(cam);cam.data.type='ORTHO';cam.data.ortho_scale=2.15;cam.data.clip_start=.001;cam.data.clip_end=100;cam.location=center+Vector((0,-.48,2.6)if angled else(0,0,3));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();return cam
top=camera('01 — Весь мир сверху');angled=camera('02 — Небольшой наклон');sc.camera=top
for name,pos,power,size in [('Большой мягкий свет',(-.6,-1.3,2),160,2),('Заполняющий',(2,0,1.7),90,2)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.size=size;ob=bpy.data.objects.new(name,data);fx.objects.link(ob);ob.location=pos;ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
mesh=bpy.data.meshes.new('Фон');mesh.from_pydata([(-5,-5,-.005),(5,-5,-.005),(5,5,-.005),(-5,5,-.005)],[],[(0,1,2,3)]);ob=bpy.data.objects.new('Фон',mesh);fx.objects.link(ob);mat=bpy.data.materials.new('Фон — светлый тёплый');mat.diffuse_color=(.79,.79,.77,1);mat.use_nodes=True;mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.79,.79,.77,1);mesh.materials.append(mat)
sc.world=bpy.data.worlds.new('Свет мира');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=False;sc.render.resolution_x=2400;sc.render.resolution_y=1700;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast'
sc['Назначение']='Общее географическое расположение утверждённого рельефа. Для резки использовать отдельные SVG 740 × 740 мм.';sc['Новые комплекты']='Острова, Гренландия, Австралия';sc['Антарктида']='Исходный плоский силуэт для ориентира, без нового рельефа.';sc['Масштаб']='Континентальные сборки совмещены приближённо по географическим координатам. XY масштаб блоков согласован для общего вида, Z и высоты исходных слоёв сохранены.'
tx=bpy.data.texts.new('ПРОЧТИ-МЕНЯ — расположение мира');tx.write((P/'ПРОЧТИ-МЕНЯ.txt').read_text())
bpy.context.view_layer.update();sc.view_layers[0].layer_collection.children[fx.name].hide_viewport=True
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   sp=area.spaces.active;sp.shading.type='MATERIAL';sp.clip_start=.0001;sp.clip_end=100;sp.overlay.show_floor=False;sp.region_3d.view_location=center;sp.region_3d.view_distance=2.25;sp.region_3d.view_rotation=Quaternion((1,0,0,0));sp.region_3d.view_perspective='ORTHO'
for o in sc.objects:o.select_set(False)
bpy.data.orphans_purge(do_recursive=True)
wood=[o for o in sc.objects if o.get('Role')=='PlywoodPiece'];assert len(wood)==sum(r['wood_pieces']for r in report);assert len(report)==7
assert all(abs(o.scale.z-1)<1e-6 for o in sc.objects if o.get('Role')=='WorldBlockController')
for o in wood:
 assert min(v.co.z for v in o.data.vertices)>-1e-6,(o.name,'bottom origin changed')
report={'blocks':report,'wood_pieces':len(wood),'no_duplicate_native_sources':True,'z_unchanged':True,'antarctica':'original flat reference','external_dependencies_packed':True};(P/'Проверка-общей-сборки.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'04-Мир-общее-расположение.blend'),compress=True);print('WORLD SAVED',len(wood),'pieces',flush=True)
if '--no-render'not in sys.argv:
 sc.render.filepath=str(P/'04-Мир-вид-сверху.png');bpy.ops.render.render(write_still=True)
 sc.camera=angled;sc.render.filepath=str(P/'04-Мир-рельеф-3D.png');bpy.ops.render.render(write_still=True)
