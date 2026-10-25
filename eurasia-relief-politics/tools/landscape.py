"""One continuous six-step artistic landscape, with protected Russian seam levels."""
import json,math
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree
import contourpy
from shapely.geometry import Polygon,Point,LineString,shape
from shapely.ops import unary_union
from shapely import contains_xy
from common import DATA,C,M,xy,project,clean,polys,polygonal

def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

def build_landscape(base,features):
 A=np.load(DATA/'dem-eurasia.npz');lon,lat=A['lon'],A['lat'];xx,yy=np.meshgrid(lon,lat)
 z=gaussian_filter(np.maximum(A['z'],0),C['style']['dem_smoothing_pixels'])
 anchors=[-28,0,25,45,65,85,110,135,150]
 rows=[[55,55,65,80,110,150,100,110,110],[150,150,190,260,450,550,400,450,450],[420,420,550,800,1100,1300,1000,1100,1100],[1050,1050,1250,1700,2100,2600,2200,2300,2300],[2100,2100,2400,3100,3900,4300,3900,3800,3800]]
 thresholds=np.array([np.broadcast_to(np.interp(lon,anchors,r),z.shape).copy() for r in rows])
 # Broad Tibet steps retain the plateau below the exceptional Himalayan ridge.
 tib=smooth(70,76,xx)*(1-smooth(102,109,xx))*smooth(24,28,yy)*(1-smooth(37,42,yy))
 for k,h in enumerate([260,950,2200,4200,5800]):thresholds[k]=thresholds[k]*(1-tib)+h*tib
 gob=smooth(88,96,xx)*(1-smooth(112,120,xx))*smooth(37,41,yy)*(1-smooth(46,51,yy))
 for k,h in enumerate([350,850,1500,2400,4100]):thresholds[k]=thresholds[k]*(1-gob)+h*gob
 field=np.ones_like(z);low=np.zeros_like(z)
 for high in thresholds:
  field+=np.clip((z-low)/np.maximum(high-low,1),0,1);low=high
 sx,sy=xy(xx,yy);xm,ym=sx*M,sy*M
 # Mounds follow real mountain provinces. Their overlapping broad shoulders are
 # added to the same elevation field, never drawn as detached buffered strips.
 mounds=[
  (6.8,46.0,9,4,0,1.1),(9.5,46.5,12,5,-5,1.0),(12.5,46.6,8,4,10,.7),(.6,42.7,10,4,-10,.6),
  (13,43,14,4,50,.6),(20,49,7,5,-10,.5),(24,48,8,5,25,.5),(25,45.8,8,5,-15,.5),
  (7.5,61,6,14,-10,.65),(11,65,6,16,-10,.6),(18,68,7,15,-25,.5),(17,44,11,4,45,.55),(24.4,42.8,9,4,0,.4),(-4.7,57.2,6,7,-10,.5),
  (74,42,10,5,-5,.8),(79,42.2,11,5,-5,.85),(83,43,8,4,5,.6),(80,45.1,6,4,-15,.6),(72.5,38.5,9,8,0,.65),
  (77,32.5,12,6,25,.9),(83,29.3,17,6,20,1.0),(88,27.8,16,6,-5,1.0),(93,28,10,6,-25,.9),(76.5,35.5,8,5,10,.8),
  (85,36,22,5,-5,.5),(99.5,38.4,12,5,-15,.6),(99,29,6,16,-10,.65),(70.8,48.9,17,10,0,.3),
  (77,18,17,24,0,.3),(75.5,14.7,4,17,-15,.6),(82,18,5,16,-15,.2),
  (34,37,14,5,-5,.5),(39.2,40.5,12,5,0,.5),(34,39,15,9,0,.25),(48.5,31.5,17,5,45,.6),(51.4,36,12,4,0,.65),(55,32,19,16,0,.25),
  (41.7,20,5,19,-20,.6),(57.2,23.2,8,4,-35,.65),(44,15.5,10,8,0,.5),(102,22,9,15,-5,.45),
  (138,37,6,17,-35,.4),(101,-.5,5,20,35,.45),(110,-7.5,18,3,0,.45),(115,1,14,13,0,.4),(121,-2,10,15,0,.35),(-19,65,12,9,0,.5)]
 prominence=np.zeros_like(z)
 for lo,la,wx,wy,angle,strength in mounds:
  cx,cy=xy(lo,la);dx=xm-cx*M;dy=ym-cy*M;t=math.radians(angle);u=dx*math.cos(t)+dy*math.sin(t);v=-dx*math.sin(t)+dy*math.cos(t)
  prominence=np.maximum(prominence,strength*np.exp(-.5*(u*u/wx**2+v*v/wy**2)))
 field+=prominence
 # Large low dunes grow out of the same desert plateaux; dry valleys remain wood.
 for lo,la,wx,wy,amp,angle in [(49.5,20.5,21,12,.42,-20),(41.2,28,10,8,.3,15),(105,43,28,15,.2,10),(83,39,20,9,.25,0),(70.7,27.5,12,13,.22,10),(63,42.5,16,9,.15,-15),(59,39.5,13,10,.15,-10)]:
  cx,cy=xy(lo,la);dx=xm-cx*M;dy=ym-cy*M;t=math.radians(angle);u=dx*math.cos(t)+dy*math.sin(t);v=-dx*math.sin(t)+dy*math.cos(t)
  envelope=np.exp(-.5*(u*u/wx**2+v*v/wy**2));waves=.5+.5*np.sin(v/4+.28*np.sin(u/12));field+=amp*envelope*waves
 field=gaussian_filter(field,[.5,.65])
 # Heights at the shared Russian edge are read from its frozen authored layers.
 RU=json.load(open(DATA/'russia-reference.json'));seam=shape(json.load(open(DATA/'russia-shared-seam.json')));rus=shape(RU['source_outline']);samples=[];inner=[]
 lines=list(seam.geoms) if hasattr(seam,'geoms') else [seam]
 for line in lines:
  if line.geom_type not in ['LineString','LinearRing'] or line.length<.001:continue
  for t in np.linspace(0,line.length,max(2,math.ceil(line.length*M/.45))):
   q=line.interpolate(t);a=line.interpolate(max(0,t-.2));b=line.interpolate(min(line.length,t+.2));dx,dy=b.x-a.x,b.y-a.y;l=math.hypot(dx,dy)
   if l<1e-12:continue
   nx,ny=-dy/l*.025/M,dx/l*.025/M;p=Point(q.x+nx,q.y+ny)
   if not rus.covers(p):p=Point(q.x-nx,q.y-ny)
   samples.append((q.x,q.y));inner.append((p.x,p.y))
 if samples:
  samples=np.array(samples);inner=np.array(inner);target=np.zeros(len(inner))
  for i,g in enumerate(RU['layers'],1):target[contains_xy(shape(g),inner[:,0],inner[:,1])]=i
  dist,idx=cKDTree(samples).query(np.column_stack([sx.ravel(),sy.ravel()]),workers=4);dist=dist.reshape(z.shape)*M;idx=idx.reshape(z.shape)
  mix=(1-smooth(0,C['style']['seam_blend_mm'],dist));field=field*(1-mix)+(target[idx]+.35)*mix
 cg=contourpy.contour_generator(x=lon,y=lat,z=field,fill_type='OuterOffset');layers=[base]
 for tier in range(2,7):
  points,offsets=cg.filled(tier,100);geoms=[]
  for ps,offs in zip(points,offsets):
   rings=[ps[a:b] for a,b in zip(offs[:-1],offs[1:])]
   if rings:geoms.append(Polygon(rings[0],rings[1:]))
  raw=project(unary_union(geoms)).intersection(base)
  g=clean(raw,area=C['production']['ordinary_min_area_mm2'][tier-1],join=C['production']['join_radius_mm'],neck=C['production']['min_neck_mm'],simplify=C['production']['simplify_mm'],holes=C['production']['min_terrain_hole_mm2'])
  # On small separate islands, retain one connected natural upper silhouette.
  for island in polys(base):
   area=island.area*M*M
   if 8<=area<550 and tier<=4:
    options=sorted(polys(raw.intersection(island)),key=lambda p:-p.area)
    if options and options[0].area*M*M>=1.8:g=unary_union([g,clean(options[0],simplify=.09)])
  layers.append(polygonal(g.intersection(base)))
  print('FIELD LEVEL',tier,'components',len(polys(layers[-1])),'area',round(layers[-1].area*M*M),flush=True)
 return layers,{'method':'continuous_elevation_field','tibet_plateau_remapped':True,'same_six_heights_mm':[3,6,9,12,15,18],'shared_russian_height_samples':len(samples)}
