"""Keep Taymyr's branching shoreline in the narrow lower cut, instead of scaling arms away."""
import json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt
from skimage.morphology import skeletonize
from shapely.geometry import shape,Point,mapping,Polygon
from shapely.ops import unary_union
from shapely import make_valid,set_precision
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));upper=shape(D['upper_water']['Таймыр']);old=shape(D['base_water']['Таймыр']);step=.05;x0,y0,x1,y1=upper.bounds;pad=4;ox=x0-pad*step;oy=y0-pad*step;im=Image.new('1',(math.ceil((x1-x0)/step)+2*pad+1,math.ceil((y1-y0)/step)+2*pad+1));dr=ImageDraw.Draw(im)
ps=[upper]if upper.geom_type=='Polygon'else list(upper.geoms)
for q in ps:
 dr.polygon([((x-ox)/step,(y-oy)/step)for x,y in q.exterior.coords],fill=1)
 for h in q.interiors:dr.polygon([((x-ox)/step,(y-oy)/step)for x,y in h.coords],fill=0)
a=np.array(im,dtype=np.uint8)>0;dist=distance_transform_edt(a)*step;sk=skeletonize(a);yy,xx=np.where(sk);disks=[]
for x,y in zip(xx,yy):
 radius=float(dist[y,x])*.55
 if radius<.13:continue
 disks.append(Point(ox+float(x)*step,oy+float(y)*step).buffer(radius,quad_segs=6))
new=unary_union(disks).buffer(.08,quad_segs=6).buffer(-.08,quad_segs=6).simplify(.025,preserve_topology=True).intersection(upper.buffer(-.10));new=set_precision(make_valid(new),.001)
if new.geom_type!='Polygon':new=max([q for q in new.geoms if q.geom_type=='Polygon'],key=lambda q:q.area)
assert new.is_valid and new.difference(upper.buffer(.00001)).area<.001;assert upper.area>new.area*1.3
# Source placement and typography stay fixed; no label or upper ply occupies the modified water.
for p in D['pieces']:
 if p['tier']!=1:continue
 g=shape(p['geom'])
 if g.intersection(upper).area<1:continue
 before=g;g=set_precision(make_valid(g.union(old).difference(new)),.001);assert g.geom_type=='Polygon';p['geom']=mapping(g);p['area_mm2']=g.area;p['visible']=mapping(g.difference(shape(D['layers'][1])))
 for label in D['labels']:
  if label['piece']==p['id']:assert shape(label['bbox']).difference(g).area<.0001
 for mark in D['city_markers']:
  if mark['piece']==p['id']:assert shape(mark['geom']).difference(g).area<.0001
old_feature_union=unary_union([shape(v)for v in D['base_water'].values()]);extras=shape(D['water_base_union']).difference(old_feature_union);D['base_water']['Таймыр']=mapping(new);D['water_base_union']=mapping(unary_union([shape(v)for v in D['base_water'].values()]+[extras]));D['layers'][0]=mapping(unary_union([shape(p['geom'])for p in D['pieces']if p['tier']==1]));D['visible'][0]=mapping(shape(D['layers'][0]).difference(shape(D['layers'][1])));D['taymyr_lower_profile_method']='smoothed medial-axis envelopes at 55 percent local bank radius';D['parameters']['taymyr_lower_profile']='local_width_medial_axis';(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));(P/'data/water-reference.json').write_text(json.dumps([{'name':'Оргстекло_под_водой_СПРАВОЧНО','geom':D['water_base_union']}],ensure_ascii=False));(P/'Таймыр-профиль.json').write_text(json.dumps({'lower_profile_method':D['taymyr_lower_profile_method'],'upper_area_mm2':upper.area,'old_lower_area_mm2':old.area,'new_lower_area_mm2':new.area,'lower_connected_closed_outline':True,'labels_unchanged':True,'parts_unchanged':len(D['pieces'])},ensure_ascii=False,indent=2));print('TAYMYR REFINED',upper.area,old.area,new.area,flush=True)
