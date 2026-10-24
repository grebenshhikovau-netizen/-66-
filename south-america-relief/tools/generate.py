"""Six nested plywood terraces from ETOPO10, registered to the user's CDR silhouette."""
import json,math,csv,sys
from pathlib import Path
import numpy as np
from scipy.interpolate import RBFInterpolator
from scipy.ndimage import gaussian_filter
from shapely.geometry import shape,mapping,Polygon,Point,LineString,box
from shapely.ops import unary_union,transform
from shapely.geometry.polygon import orient
from shapely import make_valid
import contourpy
from lxml import etree as E
P=Path(__file__).resolve().parent
if P.name=='tools':D=P.parent/'data';OUT=P.parent
else:D=P;OUT=P
MM=1600/4251.9685;S='http://www.w3.org/2000/svg'
base=shape(json.load(open(D/'source-base.json')));countries=json.load(open(D/'countries-source.json'));features=json.load(open(D/'geographic-features.json'));controls=json.load(open(D/'geographic-controls.json'));dem=np.load(D/'dem-south-america.npz');warp=RBFInterpolator(np.array([[c[1],c[2]] for c in controls]),np.array([[c[3],c[4]] for c in controls]),kernel='thin_plate_spline',smoothing=1.8)
def warpfn(x,y,z=None):
 a=np.column_stack([np.atleast_1d(x),np.atleast_1d(y)]);b=warp(a);return (b[:,0],b[:,1])
def proj(g):return transform(warpfn,g)
def polys(g):
 if g.geom_type=='Polygon':return [g] if g.area>1e-9 else []
 return [p for c in getattr(g,'geoms',[]) for p in polys(c)]
def clean(g,min_area=3.0,opening=.35):
 g=make_valid(g);g=unary_union(polys(g))
 if opening:g=g.buffer(-opening/MM,join_style=1).buffer(opening/MM,join_style=1)
 g=g.simplify(.12/MM,preserve_topology=True);out=[]
 for p in polys(g):
  if p.area*MM*MM<min_area:continue
  out.append(Polygon(p.exterior,[r.coords for r in p.interiors if Polygon(r).area*MM*MM>1]))
 return unary_union(out)
# The DEM is sampled at 10 arc-minutes. A light subcell filter suppresses isolated grid noise.
z=gaussian_filter(dem['z'],.60);cg=contourpy.contour_generator(x=dem['lon'],y=dem['lat'],z=z,fill_type='OuterOffset')
def terrain_above(h,raw=False,region=None):
 points,offsets=cg.filled(h,10000);ps=[]
 for points_i,offset_i in zip(points,offsets):
  rings=[points_i[a:b] for a,b in zip(offset_i[:-1],offset_i[1:])];ps.append(Polygon(rings[0],rings[1:]))
 geo=unary_union(ps)
 if region is not None:geo=geo.intersection(region)
 g=make_valid(proj(geo)).intersection(base)
 return g if raw else clean(g)
thresholds=[0,200,600,1400,2600,4000];layers=[base]+[terrain_above(h) for h in thresholds[1:]]
# Broad lowland deck lets the main river system step down to the continuous base, without below-base holes.
basin=None
if (D/'amazon-basin.json').exists():basin=proj(shape(json.load(open(D/'amazon-basin.json')))).intersection(base)
if basin is not None:layers[1]=clean(unary_union([layers[1],basin]),opening=.22)
rivercuts=[];riverpaths=[]
for f in features['rivers']:
 g=proj(shape(f['geom']));name=f['name'];cent=shape(f['geom']).centroid
 if name in ['Amazonas','Madeira','Tapajós','Xingu','Ucayali','Marañón'] or name=='Negro' and cent.y>-5 and cent.x<-55:
  width=1.35 if name=='Amazonas' else .85
  rivercuts.append(g.buffer(width/2/MM,cap_style=1));riverpaths.append({'name':name,'geom':mapping(g)})
rivercut=unary_union(rivercuts).intersection(base)
# Keep rivers as recesses in upper plies; never cut the base.
river_terraces=list(layers)
for i in range(1,6):
 incision=rivercut.difference(river_terraces[i+1].buffer(.25/MM)) if i<5 else rivercut
 layers[i]=layers[i].difference(incision)
# High-altitude lakes lower one step within their surrounding highland, rather than cutting to sea level.
landmarks=[];lake_shapes=[]
for f in features['lakes']:
 g=proj(shape(f['geom'])).intersection(base)
 if f['name']=='Lago Titicaca':
  lake_shapes.append(g);layers[3]=unary_union([layers[3],g.buffer(.65/MM)]).intersection(base)
  for i in [4,5]:layers[i]=layers[i].difference(g)
  landmarks.append({'name':'Титикака','lon':-69.35,'lat':-15.85,'operation':'Котловина: L4 виден сквозь L5 и L6','geom':mapping(g)})
 else:
  for i in range(2,6):layers[i]=layers[i].difference(g)
# Uyuni is a quiet high plateau, never a peak.
uyuni=proj(shape(features['uyuni'])).intersection(base)
for i in range(1,5):layers[i]=unary_union([layers[i],uyuni])
layers[5]=layers[5].difference(uyuni.buffer(.4/MM));landmarks.append({'name':'Уюни','lon':-67.5,'lat':-20.15,'operation':'Ровная площадка L5; без шестого слоя','geom':mapping(uyuni)})
# Auyan-tepui: local emphasis confined to the real massif and Venezuela. Flat cap, five plies maximum.
auyan=proj(box(-63.05,5.35,-62.15,6.35));ven=shape(next(c['geom'] for c in countries if c['id']=='VEN'))
cap=clean(terrain_above(1000,raw=True,region=box(-63.05,5.35,-62.15,6.35)).intersection(ven),min_area=.05,opening=0)
if not cap.is_empty:
 cap=min(polys(cap),key=lambda g:g.distance(proj(Point(-62.55,5.97)))).buffer(.85/MM).intersection(ven)
if not cap.is_empty:
 for i in range(1,5):layers[i]=unary_union([layers[i],cap.buffer((4-i)*.45/MM)])
 layers[5]=layers[5].difference(auyan)
angel=proj(Point(-62.536,5.967));angelvalley=proj(LineString([(-62.536,5.967),(-62.50,6.05),(-62.47,6.12)])).buffer(.48/MM)
for i in [3,4,5]:layers[i]=layers[i].difference(angelvalley)
landmarks.append({'name':'Ауянтепуи / Анхель','lon':-62.536,'lat':5.967,'operation':'Плоская вершина и локальный уступ; усиление для масштаба','geom':mapping(cap)})
# Iguazu is a small river recess; no oversized canyon or invented mountain.
iguazu=proj(LineString([(-54.60,-25.58),(-54.48,-25.68),(-54.436,-25.696),(-54.35,-25.72)]));igcut=iguazu.buffer(.45/MM)
for i in range(1,6):layers[i]=layers[i].difference(igcut)
landmarks.append({'name':'Игуасу','lon':-54.436,'lat':-25.696,'operation':'Локальный вырез в верхних террасах','geom':mapping(igcut)})
# A small plain inside the highland at Machu Picchu, flattened without raising its surroundings.
mp=proj(Point(-72.545,-13.163));mppad=mp.buffer(1.1/MM);level=next((i for i in range(5,-1,-1) if layers[i].covers(mp)),2)
for i in range(level+1,6):layers[i]=layers[i].difference(mppad)
landmarks.append({'name':'Мачу-Пикчу','lon':-72.545,'lat':-13.163,'operation':f'Место под дальнейшую террасировку на L{level+1}','geom':mapping(mppad)})
# Clean only upper contours; preserve the original silhouette. Enforce exact nesting after every adaptation.
for i in range(1,6):layers[i]=clean(layers[i],min_area=2.5,opening=.28).intersection(layers[i-1]);layers[i]=unary_union(polys(make_valid(layers[i])))
# Political seams are engraving and paint masks, independent from the natural cutting contours.
countrygeoms={c['id']:shape(c['geom']) for c in countries};boundaries=unary_union([g.boundary for g in countrygeoms.values()]).difference(base.boundary.buffer(.12/MM));seam=boundaries.buffer(.12/MM,cap_style=2,join_style=1).intersection(base)
visible=[layers[i].difference(layers[i+1]) if i<5 else layers[i] for i in range(6)]
palette={
'BRA':('Бразилия','#e9dfca','Светлая натуральная фанера'), 'CHL':('Чили','#e9dfca','Светлая натуральная фанера'),
'ARG':('Аргентина','#be7745','Рыжий / медовый'), 'BOL':('Боливия','#77513b','Орех'), 'PER':('Перу','#44352e','Тёмный акцент'),
'COL':('Колумбия','#ad6049','Терракота'), 'VEN':('Венесуэла','#ad6049','Терракота'),
'URY':('Уругвай','#8c9275','Приглушённый оливково-серый'), 'PRY':('Парагвай','#b59c77','Светлый тауп'),
'ECU':('Эквадор','#967052','Тёплый табачный'), 'GUY':('Гайана','#aa9674','Песочный'), 'SUR':('Суринам','#80816c','Шалфейный'), 'GUF':('Французская Гвиана','#c3ad8a','Светлый песочный')}
def dpath(g):return ' '.join('M'+' L'.join(f'{x:.6f},{y:.6f}' for x,y in list(r.coords)[:-1])+' Z' for p in polys(g) for r in [orient(p,-1).exterior,*orient(p,-1).interiors])
def root():return E.Element('svg',nsmap={None:S},width='1600mm',height='1000mm',viewBox='0 0 4251.9685 2657.4803125')
def path(r,g,id,fill,**kw):
 if g.is_empty:return
 return E.SubElement(r,'path',id=id,d=dpath(g),fill=fill,attrib={'fill-rule':'nonzero',**{k.replace('_','-'):str(v) for k,v in kw.items()}})
def write(r,n):E.ElementTree(r).write(str(OUT/n),encoding='UTF-8',xml_declaration=True)
assembly=root();color=root();engrave=root();levelcolors=['#9f815d','#b79a70','#c9b084','#dac59b','#e5d6b3','#f3e8cf']
for i,g in enumerate(layers,1):
 r=root();path(r,g,f'L{i:02d}_CUT','#000000');write(r,f'Слой-{i:02d}-резка.svg');path(assembly,g,f'L{i:02d}',levelcolors[i-1],stroke='#5a4630',stroke_width='.45')
 eg=seam.intersection(visible[i-1]);r=root();path(r,eg,f'L{i:02d}_ENGRAVE','#302b25');write(r,f'Границы-гравировка-уровень-{i}.svg');path(engrave,eg,f'L{i:02d}_ENGRAVE','#302b25')
 for code,cg in countrygeoms.items():
  v=g.intersection(cg);name,c,description=palette[code]
  path(color,visible[i-1].intersection(cg),f'{code}_L{i:02d}',c,stroke='#5a4935',stroke_width='.38')
write(assembly,'Рельеф-шесть-уровней.svg');path(color,seam,'Политические_границы','#3a3028');write(color,'Карта-цвета-и-границы.svg');write(engrave,'Границы-гравировка-все.svg')
mask=root()
for code,cg in countrygeoms.items():
 name,c,description=palette[code];path(mask,cg,code,c)
write(mask,'Маски-окраски-по-странам.svg')
# A separate annotated diagram is reference-only; no names enter the production geometry.
guide=root()
for i,g in enumerate(layers):path(guide,g,f'L{i+1}',levelcolors[i],stroke='#65553d',stroke_width='.45')
for label,lon,lat in [('Анды',-70,-27),('Амазонская низменность',-61,-5),('Бразильское плоскогорье',-48,-17),('Гвианское плоскогорье',-61,5),('Патагония',-68,-45),('Атакама',-69.5,-24)]+[(p['name'],p['lon'],p['lat']) for p in landmarks]:
 q=proj(Point(lon,lat));E.SubElement(guide,'circle',cx=str(q.x),cy=str(q.y),r='2',fill='#78432a');t=E.SubElement(guide,'text',x=str(q.x+4),y=str(q.y-4),fill='#493b2c',attrib={'font-size':'9','font-family':'sans-serif'});t.text=label
write(guide,'Схема-природных-объектов.svg')
# Manufacturing and registration checks.
checks=[]
for i,g in enumerate(layers):
 assert g.is_valid and not g.is_empty,(i,g.is_valid)
 if i:assert g.difference(layers[i-1]).area<1e-6
 checks.append({'tier':i+1,'top_mm':(i+1)*3,'threshold_m':thresholds[i],'closed_parts':len(polys(g)),'area_mm2':g.area*MM**2})
cu=unary_union(list(countrygeoms.values()));assert cu.symmetric_difference(base).area<1e-6
report={'main_levels':6,'height_mm':[3,6,9,12,15,18],'real_elevation_source':'ETOPO10 derived from NOAA ETOPO1','dem_resolution_arcmin':10,'thresholds_m':thresholds,'dem_smoothing_cells':.6,'source_silhouette_preserved':True,'nested_layers':True,'base_without_holes':not any(p.interiors for p in polys(layers[0])),'country_masks_cover_source':True,'all_valid':True,'layers':checks,'manufacturing_generalization_mm':{'simplification':.12,'opening_radius':.28,'minimum_upper_part_area_mm2':2.5},'landmark_emphasis':['Auyan-tepui cap and Angel recess','Iguazu local recess','Uyuni flat L5','Titicaca L4 floor']}
(OUT/'Проверка-геометрии.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(OUT/'terrain-geometry.json').write_text(json.dumps({'base':mapping(base),'layers':[mapping(g) for g in layers],'visible':[mapping(g) for g in visible],'countries':countries,'seam':mapping(seam),'landmarks':landmarks,'mm_per_unit':MM,'palette':palette,'places':[]},ensure_ascii=False))
with (OUT/'Палитра.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f,lineterminator='\n');w.writerow(['Код','Страна','HEX для визуализации','Отделка']);w.writerows((code,*v) for code,v in palette.items())
with (OUT/'Состав-слоёв.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f,lineterminator='\n');w.writerow(['Слой','Верх, мм','Порог DEM, м','Деталей','Площадь, мм2']);w.writerows((c['tier'],c['top_mm'],c['threshold_m'],c['closed_parts'],round(c['area_mm2'],3)) for c in checks)
print('LAYERS',checks,flush=True)
