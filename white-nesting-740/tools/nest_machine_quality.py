"""Keep dense engraving toward right/bottom; protect the upper-left engraving area."""
exec((__import__('pathlib').Path(__file__).parent/'nest.py').read_text().split('ids=list(cache);rng=')[0])
from itertools import permutations

original=json.loads((P/'layout-before-machine-quality.json').read_text())
ids=list(cache);byid={p['id']:p for p in parts};yy0,xx0=np.mgrid[0:H,0:W]
corner=((xx0<220)&(yy0<220)).astype(np.float32)
risk=np.exp(-((xx0/310)**2+(yy0/310)**2)).astype(np.float32)
for id,r in cache.items():
 fine=np.zeros(r['mask'].shape,np.float32)
 for x,y in byid[id]['fine_points']:
  xx=int(round(x-r['origin'][0]));yy=int(round(y-r['origin'][1]))
  if 0<=xx<r['w']and 0<=yy<r['h']:fine[yy,xx]+=1
 r['fine_count']=float(fine.sum())
 r['risk']=fftconvolve(risk,fine[::-1,::-1],mode='valid')
 r['forbidden']=fftconvolve(corner,fine[::-1,::-1],mode='valid')

def quality_pack(order,trial=0,main=False):
 occ=np.zeros((H,W),dtype=np.float32);out=[]
 for k,item in enumerate(order):
  id,copy=item if isinstance(item,tuple)else(item,1);p=cache[id]
  collision=fftconvolve(occ,p['mask'][::-1,::-1],mode='valid')
  ys,xs=np.where((collision<.1)&(p['forbidden']<.1))
  good=(xs>=M)&(ys>=M)&(xs+p['w']<=W-M)&(ys+p['h']<=H-M);xs,ys=xs[good],ys[good]
  if main and id in ['P003','P008','P006']:
   good=ys+p['h']>=H-M-1;xs,ys=xs[good],ys[good]
  if main and id in ['P007','P002']:
   good=(xs+p['w']>=W-M-8)|(ys+p['h']>=H-M-8);xs,ys=xs[good],ys[good]
  if not len(xs):return None
  if id=='P014'and main:
   score=xs*H+ys
  elif id in ['P001','P005']and main and k<3:
   score=ys*W+xs
  elif p['fine_count']>30:
   # Dense groups rank real engraving quality first, then a lower/right placement.
   score=p['risk'][ys,xs]/max(p['fine_count'],1)*1e5
   score+=(W-xs-p['w'])*([.03,.07,.15,.02][trial%4])+(H-ys-p['h'])*([.12,.05,.02,.16][trial%4])
  else:
   score=ys*W+xs
  index=int(np.argmin(score));x,y=int(xs[index]),int(ys[index]);occ[y:y+p['h'],x:x+p['w']]+=p['mask']
  out.append({'source_id':id,'copy':copy,'dx_mm':x-p['origin'][0],'dy_mm':y-p['origin'][1],
              'rotation_degrees':0,'mirrored':False,'scale':1})
 return out

def measure(rows):
 score=0;bad=0;locations=[]
 for q in rows:
  id=q['source_id'];pts=[(x+q['dx_mm'],y+q['dy_mm'])for x,y in byid[id]['fine_points']]
  score+=sum(math.exp(-((x/310)**2+(y/310)**2))for x,y in pts)
  bad+=sum(x<220 and y<220 for x,y in pts)
  g=translate(cache[id]['geom'],q['dx_mm'],q['dy_mm']);locations.append((id,g.bounds))
 return score,bad,locations

rng=random.Random(7402026);base_main_ids=[q['source_id']for q in original['main']]
best=None;attempts=[];start=time.time();chosen_drop=[]
for drop in [['P009'],['P005'],['P004'],['P012','P009']]:
 main_ids=[id for id in base_main_ids if id not in drop]
 prefixes=[]
 for sparse in [['P014','P001'],['P014','P001','P005'],['P001','P014']]:
  sparse=[id for id in sparse if id not in drop]
  for central in permutations(['P003','P008','P006']):
   for important in permutations([id for id in ['P002','P007','P004']if id not in drop]):
    prefixes.append([*sparse,*central,*important])
 rng.shuffle(prefixes)
 for trial,first in enumerate(prefixes[:96]):
  remainder=[id for id in main_ids if id not in first]
  jitter={id:rng.uniform(.9,1.15)for id in remainder};remainder.sort(key=lambda id:-cache[id]['area']*jitter[id])
  result=quality_pack(first+remainder,trial,True)
  attempts.append({'drop':drop,'trial':trial,'success':result is not None})
  if result:
   score,bad,loc=measure(result)
   if best is None or score<best[0]:best=(score,result);chosen_drop=drop;print('MAIN SUCCESS',drop,trial,'risk',round(score,2),'bad',bad,'sec',round(time.time()-start,1),flush=True)
  if trial%24==0:print('MAIN TRY',drop,trial,bool(result),flush=True)
  if trial>=24 and best:break
 if best:break
assert best,'No quality-compliant main arrangement found'

remaining=original['remaining']+chosen_drop;extra=None;chosen_n=None
for n in range(original['repeat'],0,-1):
 full=[(id,c)for c in range(1,n+1)for id in remaining]
 best_extra=None
 for trial in range(24):
  if trial==0:order=sorted(full,key=lambda q:-cache[q[0]]['fine_count'])
  elif trial==1:order=sorted(full,key=lambda q:-cache[q[0]]['area'])
  else:
   jitter={q:rng.uniform(.65,1.5)for q in full};order=sorted(full,key=lambda q:-cache[q[0]]['area']*jitter[q])
  result=quality_pack(order,trial,False)
  if result:
   score,bad,loc=measure(result)
   if best_extra is None or score<best_extra[0]:best_extra=(score,result)
   print('EXTRA SUCCESS',n,trial,'risk',round(score,2),'bad',bad,flush=True)
 if best_extra:extra=best_extra[1];chosen_n=n;break
 assert n>1,'No quality-compliant supplementary arrangement found'
assert extra

new={'main':best[1],'supplementary':extra,'repeat':chosen_n,'remaining':remaining,
     'stock_mm':[740,740],'edge_margin_mm':M,'required_gap_mm':GAP,'translation_only':True,
     'machine_quality':{'fine_marking_protected_upper_left_mm':[220,220],
       'risk_field':'exp(-((x/310)^2+(y/310)^2)); x right, y down',
       'mandatory_bottom_groups':['P003','P008','P006'],'USA_and_large_Africa_right_or_bottom':True},'attempts':attempts}
checks=[]
for field in ['main','supplementary']:
 rows=new[field];geoms=[translate(cache[q['source_id']]['geom'],q['dx_mm'],q['dy_mm'])for q in rows];gap=1e9
 for i,g in enumerate(geoms):
  assert box(M,M,W-M,H-M).covers(g)
  for h in geoms[:i]:gap=min(gap,g.distance(h));assert gap>=GAP
 score,bad,loc=measure(rows);assert bad==0
 before=measure(original[field])[0]/(original['repeat']if field=='supplementary'else 1)
 after=score/(chosen_n if field=='supplementary'else 1)
 checks.append({'field':field,'groups':len(rows),'minimum_gap_mm':gap,'quality_risk_per_main_run_before':before,
                'quality_risk_per_main_run_after':after,'fine_points_in_protected_corner':bad})
new['checks']=checks
(P/'layout.json').write_text(json.dumps(new,ensure_ascii=False,indent=2))
(P/'Проверка-зоны-станка.json').write_text(json.dumps({'passed':True,'protected_corner_mm':[220,220],
 'fine_geometry_method':'red source elements with maximum bounding dimension <= 6 mm and > 0.15 mm',
 'checks':checks,'central_Russia_bottom_bounds':{q['source_id']:next(b for id,b in measure([q])[2]if id==q['source_id'])for q in new['main']if q['source_id']in ['P003','P008','P006']}},ensure_ascii=False,indent=2))
print('QUALITY LAYOUT DONE',chosen_n,checks,flush=True)
