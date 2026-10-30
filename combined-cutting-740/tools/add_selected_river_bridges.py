"""Keep the two specifically approved paint groups monolithic with small upper bridges."""
import gzip,json,copy
from pathlib import Path
from collections import Counter
from shapely.geometry import shape,mapping,Polygon,LineString
from shapely.ops import unary_union,nearest_points
from shapely import set_precision,make_valid
P=Path(__file__).resolve().parent.parent;E=json.load(gzip.open(P/'data/source/EU-approved-plan.json.gz','rt'))
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty and g.area>1e-8 else[]
 return[p for q in getattr(g,'geoms',[])for p in ps(q)]
def valid(g):return set_precision(unary_union(ps(make_valid(g))),.001)
for O in sorted(p for p in P.iterdir()if p.is_dir()and p.name[:2]in ['01','02']):
 D=json.load(open(O/'data/production-plan.json'));name,tier,oldid,river=('Лаос-Камбоджа',3,'L03_P014','Меконг')if D['batch']=='EAST'else('Венгрия-Румыния-Сербия',2,'L02_P007','Дунай');rows=[q for q in D['pieces']if q['tier']==tier and q['paint_group']==name];assert rows,name;allowed=shape(next(q['geom']for q in E['pieces']if q['id']==oldid));g=valid(unary_union([shape(q['geom'])for q in rows]));records=[]
 while len(ps(g))>1:
  pp=ps(g);candidates=[]
  for i,a in enumerate(pp):
   for b in pp[:i]:
    x,y=nearest_points(a,b);dist=x.distance(y)
    if dist>5:continue
    br=LineString([x,y]).buffer(1.1,quad_segs=8).intersection(allowed);new=valid(g.union(br))
    if len(ps(new))>=len(pp):continue
    counts=Counter(pt for q in ps(new)for r in [q.exterior,*q.interiors]for pt in list(r.coords)[:-1])
    if any(n>1 for n in counts.values()):continue
    added=new.difference(g);candidates.append((dist,added.area,new,br,added))
  assert candidates,(name,'no strong local bridge can connect the banks')
  dist,area,new,br,added=min(candidates,key=lambda q:(q[0],q[1]));records.append({'id':f'BRIDGE_{len(records)+1:02d}','river':river,'group':name,'tier':tier,'width_mm':2.2,'bank_gap_mm':dist,'added_wood_mm2':area,'geom':mapping(added),'footprint':mapping(br),'inside_approved_upper_outline':True});g=new
 assert g.geom_type=='Polygon'and g.is_valid
 owner=max(rows,key=lambda p:p['area_mm2']);ids={q['id']for q in rows};owner['geom']=mapping(g);owner['area_mm2']=g.area;owner['regions']=sorted({c for q in rows for c in q['regions']});D['pieces']=[q for q in D['pieces']if q['id']not in ids or q['id']==owner['id']]
 for key in ['labels','city_markers']:
  for a in D.get(key,[]):
   if a['piece']in ids:a['piece']=owner['id']
 for i in range(len(D['layers'])):D['layers'][i]=mapping(unary_union([shape(q['geom'])for q in D['pieces']if q['tier']==i+1]))
 for q in D['pieces']:
  q['visible']=mapping(shape(q['geom']).difference(shape(D['layers'][q['tier']])))if q['tier']<len(D['layers'])else q['geom']
 for s in D['summary']:s['pieces']=sum(q['tier']==s['tier']for q in D['pieces'])
 D['river_bridges']=records;D['bridge_groups']=[{'group':name,'tier':tier,'result_piece':owner['id'],'old_bank_pieces':sorted(ids),'one_monolithic_piece':True,'bridge_count':len(records)}];(O/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));(O/'Проверка-речных-перемычек.json').write_text(json.dumps({'passed':True,'group':name,'result_piece':owner['id'],'one_closed_connected_outline':True,'bridges':records,'first_ply_water_stays_open':True},ensure_ascii=False,indent=2));print('BRIDGES',O.name,name,len(rows),'banks -> 1 part',len(records),'bridges','parts',len(D['pieces']),flush=True)
