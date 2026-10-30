"""Render the verified combined kit and its useful close-ups without modifying the saved scene."""
import bpy,json,os,sys
sys.path.extend(p for p in os.environ.get('PYTHONPATH','').split(os.pathsep)if p and p not in sys.path)
from pathlib import Path
from mathutils import Vector
from shapely.geometry import shape
from shapely.ops import unary_union
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));bpy.ops.wm.open_mainfile(filepath=str(P/'Сборка-комплекта.blend'));s=bpy.data.scenes['01 — Собранная карта'];cam=s.camera;s.cycles.samples=20;s.cycles.use_denoising=False;s.render.resolution_percentage=100;s.render.filepath=str(P/'Сборка-комплекта.png');bpy.ops.render.render(write_still=True,scene=s.name)
def focus(g,name,w,h,solo_scand=False):
 x0,y0,x1,y1=g.bounds;target=Vector(((x0+x1)/2000,-(y0+y1)/2000,.006));cam.location=target+Vector((.008,-.06,.22));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=(max((x1-x0)/1000,(y1-y0)/1000*w/h)if w>=h else max((y1-y0)/1000,(x1-x0)/1000*h/w))*1.15;s.render.resolution_x=w;s.render.resolution_y=h
 if solo_scand:
  ids={p['id']for p in D['pieces']if p.get('block')=='SCAND'}
  for o in s.objects:
   owner=o.get('Piece_ID')
   if owner and owner not in ids:o.hide_render=True
 s.render.filepath=str(P/name);bpy.ops.render.render(write_still=True,scene=s.name)
 if solo_scand:
  for o in s.objects:
   if o.get('Piece_ID'):o.hide_render=False
if D['batch']=='EAST':
 focus(shape(D['regions']['CHN']),'Китай-реки-и-провинции.png',2300,1800)
else:
 focus(shape(D['pyramid_block']),'Египет-цельная-пирамида.png',1500,1550)
 main=max([shape(p['geom'])for p in D['pieces']if p.get('block')=='SCAND'and p['tier']==1],key=lambda g:g.area);focus(main,'Скандинавия-отдельный-блок.png',1750,2150,True)
print('RENDERS COMPLETE',D['title'],flush=True)
