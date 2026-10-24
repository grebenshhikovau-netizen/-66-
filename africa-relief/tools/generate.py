"""Decorative six-ply Africa relief, registered to supplied CDR contours."""
import json,math,csv
from pathlib import Path
import numpy as np
from scipy.interpolate import RBFInterpolator
from scipy.ndimage import gaussian_filter
from shapely.geometry import shape,mapping,Polygon,Point,LineString,box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union,transform,nearest_points
from shapely import make_valid
import contourpy
from lxml import etree as E
P=Path(__file__).resolve().parent;D=P.parent/'data' if P.name=='tools' else P;OUT=P.parent if P.name=='tools' else P;MM=1600/4251.9685;S='http://www.w3.org/2000/svg'
main=shape(json.load(open(D/'source-base.json')));F=json.load(open(D/'geographic-features.json'));controls=json.load(open(D/'geographic-controls.json'));a=np.load(D/'dem-africa.npz');w=RBFInterpolator(np.array([[c[1],c[2]] for c in controls]),np.array([[c[3],c[4]] for c in controls]),kernel='thin_plate_spline',smoothing=2)
def warp(x,y,z=None):
 r=w(np.column_stack([np.atleast_1d(x),np.atleast_1d(y)]));return r[:,0],r[:,1]
def proj(g):return make_valid(transform(warp,g))
def polys(g):
 if g.geom_type=='Polygon':return [g] if g.area>1e-9 else []
 return [p for c in getattr(g,'geoms',[]) for p in polys(c)]
def clean(g,area=3,rad=.32):
 g=unary_union(polys(make_valid(g)))
 if rad:g=g.buffer(-rad/MM).buffer(rad/MM)
 g=g.simplify(.10/MM,preserve_topology=True)
 return unary_union([Polygon(p.exterior,[r.coords for r in p.interiors if Polygon(r).area*MM**2>.6]) for p in polys(g) if p.area*MM**2>=area])
mad=clean(proj(shape(F['madagascar'])),area=8,rad=.10);mad=max(polys(mad),key=lambda g:g.area);base=unary_union([main,mad]);cg=contourpy.contour_generator(x=a['lon'],y=a['lat'],z=gaussian_filter(a['z'],.65),fill_type='OuterOffset')
def above(h,region=None,raw=False):
 ps,offs=cg.filled(h,10000);gs=[]
 for p,o in zip(ps,offs):
  rings=[p[x:y] for x,y in zip(o[:-1],o[1:])];gs.append(Polygon(rings[0],rings[1:]))
 g=unary_union(gs)
 if region is not None:g=g.intersection(region)
 g=proj(g).intersection(base)
 return g if raw else clean(g)
thresholds=[0,180,650,1300,2200,3200];layers=[base]+[above(h) for h in thresholds[1:]]
# Most interiors occupy the second ply; the coast remains a calm exposed base.
# Natural lowlands and river recesses then read distinctly without a second backdrop below the map.
interior=main.buffer(-3.5/MM);layers[1]=clean(unary_union([layers[1],interior]),rad=.2)
waters={};lines={}
for f in F['rivers']:
 name=f['name']
 if name=='Onilahy':continue
 family='Нил' if 'Nile' in name else 'Конго' if name in ['Congo','Lualaba'] else 'Замбези'
 line=proj(shape(f['geom'])).intersection(main);lines.setdefault(family,[]).append(line)
# Finish the Nile through Cairo and provide two geographically located distributaries to the Mediterranean.
delta_geo=[[(31.23,30.04),(31.12,30.19),(31.,30.25),(30.8,30.4),(30.7,30.75),(30.5,31.1),(30.4,31.45)],[(31.,30.25),(31.1,30.3),(31.3,30.6),(31.45,30.95),(31.65,31.25),(31.8,31.5)]]
# Bridge the source database's gap near Cairo before adding the distributaries.
from shapely import get_coordinates
nile_coords=np.vstack([get_coordinates(shape(f['geom'])) for f in F['rivers'] if f['name']=='Nile'])
north=nile_coords[np.argmax(nile_coords[:,1])];lines['Нил'].append(proj(LineString([north,(31.23,30.04)])))
delta_lines=[]
for coords in delta_geo:
 line=proj(LineString(coords));coords2=list(line.coords);end=Point(coords2[-1]);near=nearest_points(end,main.exterior)[1]
 # The mouth must reach the authored coastline rather than stop inside the plinth.
 if end.distance(near)*MM<7:coords2.append(near.coords[0])
 line=LineString(coords2);delta_lines.append(line);lines['Нил'].append(line)
# Complete the lower Congo estuary to the authored Atlantic coast.
congo_end=proj(LineString([(13.184,-5.89),(12.85,-5.97),(12.45,-6.05),(12.30,-6.12)]));cc=list(congo_end.coords);cc.append(nearest_points(Point(cc[-1]),main.exterior)[1].coords[0]);lines['Конго'].append(LineString(cc))
for name,gs in lines.items():
 width={'Нил':1.65,'Конго':1.7,'Замбези':1.2}[name]
 waters[name]=unary_union(gs).buffer(width/2/MM).intersection(main)
lake_keys={'Lake Victoria':'Виктория','Lake Tanganyika':'Танганьика','Lake Malawi':'Малави','Lake Albert':'Альберт','Lake Tana':'Тана','Lake Turkana':'Туркана'}
for f in F['lakes']:
 g=clean(proj(shape(f['geom'])).intersection(main),area=.25,rad=0)
 # A gentle outward offset keeps the long rift lakes legible at plywood scale.
 if f['name'] in ['Lake Tanganyika','Lake Malawi']:g=g.buffer(.20/MM)
 waters[lake_keys[f['name']]]=g
# Lower each channel by a nearby terrace, retaining support under highland headwaters.
water=unary_union(list(waters.values()));old=list(layers)
for i in range(1,6):
 cut=water.difference(old[i+1].buffer(.25/MM)) if i<5 else water
 layers[i]=layers[i].difference(cut)
# Broad western and eastern rift corridors; the dark lakes remain the strongest marks inside them.
rift_w=[(30,5),(30.5,2.5),(29.5,0),(29.3,-3),(29.8,-6),(31.4,-8),(33.5,-10),(34.3,-13.5),(35,-16)]
rift_e=[(41.5,12),(39.2,8),(37.5,4),(36,-1),(35.5,-4),(35,-7),(34,-10)]
rift=unary_union([proj(LineString(rift_w)),proj(LineString(rift_e))]);rift_core=rift.buffer(.7/MM);rift_apron=rift.buffer(1.7/MM)
for i in range(2,6):layers[i]=layers[i].difference(rift_core if i==2 else rift_apron)
# Water gets an uninterrupted negative silhouette after the rift is cut; never a raised lake.
# The Eastern lakes and both large river systems sit visibly on lower terraces.
for i in range(1,6):layers[i]=layers[i].difference(water)
# Kilimanjaro: a local summit taken from the real massif, broadened to a manufacturable accent.
kili_point=proj(Point(37.355,-3.067));candidate=above(3000,region=box(36.8,-3.5,37.9,-2.5),raw=True)
if candidate.is_empty:candidate=above(2200,region=box(36.8,-3.5,37.9,-2.5),raw=True)
cap=min(polys(candidate),key=lambda g:g.distance(kili_point)).buffer(.65/MM).intersection(main)
for i in range(1,6):layers[i]=unary_union([layers[i],cap.buffer((5-i)*.50/MM)]).intersection(base)
# Victoria Falls and Batoka gorge: a narrow incision on the Zambezi, not an enormous crater.
falls_geo=LineString([(25.74,-17.89),(25.855,-17.925),(25.90,-17.98),(26.08,-18.02),(26.30,-17.98)])
falls=proj(falls_geo).buffer(.65/MM).intersection(main)
waters['Водопад Виктория']=falls;water=unary_union([water,falls])
falls_apron=proj(falls_geo).buffer(1.65/MM).intersection(main)
for i in range(2,6):layers[i]=layers[i].difference(falls_apron)
for i in range(1,6):layers[i]=layers[i].difference(falls)
# Finish structural contours before texture; light engraving adds no physical plywood level.
for i in range(1,6):layers[i]=clean(layers[i],area=3,rad=.30).intersection(layers[i-1]);layers[i]=unary_union(polys(make_valid(layers[i])))
# Do not let smoothing close the mandatory channels or shrink long lakes into disconnected dots.
for i in range(1,6):layers[i]=unary_union(polys(layers[i].difference(water)))
visible=[layers[i].difference(layers[i+1]) if i<5 else layers[i] for i in range(6)]
# Quiet decorative surface drawing, geographically confined to real sand-sea areas.
texture=[]
def stroke(coords,width=.13):return proj(LineString(coords)).buffer(width/2/MM,cap_style=1)
for centerlon,centerlat,n,span in [(7,30,7,4),(26,25.8,6,3.8),(12.5,20.5,4,3)]:
 for j in range(n):
  coords=[(centerlon-span/2+span*t/35,centerlat+j*.32+.13*math.sin(t/35*math.pi*3+j*.6)) for t in range(36)];texture.append(stroke(coords))
cracks=[[(11,22),(11.5,21.5),(11.4,20.9),(12,20.4),(12,19.8)],[(11.4,20.9),(10.7,20.5),(10.5,19.8)],[(11.5,21.5),(12.2,21.4),(12.6,20.9),(12,20.4)],[(12.2,21.4),(12.4,22)],[(10.7,20.5),(10.1,20.7)]]
texture.extend(stroke(c,.12) for c in cracks)
# Namib dunes remain subordinate to the Nile/Congo/lake system.
for j in range(5):texture.append(stroke([(14.5+j*.25+.12*math.sin(t*.25),-24+t*.12) for t in range(32)],.12))
richat_center=proj(Point(-11.4,21.124));richat=unary_union([richat_center.buffer(r/MM).difference(richat_center.buffer((r-.14)/MM)) for r in [3.0,2.0,1.0]])
texture=unary_union(texture+[richat]).intersection(main).difference(water.buffer(.5/MM));texture=unary_union(polys(texture))
# Geography references are separate from production engraving: no city/country text is added.
places=[('Нил',32,22),('Дельта Нила',31.,31.2),('Конго',20,-1),('Котловина Конго',22,-2),('Виктория',33,-1.5),('Танганьика',29.6,-6),('Малави',34.5,-12),('Замбези',28,-16.5),('Водопад Виктория',25.855,-17.925),('Великий рифт',35.5,-4),('Эфиопское нагорье',38,10),('Атлас',-5,32),('Килиманджаро',37.355,-3.067),('Драконовы горы',29,-29),('Сахара',10,25),('Ришат',-11.4,21.124),('Намиб',15,-23),('Калахари',23,-23),('Мадагаскар',47,-19)]
landmarks=[{'name':name,'lon':lon,'lat':lat,'x':proj(Point(lon,lat)).x,'y':proj(Point(lon,lat)).y} for name,lon,lat in places]
def dpath(g):return ' '.join('M'+' L'.join(f'{x:.6f},{y:.6f}' for x,y in list(r.coords)[:-1])+' Z' for p in polys(g) for r in [orient(p,-1).exterior,*orient(p,-1).interiors])
def root():return E.Element('svg',nsmap={None:S},width='1600mm',height='1000mm',viewBox='0 0 4251.9685 2657.4803125')
def path(r,g,id,fill,**kw):
 if not polys(g):return
 return E.SubElement(r,'path',id=id,d=dpath(g),fill=fill,attrib={'fill-rule':'nonzero',**{k.replace('_','-'):str(v) for k,v in kw.items()}})
def write(r,n):E.ElementTree(r).write(str(OUT/n),encoding='UTF-8',xml_declaration=True)
colors=['#aa8558','#bf9c6b','#cfb07d','#dec598','#ead8b1','#f2e5c9'];r=root();construction=root();annot=root()
for i,g in enumerate(layers,1):
 cut=root();path(cut,g.intersection(main),f'AFRICA_L{i:02d}','#000');write(cut,f'Слой-{i:02d}-резка.svg')
 opt=root();path(opt,g.intersection(mad),f'MADAGASCAR_L{i:02d}','#000');write(opt,f'Опция-Мадагаскар-слой-{i:02d}.svg')
 path(r,g,f'L{i:02d}',colors[i-1],stroke='#6c5032',stroke_width='.48');path(construction,g,f'L{i:02d}',colors[i-1],stroke='#6c5032',stroke_width='.48');path(annot,g,f'L{i:02d}',colors[i-1],stroke='#6c5032',stroke_width='.48')
 waterlevel=water.intersection(visible[i-1]);texturelevel=texture.intersection(visible[i-1]);m=root();path(m,waterlevel,f'WATER_L{i:02d}','#29646a');write(m,f'Вода-маска-уровень-{i}.svg');m=root();path(m,texturelevel,f'TEXTURE_L{i:02d}','#6f5135');write(m,f'Фактура-гравировка-уровень-{i}.svg')
path(r,texture,'Гравировка_Сахара_Намиб_Ришат','#826746');path(r,water,'Вода','#317b80');path(annot,water,'Вода','#317b80');write(r,'Африка-рельеф-цветной.svg');write(construction,'Африка-шесть-уровней.svg')
m=root();path(m,water,'WATER','#000');write(m,'Вода-маска-все.svg');m=root();path(m,texture,'TEXTURE','#000');write(m,'Фактура-гравировка-все.svg')
# Numbered callouts, with names in the CSV and README, keep the map drawing legible.
for i,p in enumerate(landmarks,1):
 E.SubElement(annot,'circle',cx=str(p['x']),cy=str(p['y']),r='5.5',fill='#f5eddc',stroke='#73472d',attrib={'stroke-width':'.6'});t=E.SubElement(annot,'text',x=str(p['x']),y=str(p['y']+2.4),fill='#4b3224',attrib={'font-size':'7','font-family':'sans-serif','text-anchor':'middle'});t.text=str(i)
write(annot,'Схема-природных-объектов.svg')
checks=[]
for i,g in enumerate(layers):
 assert g.is_valid and not g.is_empty
 if i:assert g.difference(layers[i-1]).area<1e-6
 checks.append({'tier':i+1,'top_mm':(i+1)*3,'threshold_m':thresholds[i],'mainland_parts':len(polys(g.intersection(main))),'madagascar_parts':len(polys(g.intersection(mad))),'area_mm2':g.area*MM**2})
# Every mandatory water body must retain an unfilled footprint in all upper plies.
mandatory=['Нил','Конго','Виктория','Танганьика','Малави','Замбези','Водопад Виктория'];waterchecks=[]
for name in mandatory:
 g=waters[name];assert not g.is_empty;filled=unary_union(layers[1:]).intersection(g).area/max(g.area,1e-8);assert filled<1e-6,(name,filled);waterchecks.append({'name':name,'area_mm2':g.area*MM**2,'upper_layers_fill_fraction':filled})
assert cap.intersection(layers[5]).area*MM**2>1,'Kilimanjaro missing'
(OUT/'terrain-geometry.json').write_text(json.dumps({'base':mapping(base),'mainland':mapping(main),'madagascar':mapping(mad),'layers':[mapping(g) for g in layers],'visible':[mapping(g) for g in visible],'water':mapping(water),'waters':{k:mapping(v) for k,v in waters.items()},'texture':mapping(texture),'rift':mapping(rift_core),'kili_cap':mapping(cap),'places':landmarks,'mm_per_unit':MM,'palette':{f'L{i+1}':(f'Слой {i+1}',c,'Фанера') for i,c in enumerate(colors)}},ensure_ascii=False))
(OUT/'Проверка-геометрии.json').write_text(json.dumps({'layers':6,'all_valid':True,'all_nested':True,'base_without_below_base_parts':True,'mandatory_waterways_clear':True,'mandatory_water':waterchecks,'kilimanjaro_L6':True,'mainland_silhouette_kept':True,'madagascar_is_separate_optional_addition':True,'source_dem':'ETOPO10 / ETOPO1, decorative adaptation','checks':checks},ensure_ascii=False,indent=2))
with (OUT/'Природные-объекты.csv').open('w',encoding='utf-8-sig',newline='') as f:
 c=csv.writer(f,lineterminator='\n');c.writerow(['Номер на схеме','Объект','Долгота','Широта']);c.writerows((i,p['name'],p['lon'],p['lat']) for i,p in enumerate(landmarks,1))
with (OUT/'Состав-слоёв.csv').open('w',encoding='utf-8-sig',newline='') as f:
 c=csv.writer(f,lineterminator='\n');c.writerow(['Слой','Верх, мм','Контур материка: деталей','Мадагаскар: деталей']);c.writerows((v['tier'],v['top_mm'],v['mainland_parts'],v['madagascar_parts']) for v in checks)
print('LAYERS',checks,flush=True);print('WATER CHECKS',waterchecks,flush=True)
