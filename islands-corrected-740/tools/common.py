"""Three complementary CNC kits in the original Mercator atlas coordinates.
Coasts: original atlas. Australia/island terraces: NOAA ETOPO 10 bed/topography.
Greenland: intentionally decorative ice dome (not a bedrock-derived ice surface).
"""
import json,math,sys,shutil
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from shapely import make_valid,set_precision,prepare
from shapely.geometry import shape,mapping,Polygon,Point,LineString,box
from shapely.ops import unary_union,transform,nearest_points,linemerge,polylabel
from shapely.affinity import scale,translate,rotate,affine_transform
from font_geometry import word_geom
P=Path(__file__).resolve().parent.parent
PROJ=json.load(open(P/'data/source/world-projection.json'))
def project(lon,lat):
 return PROJ['lon_to_x_mm']*np.asarray(lon)+PROJ['x_offset_mm'],PROJ['y_offset_mm']-PROJ['mercator_to_y_mm']*np.log(np.tan(np.pi/4+np.radians(lat)/2))
C={x['code']:x for x in json.load(open(P/'data/source/master-countries.json'))}
DEM=gaussian_filter(np.fromfile(P/'data/source/etopo10_bed_g_i2.bin',dtype='<i2').reshape(1081,2161).astype(float),1)
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty and g.area>1e-7 else[]
 return[p for q in getattr(g,'geoms',[])for p in ps(q)]
def ls(g):
 if g.geom_type in ['LineString','LinearRing']:return[g]if g.length>.15 else[]
 return[l for q in getattr(g,'geoms',[])for l in ls(q)]
def polygonal(g):return unary_union(ps(make_valid(g)))
def smooth(g,r=.35,t=.18,minarea=3):
 g=polygonal(g);g=g.buffer(r,quad_segs=6).buffer(-2*r,quad_segs=6).buffer(r,quad_segs=6).simplify(t,preserve_topology=True)
 return unary_union([Polygon(p.exterior,[r for r in p.interiors if Polygon(r).area>8])for p in ps(g)if p.area>=minarea])
def terrace(base,threshold,minarea=35,close=2):
 x0,y0,x1,y1=base.bounds;lon0=(x0-PROJ['x_offset_mm'])/PROJ['lon_to_x_mm'];lon1=(x1-PROJ['x_offset_mm'])/PROJ['lon_to_x_mm'];inv=lambda y:math.degrees(2*math.atan(math.exp((PROJ['y_offset_mm']-y)/PROJ['mercator_to_y_mm']))-math.pi/2);lat0=inv(y1);lat1=inv(y0)
 j0=max(0,int((lon0+180)*6)-4);j1=min(2161,int((lon1+180)*6)+5);i0=max(0,int((90-lat1)*6)-4);i1=min(1081,int((90-lat0)*6)+5)
 if j1-j0<2 or i1-i0<2:return Polygon()
 lon=-180+np.arange(j0,j1)/6;lat=90-np.arange(i0,i1)/6;z=DEM[i0:i1,j0:j1]
 if z.max()<threshold:return Polygon()
 fig,ax=plt.subplots();cs=ax.contourf(lon,lat,z,levels=[threshold,10000]);rings=cs.get_paths()[0].to_polygons();plt.close(fig);out=[];holes=[]
 outer_sign=1
 if len(rings):
  largest=max(rings,key=lambda r:abs(np.sum(r[:-1,0]*r[1:,1]-r[1:,0]*r[:-1,1])));outer_sign=1 if np.sum(largest[:-1,0]*largest[1:,1]-largest[1:,0]*largest[:-1,1])>0 else -1
 for r in rings:
  if len(r)<4:continue
  sign=np.sum(r[:-1,0]*r[1:,1]-r[1:,0]*r[:-1,1]);p=Polygon(r)
  (out if sign*outer_sign>0 else holes).append(p)
 land=polygonal(unary_union(out).difference(unary_union(holes)))
 g=transform(project,land).intersection(base.buffer(-1.2));g=smooth(g,close,.3,minarea)
 return unary_union([q for q in ps(g.intersection(base.buffer(-.6)))if q.area>=minarea and not q.buffer(-1).is_empty])
def write_json(path,d):path.write_text(json.dumps(d,ensure_ascii=False))
class Kit:
 def __init__(self,key,title,base,layers):
  self.key=key;self.title=title;self.path=P/key;self.path.mkdir(exist_ok=True);(self.path/'data').mkdir(exist_ok=True)
  self.layers=layers;self.pieces=[];self.labels=[];self.markers=[];self.busy=[];self.failed=[];self.regions=[]
  for i,g in enumerate(layers):
   for j,p in enumerate(sorted(ps(g),key=lambda p:-p.area)):
    self.pieces.append({'id':f'L{i+1:02d}_P{j+1:03d}','tier':i+1,'geom':mapping(set_precision(p,.00001)),'area_mm2':p.area,'regions':[key],'red_internal':mapping(LineString()),'engraving':mapping(Polygon())})
  for r in self.pieces:
   r['_g']=shape(r['geom']);r['_visible']=r['_g'].difference(layers[r['tier']] if r['tier']<len(layers)else Polygon());r['_eng']=[]
 def label(self,text,target,kind='city',territory=None,sizes=None,maxdistance=14,only_tiers=None,owner_ids=None):
  x,y=target;words=[word_geom(line)for line in text.split('\n')];width=max(g.bounds[2]-g.bounds[0]for g in words);textlines=[];shapes=[]
  for i,(line,g)in enumerate(zip(text.split('\n'),words)):
   xx=(width-(g.bounds[2]-g.bounds[0]))/2-g.bounds[0];yy=i*1.30;textlines.append({'text':line,'x_em':xx,'y_em':yy});shapes.append(translate(g,xx,yy))
  raw=unary_union(shapes);sizes=sizes or ([2.35,2.15,1.95,1.8]if kind=='city'else [3.2,2.8,2.5]if kind=='region'else [6,5,4]);best=None
  own=territory if territory is not None else self.layers[0];point=Point(x,y)
  # Only natural faces of this island/region may receive the caption.
  surfaces=[]
  for r in self.pieces:
   if only_tiers is not None and r['tier']not in only_tiers:continue
   if owner_ids is not None and r['id']not in owner_ids:continue
   surface=polygonal(r['_visible'].intersection(own)).buffer(-.25)
   if surface.is_empty or point.distance(surface)>maxdistance:continue
   prepare(surface);surfaces.append((r,surface))
  if not surfaces:self.failed.append({'text':text,'reason':'no sufficiently large visible surface'});return False
  for tilt in [0,-15,15,-30,30,-45,45,-60,60,-75,75,90]:
   for size in sizes:
    ink=rotate(scale(raw,xfact=size,yfact=size,origin=(0,0)),tilt,origin=(0,0));frame=rotate(scale(box(*raw.bounds),xfact=size,yfact=size,origin=(0,0)),tilt,origin=(0,0));b=ink.bounds;w=b[2]-b[0];h=b[3]-b[1]
    for r,surface in surfaces:
     anchor=nearest_points(point,surface)[1];candidates=[]
     if kind=='city':
      for dist in [1.2,2.5,4,6,9,12]:
       for angle in [0,180,90,270,45,135,225,315]:
        a=math.radians(angle);cx=anchor.x+math.cos(a)*(w/2+dist);cy=anchor.y+math.sin(a)*(h/2+dist);candidates.append((cx,cy))
      for oy in np.arange(-maxdistance,maxdistance+.1,1.2):
       for ox in np.arange(-maxdistance-w*.4,maxdistance+w*.4+.1,1.2):
        if abs(oy)+abs(ox)>maxdistance+w*.4:continue
        candidates.append((anchor.x+ox,anchor.y+oy))
     else:
      candidates.extend([(x,y),tuple(surface.representative_point().coords)[0]])
      for p in sorted(ps(surface),key=lambda p:-p.area)[:4]:
       bx=p.bounds
       pole=polylabel(p,tolerance=.1);candidates.append((pole.x,pole.y))
       step=max(.4,max(bx[2]-bx[0],bx[3]-bx[1])/45)
       for yy in np.arange(bx[1],bx[3]+step,step):
        for xx in np.arange(bx[0],bx[2]+step,step):candidates.append((xx,yy))
       for fy in [.25,.4,.55,.7]:
        for fx in [.25,.4,.55,.7]:candidates.append((bx[0]+fx*(bx[2]-bx[0]),bx[1]+fy*(bx[3]-bx[1])))
      for oy in np.arange(-maxdistance,maxdistance+.1,max(1.5,maxdistance/25)):
       for ox in np.arange(-maxdistance,maxdistance+.1,max(1.5,maxdistance/25)):
        if abs(ox)+abs(oy)<maxdistance:candidates.append((x+ox,y+oy))
     for cx,cy in candidates:
      if math.hypot(cx-x,cy-y)>maxdistance+w*.55:continue
      dx=cx-(b[0]+b[2])/2;dy=cy-(b[1]+b[3])/2;bbox=translate(frame,dx,dy).buffer(.22,join_style=2)
      if not surface.covers(bbox)or any(bbox.intersects(q)for q in self.busy):continue
      penalty=math.hypot(cx-x,cy-y)+((max(sizes)-size)*12)+abs(tilt)*.025
      if best is None or penalty<best[0]:best=(penalty,r,size,dx,dy,translate(ink,dx,dy),bbox,anchor,tilt)
    if best:break
   if best:break
  if best is None:self.failed.append({'text':text,'reason':'caption would collide or cross a terrace/coast'});return False
  _,r,size,dx,dy,ink,bbox,anchor,tilt=best;ang=math.radians(tilt);ident=f'TEXT_{len(self.labels)+1:03d}';color='#0000ff'if kind=='country'else '#ff0000'
  self.labels.append({'id':ident,'text':text,'kind':kind,'piece':r['id'],'color':color,'font_size_mm':size,'matrix':[math.cos(ang),math.sin(ang),-math.sin(ang),math.cos(ang),dx,dy],'lines':textlines,'outline_for_validation':mapping(ink)});r['_eng'].append(ink);self.busy.append(bbox)
  if kind=='city':
   dot=anchor.buffer(.22,quad_segs=8)
   if r['_visible'].covers(dot)and not any(dot.buffer(.15).intersects(q)for q in self.busy):
    self.markers.append({'id':ident+'_DOT','piece':r['id'],'point':[anchor.x,anchor.y]});r['_eng'].append(dot);self.busy.append(dot.buffer(.4))
  return True
 def admin(self,features):
  # Unique shared boundaries only; no doubled coastlines and no lines under upper plies.
  geoms=[g for name,g in features];network=[]
  for i,g in enumerate(geoms):
   for h in geoms[:i]:network.extend(ls(g.boundary.intersection(h.boundary)))
  network=unary_union(network).simplify(.25,preserve_topology=True);self.regions=[name for name,g in features]
  for r in self.pieces:
   lines=ls(network.intersection(r['_visible'].buffer(-.30)))
   clean=unary_union(lines);clean=linemerge(clean)if clean.geom_type=='MultiLineString'else clean
   r['red_internal']=mapping(clean)
 def save(self,notes):
  for r in self.pieces:
   protected=unary_union([shape(a['outline_for_validation']).envelope.buffer(.35)for a in self.labels if a['piece']==r['id']]);net=unary_union([l for l in ls(shape(r['red_internal']).difference(protected))if l.length>=.7]);r['red_internal']=mapping(net);r['_eng'].append(net.buffer(.045,quad_segs=3))
   r['engraving']=mapping(unary_union(r['_eng']).intersection(r['_visible']));r['paint']={};del r['_g'];del r['_eng'];del r['_visible']
  d={'title':self.title,'key':self.key,'layers':[mapping(g)for g in self.layers],'pieces':self.pieces,'labels':self.labels,'city_markers':self.markers,'country_names':{self.key:self.title},'colors':{'NATURAL':[.72,.53,.31]},'regions':self.regions,'summary':[{'tier':i+1,'pieces':sum(r['tier']==i+1 for r in self.pieces)}for i in range(len(self.layers))],'notes':notes,'omitted_labels':self.failed}
  # Use exactly the approved Russia/Asia + Africa/Europe manufacturing XY scale.
  # The world overview applies the same atlas registration to old and new kits.
  reg=json.load(open(P/'data/world-registration.json'))['russia-asia']['affine'];s=reg[0];tx,ty=reg[4:];inv=[1/s,0,0,1/s,-tx/s,-ty/s]
  d['layers']=[mapping(affine_transform(shape(g),inv))for g in d['layers']]
  for r in d['pieces']:
   for key in ['geom','engraving','red_internal']:r[key]=mapping(affine_transform(shape(r[key]),inv))
   r['area_mm2']/=s*s
  for a in d['labels']:
   a['font_size_mm']/=s;a['matrix'][4]=(a['matrix'][4]-tx)/s;a['matrix'][5]=(a['matrix'][5]-ty)/s;a['outline_for_validation']=mapping(affine_transform(shape(a['outline_for_validation']),inv))
  for m in d['city_markers']:m['point']=[(m['point'][0]-tx)/s,(m['point'][1]-ty)/s];m['radius_mm']=.22/s
  d['production_frame']='Approved combined Russia/Asia and Africa/Europe manufacturing frame';d['atlas_registration_xy']=reg
  write_json(self.path/'data/production-plan.json',d);print(self.key,len(self.pieces),'pieces',len(self.labels),'captions',self.regions,'omitted:',[x['text']for x in self.failed],flush=True)
  return d
