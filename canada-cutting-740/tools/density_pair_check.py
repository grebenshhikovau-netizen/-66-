from pathlib import Path
import time,json
p=Path(__file__).resolve().parent.parent;s=(p/'tools/nest.py').read_text();ns={'__file__':str(p/'tools/nest.py')};exec(compile(s[:s.index('rng=random.Random(741)')],str(p/'tools/nest.py'),'exec'),ns)
np=ns['np'];fft=ns['fftconvolve'];cache=ns['cache'];choices=ns['choices'];seed=ns['seed_base_pair'];start=time.time();found=[]
for i,delta in enumerate(choices):
 occ,pl=seed(delta)
 for id in ['L02_P008','L02_P010']:
  r=cache[id];cost=fft(occ,r['mask'][::-1,::-1],mode='valid');ys,xs=np.where(cost<.1);ok=(xs>=5)&(ys>=5)&(xs+r['w']<=735)&(ys+r['h']<=735);xs,ys=xs[ok],ys[ok]
  if len(xs):
   found.append({'delta':delta,'large_part':id,'x':int(xs[0]),'y':int(ys[0])});print('FOUND',found[-1],flush=True);break
 if len(found)>=8:break
 if i%400==0:print('SCAN',i,'of',len(choices),'sec',round(time.time()-start,1),flush=True)
(p/'data/density-pair-large-check.json').write_text(json.dumps({'pair_shifts_checked':i+1,'total_valid_pair_shifts':len(choices),'placements_found':found,'grid_mm':1,'clearance_buffer_mm':ns['BUFFER']},indent=2));print('COMPLETE',len(found),'sec',round(time.time()-start,1),flush=True)
