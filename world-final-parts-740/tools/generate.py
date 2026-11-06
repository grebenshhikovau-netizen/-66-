"""Three complementary CNC kits in the original Mercator atlas coordinates.
Coasts: original atlas. Australia/island terraces: NOAA ETOPO 10 bed/topography.
Greenland: intentionally decorative ice dome (not a bedrock-derived ice surface).
"""
import json,math,sys,shutil
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from shapely import make_valid,set_precision
from shapely.geometry import shape,mapping,Polygon,Point,LineString,box
from shapely.ops import unary_union,transform,nearest_points,linemerge
from shapely.affinity import scale,translate,rotate,affine_transform
from font_geometry import word_geom
P=Path(__file__).resolve().parent.parent
PROJ=json.load(open(P/'data/source/world-projection.json'))
def project(lon,lat):
 return PROJ['lon_to_x_mm']*np.asarray(lon)+PROJ['x_offset_mm'],PROJ['y_offset_mm']-PROJ['mercator_to_y_mm']*np.log(np.tan(np.pi/4+np.radians(lat)/2))
C={x['code']:x for x in json.load(open(P/'data/source/master-countries.json'))}
DEM=gaussian_filter(np.fromfile(P/'data/source/etopo10_bed_g_i2.bin',dtype='<i2').reshape(1081,2161).astype(float),1)
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty and g.area>1e-7 else[]
 return[p for q in getattr(g,'geoms',[])for p in ps(q)]
def ls(g):
 if g.geom_type in ['LineString','LinearRing']:return[g]if g.length>.15 else[]
 return[l for q in getattr(g,'geoms',[])for l in ls(q)]
def polygonal(g):return unary_union(ps(make_valid(g)))
def smooth(g,r=.35,t=.18,minarea=3):
 g=polygonal(g);g=g.buffer(r,quad_segs=6).buffer(-2*r,quad_segs=6).buffer(r,quad_segs=6).simplify(t,preserve_topology=True)
 return unary_union([Polygon(p.exterior,[r for r in p.interiors if Polygon(r).area>8])for p in ps(g)if p.area>=minarea])
def terrace(base,threshold,minarea=35,close=2):
 x0,y0,x1,y1=base.bounds;lon0=(x0-PROJ['x_offset_mm'])/PROJ['lon_to_x_mm'];lon1=(x1-PROJ['x_offset_mm'])/PROJ['lon_to_x_mm'];inv=lambda y:math.degrees(2*math.atan(math.exp((PROJ['y_offset_mm']-y)/PROJ['mercator_to_y_mm']))-math.pi/2);lat0=inv(y1);lat1=inv(y0)
 j0=max(0,int((lon0+180)*6)-4);j1=min(2161,int((lon1+180)*6)+5);i0=max(0,int((90-lat1)*6)-4);i1=min(1081,int((90-lat0)*6)+5)
 if j1-j0<2 or i1-i0<2:return Polygon()
 lon=-180+np.arange(j0,j1)/6;lat=90-np.arange(i0,i1)/6;z=DEM[i0:i1,j0:j1]
 if z.max()<threshold:return Polygon()
 fig,ax=plt.subplots();cs=ax.contourf(lon,lat,z,levels=[threshold,10000]);rings=cs.get_paths()[0].to_polygons();plt.close(fig);out=[];holes=[]
 outer_sign=1
 if len(rings):
  largest=max(rings,key=lambda r:abs(np.sum(r[:-1,0]*r[1:,1]-r[1:,0]*r[:-1,1])));outer_sign=1 if np.sum(largest[:-1,0]*largest[1:,1]-largest[1:,0]*largest[:-1,1])>0 else -1
 for r in rings:
  if len(r)<4:continue
  sign=np.sum(r[:-1,0]*r[1:,1]-r[1:,0]*r[:-1,1]);p=Polygon(r)
  (out if sign*outer_sign>0 else holes).append(p)
 land=polygonal(unary_union(out).difference(unary_union(holes)))
 g=transform(project,land).intersection(base.buffer(-1.2));g=smooth(g,close,.3,minarea)
 return unary_union([q for q in ps(g.intersection(base.buffer(-.6)))if q.area>=minarea and not q.buffer(-1).is_empty])
def write_json(path,d):path.write_text(json.dumps(d,ensure_ascii=False))
class Kit:
 def __init__(self,key,title,base,layers):
  self.key=key;self.title=title;self.path=P/key;self.path.mkdir(exist_ok=True);(self.path/'data').mkdir(exist_ok=True)
  self.layers=layers;self.pieces=[];self.labels=[];self.markers=[];self.busy=[];self.failed=[];self.regions=[]
  for i,g in enumerate(layers):
   for j,p in enumerate(sorted(ps(g),key=lambda p:-p.area)):
    self.pieces.append({'id':f'L{i+1:02d}_P{j+1:03d}','tier':i+1,'geom':mapping(set_precision(p,.00001)),'area_mm2':p.area,'regions':[key],'red_internal':mapping(LineString()),'engraving':mapping(Polygon())})
  for r in self.pieces:
   r['_g']=shape(r['geom']);r['_visible']=r['_g'].difference(layers[r['tier']] if r['tier']<len(layers)else Polygon());r['_eng']=[]
 def label(self,text,target,kind='city',territory=None,sizes=None,maxdistance=14):
  x,y=target;words=[word_geom(line)for line in text.split('\n')];width=max(g.bounds[2]-g.bounds[0]for g in words);textlines=[];shapes=[]
  for i,(line,g)in enumerate(zip(text.split('\n'),words)):
   xx=(width-(g.bounds[2]-g.bounds[0]))/2-g.bounds[0];yy=i*1.30;textlines.append({'text':line,'x_em':xx,'y_em':yy});shapes.append(translate(g,xx,yy))
  raw=unary_union(shapes);sizes=sizes or ([2.35,2.15,1.95,1.8]if kind=='city'else [3.2,2.8,2.5]if kind=='region'else [6,5,4]);best=None
  own=territory if territory is not None else self.layers[0];point=Point(x,y)
  # Only natural faces of this island/region may receive the caption.
  surfaces=[]
  for r in self.pieces:
   surface=polygonal(r['_visible'].intersection(own)).buffer(-.25)
   if surface.is_empty or point.distance(surface)>maxdistance:continue
   surfaces.append((r,surface))
  if not surfaces:self.failed.append({'text':text,'reason':'no sufficiently large visible surface'});return False
  for tilt in [0,-30,30,-50,50,-70,70,90]:
   for size in sizes:
    ink=rotate(scale(raw,xfact=size,yfact=size,origin=(0,0)),tilt,origin=(0,0));frame=rotate(scale(box(*raw.bounds),xfact=size,yfact=size,origin=(0,0)),tilt,origin=(0,0));b=ink.bounds;w=b[2]-b[0];h=b[3]-b[1]
    for r,surface in surfaces:
     anchor=nearest_points(point,surface)[1];candidates=[]
     if kind=='city':
      for dist in [1.2,2.5,4,6,9,12]:
       for angle in [0,180,90,270,45,135,225,315]:
        a=math.radians(angle);cx=anchor.x+math.cos(a)*(w/2+dist);cy=anchor.y+math.sin(a)*(h/2+dist);candidates.append((cx,cy))
      for oy in np.arange(-maxdistance,maxdistance+.1,1.2):
       for ox in np.arange(-maxdistance-w*.4,maxdistance+w*.4+.1,1.2):
        if abs(oy)+abs(ox)>maxdistance+w*.4:continue
        candidates.append((anchor.x+ox,anchor.y+oy))
     else:
      candidates.extend([(x,y),tuple(surface.representative_point().coords)[0]])
      for p in sorted(ps(surface),key=lambda p:-p.area)[:4]:
       bx=p.bounds
       for fy in [.25,.4,.55,.7]:
        for fx in [.25,.4,.55,.7]:candidates.append((bx[0]+fx*(bx[2]-bx[0]),bx[1]+fy*(bx[3]-bx[1])))
      for oy in np.arange(-maxdistance,maxdistance+.1,1.5):
       for ox in np.arange(-maxdistance,maxdistance+.1,1.5):
        if abs(ox)+abs(oy)<maxdistance:candidates.append((x+ox,y+oy))
     for cx,cy in candidates:
      if math.hypot(cx-x,cy-y)>maxdistance+w*.55:continue
      dx=cx-(b[0]+b[2])/2;dy=cy-(b[1]+b[3])/2;ink2=translate(ink,dx,dy);bbox=translate(frame,dx,dy).buffer(.22,join_style=2)
      if not surface.covers(bbox)or any(bbox.intersects(q)for q in self.busy):continue
      penalty=math.hypot(cx-x,cy-y)+((max(sizes)-size)*12)+abs(tilt)*.025
      if best is None or penalty<best[0]:best=(penalty,r,size,dx,dy,ink2,bbox,anchor,tilt)
    if best:break
   if best:break
  if best is None:self.failed.append({'text':text,'reason':'caption would collide or cross a terrace/coast'});return False
  _,r,size,dx,dy,ink,bbox,anchor,tilt=best;ang=math.radians(tilt);ident=f'TEXT_{len(self.labels)+1:03d}';color='#0000ff'if kind=='country'else '#ff0000'
  self.labels.append({'id':ident,'text':text,'kind':kind,'piece':r['id'],'color':color,'font_size_mm':size,'matrix':[math.cos(ang),math.sin(ang),-math.sin(ang),math.cos(ang),dx,dy],'lines':textlines,'outline_for_validation':mapping(ink)});r['_eng'].append(ink);self.busy.append(bbox)
  if kind=='city':
   dot=anchor.buffer(.22,quad_segs=8)
   if r['_visible'].covers(dot)and not any(dot.buffer(.15).intersects(q)for q in self.busy):
    self.markers.append({'id':ident+'_DOT','piece':r['id'],'point':[anchor.x,anchor.y]});r['_eng'].append(dot);self.busy.append(dot.buffer(.4))
  return True
 def admin(self,features):
  # Unique shared boundaries only; no doubled coastlines and no lines under upper plies.
  geoms=[g for name,g in features];network=[]
  for i,g in enumerate(geoms):
   for h in geoms[:i]:network.extend(ls(g.boundary.intersection(h.boundary)))
  network=unary_union(network).simplify(.25,preserve_topology=True);self.regions=[name for name,g in features]
  for r in self.pieces:
   lines=ls(network.intersection(r['_visible'].buffer(-.30)))
   clean=unary_union(lines);clean=linemerge(clean)if clean.geom_type=='MultiLineString'else clean
   r['red_internal']=mapping(clean)
 def save(self,notes):
  for r in self.pieces:
   protected=unary_union([shape(a['outline_for_validation']).envelope.buffer(.35)for a in self.labels if a['piece']==r['id']]);net=unary_union([l for l in ls(shape(r['red_internal']).difference(protected))if l.length>=.7]);r['red_internal']=mapping(net);r['_eng'].append(net.buffer(.045,quad_segs=3))
   r['engraving']=mapping(unary_union(r['_eng']).intersection(r['_visible']));r['paint']={};del r['_g'];del r['_eng'];del r['_visible']
  d={'title':self.title,'key':self.key,'layers':[mapping(g)for g in self.layers],'pieces':self.pieces,'labels':self.labels,'city_markers':self.markers,'country_names':{self.key:self.title},'colors':{'NATURAL':[.72,.53,.31]},'regions':self.regions,'summary':[{'tier':i+1,'pieces':sum(r['tier']==i+1 for r in self.pieces)}for i in range(len(self.layers))],'notes':notes,'omitted_labels':self.failed}
  # Use exactly the approved Russia/Asia + Africa/Europe manufacturing XY scale.
  # The world overview applies the same atlas registration to old and new kits.
  reg=json.load(open(P/'data/world-registration.json'))['russia-asia']['affine'];s=reg[0];tx,ty=reg[4:];inv=[1/s,0,0,1/s,-tx/s,-ty/s]
  d['layers']=[mapping(affine_transform(shape(g),inv))for g in d['layers']]
  for r in d['pieces']:
   for key in ['geom','engraving','red_internal']:r[key]=mapping(affine_transform(shape(r[key]),inv))
   r['area_mm2']/=s*s
  for a in d['labels']:
   a['font_size_mm']/=s;a['matrix'][4]=(a['matrix'][4]-tx)/s;a['matrix'][5]=(a['matrix'][5]-ty)/s;a['outline_for_validation']=mapping(affine_transform(shape(a['outline_for_validation']),inv))
  for m in d['city_markers']:m['point']=[(m['point'][0]-tx)/s,(m['point'][1]-ty)/s];m['radius_mm']=.22/s
  d['production_frame']='Approved combined Russia/Asia and Africa/Europe manufacturing frame';d['atlas_registration_xy']=reg
  write_json(self.path/'data/production-plan.json',d);print(self.key,len(self.pieces),'pieces',len(self.labels),'captions',self.regions,'omitted:',[x['text']for x in self.failed],flush=True)
  return d

def au():
 base=smooth(shape(C['AUS']['geom']),.40,.20,10);mid=terrace(base,220,100,2.8);top=terrace(base,650,65,2.1).intersection(mid.buffer(-1));layers=[base,mid,top];k=Kit('03-Australia','Австралия',base,layers)
 adm=json.load(open(P/'data/source/admin-reference.geojson'));groups={};names={'Western Australia':'Западная Австралия','Northern Territory':'Северная территория','South Australia':'Южная Австралия','Queensland':'Квинсленд','New South Wales':'Новый Южный Уэльс','Victoria':'Виктория','Tasmania':'Тасмания','Australian Capital Territory':'АСТ'}
 for f in adm['features']:
  n=f['properties']['name']
  if f['properties'].get('adm0_a3')!='AUS' or n not in names:continue
  g=transform(project,shape(f['geometry']));groups[n]=polygonal(g.intersection(base))
 features=[(names[n],g)for n,g in groups.items()];k.admin(features)
 for text,lon,lat in [('Канберра',149.13,-35.28),('Перт',115.86,-31.95),('Брум',122.24,-17.96),('Джералдтон',114.61,-28.77),('Калгурли',121.47,-30.75),('Дарвин',130.84,-12.46),('Алис-Спрингс',133.88,-23.70),('Аделаида',138.60,-34.93),('Порт-Огаста',137.77,-32.49),('Мельбурн',144.96,-37.81),('Сидней',151.21,-33.87),('Брисбен',153.03,-27.47),('Кэрнс',145.77,-16.92),('Таунсвилл',146.82,-19.26),('Рокгемптон',150.51,-23.38),('Хобарт',147.33,-42.88),('Лонсестон',147.14,-41.44)]:k.label(text,project(lon,lat),maxdistance=12)
 k.label('АВСТРАЛИЯ',project(133,-25),'country',maxdistance=80)
 for n,g in features:
  if g.area<100:continue
  text=n.replace('Австралия','\nАвстралия').replace('Северная территория','Северная\nтерритория').replace('Новый Южный Уэльс','Новый Южный\nУэльс');pt=g.representative_point();k.label(text,(pt.x,pt.y),'region',g,maxdistance=35,sizes=[3,2.5,2,1.7])
 return k.save('Три слоя 3/6/9 мм. Основные штаты/территории нанесены гравировкой только на открытые поверхности. Рельеф стилизован по NOAA ETOPO10; мелкие выступы и изолированные возвышенности удалены. ACT отмечена Канберрой из-за малого размера.')
def grl():
 base=smooth(shape(C['GRL']['geom']),.6,.28,15);main=max(ps(base),key=lambda g:g.area)
 # Connected expressive domed ice cap; no arbitrary bedrock depressions under the ice.
 mid=smooth(main.buffer(-14),2,.35,200);mid=max(ps(mid),key=lambda g:g.area)
 top=smooth(main.buffer(-34),3,.40,200);top=max(ps(top),key=lambda g:g.area)
 # Width is limited for translation-only placement of all three plies on a 740 mm sheet.
 if top.bounds[2]-top.bounds[0]>145:top=scale(top,xfact=145/(top.bounds[2]-top.bounds[0]),yfact=1,origin='center')
 top=polygonal(top.intersection(mid.buffer(-2)));k=Kit('02-Greenland','Гренландия',base,[base,mid,top]);k.label('ГРЕНЛАНДИЯ',project(-41,74),'country',maxdistance=100)
 # Geographic coastal regions, not the obsolete pre-2018 municipal dataset.
 for text,lon,lat in [('Северная\nГренландия',-38,79),('Западная\nГренландия',-48,70),('Восточная\nГренландия',-29,72),('Южная\nГренландия',-44,64)]:k.label(text,project(lon,lat),'region',maxdistance=55,sizes=[3,2.6,2.2,1.8])
 for text,lon,lat in [('Нуук',-51.72,64.18),('Сисимиут',-53.67,66.94),('Илулиссат',-51.10,69.22),('Аасиаат',-52.87,68.71),('Какорток',-46.04,60.72),('Нарсак',-46.05,60.91),('Нанорталик',-45.24,60.14),('Маниитсок',-52.90,65.42),('Уумманнак',-52.13,70.68),('Упернавик',-56.15,72.79),('Каанаак',-69.22,77.47),('Тасиилак',-37.64,65.61),('Иттоккортоормиит',-21.97,70.49)]:k.label(text,project(lon,lat),maxdistance=12)
 return k.save('Три монолитные ступени ледникового купола, 3/6/9 мм. Художественная модель поверхности льда, не карта высот подледного ложа. Подписи четырёх географических зон; историческая муниципальная сетка Qaasuitsup не использована, чтобы не выдавать её за современную.')
def islands():
 inv=json.load(open(P/'data/island-inventory.json'));inv=[r for r in inv if r['area_mm2']>=18 and not shape(r['geom']).buffer(-1.1).is_empty];baseparts=[];midparts=[];topparts=[];entries=[]
 # Source island names are indexed by original country component; never depend on sorting.
 arctic={78:'Элсмир',82:'Баффинова Земля',10:'Виктория',52:'Аксель-Хейберг',58:'Девон',9:'Банкс',7:'Мелвилл',42:'Принца Уэльского',4:'Принс-Патрик',61:'Сомерсет',27:'Эллеф-Рингнес',35:'Батерст',71:'Саутгемптон',60:'Байлот',28:'Амунд-Рингнес',2:'Маккензи-Кинг',59:'Корнуоллис',0:'Борден'}
 name={'PNG':'ПАПУА — НОВАЯ ГВИНЕЯ','NZL':'НОВАЯ ЗЕЛАНДИЯ','CUB':'КУБА','DOM':'ДОМИНИКАНА','HTI':'ГАИТИ','JAM':'ЯМАЙКА','PRI':'ПУЭРТО-РИКО','NCL':'НОВАЯ КАЛЕДОНИЯ','SLB':'СОЛОМОНОВЫ О-ВА','FLK':'ФОЛКЛЕНДСКИЕ О-ВА'}
 for r in inv:
  g=smooth(shape(r['geom']),.28,.16,12)
  for p in ps(g):
   if p.area<18:continue
   baseparts.append(p);entries.append((r,p))
   if p.area>450:
    mid=polygonal(terrace(p,300,38,1.7).intersection(p.buffer(-2.8)));midparts.extend(ps(mid))
    if p.area>1500 or r['code']=='PNG':topparts.extend(ps(terrace(p,950,45,1.7).intersection(mid.buffer(-.7))))
 base=unary_union(baseparts);mid=unary_union(midparts);top=unary_union(topparts);k=Kit('01-Islands','Острова',base,[base,mid,top]);used=set()
 cities=[('Икалуит',-68.52,63.75),('Кеймбридж-Бей',-105.06,69.12),('Сакс-Харбор',-125.25,71.99),('Грис-Фьорд',-82.90,76.42),('Гавана',-82.37,23.11),('Кингстон',-76.79,17.97),('Порт-о-Пренс',-72.34,18.54),('Санто-Доминго',-69.93,18.49),('Сан-Хуан',-66.11,18.47),('Порт-\nМорсби',147.18,-9.44),('Лаэ',146.99,-6.72),('Маданг',145.79,-5.22),('Окленд',174.76,-36.85),('Веллингтон',174.78,-41.29),('Крайстчерч',172.64,-43.53),('Данидин',170.50,-45.87),('Нумеа',166.45,-22.27)]
 city_island={
 'Икалуит':('CAN',82),'Кеймбридж-Бей':('CAN',10),'Сакс-Харбор':('CAN',9),'Грис-Фьорд':('CAN',78),
 'Гавана':('CUB',1),'Кингстон':('JAM',0),'Порт-о-Пренс':('HTI',0),'Санто-Доминго':('DOM',0),'Сан-Хуан':('PRI',0),
 'Порт-\nМорсби':('PNG',4),'Лаэ':('PNG',4),'Маданг':('PNG',4),'Окленд':('NZL',0),'Веллингтон':('NZL',0),'Крайстчерч':('NZL',1),'Данидин':('NZL',1),'Нумеа':('NCL',1)}
 for text,lon,lat in cities:
  code,idx=city_island[text];territory=ps(shape(C[code]['geom']))[idx]
  if k.label(text,project(lon,lat),territory=territory,maxdistance=8,sizes=[2.0,1.8,1.65,1.5]):k.labels[-1]['source_country']=code;k.labels[-1]['source_component']=idx
 for r,g in entries:
  text=arctic.get(r['source_component']) if r['code']=='CAN'else name.get(r['code'])
  if r['code']=='NZL':text='СЕВЕРНЫЙ\nОСТРОВ'if r['source_component']==0 else 'НОВАЯ\nЗЕЛАНДИЯ'
  if r['code']=='PNG':text='ПАПУА —\nНОВАЯ\nГВИНЕЯ'
  if r['code']=='NCL':text='НОВАЯ\nКАЛЕДОНИЯ'
  if r['code']=='FLK':text='ФОЛКЛЕНДСКИЕ\nОСТРОВА'
  if r['code']=='DOM':text='ДОМИНИ-\nКАНА'
  if text and text not in used:
   used.add(text);p=g.representative_point();kind='country'if r['code']not in ['CAN','FLK']and not(r['code']=='NZL'and r['source_component']==0)else 'region';k.label(text,(p.x,p.y),kind,g,sizes=[3.2,2.6,2.1,1.8,1.5]if g.area>150 else[1.8,1.6,1.5],maxdistance=25)
  if r['code']=='PNG'and r['source_component']==2:k.label('Новая Британия',tuple(g.representative_point().coords)[0],'region',g,sizes=[1.8,1.6])
 return k.save('Только недостающие острова: острова из утверждённых Евразии, России и Африки не продублированы. Берега сглажены; площадь отдельного острова от 18 мм², верхних деталей от 38–45 мм². Никаких искусственных перемычек между разными островами. Мелкие острова однослойные, крупные — до трёх слоёв. Масштаб исходного атласа сохранён.')
if __name__=='__main__':
 for f in [au,grl,islands]:f()
