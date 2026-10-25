"""Render the saved scene without rebuilding or changing the native project."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent.parent;scene=bpy.context.scene;camera=scene.camera
variant=sys.argv[sys.argv.index('--variant')+1] if '--variant' in sys.argv else 'relief'
scene.render.resolution_x=2600;scene.render.resolution_y=1700;scene.render.resolution_percentage=100;scene.cycles.samples=32;scene.cycles.use_denoising=False;scene.cycles.max_bounces=4;scene.cycles.diffuse_bounces=2;scene.cycles.glossy_bounces=2
names={'relief':'Евразия-Россия-рельеф-3D.png','political':'Евразия-политическая-3D.png','political_water':'Евразия-политическая-с-водой-3D.png'}
if '--details-only' not in sys.argv:
 scene.render.filepath=str(P/names[variant]);bpy.ops.render.render(write_still=True)
if variant=='relief' and '--main-only' not in sys.argv:
 scene.cycles.samples=24
 cfg=json.load(open(P/'data/config.json'));pr=cfg['projection'];s=cfg['mm_per_unit']/1000;mc=math.log(math.tan(math.pi/4+math.radians(pr['latmin'])/2))
 for name,lon,lat,span in [('Европа-Альпы-3D.png',10,47,.30),('Гималаи-Тибет-3D.png',85,31,.28),('Аравия-Иран-3D.png',47,27,.29),('Япония-Фудзи-3D.png',138,36,.12),('Индонезия-3D.png',112,-4,.29),('Тянь-Шань-Памир-3D.png',76,41,.24)]:
  if '--view' in sys.argv and sys.argv[sys.argv.index('--view')+1] not in name:continue
  x=pr['source_xmin']+(lon-pr['lonmin'])*pr['kx_per_degree'];y=pr['source_ymax']-(math.log(math.tan(math.pi/4+math.radians(lat)/2))-mc)*pr['ky_per_mercator'];target=Vector((x*s,(2657.4803125-y)*s,.007))
  camera.location=target+Vector((.025,-.09,.23));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=span;scene.render.resolution_x=1600;scene.render.resolution_y=1250;scene.render.filepath=str(P/name);bpy.ops.render.render(write_still=True)
print('RENDER COMPLETE',variant,flush=True)
