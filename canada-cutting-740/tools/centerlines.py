"""Centerline existing outlined glyphs without retyping, OCR, or changing placement."""
import math
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt
from skimage.morphology import skeletonize
from shapely.geometry import LineString,MultiLineString
from shapely.ops import unary_union

def polys(g):
 if g.geom_type=='Polygon':return [g]if not g.is_empty else []
 return [p for q in getattr(g,'geoms',[])for p in polys(q)]

def centerline(g,step=.008):
 result=[]
 for glyph in polys(g):
  x0,y0,x1,y1=glyph.bounds;pad=4;ox=x0-pad*step;oy=y0-pad*step
  im=Image.new('1',(math.ceil((x1-x0)/step)+2*pad+1,math.ceil((y1-y0)/step)+2*pad+1));dr=ImageDraw.Draw(im)
  dr.polygon([((x-ox)/step,(y-oy)/step)for x,y in glyph.exterior.coords],fill=1)
  for h in glyph.interiors:dr.polygon([((x-ox)/step,(y-oy)/step)for x,y in h.coords],fill=0)
  a=np.array(im,dtype=np.uint8)>0;sk=skeletonize(a);radii=distance_transform_edt(a)*step
  yy,xx=np.where(sk);nodes=set(zip(xx.tolist(),yy.tolist()));adj={q:set()for q in nodes}
  for x,y in nodes:
   for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
    q=(x+dx,y+dy)
    if q not in nodes:continue
    # Avoid triangular graph branches around a single corner.
    if dx and dy and ((x+dx,y)in nodes or(x,y+dy)in nodes):continue
    adj[(x,y)].add(q)
  isolated=[q for q in nodes if not adj[q]]
  def edge(a,b):return tuple(sorted((a,b)))
  def trace():
   seen=set();chains=[]
   def walk(start,nxt):
    chain=[start,nxt];seen.add(edge(start,nxt));prev,cur=start,nxt
    while len(adj[cur])==2:
     q=next(q for q in adj[cur]if q!=prev)
     if edge(cur,q)in seen:break
     chain.append(q);seen.add(edge(cur,q));prev,cur=cur,q
    return chain
   for q in sorted(nodes):
    if len(adj[q])==2:continue
    for n in sorted(adj[q]):
     if edge(q,n)not in seen:chains.append(walk(q,n))
   for q in sorted(nodes):
    for n in sorted(adj[q]):
     if edge(q,n)not in seen:chains.append(walk(q,n))
   return chains
  def world(chain):return[(x*step+ox,y*step+oy)for x,y in chain]
  # Remove tiny raster branches first, then recompute actual graph junctions.
  for iteration in range(3):
   changed=False
   for chain in trace():
    ends=[q for q in [chain[0],chain[-1]]if len(adj[q])==1];js=[q for q in [chain[0],chain[-1]]if len(adj[q])>2]
    if ends and js and LineString(world(chain)).length<max(.025,1.25*radii[js[0][1],js[0][0]]):
     for a,b in zip(chain,chain[1:]):adj[a].discard(b);adj[b].discard(a)
     changed=True
   if not changed:break
  chains=trace();relocate={};omit=set()
  # Acute joins in M, A etc. create a false Y in a medial skeleton. Collapse
  # its short terminal to the endpoint and join the real strokes there.
  for i,chain in enumerate(chains):
   ends=[q for q in [chain[0],chain[-1]]if len(adj[q])==1];js=[q for q in [chain[0],chain[-1]]if len(adj[q])>2]
   if not ends or not js:continue
   j=js[0];length=LineString(world(chain)).length
   if length<3.25*radii[j[1],j[0]] and j not in relocate:
    relocate[j]=(world([ends[0]])[0],length);omit.add(i)
  for i,chain in enumerate(chains):
   if i in omit:continue
   coords=world(chain)
   for reverse in [False,True]:
    if reverse:coords.reverse();chain=chain[::-1]
    if chain[0]in relocate:
     xy,length=relocate[chain[0]];total=0;j=1
     while j<len(coords)-1:
      total+=math.dist(coords[j-1],coords[j])
      if total>=length*1.05:break
      j+=1
     candidate=[xy,*coords[j:]]
     # Retain the original stroke if moving a joint would leave the glyph.
     if LineString(candidate).difference(glyph.buffer(.025)).length<.015:coords=candidate
    if reverse:coords.reverse()
   line=LineString(coords)
   if line.length>.002:result.append(line.simplify(step*.8,preserve_topology=False))
  for q in isolated:
   if not adj[q]:
    x,y=q;cx,cy=x*step+ox,y*step+oy;length=max(.018,min(.09,math.sqrt(glyph.area)*.5));result.append(LineString([(cx-length/2,cy),(cx+length/2,cy)]))
  if not chains and not nodes:
   c=glyph.centroid;result.append(LineString([(c.x-.009,c.y),(c.x+.009,c.y)]))
 return unary_union(result)
