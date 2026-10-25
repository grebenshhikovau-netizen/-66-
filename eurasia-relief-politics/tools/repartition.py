"""Reclip an existing shared landscape after correcting political boundaries."""
import json
from shapely.geometry import shape,mapping,Point
from shapely.ops import unary_union
from common import *
D=json.load(open(ROOT/'geometry.json'));regions=json.load(open(DATA/'regions.json'));land=shape(D['pure_base']);L=[shape(g) for g in D['layers']];parts={};removed=[]
accents=[Point(f['x'],f['y']) for f in D['landmarks'] if f['kind'] in ['summit','volcano','rocks']]
for r in regions:
 g=polygonal(shape(r['geom'])).intersection(land);r['geom']=mapping(g);rr=[polygonal(layer.intersection(g)) for layer in L]
 for i in range(5,0,-1):
  keep=[]
  for p in polys(rr[i]):
   if p.area*M*M>=C['production']['political_min_upper_part_mm2'] or any(p.covers(q) for q in accents):keep.append(p)
   else:removed.append({'region':r['id'],'tier':i+1,'area_mm2':p.area*M*M})
  rr[i]=unary_union(keep)
  rr[i-1]=unary_union([rr[i-1],rr[i]])
 baseparts=polys(rr[0]);largest=max(baseparts,key=lambda p:p.area) if baseparts else None
 rr[0]=unary_union([p for p in baseparts if p is largest or p.area*M*M>=C['production']['political_min_base_scrap_mm2'] or p.intersection(rr[1]).area*M*M>.001])
 parts[r['id']]=rr
L=[unary_union([rr[i] for rr in parts.values()]) for i in range(6)]
D['regions']=regions;D['region_layers']={k:[mapping(g) for g in gg] for k,gg in parts.items()};D['layers']=[mapping(g) for g in L];D['base']=mapping(L[0]);D['visible']=[mapping(L[i].difference(L[i+1]) if i<5 else L[i]) for i in range(6)];dump('geometry.json',D)
dump('Дополнительное-укрупнение-стыков.json',{'small_upper_pieces_lowered':len(removed),'details':removed,'named_accent_centers_preserved':True,'min_upper_mm2':C['production']['political_min_upper_part_mm2']})
report=json.load(open(ROOT/'Проверка-геометрии.json'));counts=[sum(len(polys(rr[i])) for rr in parts.values()) for i in range(6)];report['parts_after_political_split_by_level']=counts;report['parts_after_political_split']=sum(counts);report['political_countries_restored']=['NPL','BTN','ARM','AZE','KWT'];dump('Проверка-геометрии.json',report)
print('REPARTITIONED',counts,'TOTAL',sum(counts),'SMALL UPPER REMOVED',len(removed),flush=True)
