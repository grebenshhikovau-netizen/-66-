"""Independent geographic relationships and country-coating checks."""
import json
from shapely.geometry import shape
from common import *
D=json.load(open(ROOT/'geometry.json'));R=json.load(open(DATA/'russia-reference.json'));w={k:shape(v) for k,v in D['waters'].items()};checks=[]
for a,b in [('Рейн','Боденское озеро'),('Рона','Женевское озеро'),('Или','Балхаш'),('Ганг','Брахмапутра'),('Тигр','Евфрат'),('Тигр','Шатт-эль-Араб'),('Евфрат','Шатт-эль-Араб')]:
 gap=w[a].distance(w[b])*M;assert gap<.001,(a,b,gap);checks.append({'a':a,'b':b,'gap_mm':gap})
for name in ['Иртыш','Амур']:
 gap=w[name].distance(shape(R['waters'][name]))*M;assert gap<.001;checks.append({'a':name,'b':'Россия: '+name,'gap_mm':gap})
assert w['Северный Арал'].distance(w['Южный Арал'])*M>1
assert {f['name'] for f in D['landmarks'] if f['kind']=='volcano'}<={f['name'] for f in D['craters']},'A required volcano lost its crater'
rr=D['regions'];conflicts=[];geoms={r['id']:unary_union(polys(shape(r['geom']))) for r in rr}
for i,a in enumerate(rr):
 for b in rr[i+1:]:
  if a['country']!=b['country'] and a['color']==b['color'] and geoms[a['id']].boundary.intersection(geoms[b['id']].boundary).length*M>.1:conflicts.append((a['id'],b['id']))
assert not conflicts,conflicts
for code,expected in json.load(open(DATA/'political-boundary-restoration.json'))['target_country_geometries'].items():
 actual=unary_union([shape(r['geom']) for r in rr if r['country']==code]);assert actual.intersection(shape(expected)).area/shape(expected).area>.98,('obscured country',code)
for country in {r['country'] for r in rr}:assert len({r['color'] for r in rr if r['country']==country})==1
obj=json.load(open(ROOT/'model-data.json'))['objects'];small=[{'object':o['id'],'area_mm2':o['area_mm2'],'tier':o['tier']} for o in obj if o['variant']=='relief' and o['area_mm2']<1]
dump('Малые-политические-детали.json',small);dump('Проверка-географии-и-покрытий.json',{'water_connections':checks,'north_and_south_aral_separate':True,'neighbor_country_color_conflicts':conflicts,'countries':len(set(r['country'] for r in rr)),'regions':len(rr),'coatings':len(set(r['color'] for r in rr)),'one_coating_per_country':True,'small_relief_pieces_below_1mm2':len(small),'named_landmarks':len(D['landmarks']),'restored_countries_cover_reference':True})
print('GEOGRAPHY VERIFIED',len(rr),'regions;',len(small),'small base/microstate parts',flush=True)
