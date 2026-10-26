from pathlib import Path
import json,time,random,math,sys
p=Path(__file__).resolve().parent.parent;ns={'__file__':str(p/'tools/nest.py')};src=(p/'tools/nest.py').read_text();exec(compile(src[:src.index('ids=list(cache)')],ns['__file__'],'exec'),ns)
np=ns['np'];fft=ns['fftconvolve'];cache=ns['cache'];W=H=740;MARGIN=5
# Search the difficult sheet: one whole base plus all six large second-ply parts.
orders=[['L01_P001']+['L02_P008']*3+['L02_P010']*3,['L01_P001']+['L02_P010']*3+['L02_P008']*3,['L01_P001']+['L02_P008','L02_P010']*3,['L02_P008','L02_P010']*3+['L01_P001']]
start=time.time();best=0
for oi,order in enumerate(orders):
 beam=[(np.zeros((H,W),np.float32),[],0)]
 for k,id in enumerate(order):
  r=cache[id];nexts=[]
  for occ,placed,score in beam:
   costs=fft(occ,r['mask'][::-1,::-1],mode='valid');ys,xs=np.where(costs<.1);ok=(xs>=5)&(ys>=5)&(xs+r['w']<=735)&(ys+r['h']<=735);ys,xs=ys[ok],xs[ok]
   if not len(xs):continue
   # Diverse extreme positions, spread spatially.
   cand=[]
   for mode in range(4):
    val=[ys*740+xs,ys*740-xs,-ys*740+xs,-ys*740-xs][mode];inds=np.argsort(val)
    taken=[]
    for idx in inds:
     x,y=int(xs[idx]),int(ys[idx])
     if any(abs(x-a)<45 and abs(y-b)<45 for a,b in taken):continue
     taken.append((x,y));cand.append((x,y))
     if len(taken)>=3:break
   for x,y in sorted(set(cand)):
    new=occ.copy();new[y:y+r['h'],x:x+r['w']]+=r['mask'];pl=placed+[(id,x,y)];minx=min(a for _,a,b in pl);miny=min(b for _,a,b in pl);maxx=max(a+cache[i]['w']for i,a,b in pl);maxy=max(b+cache[i]['h']for i,a,b in pl);sc=(maxx-minx)*(maxy-miny);nexts.append((new,pl,sc))
  # Keep diversity by discretized last position and direction, then compactness.
  nexts.sort(key=lambda q:q[2]);beam=[];keys=set()
  for item in nexts:
   # Retain distinct placements including different offsets of the initial base.
   key=tuple((id,x//35,y//35)for id,x,y in item[1])
   if key in keys:continue
   keys.add(key);beam.append(item)
   if len(beam)>=32:break
  best=max(best,k+1 if beam else k);print('BEAM',oi,k+1,'survivors',len(beam),'sec',round(time.time()-start,1),flush=True)
  if not beam:break
 if beam and len(beam[0][1])==7:
  (p/'data/density-large-parts.json').write_text(json.dumps(beam[0][1]));print('FOUND LARGE PARTS',beam[0][1],flush=True);sys.exit(0)
(p/'data/density-beam-report.json').write_text(json.dumps({'orders_tested':orders,'beam_width':32,'large_pieces_required':7,'maximum_placed_in_search':best,'found_complete_solution':False,'rotations_allowed':False,'source_shapes_unchanged':True},indent=2));print('NOT FIT; max large pieces',best,flush=True)
