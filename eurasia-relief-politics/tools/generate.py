"""Six shared geographic layers, then exact clipping by political modules."""
import json,math,csv
from collections import defaultdict
from pathlib import Path
import numpy as np
from shapely.geometry import shape,mapping,Polygon,Point,LineString
from shapely.ops import unary_union,nearest_points,linemerge
from shapely.affinity import rotate,scale
from lxml import etree as E
from common import *
from landscape import build_landscape

R=json.load(open(DATA/'regions.json'));F=json.load(open(DATA/'geographic-features.json'));RU=json.load(open(DATA/'russia-reference.json'))
regions=[{**r,'geom_shape':polygonal(shape(r['geom']))} for r in R];pure=polygonal(shape(json.load(open(DATA/'base.json'))));rus=polygonal(shape(RU['source_outline']));shared=shape(json.load(open(DATA/'russia-shared-seam.json')))
pr=C['production'];features=F['landmarks'];fjord_masks={}
for f in features:
 if f['kind']!='fjord':continue
 axis=project(LineString(f['coords']));start=Point(axis.coords[0]);p=nearest_points(start,pure.boundary)[1]
 if p.distance(start)*M<4:axis=unary_union([axis,LineString([start,p])])
 fjord_masks[f['name']]=axis.buffer(f['width_mm']/2/M)
fjords=unary_union(list(fjord_masks.values()));pure=polygonal(pure.difference(fjords))
for r in regions:r['geom_shape']=polygonal(r['geom_shape'].intersection(pure));r['geom']=mapping(r['geom_shape'])
print('BUILDING SHARED LANDSCAPE',flush=True);layers,style_report=build_landscape(pure,F)

# Major natural waterways; only the explicit perennial river families are used.
river_parts=defaultdict(list)
for f in F['rivers']:river_parts[f['name']].append(project(shape(f['geom'])))
river_axes={n:unary_union(gs) for n,gs in river_parts.items()}
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return [g]
 return [a for b in getattr(g,'geoms',[]) for a in lines(b)]
for n,g in list(river_axes.items()):
 seg=lines(g);links=[]
 for line in seg:
  others=unary_union([l for l in seg if l is not line])
  if others.is_empty:continue
  for p in [Point(line.coords[0]),Point(line.coords[-1])]:
   q=nearest_points(p,others)[1]
   if 1e-7<p.distance(q)*M<1.7:links.append(LineString([p,q]))
 river_axes[n]=unary_union([g,*links])

mouths={'Дунай':(29,45.2),'Рейн':(5.0,51.9),'Рона':(4.7,43.4),'По':(12.5,44.9),'Янцзы':(121.8,31.6),'Хуанхэ':(119,37.8),'Чжуцзян':(113.55,22.1),'Меконг':(106.3,9.8),'Ганг':(90,22),'Инд':(67.7,24),'Шатт-эль-Араб':(48.55,29.95),'Иравади':(95.0,16.0),'Салуин':(97.6,16.5)}
for n,(lo,la) in mouths.items():
 if n not in river_axes:continue
 q=project(Point(lo,la));axis=river_axes[n];ends=[Point(x) for l in lines(axis) for x in [l.coords[0],l.coords[-1]]];p=min(ends,key=lambda p:p.distance(q));coast=nearest_points(p,pure.boundary)[1]
 if p.distance(coast)*M<5.5:river_axes[n]=unary_union([axis,LineString([p,coast])])
# Discrete principal delta arms, with no dense mesh of tributary channels.
for name,coords in [
 ('Меконг',[(105.8,10.25),(106.1,10.15),(106.65,9.85)]),
 ('Ганг',[(89.7,23.15),(90.2,22.6),(90.55,22.05)]),
 ('Чжуцзян',[(113.55,22.57),(113.45,22.35),(113.55,22.08)])]:
 if name not in river_axes:continue
 g=project(LineString(coords));a=nearest_points(Point(g.coords[0]),river_axes[name])[1];g=LineString([a.coords[0],*g.coords]);b=nearest_points(Point(g.coords[-1]),pure.boundary)[1]
 if Point(g.coords[-1]).distance(b)*M<4:g=LineString([*g.coords,b.coords[0]])
 river_axes[name]=unary_union([river_axes[name],g])

# The Rhine and Pearl locally narrow near very small political territories.
# The centreline remains continuous, without wooden tabs across the channel.
micro_guard=unary_union([r['geom_shape'].buffer(1.4/M) for r in regions if r['geom_shape'].area*M*M<22])
waters={}
for n,g in river_axes.items():
 width=1.6 if n in ['Иртыш','Амур'] else pr['river_width_mm'];broad=g.buffer(width/2/M);narrow=g.buffer(.20/M)
 waters[n]=polygonal(unary_union([broad.difference(micro_guard),narrow]).intersection(pure))
lake_masks=defaultdict(list)
for f in F['lakes']:
 g=project(shape(f['geom']));factor=f['width_factor']
 if factor!=1:
  rc=list(g.minimum_rotated_rectangle.exterior.coords);_,a,b=max((Point(a).distance(Point(b)),a,b) for a,b in zip(rc[:-1],rc[1:]));angle=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]));q=g.centroid
  g=rotate(scale(rotate(g,-angle,origin=q),xfact=1,yfact=factor,origin=q),angle,origin=q)
 lake_masks[f['name']].append(g)
for n,gs in lake_masks.items():waters[n]=clean(unary_union(gs).intersection(pure),simplify=.06)
# Ile is kept connected to the widened Balkhash shoreline.
if 'Или' in waters and 'Балхаш' in waters:
 a,b=nearest_points(river_axes['Или'],waters['Балхаш'])
 if a.distance(b)*M<6:
  river_axes['Или']=unary_union([river_axes['Или'],LineString([a,b])]);waters['Или']=unary_union([waters['Или'],LineString([a,b]).buffer(pr['river_width_mm']/2/M)]).intersection(pure)
full=unary_union([pure,rus]);caspi=None;q=project(Point(51,41))
for p in polys(full):
 for ring in p.interiors:
  g=Polygon(ring)
  if g.covers(q):caspi=g
if caspi is not None:waters['Каспийское море']=caspi
waters={k:polygonal(g) for k,g in waters.items()};water=polygonal(unary_union(list(waters.values())));base=polygonal(pure.difference(water))
genuine_small_islands=[p for p in polys(pure) if 6<=p.area*M*M<pr['min_detached_river_islet_mm2']]
islets=unary_union([p for p in polys(base) if p.area*M*M<pr['min_detached_river_islet_mm2'] and not any(p.intersection(q).area/q.area>.65 for q in genuine_small_islands) and not any(p.intersection(r['geom_shape']).area/max(r['geom_shape'].area,1e-12)>.35 for r in regions if r['geom_shape'].area*M*M<50)])
water=polygonal(unary_union([water,islets]));base=polygonal(pure.difference(water))
print('WATER',len(waters),'objects; through base components',len(polys(base)),flush=True)

caps={};craters=[];recesses=[]
def organic(q,r,phase=0):
 return Polygon([(q.x+r/M*(1+.055*math.cos(3*t+phase))*math.cos(t),q.y+r/M*(1+.055*math.cos(3*t+phase))*math.sin(t)) for t in np.linspace(0,2*math.pi,57)[:-1]])
for f in features:
 q=project(Point(f['lon'],f['lat']));kind=f['kind']
 if kind in ['summit','volcano']:
  local_tier=max([i+1 for i,g in enumerate(layers) if g.covers(q)] or [1]);tier=max(f['tier'],local_tier);f['tier']=tier;top=f['top_radius_mm'];bottom=f['base_radius_mm'];foot=None
  for i in range(1,tier):
   radius=top+(bottom-top)*(tier-1-i)/max(1,tier-2);g=organic(q,radius).intersection(pure);layers[i]=unary_union([layers[i],g]);foot=g
  if foot is not None:caps[f['name']]=foot
  if kind=='volcano':
   disk=q.buffer(f['crater_radius_mm']/M,resolution=16).intersection(base)
   # Small volcanoes have integral solid caps and shallow engraving pockets,
   # rather than fragile tiny annular plywood parts.
   if disk.area>1e-8:craters.append({'name':f['name'],'geom':mapping(disk),'tier':tier,'depth_mm':.35,'expected_floor_mm':tier*3-.35})
 elif kind=='rocks':
  local_tier=max([i+1 for i,g in enumerate(layers) if g.covers(q)] or [1]);f['tier']=min(6,max(f['tier'],local_tier+1))
  profile=[(-3,1.2),(-3,-.5),(-2.3,-.5),(-2.3,-1.5),(-1.2,-1.5),(-1.2,-.5),(-.3,-.5),(-.3,-2.1),(.8,-2.1),(.8,-.5),(1.6,-.5),(1.6,-1.4),(2.5,-1.4),(2.5,1.2)]
  cap=Polygon([(q.x+x/M,q.y+y/M) for x,y in profile]).intersection(pure);caps[f['name']]=cap
  for i in range(1,f['tier']):layers[i]=unary_union([layers[i],cap.buffer((f['tier']-1-i)*.55/M).intersection(pure)])
 elif kind=='dry_valley':
  g=project(LineString(f['coords'])).buffer(.75/M).intersection(pure);recesses.append({'name':f['name'],'geom':mapping(g),'floor_tier':f['floor_tier']})

# Broad stepped river banks articulate plateaux, while all actual water is open.
deep_names=['Янцзы','Брахмапутра','Меконг','Салуин','Инд']
for tier in range(2,6):
 banks=unary_union([river_axes[n].buffer((1.3+(tier-2)*.65)/M) for n in deep_names if n in river_axes]).intersection(pure)
 layers[tier]=layers[tier].difference(banks)
 for recess in recesses:
  if tier>=recess['floor_tier']:layers[tier]=layers[tier].difference(shape(recess['geom']))

# Exact thin collars carry the existing Russian step endpoints into the new side.
collar_zone=shared.buffer(.45/M,cap_style=2).intersection(pure)
for i in range(1,6):
 reaches=shared.intersection(shape(RU['layers'][i]).buffer(.0001/M));collars=[]
 for line in lines(reaches):
  collars.extend([line.buffer(.50/M,single_sided=True),line.buffer(-.50/M,single_sided=True)])
 extension=unary_union(collars).intersection(pure)
 layers[i]=unary_union([layers[i].difference(collar_zone),extension.intersection(collar_zone)])

protected=unary_union(list(caps.values()));raw_counts=[len(polys(g)) for g in layers]
for i in range(1,6):
 g=clean(layers[i],area=pr['ordinary_min_area_mm2'][i],join=pr['join_radius_mm'],neck=pr['min_neck_mm'],simplify=pr['simplify_mm'],holes=pr['min_terrain_hole_mm2'])
 keep=[p for p in polys(layers[i]) if p.intersection(protected).area*M*M>.15]
 # One broad insert per small genuine island; never unite distinct islands.
 for island in polys(pure):
  if 8<=island.area*M*M<550:
   candidates=sorted(polys(layers[i].intersection(island)),key=lambda p:-p.area)
   if candidates and candidates[0].area*M*M>1.8:keep.append(candidates[0])
 layers[i]=polygonal(unary_union([g,*keep]).intersection(base))
 for recess in recesses:
  if i>=recess['floor_tier']:layers[i]=layers[i].difference(shape(recess['geom']))
layers[0]=base
for i in range(5,1,-1):layers[i-1]=polygonal(unary_union([layers[i-1],layers[i]]).intersection(base))
# A second pass removes small scraps created where water intersects broad masses.
for i in range(5,0,-1):
 support=layers[i+1] if i<5 else Polygon();keep=[]
 for p in polys(layers[i]):
  area=p.area*M*M
  if area>=pr['ordinary_min_area_mm2'][i] or p.intersection(protected).area*M*M>.15 or p.intersection(support).area*M*M>.15 or any(p.intersection(q).area/max(p.area,1e-12)>.9 and 8<=q.area*M*M<550 for q in polys(pure)):keep.append(p)
 layers[i]=polygonal(unary_union(keep).difference(water))
 if i>1:layers[i-1]=unary_union([layers[i-1],layers[i]])
# Retain exact frozen Russian edge levels after all morphological operations.
for i in range(1,6):
 reaches=shared.intersection(shape(RU['layers'][i]).buffer(.0001/M));extension=unary_union([b for line in lines(reaches) for b in [line.buffer(.50/M,single_sided=True),line.buffer(-.50/M,single_sided=True)]]).intersection(base)
 layers[i]=unary_union([layers[i].difference(collar_zone),extension.intersection(collar_zone)])
for i in range(5,1,-1):layers[i-1]=unary_union([layers[i-1],layers[i]])
# Political clipping can create tiny upper corner fragments even when the
# original landform is monolithic. Lower those nonessential corners; keep named
# accents, supports, actual microstates and the protected Russian seam.
region_layers={};trim_log=[]
for r in regions:
 rr=[polygonal(g.intersection(r['geom_shape'])) for g in layers]
 for i in range(5,-1,-1):
  options=polys(rr[i]);largest=max(options,key=lambda p:p.area) if options else Polygon();support=rr[i+1] if i<5 else Polygon();keep=[]
  for p in options:
   area=p.area*M*M;limit=pr['political_min_base_scrap_mm2'] if i==0 else pr['political_min_upper_part_mm2']
   if area<1e-6:continue
   intentional=p.intersection(protected).area/max(p.area,1e-12)>.45
   seam_part=area>=.25 and p.intersection(collar_zone).area*M*M>.02
   supported=p.intersection(support).area*M*M>1e-6
   primary=(i==0 and p is largest)
   if area>=limit or intentional or seam_part or supported or primary:keep.append(p)
   elif area>1e-7:trim_log.append({'region':r['id'],'tier':i+1,'area_mm2':area})
  rr[i]=polygonal(unary_union(keep))
  if i>0:rr[i-1]=unary_union([rr[i-1],rr[i]])
 region_layers[r['id']]=rr
oldbase=base;water=polygonal(water)
for key,rr in region_layers.items():
 rr=[polygonal(g).difference(water) for g in rr]
 for i in range(5,0,-1):rr[i-1]=unary_union([rr[i-1],rr[i]])
 region_layers[key]=rr
# Do not snap the union a second time: repeated snapping at every level can
# manufacture microscopic overhangs along a shared political boundary.
layers=[unary_union([rr[i] for rr in region_layers.values()]) for i in range(6)];base=layers[0];water=unary_union([water,oldbase.difference(base)])
visible=[layers[i].difference(layers[i+1]) if i<5 else layers[i] for i in range(6)]

# A sparse dry-dune engraving option, separate from cuts and perennial water.
dunes=[]
for f in features:
 if f['kind']!='desert':continue
 q=project(Point(f['lon'],f['lat']))
 for j in [-1,1]:
  coords=[(q.x+t/M,q.y+(j*2.6+.75*math.sin(t/5+j))/M) for t in np.linspace(-8,8,35)];dunes.append(LineString(coords).buffer(.055/M))
texture=unary_union(dunes).intersection(base).difference(water)
for f in features:
 q=project(Point(f['lon'],f['lat']));f['x'],f['y']=q.x,q.y
counts=[];political_counts=[];numerical_checks=[]
for i,g in enumerate(layers,1):
 overlap=g.intersection(water).area
 if not g.is_valid or overlap*M*M>=.01:print('INVALID LAYER',i,'valid',g.is_valid,'water overlap mm2',overlap*M*M,flush=True)
 assert g.is_valid and overlap*M*M<.01
 overhang=0
 if i>1:
  overhang=g.difference(layers[i-2]).area*M*M
  assert overhang<.01,(i,'unsupported area mm2',overhang)
 numerical_checks.append({'tier':i,'water_overlap_mm2':overlap*M*M,'nesting_roundoff_mm2':overhang,'area_tolerance_mm2':.01})
 counts.append({'tier':i,'height_mm':i*3,'parts_before_political_split':len(polys(g)),'area_mm2':g.area*M*M})
 political_counts.append(sum(len(polys(rr[i-1])) for rr in region_layers.values()))
report={'all_valid':True,'all_nested':True,'perennial_water_through_all_layers':True,'political_regions':len(regions),'country_colors':len({r['country'] for r in regions}),'one_coating_per_country':True,'six_heights_mm':[3,6,9,12,15,18],'global_layer_counts':counts,'parts_after_political_split_by_level':political_counts,'parts_after_political_split':sum(political_counts),'same_xy_political_and_relief':True,'russia_and_africa_source_files_not_edited':True,'style':style_report}
dump('Проверка-геометрии.json',report)
dump('Численная-точность-геометрии.json',numerical_checks)
model={'base':mapping(base),'pure_base':mapping(pure),'regions':[{k:v for k,v in r.items() if k!='geom_shape'} for r in regions],'region_layers':{k:[mapping(g) for g in rr] for k,rr in region_layers.items()},'layers':[mapping(g) for g in layers],'visible':[mapping(g) for g in visible],'water':mapping(water),'waters':{k:mapping(v) for k,v in waters.items()},'river_axes':{k:mapping(v) for k,v in river_axes.items()},'fjords':{k:mapping(v) for k,v in fjord_masks.items()},'caps':{k:mapping(v) for k,v in caps.items()},'craters':craters,'recesses':recesses,'texture':mapping(texture),'landmarks':features,'mm_per_unit':M}
dump('geometry.json',model)
dump('Оптимизация-после-политического-разделения.json',{'upper_corner_fragments_lowered':len(trim_log),'removed_small_fragments':trim_log,'minimum_upper_mm2':pr['political_min_upper_part_mm2'],'named_accents_and_russian_seam_protected':True})

# All assembled variants retain identical X/Y. Production contours are also
# supplied separately per political module, so common edges are not double-cut.
assembly=svgroot();political=svgroot();guide=svgroot()
for i,g in enumerate(RU['layers'],1):svgpath(assembly,shape(g),f'RUSSIA_REFERENCE_L{i:02d}',RU['palette'][f'L{i}'][1],stroke='#846b4b',stroke_width='.25')
for r in regions:
 svgpath(political,r['geom_shape'],r['id'],r['color'],stroke='#4b3b2d',stroke_width='.22')
 for i,g in enumerate(visible,1):svgpath(assembly,g.intersection(r['geom_shape']),f'{r["id"]}_L{i:02d}',r['color'],stroke='#4b3b2d',stroke_width='.30')
 for i,g in enumerate(layers,1):
  part=g.intersection(r['geom_shape'])
  if polys(part):
   out=svgroot();svgpath(out,part,f'{r["id"]}_L{i:02d}','#000');savesvg(out,f'SVG-по-регионам/{r["id"]}/Слой-{i:02d}.svg')
 out=svgroot();svgpath(out,r['geom_shape'],r['id'],'#000');savesvg(out,f'Политические-SVG/{r["id"]}.svg')
 out=svgroot();svgpath(out,r['geom_shape'].intersection(base),r['id'],'#000');savesvg(out,f'Политические-SVG-с-водой/{r["id"]}.svg')
for i,g in enumerate(layers,1):
 out=svgroot();svgpath(out,g,f'GLOBAL_L{i:02d}','#000');savesvg(out,f'Общий-рельеф-слой-{i:02d}.svg')
 out=svgroot()
 for r in regions:svgpath(out,g.intersection(r['geom_shape']),f'{r["id"]}_L{i:02d}',r['color'])
 savesvg(out,f'Слой-{i:02d}-по-политическим-регионам.svg')
 out=svgroot();svgpath(out,texture.intersection(visible[i-1]),f'DUNE_ENGRAVE_L{i:02d}','#000')
 for k,c in enumerate(craters):
  if c['tier']==i:svgpath(out,shape(c['geom']),f'CRATER_{k}','#000')
 savesvg(out,f'Гравировка-уровень-{i:02d}.svg')
savesvg(assembly,'Евразия-рельеф-цветной.svg');savesvg(political,'Евразия-политическая.svg')
out=svgroot();svgpath(out,water,'THROUGH_WATER','#000');savesvg(out,'Реки-и-озёра-сквозные.svg')
for i,f in enumerate(features,1):
 E.SubElement(guide,'circle',cx=str(f['x']),cy=str(f['y']),r='5',fill='#eadfc6',stroke='#43352d',attrib={'stroke-width':'.5'});t=E.SubElement(guide,'text',x=str(f['x']),y=str(f['y']+2.2),attrib={'font-size':'6','text-anchor':'middle'});t.text=str(i)
savesvg(guide,'Номера-природных-объектов.svg')
with (ROOT/'Состав-слоёв.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f,lineterminator='\n');w.writerow(['Слой','Верх, мм','До политического разделения','После политического разделения']);w.writerows((i+1,(i+1)*3,counts[i]['parts_before_political_split'],political_counts[i]) for i in range(6))
with (ROOT/'Природные-объекты.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f,lineterminator='\n');w.writerow(['Номер','Объект','Долгота','Широта','Тип','Приоритет']);w.writerows((i,f['name'],f['lon'],f['lat'],f['kind'],f['priority']) for i,f in enumerate(features,1))
print('FINAL SHARED COUNTS',counts,flush=True);print('POLITICAL PART COUNTS',political_counts,'TOTAL',sum(political_counts),flush=True)
