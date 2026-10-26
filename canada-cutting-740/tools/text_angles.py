import json,math
from pathlib import Path
import numpy as np
from shapely.geometry import shape
P=Path(__file__).resolve().parent.parent;A=json.load(open(P/'data/annotations.json'));meta={}
for a in A:
 if not a['id'].startswith('TEXT_'):continue
 g=shape(a['source_outline']);coords=list(g.minimum_rotated_rectangle.exterior.coords);_,v,w=max((math.dist(x,y),x,y)for x,y in zip(coords,coords[1:]));angle=(math.degrees(math.atan2(w[1]-v[1],w[0]-v[0]))+90)%180-90;meta[a['id']]={'id':a['id'],'angle':angle}
for a in A:
 if a['kind']!='red_stroke':continue
 g=shape(a['source_outline']);edges=[]
 for p in ([g]if g.geom_type=='Polygon'else g.geoms):
  for ring in [p.exterior,*p.interiors]:
   for v,w in zip(ring.coords,list(ring.coords)[1:]):
    dx,dy=w[0]-v[0],w[1]-v[1];length=math.hypot(dx,dy)
    if length>.025:edges.append((math.degrees(math.atan2(dy,dx))%90,length))
 bins=np.arange(0,90,.05);score=np.zeros_like(bins)
 for ang,length in edges:
  diff=np.abs(bins-ang);diff=np.minimum(diff,90-diff);score+=np.exp(-.5*(diff/.2)**2)*length
 angle=float(bins[np.argmax(score)]);ref=meta[a['id']]['angle'];angle=min([angle+k*90 for k in range(-2,3)],key=lambda x:abs(x-ref));print(a['id'],'MRR',round(ref,1),'stems',round(angle,2))
 meta[a['id']]['angle']=angle
(P/'data/text-geometry.json').write_text(json.dumps(list(meta.values()),ensure_ascii=False,indent=2))
