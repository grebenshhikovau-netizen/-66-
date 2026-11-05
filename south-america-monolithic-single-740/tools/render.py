"""Render the actual saved assembly and a close-up of its two bank levels."""
import os,sys,json,math
sys.path.extend(p for p in os.environ.get('PYTHONPATH','').split(os.pathsep)if p)
from pathlib import Path
import bpy
from mathutils import Vector
from shapely.geometry import shape,Point
from scipy.interpolate import RBFInterpolator
import numpy as np
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'))
bpy.ops.wm.open_mainfile(filepath=str(P/'Южная-Америка-производственная-сборка.blend'));s=bpy.data.scenes['01 — Собранная карта']
s.cycles.samples=20;s.cycles.use_denoising=False;s.render.resolution_percentage=100;s.render.resolution_x=1350;s.render.resolution_y=1800
s.render.filepath=str(P/'Южная-Америка-монолит-сборка.png')
if '--detail-only'not in sys.argv:bpy.ops.render.render(write_still=True,scene=s.name)
water=shape(D['base_water_union']);upper=shape(D['layers'][1]);C=json.load(open(P/'data/source/geographic-controls.json'))
w=RBFInterpolator(np.array([[c[1],c[2]]for c in C]),np.array([[c[3],c[4]]for c in C]),kernel='thin_plate_spline',smoothing=1.8);q=w([[-60.021,-3.119]])[0];preferred=Point(q[0]*(1600/4251.9685),q[1]*(1600/4251.9685)-1000)
choices=[]
for r in D['river_lines']:
 if r['name']!='Amazonas':continue
 g=shape(r['geom']);segments=[g]if g.geom_type=='LineString'else g.geoms
 for seg in segments:
  for v in np.arange(.5,seg.length,.7):
   p=seg.interpolate(v)
   if water.covers(p)and .2<p.distance(upper)<1.3:choices.append(p)
assert choices
p=min(choices,key=lambda p:p.distance(preferred));target=Vector((p.x/1000,-p.y/1000,.003));cam=s.camera;cam.location=target+Vector((0,0,.15));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.075
s.render.resolution_x=1800;s.render.resolution_y=1350;s.render.filepath=str(P/'Амазонка-ступенька-крупно.png');bpy.ops.render.render(write_still=True,scene=s.name)
(P/'Проверка-визуализации.json').write_text(json.dumps({'passed':True,'source':'saved production .blend','river_detail_center_mm':[p.x,p.y],'base_channel_present_at_center':True,'distance_to_upper_bank_mm':p.distance(upper)},ensure_ascii=False,indent=2))
print('RENDERS COMPLETE',flush=True)
