"""Finish continuous engraving without punching gaps around lettering."""
import json,math
from pathlib import Path
from collections import defaultdict
from shapely.geometry import shape,LineString,MultiLineString,mapping,Point
from shapely.ops import unary_union,nearest_points
from shapely import union_all
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'))
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[LineString(g)]if g.length>1e-7 else[]
 return[l for a in getattr(g,'geoms',[])for l in lines(a)]
def trails(g):
 # Node once on a micrometre grid, then cover every edge once, joining through junctions.
 ls=lines(union_all(lines(g),grid_size=.001));edges={};adj=defaultdict(list)
 def node(p):return(round(p[0],3),round(p[1],3))
 for i,line in enumerate(ls):
  cc=list(line.coords);a=node(cc[0]);b=node(cc[-1]);cc[0]=a;cc[-1]=b;edges[i]=(a,b,cc);adj[a].append(i);adj[b].append(i)
 components=[];unseen=set(adj)
 while unseen:
  root=next(iter(unseen));stack=[root];group=set()
  while stack:
   a=stack.pop()
   if a in group:continue
   group.add(a);unseen.discard(a)
   for i in adj[a]:x,y,_=edges[i];stack.append(y if a==x else x)
  components.append(group)
 real=len(edges);virtual=set()
 for group in components:
  odd={a for a in group if len(adj[a])%2}
  while odd:
   a=min(odd);odd.remove(a);b=min(odd,key=lambda b:math.dist(a,b));odd.remove(b);i=len(edges);edges[i]=(a,b,None);adj[a].append(i);adj[b].append(i);virtual.add(i)
 result=[];used=set()
 for group in components:
  root=next(iter(group));stack=[(root,None)];circuit=[]
  while stack:
   a,_=stack[-1]
   while adj[a]and adj[a][-1]in used:adj[a].pop()
   if not adj[a]:circuit.append(stack.pop());continue
   i=adj[a].pop();used.add(i);x,y,_=edges[i];stack.append((y if a==x else x,i))
  circuit.reverse();steps=[]
  for (a,_),(b,i)in zip(circuit,circuit[1:]):
   cc=edges[i][2]
   if cc is not None:cc=cc if node(cc[0])==a else cc[::-1]
   steps.append(cc)
  if any(q is None for q in steps):
   k=next(i for i,q in enumerate(steps)if q is None);steps=steps[k+1:]+steps[:k+1]
  chain=[]
  for cc in steps+[None]:
   if cc is None:
    if len(chain)>1:result.append(LineString(chain))
    chain=[]
   else:chain.extend(cc if not chain else cc[1:])
 assert len(used)==len(edges)
 return MultiLineString(result)
texture=shape(json.load(open(P/'data/source/texture-reference.json'))).difference(shape(json.load(open(P/'data/source/pyramid-reference.json'))['country']).buffer(.6));boxes=unary_union([shape(a['bbox']).buffer(.16)for a in D['labels']]);marks=unary_union([shape(a['geom']).buffer(.08)for a in D['city_markers']]);notes=[]
for row in D['pieces']:
 g=shape(row['geom']);visible=shape(row['visible']);graph=trails(shape(row['structural_engraving']));leaders=[]
 for a in D['labels']:
  if a['piece']!=row['id']or not a.get('leader'):continue
  line=shape(a['leader'])
  # A leader belongs to one carrier; do not engrave scattered fragments across height steps.
  if visible.buffer(.002).covers(line):leaders.append(line)
  else:notes.append({'text':a['text'],'reason':'leader across separate height surfaces omitted; lettering kept'})
 leader=MultiLineString(lines(unary_union(leaders)));red=MultiLineString(lines(graph)+lines(leader));tex=texture.intersection(visible).intersection(g.buffer(-.24)).difference(boxes).difference(marks);row['red_structural']=mapping(graph);row['red_internal']=mapping(red);row['red_leaders']=mapping(leader);row['red_texture']=mapping(tex);ink=unary_union([shape(a['geometry'])for a in D['labels']if a['piece']==row['id']]+[shape(a['geom'])for a in D['city_markers']if a['piece']==row['id']]);row['engraving']=mapping(ink.union(red.buffer(.022,cap_style=2,join_style=2)).union(tex).intersection(g))
 assert graph.intersection(boxes.buffer(-.1)).length<.01,(row['id'],'border through lettering')
D['line_cleanup_notes']=notes;(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));print('CONTINUOUS ENGRAVING READY',len(D['labels']),'texts',len(notes),'leader notes',flush=True)
