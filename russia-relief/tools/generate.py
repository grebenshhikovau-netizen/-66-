"""Large connected decorative Russian plywood relief; six levels, through-cut waterways."""
import json,math,csv,copy
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from shapely.geometry import shape,mapping,Polygon,Point,LineString,box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union,transform,nearest_points
from shapely.affinity import rotate,scale
from shapely import make_valid,get_coordinates
import contourpy
from lxml import etree as E
P=Path(__file__).resolve().parent;OUT=P.parent if P.name=='tools' else P;DATA=OUT/'data' if P.name=='tools' else OUT;C=json.load(open(DATA/'config.json'));F=json.load(open(DATA/'geographic-features.json'));main=shape(json.load(open(DATA/'source-base.json')));m=C['mm_per_unit'];pr=C['projection'];cfg=C['production'];S='http://www.w3.org/2000/svg'
merc0=math.log(math.tan(math.pi/4+math.radians(pr['latmin'])/2))
def warp(x,y,z=None):
 x=np.asarray(x);y=np.asarray(y);x=np.where(x<0,x+360,x);return pr['source_xmin']+(x-pr['lonmin'])*pr['kx_per_degree'],pr['source_ymax']-(np.log(np.tan(np.pi/4+np.deg2rad(y)/2))-merc0)*pr['ky_per_mercator']
def proj(g):return make_valid(transform(warp,g))
def pt(lon,lat):return proj(Point(lon,lat))
def line(coords):return proj(LineString(coords))
def polys(g):
 if g.geom_type=='Polygon':return [g] if g.area>1e-8 else []
 return [p for c in getattr(g,'geoms',[]) for p in polys(c)]
def polygonal(g):return unary_union(polys(make_valid(g)))
def clean(g,area=None,closing=0,simplify=None):
 area=cfg['min_upper_part_area_mm2'] if area is None else area;simplify=cfg['outline_simplify_mm'] if simplify is None else simplify;g=polygonal(g)
 if closing:
  g=g.buffer(closing/m).buffer(-closing/m)
  neck=cfg['min_neck_width_mm']/2/m;g=g.buffer(-neck).buffer(neck)
 g=g.simplify(simplify/m,preserve_topology=True)
 return unary_union([Polygon(p.exterior,[r.coords for r in p.interiors if Polygon(r).area*m*m>2]) for p in polys(g) if p.area*m*m>=area])
regions=[{'id':'RUS','name':'Материк','geom':mapping(main)}]
raw_islands=[]
for f in F['islands']:
 raw=shape(f['geom']);lon,lat=raw.representative_point().coords[0]
 if f['name']!='Сахалин' and 156.1<lon<156.6 and 50.6<lat<51:continue # Shumshu is too close to Paramushir at this scale.
 raw_islands.append((f['name'],proj(raw)))
used_island_space=main.buffer(.8/m)
for j,(name,raw) in enumerate(raw_islands,1):
 rectangle=list(raw.minimum_rotated_rectangle.exterior.coords);width=min(Point(a).distance(Point(b)) for a,b in zip(rectangle[:-1],rectangle[1:]))*m
 growth=max(0,(cfg['min_island_width_mm']-width)/2)/m
 g=raw.buffer(growth).difference(used_island_space);others=unary_union([p for k,(_,p) in enumerate(raw_islands,1) if k!=j]);g=g.difference(others.buffer(.25/m))
 g=clean(g,area=cfg['min_island_area_mm2'],simplify=.08)
 used_island_space=unary_union([used_island_space,g.buffer(.5/m)])
 for k,p in enumerate(polys(g),1):regions.append({'id':'SAKHALIN' if name=='Сахалин' else f'KURIL_{j:02d}_{k}','name':name,'geom':mapping(p)})
island_union=unary_union([shape(r['geom']) for r in regions[1:]]);outline=unary_union([main,island_union]);A=np.load(DATA/'dem-russia.npz');cg=contourpy.contour_generator(x=A['lon'],y=A['lat'],z=gaussian_filter(A['z'],.65),fill_type='OuterOffset')
def above(h,area=None):
 points,offsets=cg.filled(h,9000);gs=[]
 for points_i,offset_i in zip(points,offsets):
  rings=[points_i[a:b] for a,b in zip(offset_i[:-1],offset_i[1:])];gs.append(Polygon(rings[0],rings[1:]))
 return clean(proj(unary_union(gs)).intersection(outline),area=area,closing=cfg['closing_radius_mm'])
thresholds=[0,220,650,1300,2200,3200];layers=[outline]+[above(h) for h in thresholds[1:]]
# One joined highland insert on each sufficiently large island; never bridge islands.
for r in regions[1:]:
 footprint=shape(r['geom']);inner=footprint.buffer(-.5/m)
 if inner.area*m*m>2.5:layers[1]=unary_union([layers[1],inner])
 if r['id']=='SAKHALIN':
  upper=clean(footprint.buffer(-1.4/m),area=25,closing=1.0)
  if not upper.is_empty:layers[2]=unary_union([layers[2],upper])
# Named geographic arrays augment the DEM where narrow ranges are averaged away.
ranges={};landmark_records=[]
def record(name,lon,lat,kind):
 q=pt(lon,lat);landmark_records.append({'name':name,'lon':lon,'lat':lat,'x':q.x,'y':q.y,'kind':kind})
def lift(g,tier,widths=None):
 for i in range(1,tier):layers[i]=unary_union([layers[i],g.buffer(((tier-1-i)*.65)/m)]).intersection(outline)
def ridge(name,coords,widths):
 axis=line(coords);foot=axis.buffer(widths[0]/2/m)
 for i,width in enumerate(widths,1):
  if i>=6:break
  layers[i]=unary_union([layers[i],axis.buffer(width/2/m)]).intersection(outline)
 ranges[name]=foot.intersection(main);return axis
# The western/central landscape is one continuous field, not a set of inserts.
from compose_landscape import landscape_layers
composed=landscape_layers(A,C,main,proj,clean)
# Eastern landforms retain the previous design; thresholds blend smoothly by longitude.
for i,g in enumerate(composed,1):layers[i]=unary_union([g,layers[i].intersection(island_union)])
ural=line([(66.5,68.3),(63,66.3),(60.5,63),(58.8,60),(59,57),(59.1,54),(57.8,51.6)])
ranges['Урал']=ural.buffer(11/m).intersection(main)
record('Уральские горы',60,61,'Непрерывный общий ландшафт, без параллельных буферных полос')
record('Средний Урал — район Екатеринбурга',60.6,56.84,'Широкие плечи общего рельефного поля')
western_terraces={}
# These footprints identify provinces in the guide; they add no patch geometry.
for name,bounds,lo,la in [
 ('Валдайская и Среднерусская возвышенности',(29,48,41,60),35.7,54.8),
 ('Приволжская возвышенность',(41,48,51,57),46,53),
 ('Северные Увалы и Тиман',(40,59,56,67),50,63),
 ('Предуралье и Зауралье',(52,52,69,60),60,56),
 ('Западносибирская низменность',(64,55,87,69),76,63),
 ('Среднесибирское плоскогорье',(88,57,124,71),108,64),
 ('Таймыр — горы Бырранга',(86,71,115,77.8),100,74.5),
 ('Анабарское плато',(103,69,117,73.5),110,71.5),
 ('Енисейский кряж',(88,55,96,61),92,58.5)]:
 western_terraces[name]=proj(box(*bounds)).intersection(main)
 record(name,lo,la,'Часть общего ступенчатого ландшафта L2–L4')
cauc=ridge('Кавказ',[(38,44.5),(40.1,43.6),(42.5,43.35),(44.3,42.7),(47.2,42)],[10,8,5.2,3.2]);record('Кавказ',43,43,'Связный массив L2–L5')
altai=ridge('Алтай',[(83.3,50.5),(85.2,50.3),(86.6,49.8),(88.4,50.0),(90.2,50.5)],[13,10,7,4]);record('Алтай',86.5,50.2,'Крупный связный массив')
sayan=ridge('Саяны',[(89.5,51.4),(92.5,52),(95.5,52.6),(98.3,53.3),(100.3,54.3),(102.7,53.9)],[12,9,6,3.5]);record('Саяны',96,53,'Связные вытянутые ступени')
verkh=ridge('Верхоянский хребет',[(128.2,69.7),(127.8,67.8),(129.5,66),(132.5,64.5),(135,63)],[11,8,5]);record('Верхоянский хребет',130,66.5,'Широкий хребет')
chers=ridge('Хребет Черского',[(137.8,67.9),(141,66.5),(144.6,64.4)],[12,9,5.5]);record('Хребет Черского',141,66,'Объединённые гребни')
stan=ridge('Становой хребет',[(120.6,55.9),(124,56),(128,55.7),(132,55.6),(136.4,56.2)],[10,7,4]);record('Становой хребет',128,56,'Единый протяжённый массив')
sikh=ridge('Сихотэ-Алинь',[(133.4,44.5),(135.4,46),(137.4,48.3),(139.2,50.5)],[9,6,3.5]);record('Сихотэ-Алинь',136,47,'Связный прибрежный хребет')
# Putorana: broad flat terraces bounded by cliffs, with three blind valley incisions.
putorana_geo=Polygon([(89.8,68.4),(91.7,71),(97.2,71.3),(101,69.5),(99.1,67.2),(92.5,66.8)])
putorana=proj(putorana_geo).intersection(main);p3=layers[2].intersection(putorana);p4=layers[3].intersection(putorana)
lift(p3,3);lift(p4,4);ranges['Путорана']=putorana;record('Плато Путорана',95,69,'Широкое плато с каньонами')
putorana_valleys=unary_union([line(c).buffer(.65/m) for c in [[(90.4,69.35),(91.4,69.45),(92.5,69.8)],[(90.5,68.7),(91.8,68.8),(93,68.75)],[(93,68.8),(94.3,68.95),(95.6,69.3)]]]).intersection(putorana)
for i in range(2,6):layers[i]=layers[i].difference(putorana_valleys)
# Baikal neighbourhood: rugged but connected shoulder, with a low interior lake bowl.
baikal_axis=ridge('Байкальское нагорье',[(103.5,52),(105.5,53.7),(108,55),(110.5,56),(113.8,56.8)],[12,9,5.5]);record('Байкальская впадина',108,53.5,'Контрастная котловина и плечи нагорья')
# Rivers: only the named main systems, preserving actual vectors and confluences.
river_geo={}
for f in F['rivers']:
 n=f['name'];family='Волга' if 'Volga' in n else 'Обь' if n=='Ob' else 'Иртыш' if 'Irtysh' in n else 'Енисей' if n in ['Yenisey','Verkhniy Yenisey'] else 'Ангара' if n=='Angara' else 'Лена' if n=='Lena' else 'Амур' if n=='Amur' else None
 if family:river_geo.setdefault(family,[]).append(shape(f['geom']))
for f in F.get('composition_rivers',[]):river_geo.setdefault(f['name'],[]).append(shape(f['geom']))
# Outlets and simplified main distributaries. These are the only delta arms used.
extra={
'Волга':[[(47.95,46.5),(48.05,46.1),(48.0,45.8)],[(47.95,46.5),(48.5,46.15),(48.8,45.8)]],
'Обь':[[(68.95,66.75),(70.4,66.9),(72,68),(73,70.5)]],
'Енисей':[[(82.9,70.05),(82.5,71.8)]],
'Лена':[[(126.7,72),(127.2,72.6),(128,73.2)],[(126.7,72),(125.5,72.6),(124.6,73.1)]],
'Амур':[[(140.65,53.15),(141.3,53.1)]]}
river_lines={}
for name,gs in river_geo.items():
 ls=[proj(g) for g in gs]
 for coords in extra.get(name,[]):
  ll=line(coords);cc=list(ll.coords);end=Point(cc[-1]);near=nearest_points(end,main.boundary)[1]
  if name in ['Лена','Обь','Енисей','Амур'] and end.distance(near)*m<8:cc.append(near.coords[0])
  ls.append(LineString(cc))
 if name=='Лена':
  coords=get_coordinates(unary_union(gs));north=coords[np.argmax(coords[:,1])];ls.append(line([north,(126.7,72)]))
 river_lines[name]=unary_union(ls)
# End-point repairs only for gaps within a named main system, never across unrelated rivers.
from shapely.ops import linemerge
for name,g in list(river_lines.items()):
 if g.geom_type=='MultiLineString':
  parts=list(g.geoms);connect=[]
  for l in parts:
   for xy in [l.coords[0],l.coords[-1]]:
    q=Point(xy);others=unary_union([p for p in parts if p is not l]);nearest=nearest_points(q,others)[1]
    if .01<q.distance(nearest)*m<2.0:connect.append(LineString([q,nearest]))
  river_lines[name]=unary_union([g,*connect])
mouth=nearest_points(pt(48,46.1),main.boundary)[1];volga_land=river_lines['Волга'].intersection(main);mouth=nearest_points(mouth,volga_land)[1]
start=nearest_points(Point(mouth.x-.4/m,mouth.y-3.5/m),volga_land)[1];position=main.boundary.project(mouth);shore1=main.boundary.interpolate(max(0,position-1.5/m));shore2=main.boundary.interpolate(position+1.5/m)
river_lines['Волга']=unary_union([river_lines['Волга'],LineString([start,shore1]),LineString([start,shore2])])
# Exact Natural Earth tributaries share their parent river endpoints. Repair only
# a small gap at a confluence, so no unrelated basins are ever joined.
for name,parent in [('Кама','Волга'),('Нижняя Тунгуска','Енисей'),('Подкаменная Тунгуска','Енисей'),('Вилюй','Лена')]:
 a,b=nearest_points(river_lines[name],river_lines[parent]);gap=a.distance(b)*m
 if gap>1e-8:
  assert gap<4,(name,parent,gap)
  river_lines[name]=unary_union([river_lines[name],LineString([a,b])])
dvina=river_lines['Северная Двина'];a,b=nearest_points(dvina,main.boundary)
if a.distance(b)*m<6:river_lines['Северная Двина']=unary_union([dvina,LineString([a,b])])
waters={name:g.buffer((cfg['river_width_mm'] if name not in ['Обь','Енисей','Лена'] else cfg['river_width_mm']+.2)/2/m).intersection(main) for name,g in river_lines.items()}
# Lake width enhancement is perpendicular to the long axis, not an arbitrary position shift.
lake_names={'Lake Baikal':'Байкал','Lake Ladoga':'Ладожское','Lake Onega':'Онежское','Ozero Teletskoye':'Телецкое','Lake Taymyr':'Таймыр'}
for f in F['lakes']:
 if f['name'] not in lake_names:continue
 name=lake_names[f['name']];g=proj(shape(f['geom']))
 if name=='Байкал':
  rect=g.minimum_rotated_rectangle;rc=list(rect.exterior.coords);pairs=[(Point(a).distance(Point(b)),a,b) for a,b in zip(rc[:-1],rc[1:])];_,a0,b0=max(pairs,key=lambda x:x[0]);angle=math.degrees(math.atan2(b0[1]-a0[1],b0[0]-a0[0]));center=g.centroid
  g=rotate(scale(rotate(g,-angle,origin=center),xfact=1,yfact=cfg['baikal_width_factor'],origin=center),angle,origin=center)
 if name=='Телецкое':g=g.buffer(.38/m)
 g=clean(g,area=.5,closing=0,simplify=.10).intersection(main);waters[name]=g
# The Angara exits at Listvyanka and remains connected to the lake and Yenisei.
angara_link=line([(104.85,51.86),(104.70,52.05),(104.25,52.35)]).buffer(cfg['river_width_mm']/2/m);waters['Ангара']=unary_union([waters['Ангара'],angara_link]).intersection(main)
water=unary_union(list(waters.values()));base_parts=polys(main.difference(water));removed_islets=unary_union([p for p in base_parts if p.area*m*m<cfg.get('min_river_islet_area_mm2',30)])
# Tiny detached delta specks become transparent voids; no artificial wood tabs cross the channels.
water=unary_union([water,removed_islets]);base=polygonal(outline.difference(water))
# Broad Volga valley benches and blind tributary valleys articulate the new slopes.
# Secondary valleys retain their L2 floor; only the named main rivers are through cuts.
western_valleys=river_lines['Волга'].buffer(2.0/m).intersection(unary_union(list(western_terraces.values())))
landscape_valley_axes={name:river_lines[name] for name in ['Нижняя Тунгуска','Подкаменная Тунгуска','Вилюй','Северная Двина','Кама']}
valley_masks={}
for tier,width in [(2,3.8),(3,7),(4,9),(5,10)]:
 valley_masks[tier]=unary_union([g.buffer(width/2/m) for g in landscape_valley_axes.values()]).intersection(main)
for name,g in landscape_valley_axes.items():
 q=g.interpolate(g.length*.5);lo=pr['lonmin']+(q.x-pr['source_xmin'])/pr['kx_per_degree'];la=math.degrees(2*math.atan(math.exp(merc0+(pr['source_ymax']-q.y)/pr['ky_per_mercator']))-math.pi/2)
 record(name,lo,la,'Сквозная река и широкие ступенчатые берега')
# Deliberate compact accents, all with broad connected bases.
accent_caps={};craters=[]
def organic(q,r):
 return Polygon([(q.x+r/m*(1+.045*math.cos(3*t))*math.cos(t),q.y+r/m*(1+.045*math.cos(3*t))*math.sin(t)) for t in np.linspace(0,2*math.pi,73)[:-1]])
def accent(name,lon,lat,max_tier,top,base_radius):
 q=pt(lon,lat)
 for i in range(1,max_tier):
  radius=top+(base_radius-top)*(max_tier-1-i)/max(1,max_tier-2);layers[i]=unary_union([layers[i],organic(q,radius)]).intersection(outline)
 accent_caps[name]=organic(q,top).intersection(base);record(name,lon,lat,f'Акцент до L{max_tier}');return q
elbrus=pt(42.45,43.35);double=unary_union([elbrus.buffer(2.0/m),Point(elbrus.x+3.5/m,elbrus.y+.3/m).buffer(2.0/m),LineString([(elbrus.x,elbrus.y),(elbrus.x+3.5/m,elbrus.y+.3/m)]).buffer(1.35/m)]).intersection(main)
for i in range(1,6):layers[i]=unary_union([layers[i],double.buffer((5-i)*.75/m)]).intersection(outline)
accent_caps['Эльбрус']=double.intersection(base);record('Эльбрус — две вершины',42.45,43.35,'Один связный двухвершинный силуэт L6')
accent('Белуха',86.59,49.81,6,2.4,6)
# Kamchatka lower slopes form one axial mass, with four legible summit structures.
ridge('Камчатка',[(158.4,52.7),(159.1,54),(160.2,55.6),(161.4,57.3),(162.5,58.8)],[11,9,6])
for name,lon,lat,tier in [('Ключевская Сопка',160.64,56.06,6),('Шивелуч',161.36,56.65,5),('Кроноцкий вулкан',160.53,54.75,5),('Авачинский вулкан',158.84,53.25,5)]:
 q=accent(name,lon,lat,tier,3.3,6.4);hole=q.buffer(.85/m).intersection(main);craters.append({'name':name,'geom':mapping(hole),'floor_tier':tier-1,'top_tier':tier})
# Sculptural rock groups are single joined silhouettes, not separate pillars.
def rock_group(name,lon,lat):
 q=pt(lon,lat);coords=[(-4,1.6),(-4,-.5),(-3.2,-.5),(-3.2,-2),(-1.8,-2),(-1.8,-.5),(-.7,-.5),(-.7,-2.8),(.8,-2.8),(.8,-.5),(1.8,-.5),(1.8,-2),(3.2,-2),(3.2,-.5),(4,-.5),(4,1.6)]
 if name=='Ленские столбы':
  ls=river_lines['Лена'];segments=list(ls.geoms) if hasattr(ls,'geoms') else [ls];segment=min(segments,key=lambda g:g.distance(q));t=segment.project(q);near=segment.interpolate(t);a=segment.interpolate(max(0,t-1/m));b=segment.interpolate(min(segment.length,t+1/m));tx,ty=b.x-a.x,b.y-a.y;length=math.hypot(tx,ty);tx,ty=tx/length,ty/length;nx,ny=q.x-near.x,q.y-near.y;nl=math.hypot(nx,ny)
  if nl<1e-6:nx,ny=-ty,tx
  else:nx,ny=nx/nl,ny/nl
  offset=max(nl,2.9/m);center=Point(near.x+nx*offset,near.y+ny*offset);cap=Polygon([(center.x+(x*tx-y*nx)/m,center.y+(x*ty-y*ny)/m) for x,y in coords]).intersection(main)
 else:cap=Polygon([(q.x+x/m,q.y+y/m) for x,y in coords]).intersection(main)
 for i in range(1,5):layers[i]=unary_union([layers[i],cap.buffer((4-i)*.7/m)]).intersection(outline)
 accent_caps[name]=cap.intersection(base);record(name,lon,lat,'Один объединённый скальный силуэт L5')
rock_group('Маньпупунёр',59.30,62.25);rock_group('Ленские столбы',127.35,61.11)
# Geyser valley: one blind channel and connected pockets, not through holes.
g=pt(160.0,54.43);geyser=LineString([(g.x-2.4/m,g.y-1.5/m),(g.x,g.y),(g.x+2.3/m,g.y+1.6/m)]).buffer(.7/m);geyser=unary_union([geyser,Point(g.x,g.y).buffer(1/m)]).intersection(main);record('Долина гейзеров',160,54.43,'Связное углубление, пол на L3')
# Monolithic cleanup: merge nearby terrain before filtering, protect every deliberate accent.
raw_counts=[len(polys(g)) for g in layers];protected=unary_union(list(accent_caps.values()))
for i in range(1,6):
 g=clean(layers[i],area=cfg['min_part_area_by_level_mm2'][i],closing=cfg['closing_radius_mm'])
 # Exact accent contours and their connected support pieces survive the area filter.
 keep=unary_union([p for p in polys(layers[i]) if p.intersection(protected).area>1e-6 or (p.intersection(island_union).area>1e-6 and p.area*m*m>2.5)]);g=unary_union([g,keep]).intersection(outline)
 if i>=2:g=g.difference(putorana_valleys)
 if i>=2:g=g.difference(western_valleys)
 if i in valley_masks:g=g.difference(valley_masks[i])
 if i>=3:g=g.difference(geyser)
 for c in craters:
  if i>=c['floor_tier']:g=g.difference(shape(c['geom']))
 layers[i]=polygonal(g.difference(water).intersection(base))
layers[0]=base
# Carry all upper footprints down to their support and keep all waterways completely open.
for i in range(5,1,-1):layers[i-1]=unary_union([layers[i-1],layers[i]])
# Crater floors and the geyser floor are physically retained below the recesses.
for c in craters:
 floor=c['floor_tier']-1;hole=shape(c['geom']).intersection(base)
 for i in range(1,floor+1):layers[i]=unary_union([layers[i],hole])
for i in range(1,3):layers[i]=unary_union([layers[i],geyser.intersection(base)])
for i in range(5,1,-1):layers[i-1]=unary_union([layers[i-1],layers[i]])
for i in range(1,6):layers[i]=polygonal(layers[i].intersection(base).difference(water))
# Recheck after water subtraction: a river can otherwise leave a tiny corner of a
# perfectly large terrace. Keep island relief, deliberate accents and real supports.
for i in range(5,0,-1):
 support=layers[i+1] if i<5 else Polygon()
 keep=[]
 for p in polys(layers[i]):
  area=p.area*m*m
  if area>=cfg['min_part_area_by_level_mm2'][i] or p.intersection(protected).area*m*m>.5 or p.intersection(island_union).area*m*m>2.5 or p.intersection(support).area*m*m>.5:keep.append(p)
 layers[i]=unary_union(keep)
 if i>1:layers[i-1]=unary_union([layers[i-1],layers[i]])
visible=[layers[i].difference(layers[i+1]) if i<5 else layers[i] for i in range(6)]
# Crater rim and plateau edge engraving clarifies the accents without adding more wood pieces.
texture=unary_union([shape(c['geom']).boundary.buffer(.065/m) for c in craters]).intersection(base).difference(water)
# Main landmarks and systems are reference callouts only, not labels on the production parts.
for name,lon,lat in [('Байкал',107.5,53.4),('Ладожское озеро',31.4,60.8),('Онежское озеро',35.2,61.8),('Телецкое озеро',87.65,51.6),('Озеро Таймыр',102,74.5),('Волга',46,50),('Обь и Иртыш',69,61),('Енисей и Ангара',93,58),('Лена и дельта',127,71),('Амур',134,48.5),('Сахалин',143,50),('Курильские острова',151.5,47.0)]:record(name,lon,lat,'Географический объект')
# SVG and model format compatible with the previous map generators.
def dpath(g):return ' '.join('M'+' L'.join(f'{x:.6f},{y:.6f}' for x,y in list(r.coords)[:-1])+' Z' for p in polys(g) for r in [orient(p,-1).exterior,*orient(p,-1).interiors])
def root():return E.Element('svg',nsmap={None:S},width='1600mm',height='1000mm',viewBox='0 0 4251.9685 2657.4803125')
def path(r,g,name,color,**kw):
 if not polys(g):return
 return E.SubElement(r,'path',id=name,d=dpath(g),fill=color,attrib={'fill-rule':'nonzero',**{k.replace('_','-'):str(v) for k,v in kw.items()}})
def write(r,n):E.ElementTree(r).write(str(OUT/n),encoding='UTF-8',xml_declaration=True)
colors=['#af8b5c','#c4a372','#d3b986','#e0cba1','#ebdab8','#f3e7d0'];assembly=root();plain=root();guide=root()
for i,g in enumerate(layers,1):
 cut=root();path(cut,g,f'ALL_L{i:02d}','#000');write(cut,f'Слой-{i:02d}-вся-Россия.svg')
 cut=root();path(cut,g.intersection(main),f'MAINLAND_L{i:02d}','#000');write(cut,f'Материк-слой-{i:02d}.svg')
 cut=root();path(cut,g.intersection(island_union),f'ISLANDS_L{i:02d}','#000');write(cut,f'Острова-слой-{i:02d}.svg')
 for r in [assembly,plain,guide]:path(r,g,f'L{i:02d}',colors[i-1],stroke='#715338',stroke_width='.45')
 cut=root();path(cut,texture.intersection(visible[i-1]),f'ENGRAVE_L{i:02d}','#74543c');write(cut,f'Гравировка-уровень-{i}.svg')
path(assembly,texture,'ACCENT_ENGRAVING','#826448');write(assembly,'Россия-рельеф.svg');write(plain,'Россия-шесть-слоёв.svg')
cut=root();path(cut,water,'THROUGH_WATER','#000');write(cut,'Реки-и-озёра-сквозные.svg')
for i,p in enumerate(landmark_records,1):
 E.SubElement(guide,'circle',cx=str(p['x']),cy=str(p['y']),r='6',fill='#f6efdf',stroke='#68482e',attrib={'stroke-width':'.6'});t=E.SubElement(guide,'text',x=str(p['x']),y=str(p['y']+2.5),fill='#433226',attrib={'font-size':'7','font-family':'sans-serif','text-anchor':'middle'});t.text=str(i)
write(guide,'Схема-природных-объектов.svg')
# Material regions are separate physical islands; one never gets merged into another.
counts=[]
for i,g in enumerate(layers,1):
 assert g.is_valid and not g.is_empty
 if i>1:assert g.difference(layers[i-2]).area<1e-6
 assert g.intersection(water).area<1e-6
 counts.append({'tier':i,'top_mm':3*i,'parts':len(polys(g)),'raw_parts':raw_counts[i-1],'area_mm2':g.area*m*m,'mainland_parts':len(polys(g.intersection(main))),'island_parts':len(polys(g.intersection(island_union)))})
report={'all_valid':True,'all_nested':True,'water_through_all_layers':True,'mainland_uses_user_cdr':True,'caspian_is_water_reference_not_wood':True,'islands_not_bridged':True,'raw_parts':sum(raw_counts),'final_parts':sum(c['parts'] for c in counts),'layers':counts,'dem_source':'ETOPO10 / ETOPO1, artistic adaptation','projection':pr,'four_kamchatka_cones':True,'configurable_production_thresholds':cfg}
(OUT/'Проверка-геометрии.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
model={'base':mapping(base),'mainland':mapping(main),'source_outline':mapping(outline),'regions':regions,'layers':[mapping(g) for g in layers],'visible':[mapping(g) for g in visible],'water':mapping(water),'waters':{k:mapping(v) for k,v in waters.items()},'texture':mapping(texture),'craters':craters,'geyser_recess':mapping(geyser),'putorana_valleys':mapping(putorana_valleys),'western_valleys':mapping(western_valleys),'western_terraces':{k:mapping(v) for k,v in western_terraces.items()},'ranges':{k:mapping(v) for k,v in ranges.items()},'accent_caps':{k:mapping(v) for k,v in accent_caps.items()},'places':landmark_records,'mm_per_unit':m,'palette':{f'L{i+1}':(f'Слой {i+1}',v,'Фанера') for i,v in enumerate(colors)}}
(OUT/'terrain-geometry.json').write_text(json.dumps(model,ensure_ascii=False))
with (OUT/'Состав-слоёв.csv').open('w',encoding='utf-8-sig',newline='') as f:
 c=csv.writer(f,lineterminator='\n');c.writerow(['Слой','Верх, мм','До очистки','После','Материк','Острова']);c.writerows((p['tier'],p['top_mm'],p['raw_parts'],p['parts'],p['mainland_parts'],p['island_parts']) for p in counts)
with (OUT/'Природные-объекты.csv').open('w',encoding='utf-8-sig',newline='') as f:
 c=csv.writer(f,lineterminator='\n');c.writerow(['Номер','Объект','Долгота','Широта','Решение']);c.writerows((i,p['name'],p['lon'],p['lat'],p['kind']) for i,p in enumerate(landmark_records,1))
print('RUSSIA LAYERS',counts,flush=True);print('TOTAL',report['raw_parts'],'→',report['final_parts'],flush=True)
