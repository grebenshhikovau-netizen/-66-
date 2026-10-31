"""Recover envelopes for nesting; preserve every original SVG path/text byte-for-byte."""
from pathlib import Path
import json,math,shutil,hashlib
import numpy as np
from lxml import etree as E
from svgpathtools import parse_path,Line,CubicBezier,QuadraticBezier,Arc
from shapely.geometry import LineString,Polygon,Point,box,mapping
from shapely.ops import unary_union,polygonize
from shapely import make_valid
from scipy.spatial import cKDTree

P=Path(__file__).resolve().parent.parent
src=P/'source.svg'
root=E.parse(str(src)).getroot();K=25.4/72
assert all(set(g.attrib)<={'id'}for g in root.iter()if E.QName(g).localname=='g')
elements=[q for q in root.iter()if E.QName(q).localname in ['path','text']]

def flatten(seg):
 a,b=seg.start*K,seg.end*K
 if isinstance(seg,Line):return [(a.real,a.imag),(b.real,b.imag)]
 if isinstance(seg,(CubicBezier,QuadraticBezier)):
  pts=[complex(q)*K for q in seg.bpoints()]
  out=[(pts[0].real,pts[0].imag)]
  def walk(pp,depth=0):
   line=LineString([(pp[0].real,pp[0].imag),(pp[-1].real,pp[-1].imag)])
   err=max(Point(p.real,p.imag).distance(line) for p in pp[1:-1])
   if err<.008 or depth>14:out.append((pp[-1].real,pp[-1].imag));return
   levels=[pp]
   while len(levels[-1])>1:levels.append([(a+b)/2 for a,b in zip(levels[-1],levels[-1][1:])])
   walk([q[0]for q in levels],depth+1);walk([q[-1]for q in levels[::-1]],depth+1)
  walk(pts);return out
 n=max(3,math.ceil(abs(b-a)/.15));pp=[seg.point(t)*K for t in np.linspace(0,1,n)]
 return[(p.real,p.imag)for p in pp]

paths=[];net=[];ends=[];leaves=[]
for i,e in enumerate(elements):
 fine_point=None
 if E.QName(e).localname=='text':
  x=float(e.get('x',0))*K;y=float(e.get('y',0))*K;g=Point(x,y)
 else:
  p=parse_path(e.get('d'));sub=[]
  if any('stroke: '+c in e.get('style','')for c in ['#cc0033','#e30016']):
   a,b,c,d=p.bbox();a,b,c,d=[v*K for v in [a,b,c,d]]
   if .15<max(b-a,d-c)<=6:fine_point=[(a+b)/2,(c+d)/2]
  for q in p.continuous_subpaths():
   xy=[]
   for seg in q:
    cc=flatten(seg);xy.extend(cc if not xy else cc[1:])
   if len(xy)>1:
    line=LineString(xy);sub.append(line)
  g=unary_union(sub)
  if g.is_empty:
   b=p.bbox();g=Point(b[0]*K,b[2]*K)
  black=any('stroke: '+c in e.get('style','')for c in ['#333333','#1b1918'])
  if black:
   for line in sub:
    if line.length>.1:
     net.append(line)
     if not line.is_ring:ends.extend([line.coords[0],line.coords[-1]])
  paths.append({'index':i,'black':black,'geom':g})
 leaves.append({'index':i,'geom':g,'element':e,'fine_point':fine_point})
 if i%1500==0:print('READ',i,flush=True)

# Close tiny laser holding tabs only in the disposable packing envelope.
# The actual source paths below remain completely unchanged.
tree=cKDTree(ends)
for a,b in tree.query_pairs(.8):
 if ends[a]!=ends[b]:net.append(LineString([ends[a],ends[b]]))
polygons=list(polygonize(unary_union(net)))
shells=[]
for p in sorted(polygons,key=lambda p:-p.area):
 if p.area<1:continue
 shell=Polygon(p.exterior)
 if any(q.buffer(.02).covers(shell)for q in shells):continue
 shells.append(shell)
print('RECOVERED',len(shells),'envelopes, area',sum(q.area for q in shells),flush=True)

# A single source curve may contain disconnected islands; keep it intact.
parent=list(range(len(shells)));shell_buffers=[q.buffer(.025)for q in shells]
def find(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
for q in paths:
 if not q['black'] or q['geom'].length<1:continue
 hits=[i for i,g in enumerate(shell_buffers)if q['geom'].intersects(g)and q['geom'].intersection(g).length>1]
 if len(hits)>1:
  for i in hits[1:]:parent[find(i)]=find(hits[0])
groups={}
for i,g in enumerate(shells):groups.setdefault(find(i),[]).append(g)
envelopes=[unary_union(v)for v in groups.values()]
members=[[]for g in envelopes];decorations=[[]for g in envelopes]
envelope_buffers=[h.buffer(.04)for h in envelopes]
from shapely.strtree import STRtree
spatial=STRtree(envelope_buffers)
for leaf in leaves:
 g=leaf['geom'];hits=spatial.query(g)
 scores={int(i):g.intersection(envelope_buffers[i]).length for i in hits}
 if scores and max(scores.values())>0:owner=max(scores,key=scores.get)
 else:owner=min(range(len(envelopes)),key=lambda i:g.distance(envelopes[i]))
 members[owner].append(leaf['index']);decorations[owner].append(g)

output=[]
for i,(g,idx,dec)in enumerate(zip(envelopes,members,decorations)):
 if not idx:continue
 occupied=g.union(unary_union(dec).buffer(.09,quad_segs=3))
 output.append({'id':f'P{i+1:03d}','geom':mapping(occupied),'material':mapping(g),
                'bounds':occupied.bounds,'area_mm2':g.area,'members':idx,
                'fine_points':[leaves[j]['fine_point']for j in idx if leaves[j]['fine_point']is not None]})
(P/'parts.json').write_text(json.dumps(output,ensure_ascii=False))
(P/'extraction.json').write_text(json.dumps({'source_elements':len(leaves),'source_paths':sum(E.QName(q).localname=='path'for q in elements),
 'source_texts':sum(E.QName(q).localname=='text'for q in elements),'parts':len(output),
 'source_svg_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'packing_tab_connection_only_mm':.8,
 'source_shapes_modified':False},indent=2))
print('EXTRACTED',len(output),flush=True)
