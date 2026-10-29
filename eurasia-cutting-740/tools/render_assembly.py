import bpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent.parent;bpy.ops.wm.open_mainfile(filepath=str(P/'Евразия-производственная-сборка.blend'));scene=bpy.data.scenes['01 — Собранная карта'];cam=scene.camera;scene.cycles.samples=20;scene.cycles.use_denoising=False;scene.render.resolution_percentage=100;scene.render.filepath=str(P/'Евразия-сборка-3D.png');bpy.ops.render.render(write_still=True,scene=scene.name)
for filename,center,ortho,width,height in [('Европа-крупно-3D.png',(.645,.704,.006),.33,1900,2000),('Азия-реки-3D.png',(1.015,.492,.006),.34,2000,1550)]:
 target=Vector(center);cam.location=target+Vector((.008,-.055,.20));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=ortho;scene.render.resolution_x=width;scene.render.resolution_y=height;scene.render.filepath=str(P/filename);bpy.ops.render.render(write_still=True,scene=scene.name)
