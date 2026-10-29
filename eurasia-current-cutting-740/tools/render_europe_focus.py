import bpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent.parent;bpy.ops.wm.open_mainfile(filepath=str(P/'Евразия-производственная-сборка.blend'));s=bpy.data.scenes['01 — Собранная карта'];cam=s.camera;target=Vector((.665,.575,.006));cam.location=target+Vector((.008,-.055,.20));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.32;s.render.resolution_x=2000;s.render.resolution_y=1650;s.render.resolution_percentage=100;s.cycles.samples=20;s.cycles.use_denoising=False;s.render.filepath=str(P/'Европа-крупно-3D.png');bpy.ops.render.render(write_still=True,scene=s.name)
