import json,math,time,random
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.signal import fftconvolve
from shapely.geometry import shape,mapping,box
from shapely.affinity import translate
P=Path(__file__).resolve().parent.parent;SRC=P/'data'/'source';D=json.load(open(SRC/'production-plan.json'));W=H=740;MARGIN=5;GAP=3;RASTER=1;BUFFER=GAP/2+.8

def polys(g):
 if g.geom_type=='Polygon':return [g]if not g.is_empty else []
 return [p for q in getattr(g,'geoms',[])for p in polys(q)]
cache={}
for p in D['pieces']:
 g=shape(p['geom']);b=g.buffer(BUFFER,quad_segs=6);x0,y0,x1,y1=b.bounds;ox,oy=math.floor(x0),math.floor(y0);ww,hh=math.ceil(x1)-ox+1,math.ceil(y1)-oy+1;im=Image.new('1',(ww,hh));draw=ImageDraw.Draw(im)
 for q in polys(b):
  draw.polygon([(x-ox,y-oy)for x,y in q.exterior.coords],fill=1)
  for ring in q.interiors:draw.polygon([(x-ox,y-oy)for x,y in ring.coords],fill=0)
 cache[p['id']]={'mask':np.array(im,dtype=np.float32),'origin':[ox,oy],'w':ww,'h':hh,'area':g.area}

def pack(order,limit=2):
 sheets=[];placements=[]
 for id in order:
  r=cache[id];chosen=None
  for si,occ in enumerate(sheets):
   cost=fftconvolve(occ,r['mask'][::-1,::-1],mode='valid');ys,xs=np.where(cost<.1);ok=(xs>=MARGIN)&(ys>=MARGIN)&(xs+r['w']<=W-MARGIN)&(ys+r['h']<=H-MARGIN);ys,xs=ys[ok],xs[ok]
   if len(xs):
    # Bottom-left placement; preserve the broadest remaining free area.
    idx=np.argmin(ys*W+xs);chosen=(si,int(xs[idx]),int(ys[idx]));break
  if chosen is None:
   if len(sheets)>=limit:return None
   occ=np.zeros((H,W),dtype=np.float32);occ[:MARGIN,:]=1;occ[-MARGIN:,:]=1;occ[:,:MARGIN]=1;occ[:,-MARGIN:]=1;sheets.append(occ);chosen=(len(sheets)-1,MARGIN,MARGIN)
  si,x,y=chosen
  if x+r['w']>W-MARGIN or y+r['h']>H-MARGIN:return None
  sheets[si][y:y+r['h'],x:x+r['w']]+=r['mask'];placements.append({'id':id,'sheet':si+1,'dx_mm':x-r['origin'][0],'dy_mm':y-r['origin'][1],'rotation_degrees':0,'mirrored':False})
 return placements
ids=list(cache);orders=[]
for key in ['area','h','w']:
 orders.append(sorted(ids,key=lambda id:-cache[id][key]))
orders.append(sorted(ids,key=lambda id:-(cache[id]['w']*cache[id]['h'])))
rng=random.Random(740)
for i in range(20):orders.append(sorted(ids,key=lambda id:-cache[id]['area']*rng.uniform(.65,1.35)))
best=None;t=time.time()
for i,order in enumerate(orders):
 result=pack(order,1)
 print('TRY',i,'one field',bool(result),'seconds',round(time.time()-t,1),flush=True)
 if result is not None:best=result;break
if best is None:best=pack(orders[0],3)
assert best is not None
geo={p['id']:shape(p['geom'])for p in D['pieces']};checks=[]
for si in sorted(set(p['sheet']for p in best)):
 placed=[(p,translate(geo[p['id']],p['dx_mm'],p['dy_mm']))for p in best if p['sheet']==si]
 gap=1e10
 for k,(p,g) in enumerate(placed):
  assert box(MARGIN,MARGIN,W-MARGIN,H-MARGIN).covers(g),(p['id'],'outside field')
  for q,h in placed[:k]:gap=min(gap,g.distance(h));assert g.distance(h)>=GAP-.0001,(p['id'],q['id'],g.distance(h))
 checks.append({'sheet':si,'count':len(placed),'actual_min_gap_mm':gap})
result={'stock_width_mm':W,'stock_height_mm':H,'edge_margin_mm':MARGIN,'required_piece_gap_mm':GAP,'nesting_raster_mm':RASTER,'placements':best,'checks':checks,'source_project':'canada-production-layers','source_piece_count':len(ids),'transforms':'translation_only','no_scaling':True,'source_scale_kept':True}
(P/'data'/'layout.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('NESTED',checks,flush=True)
