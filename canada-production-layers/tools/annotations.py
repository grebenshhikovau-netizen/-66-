# Place each complete word on a single exposed surface rather than clipping glyphs.
import re
from shapely.affinity import translate,scale as scale_shape
from shapely.geometry import box
from shapely.prepared import prep
labs={}
for r in rows:
 if r['kind']!='engraving':continue
 key=re.sub(r'\.\d+$','',r['name']);labs.setdefault(key,[]).append(shape(r['geom']))
labs={k:clean(unary_union(v)) for k,v in labs.items()}
# Remove source fragments that are wholly duplicated by another label object.
selected={};seen=Polygon()
for key,g in sorted(labs.items(),key=lambda x:-x[1].area):
 if g.is_empty or g.area<.0001:continue
 if g.difference(seen.buffer(.01)).area<g.area*.001:continue
 selected[key]=g;seen=unary_union([seen,g])
positions={};moves=[];failures=[]
for key,original in selected.items():
 print('LABEL',key,flush=True)
 g=original;area=g.area
 coverage=[(shape(p['visible']).intersection(g).area,p) for p in pieces]
 cov,owner=max(coverage,key=lambda x:x[0])
 if cov/area>=.9999:positions[key]=(g,owner['id']);continue
 # Same lettering, shifted locally; source scale is preferred.
 mark=key.startswith('MARK_');limit=3 if mark else 20
 b=g.bounds;cx,cy=g.centroid.x,g.centroid.y
 candidates=[p for p in pieces if shape(p['visible']).distance(g)<limit]
 other=unary_union([v for k,v in selected.items() if k!=key])
 best=None
 for factor in ([1] if mark else [1,.95,.90,.85,.8,.75,.7]):
  h=scale_shape(g,xfact=factor,yfact=factor,origin=(cx,cy));bb=box(*h.bounds)
  step=.25 if mark else .5
  offsets=sorted([(dx*step,dy*step) for dx in range(-int(limit/step),int(limit/step)+1) for dy in range(-int(limit/step),int(limit/step)+1) if (dx*step)**2+(dy*step)**2<=limit*limit],key=lambda q:q[0]*q[0]+q[1]*q[1])
  for p in candidates:
   v=shape(p['visible']);safe=v.buffer(-.08);pr=prep(safe)
   if safe.is_empty:continue
   for dx,dy in offsets:
    score=math.hypot(dx,dy)+(1-factor)*30
    if best and score>=best[0]:break
    hb=translate(bb,dx,dy)
    if not safe.intersects(hb):continue
    h2=translate(h,dx,dy)
    if not pr.covers(h2):continue
    if not mark and h2.buffer(.08).intersection(other).area>original.buffer(.08).intersection(other).area+.025:continue
    best=(score,p,h2,dx,dy,factor)
  if best and best[0]<1:break
 if best:
  _,owner,g,dx,dy,factor=best;positions[key]=(g,owner['id']);moves.append({'source_id':key,'piece':owner['id'],'dx_mm':dx,'dy_mm':dy,'scale':factor})
 else:
  # Keep the exact source contour if the available shelf cannot fit the whole word.
  failures.append({'source_id':key,'best_single_surface_coverage':cov/area});positions[key]=(g,None)
for p in pieces:
 gs=[g for g,owner in positions.values() if owner==p['id']]
 gs += [g.intersection(shape(p['visible'])) for g,owner in positions.values() if owner is None]
 p['engraving']=mapping(unary_union(gs))
plan['annotation_moves']=moves;plan['annotations_requiring_review']=failures;plan['unique_annotations']=len(positions)
print('ANNOTATIONS',len(positions),'moved',len(moves),'review',failures,flush=True)
