"""Translation-only nesting of complete identical kits on 740 x 740 mm stock."""
import json,math,time,random
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.signal import fftconvolve
from shapely.geometry import shape,box
from shapely.affinity import translate
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));W=H=740;MARGIN=5;GAP=3;BUFFER=2.2;cache={}
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for a in getattr(g,'geoms',[])for p in ps(a)]
for row in D['pieces']:
 g=shape(row['geom']);b=g.buffer(BUFFER,quad_segs=4);x0,y0,x1,y1=b.bounds;ox,oy=math.floor(x0),math.floor(y0);w,h=math.ceil(x1)-ox+1,math.ceil(y1)-oy+1;im=Image.new('1',(w,h));draw=ImageDraw.Draw(im)
 for q in ps(b):
  draw.polygon([(x-ox,y-oy)for x,y in q.exterior.coords],fill=1)
  for hole in q.interiors:draw.polygon([(x-ox,y-oy)for x,y in hole.coords],fill=0)
 cache[row['id']]={'mask':np.array(im,dtype=np.uint8).astype(np.float32),'origin':[ox,oy],'w':w,'h':h,'area':g.area,'geom':g}
def pack(order,width=740,strategy=0):
 occ=np.zeros((H,width),dtype=np.float32);placements=[]
 for source,kit in order:
  r=cache[source]
  if r['w']>width-2*MARGIN or r['h']>H-2*MARGIN:return None
  costs=fftconvolve(occ,r['mask'][::-1,::-1],mode='valid');yy,xx=np.where(costs<.1);ok=(xx>=MARGIN)&(yy>=MARGIN)&(xx+r['w']<=width-MARGIN)&(yy+r['h']<=H-MARGIN);yy,xx=yy[ok],xx[ok]
  if not len(xx):return None
  values=[yy*width+xx,xx*H+yy,yy*width-xx,xx*H-yy][strategy%4];idx=np.argmin(values);x,y=int(xx[idx]),int(yy[idx]);occ[y:y+r['h'],x:x+r['w']]+=r['mask'];placements.append({'id':f'K{kit:02d}_{source}','source_id':source,'kit':kit,'sheet':1,'dx_mm':x-r['origin'][0],'dy_mm':y-r['origin'][1],'rotation_degrees':0,'mirrored':False,'scale':1})
 return placements
def bounds(placements):
 bb=[translate(cache[q['source_id']]['geom'],q['dx_mm'],q['dy_mm']).bounds for q in placements];return[min(q[0]for q in bb),min(q[1]for q in bb),max(q[2]for q in bb),max(q[3]for q in bb)]
def check(placements,kits,attempts):
 shapes=[(q,translate(cache[q['source_id']]['geom'],q['dx_mm'],q['dy_mm']))for q in placements];dist=10000
 for j,(q,g)in enumerate(shapes):
  assert box(5,5,735,735).covers(g),(q['id'],'outside field')
  for r,h in shapes[:j]:
   dd=g.distance(h);assert dd>=GAP-.0001,(q['id'],r['id'],dd);dist=min(dist,dd)
 for n in range(1,kits+1):assert {q['source_id']for q in placements if q['kit']==n}==set(cache)
 return {'stock_mm':[740,740],'kits':kits,'parts_per_kit':len(cache),'part_count':len(placements),'placements':placements,'edge_margin_mm':5,'required_gap_mm':3,'actual_min_gap_mm':dist,'used_bounds_mm':bounds(placements),'translation_only':True,'part_rotation':0,'part_reflection':False,'scale':1,'attempts':attempts}
ids=list(cache);rng=random.Random(74018);orders=[sorted(ids,key=lambda id:-cache[id][key])for key in ['area','h','w']];single=None;single_score=1e12
for width in [420,500,600,740]:
 for order in orders:
  trial=pack([(id,1)for id in order],width)
  if trial:
   bb=bounds(trial);score=(bb[2]-bb[0])*(bb[3]-bb[1])
   if score<single_score:single=trial;single_score=score
assert single
(P/'data/layout-single.json').write_text(json.dumps(check(single,1,[]),ensure_ascii=False,indent=2));print('SINGLE KIT COMPACT',bounds(single),flush=True)
mask_area=sum(q['mask'].sum()for q in cache.values());cap=min(7,int((W-10)*(H-10)/mask_area));attempts=[];best=None;start=time.time()
for count in range(max(2,cap),1,-1):
 allparts=[(id,k)for k in range(1,count+1)for id in ids]
 for trial in range(28):
  if trial<3:key=lambda q:-cache[q[0]][['area','h','w'][trial]]
  else:
   noise={q:rng.uniform(.7,1.3)for q in allparts};key=lambda q:-cache[q[0]]['area']*noise[q]
  order=sorted(allparts,key=key);result=pack(order,740,trial//7);attempts.append({'kits':count,'trial':trial,'fits_one_field':result is not None})
  if trial%7==0 or result:print('NEST',count,'kits trial',trial,'fits',result is not None,'sec',round(time.time()-start,1),flush=True)
  if result is not None:best=result;break
 if best is not None:break
if best is None:best=single;count=1
report=check(best,count,attempts);report['source_actual_area_per_kit_mm2']=sum(cache[id]['area']for id in ids);report['material_utilization_percent']=report['source_actual_area_per_kit_mm2']*count/(740*740)*100;report['search_is_not_a_proof_of_optimality']=True
(P/'data/layout.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('NEST RESULT',count,'kits',len(best),'parts gap',report['actual_min_gap_mm'],'used',report['used_bounds_mm'],flush=True)
