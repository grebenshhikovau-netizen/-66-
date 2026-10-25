import json,math,csv
from pathlib import Path
from collections import defaultdict,Counter
from shapely.geometry import shape,mapping,Polygon,Point
from shapely.ops import unary_union
from shapely import make_valid,set_precision
from lxml import etree as E
P=Path(__file__).resolve().parent.parent;rows=json.load(open(P/'extracted.json'))
def ps(g):
 if g.geom_type=='Polygon':return [g] if not g.is_empty and g.area>.0001 else []
 return [p for q in getattr(g,'geoms',[]) for p in ps(q)]
def clean(g):return set_precision(set_precision(unary_union(ps(make_valid(g))),.01),0)
excluded=[r['name'] for r in rows if r['kind']=='wood' and shape(r['geom']).bounds[2]<100]
wood=[{**r,'g':clean(shape(r['geom']))} for r in rows if r['kind']=='wood' and r['name'] not in excluded];regions={};colors={}
ab=next(r['color'] for r in wood if 'Alberta' in r['region'])
for r in wood:
 rid=r['region'];n=int(rid.split('_')[1]);name=rid.split('_',2)[2];usa=(12<=n<=50 and n!=13) or n in [54,55,58,59,60,61,63,65]
 if usa:coat='NATURAL';color=[.7991,.6514,.4125]
 else:
  color=ab if 'Yukon' in rid else r['color'];coat=('ALASKA_' if n==1 else 'PAINT_')+'_'.join(str(round(c,3)) for c in color)
 r['coat']=coat;colors[coat]=color;regions.setdefault(rid,[]).append(r)
# Resolve tiny overlaps of imported political outlines once, consistently for all plies.
territories={};occupied=Polygon()
for rid,rr in sorted(regions.items()):
 raw=unary_union([r['g'] for r in rr]);territories[rid]=raw.difference(occupied);occupied=unary_union([occupied,raw])
L=[unary_union([r['g'].intersection(territories[r['region']]) for r in wood if r['hi']>=i*3-.05]) for i in [1,2,3]]
# Raise the already separate north-Arizona canyon strip to the second ply.
canyon_strip=unary_union([r['g'] for r in wood if r['name']=='REG_23_Arizona__L01_P02'])
if not canyon_strip.is_empty:
 arizona=unary_union([r['g'] for r in wood if r['region']=='REG_23_Arizona'])
 L[1]=unary_union([L[1],canyon_strip.buffer(.5).intersection(arizona).intersection(L[0])])
for i in [2,1]:L[i-1]=unary_union([L[i-1],L[i]])
# Open exact point contacts by 0.04 mm so the extruded cut has a manifold wall.
point_repairs=[]
for layer in L:
 for part in ps(layer):
  counts=Counter(tuple(v) for ring in [part.exterior,*part.interiors] for v in list(ring.coords)[:-1])
  point_repairs += [Point(q).buffer(.02,quad_segs=4) for q,n in counts.items() if n>1]
if point_repairs:
 notches=unary_union(point_repairs);L=[g.difference(notches) for g in L]

# Source top colours are read at their true height; identical imported copies
# collapse to one surface. USA remains unpainted and Yukon takes Alberta orange.
surface={}
for rid,rr in regions.items():
 coat=rr[0]['coat'];surface[coat]=unary_union([surface.get(coat,Polygon()),territories[rid]])
ink=clean(unary_union([shape(r['geom']) for r in rows if r['kind']=='engraving']));visible=[L[i].difference(L[i+1]) if i<2 else L[i] for i in range(3)]
pieces=[];contacts=[];summary=[]
for i in range(3):
 nextlayer=L[i+1] if i<2 else Polygon();nodes=[]
 for rid,rr in regions.items():
  g=unary_union([r['g'] for r in rr if r['hi']>=3*(i+1)-.05]).intersection(territories[rid]).intersection(L[i])
  if i==1 and 'Arizona' in rid:g=unary_union([g,L[1].intersection(canyon_strip.buffer(.5)).intersection(territories[rid])])
  if g.is_empty:continue
  coat=rr[0]['coat'];nodes.append({'id':rid,'g':g,'coat':coat,'v':unary_union(ps(g.intersection(visible[i])))})
 forbidden=set();edges=[]
 for a in range(len(nodes)):
  for b in range(a):
   A,B=nodes[a],nodes[b]
   boundary=A['g'].boundary.intersection(B['g'].boundary.buffer(.025));length=boundary.length
   if length<.1:continue
   conflict=A['coat']!=B['coat'] and A['v'].buffer(.025).intersection(B['v'].buffer(.025)).area>.015
   if conflict:forbidden.add((b,a));contacts.append({'tier':i+1,'a':A['id'],'b':B['id'],'length_mm':length})
   edges.append((length,a,b,conflict))
 groups=[{j} for j in range(len(nodes))]
 def owner(j):return next(k for k,v in enumerate(groups) if j in v)
 if i==0:groups=[set(range(len(nodes)))]
 else:
  for length,a,b,conflict in sorted(edges,reverse=True):
   u,v=owner(a),owner(b)
   if u==v or conflict:continue
   if any(tuple(sorted((x,y))) in forbidden for x in groups[u] for y in groups[v]):continue
   groups[u]|=groups[v];groups[v]=set()
 index=0
 for group in groups:
  if not group:continue
  merged=unary_union([nodes[j]['g'] for j in group])
  for part in sorted(ps(merged),key=lambda g:-g.area):
   index+=1;pid=f'L{i+1:02d}_P{index:03d}';exposed=part.intersection(visible[i]);paints={}
   for coat,g in surface.items():
    v=g.intersection(exposed)
    if v.is_empty or v.area<.001:continue
    expanded=unary_union([v,v.buffer(2).intersection(nextlayer).intersection(part)]);paints[coat]={'visible':mapping(v),'with_overlap':mapping(expanded),'paint':coat!='NATURAL'}
   engraving=ink.intersection(exposed);pieces.append({'id':pid,'tier':i+1,'geom':mapping(part),'visible':mapping(exposed),'engraving':mapping(engraving),'paint':paints,'regions':sorted(nodes[j]['id'] for j in group if nodes[j]['g'].intersection(part).area>.01),'area_mm2':part.area})
 summary.append({'tier':i+1,'pieces':index,'visible_conflicts_require_cut_or_stencil':sum(c['tier']==i+1 for c in contacts)})
for i,g in enumerate(L):
 rebuilt=unary_union([shape(p['geom']) for p in pieces if p['tier']==i+1]);assert rebuilt.symmetric_difference(g).area<.1,(i,rebuilt.symmetric_difference(g).area)
 for p in pieces:
  if p['tier']!=i+1:continue
  for coat,v in p['paint'].items():
   extra=shape(v['with_overlap']).difference(shape(v['visible']));assert extra.difference(L[i+1] if i<2 else Polygon()).area<.03
plan={'layers':[mapping(g) for g in L],'visible':[mapping(g) for g in visible],'pieces':pieces,'colors':colors,'summary':summary,'contact_warnings':contacts,'paint_overlap_mm':2,'yukon_orange':True,'canyon_north_strip_raised_mm':3,'canyon_extension_mm':.5,'source_wood_objects':len(wood),'source_engraving_objects':sum(r['kind']=='engraving' for r in rows),'input_file':'source.blend','excluded_misplaced_objects':excluded,'natural_is_unpainted':True,'point_contact_notch_mm':.04,'point_contact_repairs':len(point_repairs)}
exec((P/'tools'/'annotations.py').read_text())
(P/'production-plan.json').write_text(json.dumps(plan,ensure_ascii=False));print(summary,flush=True)
S='http://www.w3.org/2000/svg';x0,y0,x1,y1=L[0].bounds
def root():return E.Element('svg',nsmap={None:S},width=f'{x1-x0}mm',height=f'{y1-y0}mm',viewBox=f'{x0} {y0} {x1-x0} {y1-y0}')
def path(r,g,id,color,stroke=False):
 from shapely.geometry.polygon import orient
 d=' '.join('M'+' L'.join(f'{x:.5f},{y:.5f}' for x,y in list(ring.coords)[:-1])+' Z' for p in ps(g) for ring in [orient(p,-1).exterior,*orient(p,-1).interiors])
 if d:
  e=E.SubElement(r,'path',id=id,d=d,fill=color,attrib={'fill-rule':'nonzero'})
  if stroke:e.set('stroke','#30251e');e.set('stroke-width','.12')
def save(r,f):
 dest=P/f;dest.parent.mkdir(parents=True,exist_ok=True);E.ElementTree(r).write(str(dest),encoding='UTF-8',xml_declaration=True)
def rgb(c):return '#'+''.join(f'{round((12.92*v if v<.0031308 else 1.055*v**(1/2.4)-.055)*255):02x}' for v in c)
for i in range(3):
 cut=root();eng=root();paint=root();guide=root()
 for p in pieces:
  if p['tier']!=i+1:continue
  g=shape(p['geom']);path(cut,g,p['id'],'#000');path(eng,shape(p['engraving']),p['id']+'_TEXT','#000');path(guide,g,p['id'],'#e5d4b3',True)
  one=root();path(one,g,p['id'],'#000');save(one,f'Детали/{p["id"]}/Резка.svg');one=root();path(one,shape(p['engraving']),p['id']+'_TEXT','#000');save(one,f'Детали/{p["id"]}/Гравировка.svg')
  for coat,v in p['paint'].items():
   path(paint,shape(v['with_overlap']),p['id']+'_'+coat,rgb(colors[coat]));one=root();path(one,shape(v['with_overlap']),p['id']+'_'+coat,'#000');save(one,f'Детали/{p["id"]}/Покраска-{coat}.svg')
  q=g.representative_point();t=E.SubElement(guide,'text',x=str(q.x),y=str(q.y),attrib={'font-size':'2.4','text-anchor':'middle','font-family':'Noto Sans'},fill='#30251e');t.text=p['id']
 save(cut,f'Слой-{i+1:02d}-резка.svg');save(eng,f'Слой-{i+1:02d}-гравировка.svg');save(paint,f'Слой-{i+1:02d}-покраска-с-напуском.svg');save(guide,f'Слой-{i+1:02d}-сборка.svg')
print('Production vectors ready',flush=True)
