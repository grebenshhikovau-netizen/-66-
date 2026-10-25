import bpy,bmesh,json,os,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent.parent;bpy.ops.wm.open_mainfile(filepath=str(P/'Северная-Америка — производственные-слои.blend'));sc=bpy.data.scenes['01 — Собранная карта'];bpy.context.window.scene=sc;woods=[o for o in sc.objects if o.get('Role')=='PlywoodPiece'];assert len(woods)==len(json.load(open(P/'production-plan.json'))['pieces']);assert len(bpy.data.scenes)==2
bad=[]
for o in woods:
 bm=bmesh.new();bm.from_mesh(o.data);n=sum(not e.is_manifold for e in bm.edges);bm.free()
 if n:bad.append([o.name,n])
 assert abs(min(v.co.z for v in o.data.vertices))<1e-8
 assert abs(max(v.co.z for v in o.data.vertices)-.003)<1e-8
assert not bad,bad
bpy.context.view_layer.update()
for o in woods:
 assert abs(o.matrix_world.translation.z-(o['Tier']-1)*.003)<2e-6
 for child in o.children:
  assert child.parent==o
  assert child.matrix_world.translation.z>=o.matrix_world.translation.z+.003-1e-7
  if child.type=='CURVE':assert all(s.use_cyclic_u for s in child.data.splines)
D=json.load(open(P/'production-plan.json'))
for coat,rgb in D['colors'].items():
 mat=bpy.data.materials.get('Фанера без покраски'if coat=='NATURAL'else'ПОКРЫТИЕ — '+coat);assert mat and all(abs(mat.diffuse_color[i]-rgb[i])<1e-6 for i in range(3)),coat
fonts=[f for f in bpy.data.fonts if f.filepath and f.filepath!='<builtin>'];assert all(f.packed_file for f in fonts)
R={'opened_with_blender':bpy.app.version_string,'wood_count':len(woods),'closed_manifold_solids':True,'bottom_origins':True,'nominal_ply_thickness_mm':3,'children_above_top':True,'curve_splines_cyclic':True,'external_fonts_packed':True,'coat_colors_match_corrected_plan':True,'scenes':[s.name for s in bpy.data.scenes]};(P/'Проверка-повторного-открытия.json').write_text(json.dumps(R,ensure_ascii=False,indent=2));print('SAVED BLEND VERIFIED',R,flush=True)
