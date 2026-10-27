"""Make engraving one noded graph: common borders, no parallel duplicates, ends joined to real edges."""
import json,math
from pathlib import Path
import numpy as np
from shapely.geometry import shape,mapping,Polygon,LineString,Point
from shapely.ops import unary_union,linemerge,nearest_points,substring
from shapely import STRtree,union_all,snap
from collections import Counter
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));network=shape(D['political_network']);ledge=shape(D['water_upper_union']).difference(shape(D['water_base_union']));pyr=json.load(open(P/'data/source/pyramid-reference.json'));cx,cy=pyr['center'];x0,y0,x1,y1=shape(D['pyramid_block']).bounds;faces=unary_union([LineString([(cx,cy),q])for q in [(x0,y0),(x0,y1),(x1,y0),(x1,y1)]])
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for a in getattr(g,'geoms',[])for p in ps(a)]
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[LineString(g)]if g.length>1e-7 else[]
 return[p for a in getattr(g,'geoms',[])for p in lines(a)]
def merged(g):
 g=unary_union(lines(g));return linemerge(g)if g.geom_type=='MultiLineString'else g
def snap_ends(g,target,tol=.9):
 out=[]
 for line in lines(merged(g)):
  cc=list(line.coords)
  if line.is_ring:out.append(line);continue
  for k in [0,-1]:
   p=Point(cc[k]);near=nearest_points(p,target)[1]
   if p.distance(near)<tol:cc[k]=near.coords[0]
  if len(set(cc))>1:out.append(LineString(cc))
 return merged(unary_union(out))
def drop_parallel(g,anchor,width=.50):
 segs=[LineString([a,b])for l in lines(anchor)for a,b in zip(l.coords,list(l.coords)[1:])if math.dist(a,b)>1e-6];tree=STRtree(segs);out=[]
 for line in lines(g):
  n=max(2,math.ceil(line.length/.16));ds=np.linspace(0,line.length,n+1);pts=[line.interpolate(float(x))for x in ds];keep=[]
  for i,(a,b)in enumerate(zip(pts,pts[1:])):
   mid=Point((a.x+b.x)/2,(a.y+b.y)/2);s=segs[int(tree.nearest(mid))];v=np.array([b.x-a.x,b.y-a.y]);q=np.array(s.coords[-1])-np.array(s.coords[0]);dot=abs(float(v@q))/(np.linalg.norm(v)*np.linalg.norm(q)+1e-20);keep.append(mid.distance(s)>width or dot<.89)
  runs=np.flatnonzero(np.diff(np.r_[False,keep,False].astype(np.int8)))
  for a,b in zip(runs[::2],runs[1::2]):
   q=substring(line,float(ds[a]),float(ds[b]))
   if q.length>.75:out.append(q)
 return merged(unary_union(out))
def heal(g,carrier):
 g=snap(g,g,.012)
 for iteration in range(12):
  ll=lines(union_all(lines(g),grid_size=.001));degree=Counter()
  for line in ll:
   for pt in [line.coords[0],line.coords[-1]]:degree[(round(pt[0],3),round(pt[1],3))]+=1
  joins=[];pruned=set()
  for xy,n in degree.items():
   e=Point(xy)
   if n!=1 or e.distance(carrier.boundary)<.015:continue
   incident=[(i,q)for i,q in enumerate(ll)if xy in [(round(v[0],3),round(v[1],3))for v in [q.coords[0],q.coords[-1]]]]
   if len(incident)==1 and incident[0][1].length<.8:
    pruned.add(incident[0][0]);continue
   targets=[carrier.boundary]+[q for q in ll if e.distance(q)>.002];target=min(targets,key=lambda q:e.distance(q));q=nearest_points(e,target)[1];join=LineString([e,q])
   if join.length<1.6 and carrier.buffer(.002).covers(join):joins.append(join)
  if pruned:
   g=union_all([q for i,q in enumerate(ll)if i not in pruned],grid_size=.001);continue
  if not joins:return merged(unary_union(ll))
  g=union_all(ll+joins,grid_size=.001)
 return merged(g)
allgraph=[];stats=[]
for row in D['pieces']:
 g=shape(row['geom']);upper=unary_union([shape(q['geom'])for q in D['pieces']if q['tier']==row['tier']+1]);cover=upper.intersection(g)
 # Water-bank ledges use the existing black water cut as the boundary, eliminating nearby red copies.
 extra=[q for q in ps(ledge.intersection(g))if q.distance(cover)<.005]if not cover.is_empty else[];cover=cover.union(unary_union(extra)).intersection(g);guide=snap_ends(cover.boundary.difference(g.boundary.buffer(.008)),g.boundary,.025)if not cover.is_empty else Polygon().boundary
 guide=snap_ends(drop_parallel(guide,g.boundary),g.boundary,.95)if not guide.is_empty else guide
 # A country edge which already follows a cutting/assembly edge is represented by that edge once.
 domain=g.difference(cover);anchor=unary_union([g.boundary,guide]);political=network.intersection(domain);political=drop_parallel(political,anchor);political=snap_ends(political,anchor,.95)
 face=faces.intersection(shape(row['visible']));face=snap_ends(face,anchor,.4);structural=merged(unary_union([guide,political,face]).intersection(g));structural=heal(structural,g);row['red_political']=mapping(political.intersection(shape(row['visible'])));row['placement_guides']=mapping(guide);row['red_pyramid_faces']=mapping(face);row['assembly_closed_outlines']=mapping(upper.intersection(g));row['structural_engraving']=mapping(structural);allgraph.extend(lines(structural));stats.append({'piece':row['id'],'chains':len(lines(structural)),'length_mm':structural.length})
D['structural_engraving']=mapping(unary_union(allgraph));D['line_cleanup_method']='shared country graph; political edges join cut/assembly nodes; water-bank duplicates suppressed; full physical assembly contours separate';(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));(P/'Проверка-структуры-линий.json').write_text(json.dumps({'pieces':stats},ensure_ascii=False,indent=2));print('STRUCTURE READY',stats,flush=True)
