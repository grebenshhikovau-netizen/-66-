"""Keep every part orientation and scale; try one 740 mm field before using two."""
import json,math,random,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.signal import fftconvolve
from shapely.geometry import shape,box
from shapely.affinity import translate
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));W=H=740;M=5;GAP=3;B=2.2;cache={}
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for a in getattr(g,'geoms',[])for p in ps(a)]
for p in D['pieces']:
 g=shape(p['geom']);b=g.buffer(B,quad_segs=4);x0,y0,x1,y1=b.bounds;ox,oy=math.floor(x0),math.floor(y0);w,h=math.ceil(x1)-ox+1,math.ceil(y1)-oy+1;im=Image.new('1',(w,h));dr=ImageDraw.Draw(im)
 for q in ps(b):
  dr.polygon([(x-ox,y-oy)for x,y in q.exterior.coords],fill=1)
  for hole in q.interiors:dr.polygon([(x-ox,y-oy)for x,y in hole.coords],fill=0)
 cache[p['id']]={'geom':g,'mask':np.array(im,dtype=np.uint8).astype(np.float32),'origin':[ox,oy],'w':w,'h':h,'area':g.area}
def pack(order,limit,strategy):
 sheets=[];placed=[]
 for id in order:
  p=cache[id];chosen=None
  if p['w']>W-10 or p['h']>H-10:return None
  for si,occ in enumerate(sheets):
   cost=fftconvolve(occ,p['mask'][::-1,::-1],mode='valid');yy,xx=np.where(cost<.1);ok=(xx>=M)&(yy>=M)&(xx+p['w']<=W-M)&(yy+p['h']<=H-M);xx,yy=xx[ok],yy[ok]
   if len(xx):
    score=[yy*W+xx,xx*H+yy,yy*W-xx,xx*H-yy][strategy%4];idx=np.argmin(score);chosen=(si,int(xx[idx]),int(yy[idx]));break
  if chosen is None:
   if len(sheets)>=limit:return None
   sheets.append(np.zeros((H,W),np.float32));chosen=(len(sheets)-1,M,M)
  si,x,y=chosen;sheets[si][y:y+p['h'],x:x+p['w']]+=p['mask'];placed.append({'id':id,'source_id':id,'sheet':si+1,'kit':1,'dx_mm':x-p['origin'][0],'dy_mm':y-p['origin'][1],'rotation_degrees':0,'mirrored':False,'scale':1})
 return placed
ids=list(cache);rng=random.Random(90412);attempts=[];best=None;start=time.time()
for limit in [1,2,3]:
 for trial in range(36 if limit==1 else 12):
  if trial<3:key=lambda id:-cache[id][['area','h','w'][trial]]
  else:
   jitter={id:rng.uniform(.8,1.2)for id in ids};key=lambda id:-cache[id]['area']*jitter[id]
  result=pack(sorted(ids,key=key),limit,trial//9);attempts.append({'fields_limit':limit,'trial':trial,'success':result is not None})
  if trial%6==0 or result:print('NEST',limit,'fields',trial,bool(result),'sec',round(time.time()-start,1),flush=True)
  if result:best=result;break
 if best:break
assert best
checks=[]
for si in sorted(set(q['sheet']for q in best)):
 placed=[(q,translate(cache[q['id']]['geom'],q['dx_mm'],q['dy_mm']))for q in best if q['sheet']==si];gap=1e9
 for j,(q,g)in enumerate(placed):
  assert box(5,5,735,735).covers(g)
  for r,h in placed[:j]:dd=g.distance(h);assert dd>=GAP-.00001,(q['id'],r['id'],dd);gap=min(gap,dd)
 checks.append({'sheet':si,'parts':len(placed),'actual_min_gap_mm':gap})
output={'stock_mm':[740,740],'kits':1,'parts_per_kit':len(ids),'part_count':len(ids),'placements':best,'checks':checks,'edge_margin_mm':5,'required_gap_mm':3,'translation_only':True,'scale':1,'attempts':attempts};(P/'data/layout.json').write_text(json.dumps(output,ensure_ascii=False,indent=2));print('LAYOUT READY',checks,flush=True)
