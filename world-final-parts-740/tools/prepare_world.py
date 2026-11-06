"""Register approved assemblies to the original atlas; inventory missing islands."""
import json, math, os
from pathlib import Path
import numpy as np
from shapely.geometry import shape, mapping
from shapely.affinity import affine_transform
from shapely.ops import unary_union
P=Path(__file__).resolve().parent.parent;R=Path(os.environ.get('MAP_REPO',str(P.parent if (P.parent/'.git').exists() else '/workspace/-66-')))
C=json.load(open(P/'data/source/master-countries.json'));C={x['code']:x for x in C}
PROJ=json.load(open(P/'data/source/world-projection.json'))
def project(lon,lat):
 return PROJ['lon_to_x_mm']*np.asarray(lon)+PROJ['x_offset_mm'],PROJ['y_offset_mm']-PROJ['mercator_to_y_mm']*np.log(np.tan(np.pi/4+np.radians(lat)/2))
def polys(g):
 if g.geom_type=='Polygon':return [g] if not g.is_empty else []
 return [p for q in getattr(g,'geoms',[]) for p in polys(q)]
def fit(x,y):
 x=np.array(x);y=np.array(y);xc=x.mean(0);yc=y.mean(0);a=x-xc;b=y-yc
 u,s,v=np.linalg.svd(a.T@b);rot=u@v
 assert np.linalg.det(rot)>0
 scale=s.sum()/(a*a).sum();linear=scale*rot;t=yc-xc@linear;pred=x@linear+t
 return {'affine':[linear[0,0],linear[1,0],linear[0,1],linear[1,1],*t], 'rms_mm':float(np.sqrt(((pred-y)**2).sum(1).mean())), 'scale_xy':float(scale)}
source={
 'north-america':('canada-cutting-740/Канада-обновлённая-сборка.blend','canada-cutting-740/data/source/production-plan.json'),
 'south-america':('south-america-monolithic-single-740/Южная-Америка-производственная-сборка.blend','south-america-monolithic-single-740/data/production-plan.json'),
 'russia-asia':('combined-cutting-740/01-Россия-Азия/Сборка-комплекта.blend','combined-cutting-740/01-Россия-Азия/data/production-plan.json'),
 'africa-europe':('combined-cutting-740/02-Африка-Европа-Ближний-Восток/Сборка-комплекта.blend','combined-cutting-740/02-Африка-Европа-Ближний-Восток/data/production-plan.json')}
city={ 'Сан-Франциско':(-122.42,37.77),'Лос-Анджелес':(-118.24,34.05),'Вашингтон':(-77.04,38.91),'Нью-Йорк':(-74.01,40.71),'Майами':(-80.19,25.76),'Денвер':(-104.99,39.74),'Чикаго':(-87.63,41.88),'Бостон':(-71.06,42.36),'Ванкувер':(-123.12,49.28),'Оттава':(-75.70,45.42),'Монреаль':(-73.57,45.50),'Торонто':(-79.38,43.65),'Йеллоунайф':(-114.38,62.45),'Анкоридж':(-149.90,61.22),'Мехико':(-99.13,19.43),'Уайтхорс':(-135.06,60.72),'Фэрбанкс':(-147.72,64.84),'Ном':(-165.40,64.50)}
texts=json.load(open(R/'canada-cutting-740/data/live-text.json'));x=[];y=[]
for r in texts:
 if r['text'] in city:
  b=shape(r['outline_for_validation']).bounds;x.append([(b[0]+b[2])/2,(b[1]+b[3])/2]);y.append(project(*city[r['text']]))
T={'north-america':fit(x,y)}
ctrl=json.load(open(R/'south-america-monolithic-single-740/data/source/geographic-controls.json'));T['south-america']=fit([[r[3]*1600/4251.9685,r[4]*1600/4251.9685-1000] for r in ctrl],[project(r[1],r[2]) for r in ctrl])
q=json.load(open(R/'combined-cutting-740/data/source/world-projection.json'));m=q['mm_per_unit'];q=q['projection'];x=[];y=[]
for lon in [0,30,60,90,120,150]:
 for lat in [-30,0,30,60,75]:
  old=[m*(q['source_xmin']+(lon-q['lonmin'])*q['kx_per_degree']),m*(q['source_ymax']-(math.log(math.tan(math.pi/4+math.radians(lat)/2))-math.log(math.tan(math.pi/4+math.radians(q['latmin'])/2)))*q['ky_per_mercator'])-1000];x.append(old);y.append(project(lon,lat))
T['russia-asia']=fit(x,y);T['africa-europe']=T['russia-asia'].copy()
coverage=[];regions=set()
for key,(blend,plan) in source.items():
 d=json.load(open(R/plan));g=shape(d['layers'][0]);T[key].update({'blend_relative':blend,'plan_relative':plan,'base':mapping(affine_transform(g,T[key]['affine']))});coverage.append(shape(T[key]['base']));regions.update(d.get('regions',{}));print(key,T[key]['affine'],'RMS',T[key]['rms_mm'])
(P/'data/world-registration.json').write_text(json.dumps(T,ensure_ascii=False))
# Country parts which are already present in the east/west source must not be duplicated.
old_world=unary_union([g.simplify(.2) for g in coverage]).buffer(2)
world=unary_union([shape(x['geom']).simplify(.2).buffer(.40) for code,x in C.items() if code not in ['ATA','GRL','AUS']]);continents=sorted(polys(world),key=lambda p:-p.area)[:2];continental=unary_union(continents)
out=[];omitted=[]
for code,r in C.items():
 if code in ['GRL','AUS','ATA']:continue
 for idx,g in enumerate(polys(shape(r['geom']))):
  if continental.intersection(g).area/g.area>.97:continue
  # More exact exclusion by geographic footprint, buffered for harmless coastline warp.
  cover=old_world.intersection(g).area/g.area
  if cover>.55:continue
  # Established native components, such as Japanese and Indonesian islands, are already
  # authoritative even where small affine registration differences displace a coast.
  if code in ['JPN','IDN','PHL','TWN','LKA','GBR','IRL','ISL','MDG','RUS','NOR','SWE','FIN','ITA','GRC','ESP','DNK','CYP','CYN','MYS']:continue
  if g.area<5 or g.buffer(-.8).is_empty:omitted.append({'code':code,'area_mm2':g.area,'reason':'too small at original map scale'});continue
  out.append({'code':code,'source_component':idx,'name':r['name'],'geom':mapping(g),'area_mm2':g.area,'covered_fraction':cover})
out.sort(key=lambda x:-x['area_mm2']);(P/'data/island-inventory.json').write_text(json.dumps(out,ensure_ascii=False));(P/'data/omitted-small-islands.json').write_text(json.dumps(omitted,ensure_ascii=False,indent=2))
print('ISLAND CANDIDATES',len(out),'total area',sum(x['area_mm2']for x in out))
for x in out:print(x['code'],x['source_component'],round(x['area_mm2']),tuple(round(v,1)for v in shape(x['geom']).bounds),'covered',round(x['covered_fraction'],2))
