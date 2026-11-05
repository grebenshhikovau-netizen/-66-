"""Add cities and Brazilian administrative engraving on approved exposed plies."""
import json,math
from pathlib import Path
import numpy as np
from scipy.interpolate import RBFInterpolator
from shapely.geometry import shape,mapping,Point,Polygon,box,LineString
from shapely.ops import unary_union,transform,nearest_points,polylabel
from shapely.affinity import translate,rotate,scale
from shapely import set_precision,segmentize
from shapely.prepared import prep
from font_geometry import word_geom
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'))
C=json.load(open(P/'data/source/geographic-controls.json'))
warp=RBFInterpolator(np.array([[c[1],c[2]]for c in C]),np.array([[c[3],c[4]]for c in C]),kernel='thin_plate_spline',smoothing=1.8)
MM=1600/4251.9685
def xy(lon,lat):
 a=warp([[lon,lat]])[0];return Point(a[0]*MM,a[1]*MM-1000)
def project(g):
 def fn(x,y,z=None):
  a=warp(np.column_stack([np.atleast_1d(x),np.atleast_1d(y)]));return a[:,0]*MM,a[:,1]*MM-1000
 return transform(fn,segmentize(g,.12))
def polygons(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in polygons(q)]
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[g]if g.length>.02 else[]
 return[p for q in getattr(g,'geoms',[])for p in lines(q)]

features=json.load(open(P/'data/source/brazil-states.geojson'))['features']
geo={f['properties']['postal']:shape(f['geometry'])for f in features}
state_shapes={code:project(g).intersection(shape(D['territories']['BRA']))for code,g in geo.items()}
edges=[]
for i,(a,g)in enumerate(geo.items()):
 for b,h in list(geo.items())[:i]:
  shared=g.boundary.intersection(h.boundary)
  if not shared.is_empty:edges.extend(lines(project(shared)))
network=unary_union(edges).intersection(shape(D['territories']['BRA']).buffer(-.25)).simplify(.065)

# name;longitude;latitude — principal cities, including all Brazilian capitals.
data='''BRA;Манаус;-60.021;-3.119
BRA;Белен;-48.504;-1.456
BRA;Макапа;-51.069;.035
BRA;Боа-Виста;-60.675;2.824
BRA;Риу-Бранку;-67.81;-9.975
BRA;Порту-Велью;-63.90;-8.76
BRA;Палмас;-48.333;-10.185
BRA;Куяба;-56.097;-15.601
BRA;Кампу-Гранди;-54.647;-20.469
BRA;Бразилиа;-47.882;-15.794
BRA;Гояния;-49.264;-16.686
BRA;Сан-Луис;-44.302;-2.530
BRA;Терезина;-42.802;-5.091
BRA;Форталеза;-38.526;-3.731
BRA;Натал;-35.211;-5.794
BRA;Жуан-Песоа;-34.863;-7.115
BRA;Ресифи;-34.877;-8.047
BRA;Масейо;-35.735;-9.666
BRA;Аракажу;-37.073;-10.947
BRA;Салвадор;-38.502;-12.977
BRA;Белу-Оризонти;-43.938;-19.920
BRA;Витория;-40.308;-20.315
BRA;Рио-де-Жанейро;-43.173;-22.907
BRA;Сан-Паулу;-46.633;-23.551
BRA;Куритиба;-49.273;-25.429
BRA;Флорианополис;-48.548;-27.595
BRA;Порту-Алегри;-51.217;-30.034
ARG;Буэнос-Айрес;-58.382;-34.604
ARG;Кордова;-64.188;-31.420
ARG;Росарио;-60.639;-32.945
ARG;Мендоса;-68.845;-32.890
ARG;Ла-Плата;-57.954;-34.921
ARG;Тукуман;-65.223;-26.808
ARG;Сальта;-65.412;-24.785
ARG;Неукен;-68.06;-38.952
ARG;Комодоро-Ривадавия;-67.49;-45.864
ARG;Рио-Гальегос;-69.218;-51.624
ARG;Ушуая;-68.303;-54.802
CHL;Сантьяго;-70.669;-33.449
CHL;Вальпараисо;-71.613;-33.047
CHL;Антофагаста;-70.4;-23.65
CHL;Консепсьон;-73.05;-36.827
CHL;Пуэрто-Монт;-72.942;-41.469
CHL;Пунта-Аренас;-70.908;-53.163
PER;Лима;-77.043;-12.046
PER;Куско;-71.967;-13.532
PER;Арекипа;-71.537;-16.409
PER;Трухильо;-79.03;-8.112
PER;Икитос;-73.251;-3.744
COL;Богота;-74.072;4.711
COL;Медельин;-75.581;6.244
COL;Кали;-76.532;3.452
COL;Картахена;-75.48;10.39
COL;Барранкилья;-74.782;10.969
VEN;Каракас;-66.904;10.481
VEN;Маракайбо;-71.612;10.643
VEN;Валенсия;-68.007;10.158
VEN;Сьюдад-Гуаяна;-62.641;8.297
ECU;Кито;-78.468;-.181
ECU;Гуаякиль;-79.9;-2.17
ECU;Куэнка;-79.006;-2.901
BOL;Ла-Пас;-68.15;-16.5
BOL;Сукре;-65.261;-19.019
BOL;Санта-Крус;-63.183;-17.784
BOL;Кочабамба;-66.156;-17.393
PRY;Асунсьон;-57.576;-25.264
PRY;Сьюдад-дель-Эсте;-54.611;-25.509
URY;Монтевидео;-56.164;-34.901
GUY;Джорджтаун;-58.155;6.802
SUR;Парамарибо;-55.203;5.852
GUF;Кайенна;-52.326;4.923'''
cities=[]
for i,line in enumerate(data.splitlines()):
 code,name,lon,lat=line.split(';');pt=xy(float(lon),float(lat));cities.append({'id':f'CITY_{i+1:03d}','country':code,'text':name,'lon':float(lon),'lat':float(lat),'source':pt})
(P/'data/source/cities.json').write_text(json.dumps([{k:v for k,v in c.items()if k!='source'}for c in cities],ensure_ascii=False,indent=2))

labels=[{**a,'kind':'country','color':'#0000ff'}for a in D['labels']if a.get('kind','country')=='country']
occupied=[box(*shape(a['geometry']).bounds).buffer(.65)for a in labels];markers=[];notes=[]
available={}
for row in D['pieces']:
 for code in row['regions']:
  g=shape(row['visible']).intersection(shape(D['layer_country_masks'][row['tier']-1].get(code,mapping(Polygon()))))
  if not g.is_empty:available[(row['id'],code)]=g
rows={r['id']:r for r in D['pieces']}
for city in cities:
 choices=[]
 for (id,code),g in available.items():
  if code!=city['country']:continue
  safe=g.buffer(-.3).difference(unary_union(occupied))
  if safe.is_empty:continue
  pt=city['source']if safe.covers(city['source'])else nearest_points(city['source'],safe)[1]
  choices.append((pt.distance(city['source']),id,pt))
 if not choices:notes.append({'city':city['text'],'omitted':'no marker surface'});continue
 dist,id,pt=min(choices,key=lambda t:t[0])
 if dist>4:notes.append({'city':city['text'],'omitted':'source point over 4 mm from open country surface','distance':dist});continue
 markers.append({'id':city['id'],'country':city['country'],'name':city['text'],'piece':id,'point':[pt.x,pt.y],
                 'geometry':mapping(pt.buffer(.22,quad_segs=10)),'geographic_shift_mm':dist})
 city['marker']=markers[-1]

marker_union=unary_union([shape(m['geometry']).buffer(.35)for m in markers])
old_lines=unary_union([shape(r['red_internal'])for r in D['pieces']])
avoid_lines=unary_union([old_lines,network]).buffer(.18)

def place(text,code,kind,preferred,domain=None,marker=None):
 raw=word_geom(text);bb=box(*raw.bounds);cx,cy=bb.centroid.x,bb.centroid.y
 options=[];ink=unary_union(occupied)
 for (id,co),g in available.items():
  if co!=code:continue
  if domain is not None:g=g.intersection(domain)
  safe=g.buffer(-.30).difference(ink).difference(marker_union).difference(avoid_lines)
  if safe.is_empty:continue
  points=[]
  for p in sorted(polygons(safe),key=lambda p:-p.area)[:8]:
   points.extend([p.representative_point(),polylabel(p,tolerance=.25)])
  if kind=='city':
   # Use true geography first, then a small local grid if coast/steps constrain a word.
   for x in np.arange(preferred.x-13,preferred.x+13.1,1.4):
    for y in np.arange(preferred.y-10,preferred.y+10.1,1.4):
     if safe.covers(Point(x,y)):points.append(Point(x,y))
   points=[p for p in points if p.distance(preferred)<16]
  else:
   a,b,c,d=safe.bounds
   for x in np.arange(a,c+.1,3):
    for y in np.arange(b,d+.1,3):
     if safe.covers(Point(x,y)):points.append(Point(x,y))
  options.append((id,prep(safe),sorted(points,key=lambda p:p.distance(preferred))))
 angles=[0,-90]if code=='CHL'else[0]
 sizes=[2.3,2.1,1.9,1.7,1.5]if kind=='city'else[1.9,1.7,1.5]
 found=None
 for size in sizes:
  for angle in angles:
   rect=rotate(scale(bb,xfact=size,yfact=size,origin=(cx,cy)),angle,origin=(cx,cy));glyph=rotate(scale(raw,xfact=size,yfact=size,origin=(cx,cy)),angle,origin=(cx,cy))
   for id,safe,points in options:
    for pt in points:
     dx,dy=pt.x-cx,pt.y-cy;placed=translate(rect,dx,dy)
     if not safe.covers(placed):continue
     score=pt.distance(preferred)+(0 if marker is None or id==marker['piece']else 2)
     if found is None or score<found[0]:found=(score,id,size,angle,pt,translate(glyph,dx,dy),placed)
     break
   if found:break
  if found:break
 if found is None:return None
 _,id,size,angle,pt,glyph,rect=found;co=math.cos(math.radians(angle));si=math.sin(math.radians(angle))
 matrix=[co,si,-si,co,pt.x-co*size*cx+si*size*cy,pt.y-si*size*cx-co*size*cy]
 result={'id':f'{kind.upper()}_{len(labels):03d}','kind':kind,'country':code,'text':text,'lines':[{'text':text,'x_em':0,'y_em':0}],
         'piece':id,'tier':rows[id]['tier'],'font_family':'Open Sans Light','font_size_mm':size,'angle_degrees':angle,'matrix':matrix,
         'geometry':mapping(glyph),'color':'#ff0000'}
 labels.append(result);occupied.append(rect.buffer(.6));return result

for city in cities:
 if 'marker'not in city:continue
 marker=city['marker'];pt=Point(marker['point']);a=place(city['text'],city['country'],'city',pt,marker=marker)
 if a is None:
  markers.remove(marker);notes.append({'city':city['text'],'omitted':'caption cannot fit exposed country surface'});continue
 marker['caption']=a['id'];a['city_marker']=marker['id'];print('CITY',city['text'],a['piece'],a['font_size_mm'],flush=True)

state_names={'AM':'АМАЗОНАС','PA':'ПАРА','MT':'МАТУ-ГРОСУ','MS':'МАТУ-ГРОСУ-ДУ-СУЛ','MG':'МИНАС-ЖЕРАЙС','BA':'БАИЯ','GO':'ГОЯС','RO':'РОНДОНИЯ','AC':'АКРИ','RR':'РОРАЙМА','AP':'АМАПА','TO':'ТОКАНТИНС','MA':'МАРАНЬЯН','PI':'ПИАУИ','CE':'СЕАРА','PE':'ПЕРНАМБУКУ','SP':'САН-ПАУЛУ','PR':'ПАРАНА','SC':'САНТА-КАТАРИНА','RS':'РИУ-ГРАНДИ-ДУ-СУЛ'}
for code,name in state_names.items():
 g=state_shapes[code]
 if g.is_empty:continue
 a=place(name,'BRA','state',g.representative_point(),domain=g)
 if a:a['state']=code;print('STATE',code,a['font_size_mm'],flush=True)
 else:notes.append({'state':code,'omitted':'no clear label space'})

# Province strokes only on visible wood. Clean caption-sized gaps follow map convention.
all_text=unary_union([box(*shape(a['geometry']).bounds).buffer(.35)for a in labels])
for row in D['pieces']:
 g=shape(row['geom']);visible=shape(row['visible']);state_lines=network.intersection(visible).difference(g.boundary.buffer(.25)).difference(all_text)
 row['brazil_state_lines']=mapping(state_lines)
 row['red_internal']=mapping(unary_union([shape(row['red_internal']),state_lines]))
 ink=unary_union([shape(a['geometry'])for a in labels if a['piece']==row['id']])
 dots=unary_union([shape(m['geometry'])for m in markers if m['piece']==row['id']])
 row['engraving']=mapping(unary_union([ink,dots,shape(row['red_internal']).buffer(.025,cap_style=2,join_style=2)]))
D['labels']=labels;D['city_markers']=markers;D['brazil_states']={c:mapping(g)for c,g in state_shapes.items()};D['annotation_notes']=notes
(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False))
(P/'data/annotation-summary.json').write_text(json.dumps({'cities':len(markers),'state_names':sum(a['kind']=='state'for a in labels),'country_names':13,'brazil_states':len(state_shapes),'notes':notes},ensure_ascii=False,indent=2))
print('ANNOTATIONS DONE',len(markers),'cities',sum(a['kind']=='state'for a in labels),'state names',notes,flush=True)
