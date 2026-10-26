import bpy,json,sys,os
sys.path.extend(p for p in os.environ.get('PYTHONPATH','').split(os.pathsep)if p and p not in sys.path)
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent.parent
source=str(P/'data/source/Исходная-сборка.blend')
bpy.ops.wm.open_mainfile(filepath=source);bpy.context.view_layer.update();sc=bpy.context.scene;out=[]
for o in sc.objects:
 if o.type not in ['MESH','CURVE','FONT','EMPTY']:continue
 points=[o.matrix_world@Vector(v)for v in o.bound_box];bounds=[[min(p[i]for p in points)*1000 for i in range(3)],[max(p[i]for p in points)*1000 for i in range(3)]]
 out.append({'name':o.name,'type':o.type,'hidden':o.hide_get(),'hide_render':o.hide_render,'visible':o.visible_get(),'props':{k:str(o[k])[:500]for k in o.keys()},'bounds_mm':bounds,'location':list(o.location),'scale':list(o.scale),'text':o.data.body if o.type=='FONT'else None,'materials':[m.name if m else None for m in getattr(o.data,'materials',[])]})
(P/'data/source/inventory.json').write_text(json.dumps({'blender':bpy.app.version_string,'scene':sc.name,'unit_scale':sc.unit_settings.scale_length,'objects':out},ensure_ascii=False,indent=2))
for row in out:print(row['name'],row['type'],row['visible'],row['props'],row['bounds_mm'],row['text'],flush=True)
print('TOTAL',len(out),flush=True)
