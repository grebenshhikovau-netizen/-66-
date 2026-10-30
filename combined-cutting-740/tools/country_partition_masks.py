"""Classify the complete approved coastline; country reference rims must not become scraps."""
import gzip,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from scipy.ndimage import distance_transform_edt
from skimage.measure import find_contours
from shapely.geometry import shape,mapping,Polygon
from shapely.ops import unary_union
from shapely import make_valid,set_precision
P=Path(__file__).resolve().parent.parent;E=json.load(gzip.open(P/'data/source/EU-approved-plan.json.gz','rt'));C=json.load(open(P/'data/batch-countries.json'));west=set(C['west']);scand=set(C['scandinavia_separate_block']);land=unary_union([shape(g)for g in E['layers']]);x0,y0,x1,y1=land.bounds;step=.15;ox=x0-5;oy=y0-5;w=math.ceil((x1-x0+10)/step)+1;h=math.ceil((y1-y0+10)/step)+1;a=np.zeros((h,w),np.uint8)
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in ps(q)]
for c,g in sorted(E['regions'].items(),key=lambda v:-shape(v[1]).area):
 im=Image.new('1',(w,h));dr=ImageDraw.Draw(im)
 for p in ps(shape(g)):
  dr.polygon([((x-ox)/step,(y-oy)/step)for x,y in p.exterior.coords],fill=1)
  for r in p.interiors:dr.polygon([((x-ox)/step,(y-oy)/step)for x,y in r.coords],fill=0)
 a[np.asarray(im,dtype=np.uint8)>0]=3 if c in scand else 2 if c in west else 1
idx=distance_transform_edt(a==0,return_distances=False,return_indices=True);a=a[tuple(idx)];del idx;a=np.asarray(Image.fromarray(a).filter(ImageFilter.ModeFilter(3)))
def contour_mask(binary):
 loops=[]
 for cc in find_contours(np.pad(binary.astype(np.uint8),1),.5):
  if len(cc)<4:continue
  coords=[(ox+(float(x)-1)*step,oy+(float(y)-1)*step)for y,x in cc];g=Polygon(coords)
  if not g.is_valid:g=make_valid(g)
  loops.extend(ps(g))
 loops.sort(key=lambda g:-g.area);g=Polygon()
 for q in loops:g=g.symmetric_difference(q)
 return set_precision(g.simplify(.06,preserve_topology=True),.001)
wm=contour_mask(a!=1);sm=contour_mask(a==3);out={'step_mm':step,'west_mask':mapping(wm),'scandinavia_mask':mapping(sm),'method':'nearest country partition of entire approved coastline, shared categorical grid'};(P/'data/source/batch-partition-masks.json').write_text(json.dumps(out));print('FULL COAST PARTITIONS READY',wm.area,sm.area,flush=True)
