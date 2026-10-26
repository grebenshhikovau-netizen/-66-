import bpy
from pathlib import Path
P=Path(__file__).resolve().parent.parent;bpy.ops.wm.open_mainfile(filepath=str(P/'Южная-Америка-производственная-сборка.blend'));sc=bpy.data.scenes['01 — Собранная карта'];sc.cycles.samples=20;sc.cycles.use_denoising=False;sc.render.resolution_percentage=100;sc.render.filepath=str(P/'Южная-Америка-сборка-3D.png');bpy.ops.render.render(write_still=True,scene=sc.name)
