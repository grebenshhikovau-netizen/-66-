import bpy
from pathlib import Path
P=Path(__file__).resolve().parent.parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Северная-Америка — производственные-слои.blend'))
import json
D=json.load(open(P/'production-plan.json'))
for row in D['pieces']:
 ob=bpy.data.objects[row['id']];ob['Политические части']=', '.join(row['regions'])
for mat in bpy.data.materials:
 if not mat.use_nodes:continue
 bs=mat.node_tree.nodes.get('Principled BSDF')
 if bs:
  bs.inputs['Specular IOR Level'].default_value=.05
  if mat.name=='Гравировка':bs.inputs['Specular IOR Level'].default_value=0;bs.inputs['Base Color'].default_value=(.018,.008,.003,1);bs.inputs['Roughness'].default_value=1
for sc in bpy.data.scenes:
 sc.cycles.use_denoising=False;sc.cycles.samples=64;sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=-.3
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Северная-Америка — производственные-слои.blend'),compress=True)
for scene,filename in [('01 — Собранная карта','Карта-в-сборе.png'),('02 — Три слоя отдельно','Три-слоя-отдельно.png')]:
 sc=bpy.data.scenes[scene];sc.render.filepath=str(P/filename);bpy.ops.render.render(write_still=True,scene=sc.name)
print('RENDERS COMPLETE',flush=True)
