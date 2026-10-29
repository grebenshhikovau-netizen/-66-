import bpy,json,sys,os
sys.path.extend(p for p in os.environ.get('PYTHONPATH','').split(os.pathsep)if p and p not in sys.path)
from pathlib import Path
from shapely.geometry import Polygon,mapping
from shapely.ops import unary_union
from shapely import make_valid,set_precision
P=Path(__file__).resolve().parent.parent;bpy.context.preferences.filepaths.use_scripts_auto_execute=False;bpy.ops.wm.open_mainfile(filepath=str(P/'data/source/Исходная-сборка.blend'));bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();rows=[];texts=[];names={}
for o in bpy.context.scene.objects:
 role=o.get('Role');code=o.get('Region_ID')or o.get('Country_ID')
 if role=='RegionRoot'and code:
  tail=o.name.split('__',1)[-1];names[code]=tail.rsplit('.',1)[0]if tail.rsplit('.',1)[-1].isdigit()else tail
 if not o.visible_get()or o.hide_render:continue
 if role=='Engraving':
  word=o.get('Текст')or (o.data.body if o.type=='FONT'else None)
  if word:
   corners=[o.matrix_world@__import__('mathutils').Vector(v)for v in o.bound_box];texts.append({'name':o.name,'region':code,'text':word,'center_mm':[sum(p.x for p in corners)*125,-sum(p.y for p in corners)*125],'z_mm':max(p.z for p in corners)*1000})
  continue
 if role!='PlywoodPiece'or o.type!='MESH':continue
 eg=o.evaluated_get(dg);mesh=eg.to_mesh();vertices=[eg.matrix_world@v.co for v in mesh.vertices];lo=min(v.z for v in vertices)*1000;hi=max(v.z for v in vertices)*1000
 if hi-lo<.1:rows.append({'name':o.name,'region':code,'kind':'collapsed','lo_mm':lo,'hi_mm':hi});eg.to_mesh_clear();continue
 faces=[];recess=[]
 for f in mesh.polygons:
  p=Polygon([(round(vertices[i].x*1000,5),round(-vertices[i].y*1000,5))for i in f.vertices])
  if p.area<1e-7:continue
  faces.append(p if p.is_valid else make_valid(p))
  if f.material_index==2 and max(vertices[i].z*1000 for i in f.vertices)<hi-.1:recess.append(p)
 g=set_precision(make_valid(unary_union(faces)),.002);rg=unary_union(recess)
 rows.append({'name':o.name,'region':code,'kind':'wood','lo_mm':lo,'hi_mm':hi,'legacy_tier':o.get('Tier'),'geom':mapping(g),'recess':mapping(rg),'area_mm2':g.area});eg.to_mesh_clear();print('EXTRACT',o.name,'top',round(hi,2),'area',round(g.area,2),flush=True)
(P/'data/source/extracted.json').write_text(json.dumps(rows,ensure_ascii=False));(P/'data/source/source-texts.json').write_text(json.dumps(texts,ensure_ascii=False,indent=2));(P/'data/source/region-names.json').write_text(json.dumps(names,ensure_ascii=False,indent=2));print('EXTRACTED',len(rows),'LABELS',len(texts),'NAMES',len(names),flush=True)
