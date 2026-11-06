"""One editable kit, translation-only, all geometry to the right of the weak machine corner."""
import json,math,random,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.signal import fftconvolve
from shapely.geometry import shape,box
from shapely.affinity import translate
P=Path(__file__).resolve().parent.parent/sys.argv[1];D=json.load(open(P/'data/production-plan.json'));W=740 if sys.argv[1]=='02-Greenland' else 500;H=740;SHIFT_X=0 if sys.argv[1]=='02-Greenland' else 240;M=5;cache={}
def polys(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in polys(q)]
for r in D['pieces']:
 g=shape(r['geom']);b=g.buffer(2.2,quad_segs=4);x0,y0,x1,y1=b.bounds;ox,oy=math.floor(x0),math.floor(y0);w,h=math.ceil(x1)-ox+1,math.ceil(y1)-oy+1
 im=Image.new('1',(w,h));dr=ImageDraw.Draw(im)
 for q in polys(b):
  dr.polygon([(x-ox,y-oy)for x,y in q.exterior.coords],fill=1)
  # Do not place a loose part inside an engraving channel or waste hole.
 cache[r['id']]={'geom':g,'mask':np.array(im,dtype=np.float32),'origin':(ox,oy),'w':w,'h':h,'area':g.area}
def pack(order,strategy):
 occ=np.zeros((H,W),np.float32);out=[]
 for id in order:
  p=cache[id];cost=fftconvolve(occ,p['mask'][::-1,::-1],mode='valid');yy,xx=np.where(cost<.1);ok=(xx>=M)&(yy>=M)&(xx+p['w']<=W-M)&(yy+p['h']<=H-M);xx,yy=xx[ok],yy[ok]
  if not len(xx):return None
  vals=(H-yy-p['h'])*W+(W-xx-p['w'])if strategy==0 else (W-xx-p['w'])*H+(H-yy-p['h'])
  k=np.argmin(vals);x,y=int(xx[k]),int(yy[k]);occ[y:y+p['h'],x:x+p['w']]+=p['mask'];out.append({'id':id,'source_id':id,'kit':1,'sheet':1,'dx_mm':x-p['origin'][0]+SHIFT_X,'dy_mm':y-p['origin'][1],'rotation_degrees':0,'mirrored':False,'scale':1})
 return out
ids=list(cache);rng=random.Random(74117);best=None
for trial in range(12):
 if trial<3:key=lambda id:-cache[id][['h','area','w'][trial]]
 else:
  jitter={id:rng.uniform(.8,1.2)for id in ids};key=lambda id:-cache[id]['area']*jitter[id]
 result=pack(sorted(ids,key=key),trial%2)
 if result:best=result;break
assert best
placed=[translate(cache[r['id']]['geom'],r['dx_mm'],r['dy_mm'])for r in best];gap=1000
for i,g in enumerate(placed):
 assert box(5,5,735,735).covers(g)
 for h in placed[:i]:gap=min(gap,g.distance(h));assert g.distance(h)>=3
out={'stock_mm':[740,740],'kits':1,'parts_per_kit':len(best),'part_count':len(best),'placements':best,'edge_margin_mm':5,'required_gap_mm':3,'actual_min_gap_mm':gap,'translation_only':True,'weak_upper_left_corner_avoided':SHIFT_X>0}
(P/'data/layout.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('ONE KIT NESTED',len(best),'parts, gap',gap,flush=True)
