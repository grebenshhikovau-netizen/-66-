"""Create connected inset lake cuts using 55% of local width, retaining long rift-lake shapes."""
import json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt
from skimage.morphology import skeletonize
from shapely.geometry import shape,Point,Polygon,mapping
from shapely.ops import unary_union
from shapely import make_valid,set_precision
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));coast=shape(json.load(open(P/'data/source/coast-reference.json')))
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty and g.area>1e-6 else[]
 return[p for a in getattr(g,'geoms',[])for p in ps(a)]
def valid(g):return set_precision(unary_union(ps(make_valid(g))),.001)
names=[k for k in D['upper_water']if k not in ['Нил','Конго','Замбези','Водопад Виктория']];old=unary_union([shape(D['base_water'][k])for k in names]);report=[]
for name in names:
 upper=shape(D['upper_water'][name]);x0,y0,x1,y1=upper.bounds;step=.06;ox=x0-.3;oy=y0-.3;im=Image.new('1',(math.ceil((x1-x0+.6)/step)+1,math.ceil((y1-y0+.6)/step)+1));dr=ImageDraw.Draw(im)
 for q in ps(upper):
  dr.polygon([((x-ox)/step,(y-oy)/step)for x,y in q.exterior.coords],fill=1)
  for ring in q.interiors:dr.polygon([((x-ox)/step,(y-oy)/step)for x,y in ring.coords],fill=0)
 a=np.array(im,dtype=np.uint8)>0;dist=distance_transform_edt(a)*step;yy,xx=np.where(skeletonize(a));disks=[Point(ox+int(x)*step,oy+int(y)*step).buffer(max(.16,float(dist[y,x])*.55),quad_segs=6)for x,y in zip(xx,yy)];narrow=valid(unary_union(disks).buffer(.08,quad_segs=6).buffer(-.08,quad_segs=6).simplify(.025,preserve_topology=True).intersection(upper.buffer(-.08)))
 assert not narrow.is_empty
 narrow=max(ps(narrow),key=lambda q:q.area);D['base_water'][name]=mapping(narrow);report.append({'feature':name,'upper_area_mm2':upper.area,'lower_area_mm2':narrow.area,'local_width_factor':.55,'lower_connected':True})
BB=valid(unary_union([shape(g)for g in D['base_water'].values()]));L0=valid(shape(D['layers'][0]).union(old.intersection(coast)).difference(BB));L0=valid(unary_union([g for g in ps(L0)if g.area>=D['parameters']['minimum_base_island_area_mm2']]));D['layers'][0]=mapping(L0);D['visible'][0]=mapping(valid(L0.difference(shape(D['layers'][1]))));D['water_base_union']=mapping(BB);pieces=[q for q in D['pieces']if q['tier']!=1]
for j,g in enumerate(sorted(ps(L0),key=lambda q:-q.area),1):pieces.append({'id':f'L01_P{j:03d}','tier':1,'geom':mapping(g),'visible':mapping(valid(g.difference(shape(D['layers'][1])))),'regions':[c for c,r in D['regions'].items()if shape(r).intersection(g).area>1],'paint':{},'engraving':mapping(Polygon()),'area_mm2':g.area})
D['pieces']=sorted(pieces,key=lambda q:q['id']);D['lake_profiles']=report
for s in D['summary']:
 pp=[shape(q['geom'])for q in D['pieces']if q['tier']==s['tier']];s['pieces']=len(pp);s['smoothed_vertices']=sum(len(r.coords)for p in pp for r in [p.exterior,*p.interiors]);s['smoothed_perimeter_mm']=sum(g.length for g in pp)
r=json.load(open(P/'Проверка-сглаживания-и-воды.json'));r.update({'lake_profiles':report,'layers':D['summary'],'physical_parts':len(pieces)});(P/'Проверка-сглаживания-и-воды.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));(P/'data/water-reference.json').write_text(json.dumps([{'name':'Оргстекло_под_водой_СПРАВОЧНО','geom':D['water_base_union']}],ensure_ascii=False));print('NARROW LAKES',report,'PARTS',len(pieces),flush=True)
