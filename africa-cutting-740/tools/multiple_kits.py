"""Try multiple complete kits with translation only; preserve the verified single-kit layout."""
from pathlib import Path
import json,random,time
ROOT=Path(__file__).resolve().parent.parent
# Reuse the identical validated one-kit raster and packing implementation without its top-level run.
s=(ROOT/'tools/nest.py').read_text().split('ids=list(cache);')[0];exec(compile(s,str(ROOT/'tools/nest.py'),'exec'))
base=cache.copy();attempts=[];found=None;start=time.time()
for kits in [3,2]:
 cache={f'K{k:02d}_'+id:row for k in range(1,kits+1)for id,row in base.items()};ids=list(cache);rng=random.Random(271026)
 for trial in range(32):
  if trial<3:key=lambda id:-cache[id][['area','h','w'][trial]]
  else:
   jitter={id:rng.uniform(.75,1.25)for id in ids};key=lambda id:-cache[id]['area']*jitter[id]
  result=pack(sorted(ids,key=key),1,trial//8);attempts.append({'kits':kits,'trial':trial,'success':bool(result)})
  if trial%8==0 or result:print('MULTI',kits,trial,bool(result),round(time.time()-start,1),flush=True)
  if result:found=(kits,result);break
 if found:break
if found:
 kits,rows=found
 for row in rows:row['kit']=int(row['id'][1:3]);row['source_id']=row['id'][4:]
 out={'stock_mm':[740,740],'kits':kits,'parts_per_kit':len(base),'part_count':len(rows),'placements':rows,'edge_margin_mm':5,'required_gap_mm':3,'translation_only':True,'scale':1,'attempts':attempts};(ROOT/'data/layout-multiple.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('MULTIPLE KITS READY',kits,len(rows),flush=True)
else:(ROOT/'data/multiple-kit-attempts.json').write_text(json.dumps(attempts,indent=2));print('NO MULTI FIT FOUND',flush=True)
