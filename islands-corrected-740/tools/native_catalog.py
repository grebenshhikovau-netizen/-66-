"""A second, explicitly illustrative native scene, so no island hides at world scale."""
import bpy,json,math
from mathutils import Vector,Quaternion
def add_catalog(P,source,setup):
 roster=json.load(open(P.parent/'data/island-roster.json'));scene=bpy.data.scenes.new('02 — Каталог островов · схема');scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS';scene['Назначение']='Просмотр всех подписанных островов. Масштабы карточек условные; для производства — сцена 01 и SVG 740 × 740 мм.'
 cols=7;cw=.14;ch=.18;rows=math.ceil(len(roster)/cols)
 for i,row in enumerate(roster):
  group=bpy.data.collections.new('КАТАЛОГ / '+row['name']);group.instance_offset=(0,0,0)
  objs=[o for o in source.objects if o.get('Island_ID')==row['id']and o.get('Role')=='PlywoodPiece'];assert objs
  selected=set(objs)
  for o in objs:
   selected.update(o.children)
  for o in selected:group.objects.link(o)
  b=[999,999,-999,-999]
  for o in objs:
   for v in o.bound_box:
    p=o.matrix_world@Vector(v);b[0]=min(b[0],p.x);b[1]=min(b[1],p.y);b[2]=max(b[2],p.x);b[3]=max(b[3],p.y)
  width,height=b[2]-b[0],b[3]-b[1];factor=min((cw-.015)/width,(ch-.034)/height);group.instance_offset=((b[0]+b[2])/2,(b[1]+b[3])/2,0)
  ob=bpy.data.objects.new(f'{i+1:02d} / '+row['name'],None);scene.collection.objects.link(ob);ob.instance_type='COLLECTION';ob.instance_collection=group;ob.location=((i%cols+.5)*cw,-(i//cols+.5)*ch,0);ob.scale=(factor,factor,1);ob['Role']='CatalogInstance';ob['NotProduction']=True;ob['Island_ID']=row['id']
 center=Vector((cols*cw/2,-rows*ch/2,.003));fixtures=setup(scene,center,max(cols*cw,rows*ch)*1.1,False);scene.cycles.samples=16;scene.render.resolution_x=1800;scene.render.resolution_y=2050;scene.camera.data.ortho_scale=max(rows*ch,cols*cw*2050/1800)*1.06;scene.view_layers[0].layer_collection.children[fixtures.name].hide_viewport=True
 return scene
