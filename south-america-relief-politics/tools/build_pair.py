"""Derive political modules directly from the accepted monolithic Blender meshes."""
import bpy,bmesh,json,sys,os,math
sys.path.extend(x for x in os.environ.get('PYTHONPATH','').split(os.pathsep)if x and x not in sys.path)
from pathlib import Path
from mathutils import Vector
from shapely.geometry import shape
from shapely.geometry.polygon import orient
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data'/'compatibility.json'))
bpy.ops.wm.open_mainfile(filepath=str(P/'data'/D['source_file']));scene=bpy.context.scene;bpy.context.view_layer.update()
woods={k:bpy.data.objects[k] for k in D['relief_wood_ids']};engraves={k:bpy.data.objects[k] for k in D['engraving_ids']};snapshot={name:[tuple(ob.matrix_world@v.co)for v in ob.data.vertices]for name,ob in woods.items()};counts={}
work=bpy.data.collections.new('01_Страны — взаимозаменяемые модули');scene.collection.children.link(work);roots={};cols={}
for code,row in D['countries'].items():
 name=D['palette'][code][0];col=bpy.data.collections.new('REG_'+code+'__'+name);col['Region_ID']=code;col['Country_ID']=code;work.children.link(col);root=bpy.data.objects.new('ЧАСТЬ_'+code+'__'+name,None);col.objects.link(root);root.location=row['origin'];root.empty_display_type='PLAIN_AXES';root.empty_display_size=.004;root['Role']='RegionRoot';root['Region_ID']=code;root['Country_ID']=code;root['Вариант']='relief';root['Начало отсчёта']='Нижняя плоскость Z=0, одинаковая в обоих вариантах';roots[code]=root;cols[code]=col
bpy.context.view_layer.update()
for name,ob in {**woods,**engraves}.items():
 code=ob['Country_ID'];world=ob.matrix_world.copy()
 for c in list(ob.users_collection):c.objects.unlink(ob)
 cols[code].objects.link(ob);ob.parent=roots[code];ob.matrix_world=world;ob['Region_ID']=code;ob['Role']='PlywoodPiece' if name in woods else 'Engraving';ob['Variant']='relief'
 if name in woods:ob['Kind']='wood'
for col in list(bpy.data.collections):
 if col not in [work,*cols.values()] and not col.all_objects and not col.children:bpy.data.collections.remove(col)
bpy.context.view_layer.update()
error=max((Vector(v)-ob.matrix_world@ob.data.vertices[i].co).length for name,ob in woods.items()for i,v in enumerate(snapshot[name]));assert error<1e-7,error
# Roots, flat base and relief use identical reference coordinates and paint materials.
source_bases={code:(woods[row['base_id']].data.copy(),woods[row['base_id']].data.materials[0])for code,row in D['countries'].items()}

def verify(variant):
 allwood=[o for o in scene.objects if o.get('Role')=='PlywoodPiece'];result=[]
 for o in allwood:
  bm=bmesh.new();bm.from_mesh(o.data);bad=sum(not e.is_manifold for e in bm.edges);volume=bm.calc_volume(signed=False);bm.free();assert bad==0,(o.name,bad);assert abs(min(v.co.z for v in o.data.vertices))<1e-8,o.name
  result.append({'id':o.name,'country':o['Country_ID'],'nonmanifold_edges':bad,'volume_mm3':volume*1e9})
 for factor in [1,2,3]:
  for ob in allwood:
   if ob['Tier']==1:ob.scale.z=factor
  bpy.context.view_layer.update()
  for ob in allwood:
   if ob['Tier']>1:assert abs(ob.location.z-(factor+ob['Tier']-2)*.003)<3e-7,ob.name
  for ob in scene.objects:
   if ob.get('Role')!='Engraving':continue
   if variant=='political':assert ob.matrix_world.translation.z>=.003*factor-1e-7,ob.name
   else:assert ob.location.z>=.003*(factor+ob['Tier']-1)-1e-7,ob.name
 for ob in allwood:
  if ob['Tier']==1:ob.scale.z=1
 bpy.context.view_layer.update()
 return {'variant':variant,'country_modules':len(roots),'wood_count':len(allwood),'all_closed_manifold':True,'bottom_origins':True,'base_height_tests_mm':[3,6,9],'engraving_follows_height':True,'common_country_roots':{k:list(r.location)for k,r in roots.items()},'checks':result}

def save(variant,filename):
 scene.name='Южная Америка — '+('политическая'if variant=='political'else'монолитный рельеф по странам');scene['Вариант']=variant;scene['Инструкция']='Для замены страны выделите её деталь и запустите встроенный текст ЗАМЕНИТЬ_ВЫБРАННУЮ_СТРАНУ.py. Два файла Blender должны лежать рядом.'
 text=bpy.data.texts.get('ЗАМЕНИТЬ_ВЫБРАННУЮ_СТРАНУ.py')or bpy.data.texts.new('ЗАМЕНИТЬ_ВЫБРАННУЮ_СТРАНУ.py');text.clear();text.write((P/'tools'/'swap_country.py').read_text());info=bpy.data.texts.get('ПРОЧИТАТЬ')or bpy.data.texts.new('ПРОЧИТАТЬ');info.clear();info.write((P/'ПРОЧИТАТЬ.txt').read_text())
 report=verify(variant);report['relief_source_vertex_max_error_m']=error;(P/f'Проверка-{variant}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 bpy.ops.object.select_all(action='DESELECT');roots['BRA'].select_set(True);bpy.context.view_layer.objects.active=roots['BRA'];scene.render.resolution_x=1500;scene.render.resolution_y=1900;scene.cycles.samples=32;scene.cycles.use_denoising=False;scene.render.resolution_percentage=100
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/filename),compress=True);print('SAVED',variant,len(report['checks']),flush=True)

save('relief','Южная-Америка-рельеф-по-странам.blend')
# Remove only country geometry; retain the source render setup and exact palette.
for ob in list(woods.values())+list(engraves.values()):bpy.data.objects.remove(ob,do_unlink=True)
flat={}
for code,(mesh,mat) in source_bases.items():
 ob=bpy.data.objects.new('POL_'+code+'__'+D['palette'][code][0],mesh);cols[code].objects.link(ob);ob.parent=roots[code];ob.location=(0,0,0);ob['Role']='PlywoodPiece';ob['Country_ID']=code;ob['Region_ID']=code;ob['Tier']=1;ob['BaseHeight_m']=.003;ob['Variant']='political';ob['Начало отсчёта']='Нижняя плоскость: Dimensions Z увеличивает высоту вверх';flat[code]=ob;roots[code]['Вариант']='political'
# Full political boundary engraving on the new flat top. No terrain lines or river cuts.
def polygons(g):
 if g.geom_type=='Polygon':return [g]if not g.is_empty and g.area>1e-8 else []
 return [p for q in getattr(g,'geoms',[])for p in polygons(q)]
scale=D['mm_per_unit']/1000;seam=shape(D['seam']);burn=next(m for m in bpy.data.materials if m.name=='Гравировка политических границ')
for code,row in D['countries'].items():
 g=shape(row['geom']).intersection(seam)
 if g.is_empty:continue
 curve=bpy.data.curves.new('ГРАНИЦЫ_'+code,'CURVE');curve.dimensions='2D';curve.fill_mode='BOTH';curve.resolution_u=1
 for p in polygons(g):
  q=orient(p,-1)
  for ring in [q.exterior,*q.interiors]:
   cc=list(ring.coords)[:-1];sp=curve.splines.new('POLY');sp.points.add(len(cc)-1)
   for pt,(x,y)in zip(sp.points,cc):pt.co=(x*scale-row['origin'][0],(2657.4803125-y)*scale-row['origin'][1],0,1)
   sp.use_cyclic_u=True
 ob=bpy.data.objects.new('ГРАВИРОВКА_ГРАНИЦ_'+code,curve);cols[code].objects.link(ob);ob.parent=flat[code];ob.location.z=.00302;ob['Role']='Engraving';ob['Region_ID']=code;ob['Country_ID']=code;ob['Tier']=1;curve.materials.append(burn)
save('political','Южная-Америка-политическая.blend')
scene.render.filepath=str(P/'Южная-Америка-политическая-3D.png');bpy.ops.render.render(write_still=True);print('PAIR READY',flush=True)
