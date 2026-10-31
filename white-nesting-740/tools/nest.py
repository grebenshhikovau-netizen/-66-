"""Translation-only nesting; if needed repeat the remainder on a supplementary sheet."""
import json,math,random,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.signal import fftconvolve
from shapely.geometry import shape,box
from shapely.affinity import translate

P=Path(__file__).resolve().parent.parent
parts=json.loads((P/'parts.json').read_text());W=H=740;M=5;GAP=3;B=2.1
cache={}
def polys(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for a in getattr(g,'geoms',[])for p in polys(a)]
for p in parts:
 g=shape(p['geom']);b=g.buffer(B,quad_segs=4);x0,y0,x1,y1=b.bounds
 ox,oy=math.floor(x0),math.floor(y0);w,h=math.ceil(x1)-ox+1,math.ceil(y1)-oy+1
 im=Image.new('1',(w,h));d=ImageDraw.Draw(im)
 for q in polys(b):
  d.polygon([(x-ox,y-oy)for x,y in q.exterior.coords],fill=1)
  for hole in q.interiors:d.polygon([(x-ox,y-oy)for x,y in hole.coords],fill=0)
 cache[p['id']]={'geom':g,'mask':np.array(im,dtype=np.float32),'origin':(ox,oy),'w':w,'h':h,'area':g.area}

def pack(order,strategy=0,skip=False):
 occ=np.zeros((H,W),dtype=np.float32);out=[];missing=[]
 for item in order:
  id=item[0]if isinstance(item,tuple)else item;copy=item[1]if isinstance(item,tuple)else 1
  p=cache[id]
  cost=fftconvolve(occ,p['mask'][::-1,::-1],mode='valid');yy,xx=np.where(cost<.1)
  ok=(xx>=M)&(yy>=M)&(xx+p['w']<=W-M)&(yy+p['h']<=H-M);xx,yy=xx[ok],yy[ok]
  if not len(xx):
   if not skip:return None
   missing.append(id);continue
  score=[yy*W+xx,xx*H+yy,yy*W-xx,xx*H-yy][strategy%4]
  idx=np.argmin(score);x,y=int(xx[idx]),int(yy[idx]);occ[y:y+p['h'],x:x+p['w']]+=p['mask']
  out.append({'source_id':id,'copy':copy,'dx_mm':x-p['origin'][0],'dy_mm':y-p['origin'][1],
              'rotation_degrees':0,'mirrored':False,'scale':1})
 return (out,missing)if skip else out

ids=list(cache);rng=random.Random(740640);candidates=[];attempts=[];start=time.time();winner=None
for trial in range(240):
 if trial<4:
  field=['area','h','w','box'][trial]
  key=lambda id:-(cache[id]['w']*cache[id]['h']if field=='box'else cache[id][field])
 else:
  jit={id:rng.uniform(.65,1.45)for id in ids};key=lambda id:-cache[id]['area']*jit[id]
 order=sorted(ids,key=key)
 if trial>=96:
  # Reserve the long, narrow Antarctica part before other details fragment the field.
  tallest=max(ids,key=lambda id:cache[id]['h'])
  order.remove(tallest);order.insert(0,tallest)
 out,remaining=pack(order,trial//12,True)
 attempts.append({'trial':trial,'main_parts':len(out),'remaining':remaining})
 if not remaining:winner={'main':out,'supplementary':[],'repeat':1};print('ONE SHEET FOUND',trial,flush=True);break
 candidates.append((sum(cache[id]['area']for id in remaining),trial,out,remaining))
 if trial%8==0:print('TRY',trial,'main',len(out),'remaining',remaining,'seconds',round(time.time()-start,1),flush=True)

if winner is None:
 # Compare the best distinct residual sets; one auxiliary sheet supplies N main runs.
 seen=set();best=None
 for area,trial,main,remaining in sorted(candidates):
  stamp=tuple(sorted(remaining))
  if stamp in seen:continue
  seen.add(stamp)
  maxn=min(24,max(1,int((W-2*M)*(H-2*M)/area)))
  for n in range(maxn,0,-1):
   if best and n<best['repeat']:break
   full=[(id,c)for c in range(1,n+1)for id in remaining]
   for t in range(4):
    if t<2:order=sorted(full,key=lambda q:-cache[q[0]][['area','h'][t]])
    else:
     jitter={q:rng.uniform(.8,1.2)for q in full};order=sorted(full,key=lambda q:-cache[q[0]]['area']*jitter[q])
    extra=pack(order,t)
    if extra is not None:
     proposed={'main':main,'supplementary':extra,'repeat':n,'main_trial':trial,'remaining':remaining}
     if best is None or (n,-area)>(best['repeat'],-best['residual_area']):best={**proposed,'residual_area':area}
     break
   if extra is not None:break
  print('REMAINDER',list(stamp),'best repeat',best['repeat']if best else None,flush=True)
  if len(seen)>=12:break
 assert best;winner=best

checks=[]
for field,placed in [('main',winner['main']),('supplementary',winner['supplementary'])]:
 if not placed:continue
 geoms=[translate(cache[p['source_id']]['geom'],p['dx_mm'],p['dy_mm'])for p in placed]
 gap=1e9
 for i,g in enumerate(geoms):
  assert box(M,M,W-M,H-M).covers(g)
  for h in geoms[:i]:gap=min(gap,g.distance(h));assert g.distance(h)>=GAP-.00001
 checks.append({'field':field,'groups':len(placed),'minimum_gap_mm':gap})
winner.update({'stock_mm':[740,740],'edge_margin_mm':M,'required_gap_mm':GAP,'translation_only':True,'checks':checks,'attempts':attempts})
(P/'layout.json').write_text(json.dumps(winner,ensure_ascii=False,indent=2))
print('FINISHED',checks,'REPEAT',winner['repeat'],flush=True)
