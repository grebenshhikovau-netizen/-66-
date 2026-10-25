"""Closed bottom-origin plywood solids, including integral shallow crater pockets."""
import json,math,csv
from collections import Counter,defaultdict
from shapely.geometry import shape,mapping,Polygon,Point
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
from common import ROOT,DATA,C,M,polys,polygonal,dump

D=json.load(open(ROOT/'geometry.json'));RU=json.load(open(DATA/'russia-reference.json'));S=M/1000
objects=[];variants={'relief':[],'political':[],'political_water':[],'reference':[]};region_info={};country_info={}
contact_repairs=[]
def prepared(g,region,tier,variant):
 result=[]
 for p in polys(g):
  p=p.simplify(.002,preserve_topology=True)
  # A valid 2D polygon may have a hole tangent to its outside at one point.
  # Extruding that contact creates a four-face vertical edge. Open only those
  # exact contacts by a 0.015 mm local notch, without rounding the whole coast.
  for attempt in range(3):
   repeated=[]
   for q in polys(p):
    cc=Counter(tuple(v) for ring in [q.exterior,*q.interiors] for v in list(ring.coords)[:-1])
    repeated.extend(v for v,n in cc.items() if n>1)
   if not repeated:break
   cutters=unary_union([Point(v).buffer(.02,resolution=4) for v in repeated]);p=p.difference(cutters)
   contact_repairs.append({'variant':variant,'region':region,'tier':tier,'opened_point_contacts':len(repeated),'notch_diameter_mm':.04*M})
  result.extend(q for q in polys(p) if tier==1 or q.area*M*M>=.01)
 return sorted(result,key=lambda p:-p.area)
for r in D['regions']:
 g=shape(r['geom']);xmin,ymin,xmax,ymax=g.bounds;region_info[r['id']]={**r,'origin':[(xmin+xmax)/2*S,(2657.4803125-(ymin+ymax)/2)*S,0]}
 country_info.setdefault(r['country'],{'name':r['country_name'],'color':r['color'],'coating_name':r['coating_name'],'parts':[]})['parts'].append(g)
for c,row in country_info.items():
 g=unary_union(row.pop('parts'));x0,y0,x1,y1=g.bounds;row['origin']=[(x0+x1)/2*S,(2657.4803125-(y0+y1)/2)*S,0]

def solid(p,name,tier,region,country,variant,pockets=()):
 if p.is_empty or p.area<1e-10:return
 h=.003;z=(tier-1)*h if variant in ['relief','reference'] else 0
 discs=[]
 for c in pockets:
  if c['tier']==tier:
   q=shape(c['geom']).intersection(p)
   if q.area>1e-9:discs.append(q)
 pocket=polygonal(unary_union(discs));depth=.00035
 top=polygonal(p.difference(pocket)) if not pocket.is_empty else p
 cells=[(top,h,0)]
 if not pocket.is_empty:cells.append((pocket,h-depth,2))
 x0,y0,x1,y1=p.bounds;cx=(x0+x1)/2;cy=(y0+y1)/2
 verts=[];faces=[];mats=[];lookup={};edges=defaultdict(list);heights=defaultdict(set)
 def vk(q):return (round(q[0],8),round(q[1],8))
 def vertex(q,z):
  key=(*vk(q),round(z,12))
  if key not in lookup:lookup[key]=len(verts);verts.append([(key[0]-cx)*S,-(key[1]-cy)*S,z])
  return lookup[key]
 def face(q,z,mat,reverse=False):
  ids=[vertex(a,z) for a in q]
  if len(set(ids))!=len(ids):return
  faces.append(ids[::-1] if reverse else ids);mats.append(mat)
 for g,height,mat in cells:
  triangles=[];boundary=Counter()
  for tri in constrained_delaunay_triangles(g).geoms:
   q=[vk(x) for x in list(tri.exterior.coords)[:3]]
   if len(set(q))<3:continue
   triangles.append(q)
   for a,b in zip(q,q[1:]+q[:1]):boundary[tuple(sorted((a,b)))]+=1
  for q in triangles:face(q,height,mat);face(q,0,1,True)
  for edge,count in boundary.items():
   if count==1:
    edges[edge].append(height)
    for q in edge:heights[q].update([0,height])
 for (a,b),zs in edges.items():
  zs=sorted(set(zs));lo,hi=(0,zs[0]) if len(zs)==1 else (zs[0],zs[-1])
  if hi-lo<1e-12:continue
  seq=[(a,lo),(b,lo)]+[(b,v) for v in sorted(heights[b]) if lo<v<hi]+[(b,hi),(a,hi)]+[(a,v) for v in sorted(heights[a],reverse=True) if lo<v<hi]
  ids=[vertex(q,v) for q,v in seq]
  if len(set(ids))==len(ids):faces.append(ids);mats.append(1)
 if len(verts)<4:return
 adjacency=Counter(tuple(sorted((a,b))) for f in faces for a,b in zip(f,f[1:]+f[:1]))
 assert all(n==2 for n in adjacency.values()),('non-manifold export',name,[(e,n) for e,n in adjacency.items() if n!=2][:5])
 row={'id':name,'variant':variant,'region':region,'country':country,'tier':tier,'origin':[cx*S,(2657.4803125-cy)*S,z],'height':h,'vertices':verts,'faces':faces,'material_indices':mats,'geom':mapping(p),'area_mm2':p.area*M*M,'pockets':not pocket.is_empty}
 objects.append(row);variants[variant].append(name)

for r in D['regions']:
 code=r['id'];country=r['country'];g=shape(r['geom'])
 for variant,prefix,gs in [('political','P',[g]),('political_water','W',[shape(D['region_layers'][code][0])]),('relief','R',[shape(x) for x in D['region_layers'][code]])]:
  for i,layer in enumerate(gs,1):
   for j,p in enumerate(prepared(layer,code,i,variant),1):solid(p,f'{prefix}_{code}_L{i:02d}_P{j:03d}',i,code,country,variant,D['craters'] if variant=='relief' else ())
print('NEW TERRITORY SOLIDS',len(objects),flush=True)
for row in json.load(open(DATA/'russia-mesh-reference.json'))['objects']:
 objects.append(row);variants['reference'].append(row['id'])
refs=[o for o in objects if o['variant']=='reference'];assert len(refs)==67,len(refs)

geo={o['id']:shape(o['geom']) for o in objects if o['variant']!='reference'};byregion=defaultdict(list)
for o in objects:byregion[(o['variant'],o['region'],o['tier'])].append(o)
relations={}
for o in objects:
 if o['variant']!='relief' or o['tier']==1:continue
 owners=[p['id'] for p in byregion[('relief',o['region'],o['tier']-1)] if geo[p['id']].intersection(geo[o['id']]).area>1e-9]
 assert owners,('missing support',o['id']);relations[o['id']]=owners
dump('model-data.json',{'objects':objects,'variants':variants,'regions':region_info,'countries':country_info,'mm_per_unit':M,'russia_palette':RU['palette'],'landmarks':D['landmarks'],'craters':D['craters']})
dump('model-relations.json',{'stack':relations})
dump('Исправление-точечных-касаний.json',contact_repairs)
with (ROOT/'Детали-для-сборки.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f,lineterminator='\n');w.writerow(['Объект Blender','Вариант','Политическая часть','Страна','Слой','Площадь, мм²','Начало отсчёта'])
 for o in objects:
  if o['variant']!='reference':w.writerow([o['id'],o['variant'],o['region'],o['country'],o['tier'],round(o['area_mm2'],4),'Нижняя плоскость'])
dump('Проверка-экспорта.json',{'variant_objects':{k:len(v) for k,v in variants.items()},'russian_reference_solids':len(refs),'all_upper_pieces_have_support':True,'bottom_origin_local_z':0,'same_region_root_xy_for_all_variants':True,'integral_crater_pockets_mm':.35})
print('EXPORTED VARIANTS',{k:len(v) for k,v in variants.items()},flush=True)
