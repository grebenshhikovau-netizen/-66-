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
ids=list(cache)
# Two intact bases are necessary for 2 sets/1 sheet and 3 sets/2 sheets.
base=cache['L01_P001'];mask=base['mask'];corr=fftconvolve(mask,mask[::-1,::-1],mode='full');hh,ww=mask.shape
ys,xs=np.where(corr<.1);dxs=xs-(ww-1);dys=ys-(hh-1)
allowed=(np.abs(dxs)<=W-2*MARGIN-ww)&(np.abs(dys)<=H-2*MARGIN-hh)
choices=list(zip(dxs[allowed].tolist(),dys[allowed].tolist()))
print('TWO BASES FEASIBLE SHIFTS',len(choices),'base mask',ww,hh,flush=True)
(P/'data'/'base-pair-feasibility.json').write_text(json.dumps({'grid_mm':RASTER,'two_whole_bases_possible':bool(choices),'valid_relative_translations':len(choices),'base_mask_mm':[ww,hh],'available_field_mm':[W-2*MARGIN,H-2*MARGIN],'rotation':0,'mirroring':False},indent=2))

def seed_base_pair(delta):
 dx,dy=delta; origins=[(MARGIN+max(0,-dx),MARGIN+max(0,-dy)),(MARGIN+max(0,dx),MARGIN+max(0,dy))];occ=np.zeros((H,W),dtype=np.float32);out=[]
 for n,(x,y)in enumerate(origins,1):
  occ[y:y+hh,x:x+ww]+=mask;out.append({'id':f'SET{n}_L01_P001','source_id':'L01_P001','set':n,'sheet':1,'dx_mm':x-base['origin'][0],'dy_mm':y-base['origin'][1],'rotation_degrees':0,'mirrored':False})
 return occ,out

def pack_multi(count,sheet_limit,delta,order,strategy=0):
 occ,placements=seed_base_pair(delta);sheets=[occ]
 if count==3:
  occ=np.zeros((H,W),dtype=np.float32);occ[MARGIN:MARGIN+hh,MARGIN:MARGIN+ww]+=mask;sheets.append(occ);placements.append({'id':'SET3_L01_P001','source_id':'L01_P001','set':3,'sheet':2,'dx_mm':MARGIN-base['origin'][0],'dy_mm':MARGIN-base['origin'][1],'rotation_degrees':0,'mirrored':False})
 for ident,src,number in order:
  r=cache[src];chosen=None
  for si,occ in enumerate(sheets):
   cost=fftconvolve(occ,r['mask'][::-1,::-1],mode='valid');ys,xs=np.where(cost<.1);ok=(xs>=MARGIN)&(ys>=MARGIN)&(xs+r['w']<=W-MARGIN)&(ys+r['h']<=H-MARGIN);ys,xs=ys[ok],xs[ok]
   if not len(xs):continue
   scores=[ys*W+xs,xs*H+ys,ys*W-xs,xs*H-ys][strategy%4];i=np.argmin(scores);chosen=si,int(xs[i]),int(ys[i]);break
  if chosen is None:return None,len(placements)
  si,x,y=chosen;sheets[si][y:y+r['h'],x:x+r['w']]+=r['mask'];placements.append({'id':ident,'source_id':src,'set':number,'sheet':si+1,'dx_mm':x-r['origin'][0],'dy_mm':y-r['origin'][1],'rotation_degrees':0,'mirrored':False})
 return placements,len(placements)

rng=random.Random(741);choices.sort(key=lambda q:(ww+abs(q[0]))*(hh+abs(q[1])))
# Vary the relative translation and packing direction, never part orientation.
selected=choices[:10]+[choices[int(i*(len(choices)-1)/35)]for i in range(36)]
best=None;attempts=[];start=time.time()
for count,limit,trials in [(2,1,72),(3,2,96)]:
 rest=[(f'SET{n}_{id}',id,n)for n in range(1,count+1)for id in ids if id!='L01_P001']
 for i in range(trials):
  delta=selected[i%len(selected)]
  if i<12:key=lambda q:-cache[q[1]][['area','h','w'][i%3]]
  else:
   jitter={q[0]:rng.uniform(.7,1.3)for q in rest};key=lambda q:-cache[q[1]]['area']*jitter[q[0]]
  order=sorted(rest,key=key);result,placed=pack_multi(count,limit,delta,order,i//3)
  attempts.append({'sets':count,'sheets':limit,'attempt':i,'placed':placed,'base_delta_mm':delta})
  if i%6==0 or result:print('PACK',count,'sets',limit,'fields','try',i,'placed',placed,'of',28*count,'sec',round(time.time()-start,1),flush=True)
  if result is not None:best=result;break
 if best is not None:break
if best is None:
 # Accepted single-kit layout as a safe fallback.
 code=(P/'tools'/'nest_single.py').read_text();exec(compile(code,str(P/'tools'/'nest_single.py'),'exec'))
 for q in best:q['source_id']=q['id'];q['set']=1
 count=1;limit=max(q['sheet']for q in best)
geo={p['id']:shape(p['geom'])for p in D['pieces']};checks=[]
for si in sorted(set(p['sheet']for p in best)):
 placed=[(p,translate(geo[p['source_id']],p['dx_mm'],p['dy_mm']))for p in best if p['sheet']==si];gap=1e10
 for k,(p,g)in enumerate(placed):
  assert box(MARGIN,MARGIN,W-MARGIN,H-MARGIN).covers(g),(p['id'],'outside')
  for q,h in placed[:k]:gap=min(gap,g.distance(h));assert g.distance(h)>=GAP-.0001,(p['id'],q['id'],g.distance(h))
 checks.append({'sheet':si,'count':len(placed),'actual_min_gap_mm':gap})
result={'stock_width_mm':W,'stock_height_mm':H,'edge_margin_mm':MARGIN,'required_piece_gap_mm':GAP,'nesting_raster_mm':RASTER,'placements':best,'checks':checks,'source_piece_count':28,'sets':count,'transforms':'translation_only','no_scaling':True,'source_scale_kept':True,'density_attempts':attempts}
(P/'data'/'layout.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('NESTED FINAL',count,'sets',checks,flush=True)
