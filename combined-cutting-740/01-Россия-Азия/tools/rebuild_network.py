"""Trace a single shared border graph from the country mosaic; never smooth both sides independently."""
import json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from scipy.ndimage import distance_transform_edt
from shapely.geometry import shape,mapping,LineString
from shapely.ops import unary_union,linemerge
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));regions={c:shape(g)for c,g in D['regions'].items()};
if D['batch']=='EAST':
 refs=json.load(open(P.parent/'data/source/europe-asia-country-province-reference.json'));meta=json.load(open(P.parent/'data/source/europe-asia-country-metadata.json'));china=regions.pop('CHN');provinces={c:shape(refs[c]).intersection(china)for c,m in meta.items()if m['country']=='CHN'};regions.update(provinces);D['china_province_regions']={c:mapping(g)for c,g in provinces.items()}
codes=sorted(regions);land=shape(D['layers'][0]);x0,y0,x1,y1=land.bounds;step=.18;ox=math.floor(x0)-1;oy=math.floor(y0)-1;w=math.ceil((x1-ox+1)/step)+1;h=math.ceil((y1-oy+1)/step)+1;labels=np.zeros((h,w),np.uint8)
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for a in getattr(g,'geoms',[])for p in ps(a)]
for c in sorted(codes,key=lambda c:-regions[c].area):
 im=Image.new('1',(w,h));dr=ImageDraw.Draw(im)
 for p in ps(regions[c]):
  dr.polygon([((x-ox)/step,(y-oy)/step)for x,y in p.exterior.coords],fill=1)
  for ring in p.interiors:dr.polygon([((x-ox)/step,(y-oy)/step)for x,y in ring.coords],fill=0)
 labels[np.array(im,dtype=np.uint8)>0]=codes.index(c)+1
idx=distance_transform_edt(labels==0,return_distances=False,return_indices=True);labels=labels[tuple(idx)];labels=np.array(Image.fromarray(labels).filter(ImageFilter.ModeFilter(3)));segments=[]
# Exact pixel edges are shared by both countries, yielding one graph with real triple junctions.
for horizontal in [True,False]:
 edges=labels[1:,:]!=labels[:-1,:]if horizontal else labels[:,1:]!=labels[:,:-1]
 for row in range(edges.shape[0]if horizontal else edges.shape[1]):
  a=edges[row,:]if horizontal else edges[:,row];jj=np.flatnonzero(np.diff(np.r_[False,a,False].astype(np.int8)))
  for lo,hi in zip(jj[::2],jj[1::2]):
   if horizontal:p1=(ox+(lo-.5)*step,oy+(row+.5)*step);p2=(ox+(hi-.5)*step,oy+(row+.5)*step)
   else:p1=(ox+(row+.5)*step,oy+(lo-.5)*step);p2=(ox+(row+.5)*step,oy+(hi-.5)*step)
   segments.append(LineString([p1,p2]))
network=unary_union(segments);network=linemerge(network);out=[]
for line in network.geoms:
 points=list(line.simplify(.16).coords)
 for _ in range(2):
  if len(points)<3:break
  q=[points[0]]
  for a,b in zip(points,points[1:]):q.extend([(a[0]*.75+b[0]*.25,a[1]*.75+b[1]*.25),(a[0]*.25+b[0]*.75,a[1]*.25+b[1]*.75)])
  q.append(points[-1]);points=q
 out.append(LineString(points))
D['political_network']=mapping(unary_union(out));D['network_smoothing_version']='single_country_mosaic_shared_graph_0.15mm';(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));print('SHARED BORDER GRAPH',len(out),'chains',flush=True)
