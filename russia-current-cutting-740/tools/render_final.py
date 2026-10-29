import bpy,json,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent.parent;bpy.ops.wm.open_mainfile(filepath=str(P/'Россия-производственная-сборка.blend'));scene=bpy.data.scenes['01 — Собранная карта'];cam=scene.camera;scene.cycles.samples=20;scene.cycles.use_denoising=False;scene.render.resolution_percentage=100;scene.render.resolution_x=2000;scene.render.resolution_y=1250;scene.render.filepath=str(P/'Россия-сборка-3D.png');bpy.ops.render.render(write_still=True,scene=scene.name)
# Local cameras inspect readable western lettering and the required lake ledges.
for filename,center,ortho,width,height in [('Таймыр-ступени-3D.png',(1.055,.873,.006),.060,1450,1250)]:
 target=Vector(center);cam.location=target+Vector((.005,-.035,.13));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=ortho;scene.render.resolution_x=width;scene.render.resolution_y=height;scene.render.filepath=str(P/filename);bpy.ops.render.render(write_still=True,scene=scene.name)
