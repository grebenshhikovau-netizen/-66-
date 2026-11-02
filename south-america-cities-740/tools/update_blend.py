"""Replace only engraving in the approved Blender assembly; preserve wood and paint."""
import os,sys,json,hashlib
sys.path.extend(p for p in os.environ.get('PYTHONPATH','').split(os.pathsep)if p)
from pathlib import Path
import bpy
from shapely.geometry import shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'))
bpy.context.preferences.filepaths.use_scripts_auto_execute=False
bpy.ops.wm.open_mainfile(filepath=str(P/'data/source/Южная-Америка-производственная-сборка.blend'))
scene=bpy.data.scenes['01 — Собранная карта'];wood={o['Piece_ID']:o for o in scene.objects if o.get('Role')=='PlywoodPiece'}
def digest(o):
 h=hashlib.sha256();h.update(str([tuple(v.co)for v in o.data.vertices]).encode());h.update(str([tuple(p.vertices)for p in o.data.polygons]).encode());h.update(str(tuple(o.matrix_world)).encode());return h.hexdigest()
before={k:digest(o)for k,o in wood.items()}
for o in list(bpy.data.objects):
 if o.get('Role')=='Engraving':bpy.data.objects.remove(o,do_unlink=True)
burn=bpy.data.materials['Гравировка'];light=bpy.data.materials.get('Гравировка — светлая фанера после окраски')
if light is None:
 light=bpy.data.materials.new('Гравировка — светлая фанера после окраски');light.diffuse_color=(.65,.47,.25,1);light.use_nodes=True
 light.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.65,.47,.25,1)
 light.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.72
def polys(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in polys(q)]
def add(g,name,owner,mat):
 if g.is_empty:return
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='2D';cu.fill_mode='BOTH';cu.resolution_u=1
 for p in polys(g):
  p=orient(p,-1)
  for ring in [p.exterior,*p.interiors]:
   coords=list(ring.coords)[:-1]
   if len(coords)<3:continue
   sp=cu.splines.new('POLY');sp.points.add(len(coords)-1)
   for pt,(x,y)in zip(sp.points,coords):pt.co=(x/1000-owner.location.x,-y/1000-owner.location.y,0,1)
   sp.use_cyclic_u=True
 ob=bpy.data.objects.new(name,cu);owner.users_collection[0].objects.link(ob);ob.parent=owner;ob.location=(0,0,.003028);cu.materials.append(mat);ob['Role']='Engraving';ob['Piece_ID']=owner['Piece_ID']
for row in D['pieces']:
 dark=unary_union([shape(v['visible'])for c,v in row['paint'].items()if sum(a*b for a,b in zip(D['colors'][c],[.2126,.7152,.0722]))<.1]);g=shape(row['engraving']);ob=wood[row['id']]
 add(g.difference(dark),'ГРАВИРОВКА_'+row['id'],ob,burn);add(g.intersection(dark),'ГРАВИРОВКА_СВЕТЛАЯ_'+row['id'],ob,light)
assert before=={k:digest(o)for k,o in wood.items()}
scene['Города']=len(D['city_markers']);scene['Штаты Бразилии']='27 административных единиц, только гравировка на открытых поверхностях';scene['Подписи']='В SVG: страны синие, города и штаты красные, редактируемый текст. Контуры резки и покраска сохранены.'
if 'ПРОЧТИ-МЕНЯ'in bpy.data.texts:bpy.data.texts['ПРОЧТИ-МЕНЯ'].clear();bpy.data.texts['ПРОЧТИ-МЕНЯ'].write((P/'README.md').read_text())
report={'passed':True,'wood_meshes_and_world_transforms_unchanged':True,'wood_parts':len(wood),'hashes':before,'city_names':len(D['city_markers']),'state_names':sum(a['kind']=='state'for a in D['labels'])}
(P/'Проверка-обновления-Blender.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'Южная-Америка-производственная-сборка.blend'),compress=True)
print('UPDATED BLENDER SAVED',flush=True)
scene.render.resolution_x=1350;scene.render.resolution_y=1800;scene.cycles.samples=20;scene.cycles.use_denoising=False
scene.render.filepath=str(P/'Южная-Америка-сборка-3D.png');bpy.ops.render.render(write_still=True,scene=scene.name)
print('RENDER COMPLETE',flush=True)
