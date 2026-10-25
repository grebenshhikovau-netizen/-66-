import json,math
from pathlib import Path
from shapely.geometry import shape,mapping,box
from shapely.affinity import translate,rotate,scale
from shapely.ops import unary_union
from shapely.prepared import prep
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'production-plan.json'));R=json.load(open(P/'extracted.json'));key='TEXT_063';original=unary_union([shape(r['geom'])for r in R if r['kind']=='engraving' and r['name'].split('.')[0]==key]);ink=unary_union([shape(p['engraving'])for p in D['pieces']]);other=ink.difference(original.buffer(.025));best=None
if not any(x['source_id']==key for x in D['annotations_requiring_review']):
 print('Mexico label already fits');raise SystemExit(0)
assert all(x['source_id']==key for x in D['annotations_requiring_review'])
for angle in [40,50,60,70,90,-30,-45]:
 for factor in [1,.9,.8,.7]:
  h=rotate(scale(original,xfact=factor,yfact=factor,origin='centroid'),angle,origin='centroid');limit=23;offsets=sorted([(i,j)for i in range(-limit,limit+1)for j in range(-limit,limit+1)if i*i+j*j<limit*limit],key=lambda q:q[0]**2+q[1]**2)
  for p in D['pieces']:
   if 'REG_08_Mexico'not in p['regions']:continue
   v=shape(p['visible']).buffer(-.08);pr=prep(v)
   if v.is_empty or h.distance(v)>limit:continue
   for dx,dy in offsets:
    score=math.hypot(dx,dy)+20*(1-factor)+abs(angle)*.02
    if best and score>=best[0]:break
    hh=translate(h,dx,dy)
    if not pr.covers(hh):continue
    if hh.buffer(.1).intersection(other).area>.03:continue
    best=(score,p['id'],hh,dx,dy,factor,angle)
 if best and best[0]<5:break
assert best,'no place for Mexico label';score,owner,g,dx,dy,factor,angle=best
for p in D['pieces']:
 eng=shape(p['engraving']).difference(original.buffer(.025))
 if p['id']==owner:eng=unary_union([eng,g])
 p['engraving']=mapping(eng)
D['annotation_moves'].append({'source_id':key,'piece':owner,'dx_mm':dx,'dy_mm':dy,'scale':factor,'rotation_degrees':angle});D['annotations_requiring_review']=[];(P/'production-plan.json').write_text(json.dumps(D,ensure_ascii=False));print('MEXICO LABEL',owner,dx,dy,factor,angle,flush=True)
