"""Replace only the former island block in the approved world overview."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector,Quaternion
P=Path(__file__).resolve().parent.parent;R=P.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'world-final-parts-740/04-Мир-общее-расположение.blend'));sc=bpy.context.scene
old=[o for o in sc.objects if o.get('WorldSource')=='01-Islands'];oldwood=sum(o.get('Role')=='PlywoodPiece'for o in old)
roots=[o for o in sc.objects if o.get('Role')=='WorldBlockController'and'01-Islands'in o.get('Source','')]
assert oldwood==73 and len(roots)==1
for o in old:bpy.data.objects.remove(o,do_unlink=True)
for o in roots:bpy.data.objects.remove(o,do_unlink=True)
with bpy.data.libraries.load(str(P/'01-Islands/Сборка.blend'),link=False)as(src,dst):dst.scenes=[next(n for n in src.scenes if n.startswith('01'))]
native=dst.scenes[0];roles={'PlywoodPiece','Engraving','PaintMask','IslandController','AcrylicEngraving'};chosen={o for o in native.objects if o.get('Role')in roles}
for o in list(chosen):
 par=o.parent
 while par:chosen.add(par);par=par.parent
col=bpy.data.collections.new('05 — Исправленные острова и гравировка');sc.collection.children.link(col)
root=bpy.data.objects.new('ОСТРОВА — весь исправленный блок',None);col.objects.link(root);root['Role']='WorldBlockController';root['Source']='islands-corrected-740/01-Islands/Сборка.blend';root.empty_display_type='PLAIN_AXES';root.empty_display_size=.04
for o in chosen:
 col.objects.link(o);o.name='ОСТРОВА / '+o.name;o['WorldSource']='01-Islands'
for o in chosen:
 if o.parent not in chosen:o.parent=root
t=json.load(open(P/'data/world-registration.json'))['russia-asia']['affine'];root.scale=(t[0],t[0],1);root.location=(t[4]/1000,-t[5]/1000,0)
bpy.data.scenes.remove(native);bpy.context.view_layer.update()
newwood=sum(o.get('Role')=='PlywoodPiece'for o in chosen);assert newwood==len(json.load(open(P/'01-Islands/data/production-plan.json'))['pieces'])
sc['Исправленные острова']=str(len(json.load(open(P/'data/island-roster.json'))))+' именованных деревянных островов; мелкие острова — гравировка на оргстекле.';sc['Исходные материки']='Сохранены без изменения геометрии; заменён только прежний островной блок.'
note=(P/'ПРОЧТИ-МЕНЯ.txt').read_text();tx=bpy.data.texts.new('ПРОЧТИ-МЕНЯ — исправление островов');tx.write(note)
center=Vector((1.04,-.67,.003))
for cam in [o for o in sc.objects if o.type=='CAMERA']:
 angled='наклон'in cam.name.lower();cam.data.ortho_scale=2.33;cam.location=center+Vector((0,-.48,2.6)if angled else(0,0,3));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
sc.render.resolution_x=2400;sc.render.resolution_y=1600;sc.cycles.samples=20;sc.cycles.use_denoising=False;sc.view_settings.exposure=-.25
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   v=area.spaces.active;v.region_3d.view_location=center;v.region_3d.view_distance=2.45;v.region_3d.view_rotation=Quaternion((1,0,0,0));v.region_3d.view_perspective='ORTHO'
bpy.data.orphans_purge(do_recursive=True)
wood=[o for o in sc.objects if o.get('Role')=='PlywoodPiece'];assert len(wood)==192+newwood
assert sum(o.get('Role')=='AcrylicEngraving'for o in sc.objects)==1
(P/'data/world-update.json').write_text(json.dumps({'removed_old_wood_parts':oldwood,'new_island_wood_parts':newwood,'world_wood_parts':len(wood),'other_continents_geometry_unchanged':True,'acrylic_engraving_objects':1},ensure_ascii=False,indent=2))
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'Мир-исправленные-острова.blend'),compress=True);print('WORLD CORRECTED',len(wood),'wood parts',flush=True)
if'--no-render'not in sys.argv:sc.render.filepath=str(P/'Мир-исправленные-острова.png');bpy.ops.render.render(write_still=True)
