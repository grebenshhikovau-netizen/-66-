"""Unify the accepted South America relief while retaining its political masks."""
import json,math,csv,shutil
from pathlib import Path
import numpy as np
from scipy.interpolate import RBFInterpolator
from shapely.geometry import shape,mapping,Polygon
from shapely.ops import unary_union,transform
from shapely import make_valid
from lxml import etree as E
P=Path(__file__).resolve().parent
if P.name=='tools':P=P.parent
DATA=P/'data';DATA.mkdir(exist_ok=True)
if not (DATA/'source-relief.json').exists():
 for a,b in [('terrain-geometry.json','source-relief.json'),('geographic-controls.json','geographic-controls.json'),('geographic-features.json','geographic-features.json')]:shutil.copy2(Path('/workspace/output/south-america')/a,DATA/b)
D=json.load(open(DATA/'source-relief.json'));old=[shape(g) for g in D['layers']];m=D['mm_per_unit'];base=old[0];F=json.load(open(DATA/'geographic-features.json'));controls=json.load(open(DATA/'geographic-controls.json'));warp=RBFInterpolator(np.array([[c[1],c[2]] for c in controls]),np.array([[c[3],c[4]] for c in controls]),kernel='thin_plate_spline',smoothing=1.8)
def project(g):
 def fn(x,y,z=None):
  a=warp(np.column_stack([np.atleast_1d(x),np.atleast_1d(y)]));return a[:,0],a[:,1]
 return make_valid(transform(fn,g))
def ps(g):
 if g.geom_type=='Polygon':return [g] if not g.is_empty and g.area>1e-8 else []
 return [p for c in getattr(g,'geoms',[]) for p in ps(c)]
def poly(g):return unary_union(ps(make_valid(g)))
major=[];fine=[]
for f in F['rivers']:
 name=f['name'];g=shape(f['geom']);q=g.centroid
 if name in ['Amazonas','Madeira'] or name=='Negro' and q.y>-5 and q.x<-55:major.append(project(g).buffer((.675 if name=='Amazonas' else .425)/m))
 elif name in ['Tapajós','Xingu','Ucayali','Marañón']:fine.append(project(g).buffer(.06/m))
river=unary_union(major).intersection(base);fine=unary_union(fine).intersection(base)
zones=[shape(f['geom']).buffer(.7/m) for f in D['landmarks']];zones += [project(shape(f['geom'])).buffer(.4/m) for f in F['lakes']];protected=unary_union(zones).intersection(base)
radius=[0,4,6,5,4,3];minimum=[0,80,130,100,55,22];L=[old[0]]
for i in range(1,6):
 g=old[i].buffer(radius[i]/m).buffer(-radius[i]/m).buffer(-.65/m).buffer(.65/m).simplify(.16/m,preserve_topology=True)
 g=unary_union([p for p in ps(g) if p.area*m*m>=minimum[i]])
 g=unary_union([g.difference(protected),old[i].intersection(protected)]).intersection(base)
 incision=river.difference(old[i+1].buffer(.25/m)) if i<5 else river
 g=poly(g.difference(incision));keep=[]
 for p in ps(g):
  if p.area*m*m>=minimum[i] or p.intersection(protected).area*m*m>.05:keep.append(p)
 L.append(unary_union(keep))
for i in range(5,0,-1):L[i-1]=poly(unary_union([L[i-1],L[i]]))
assert L[0].symmetric_difference(old[0]).area<1e-6
countries=[shape(c['geom']) for c in D['countries']];before=[sum(len(ps(g.intersection(c))) for c in countries) for g in old];after=[sum(len(ps(g.intersection(c))) for c in countries) for g in L]
for i,g in enumerate(L):
 assert g.is_valid
 if i:assert g.difference(L[i-1]).area*m*m<1e-5
for landmark in D['landmarks']:
 zone=shape(landmark['geom'])
 for a,b in zip(old,L):assert a.intersection(zone).symmetric_difference(b.intersection(zone)).area*m*m<.01,(landmark['name'],'lost feature')
D['layers']=[mapping(g) for g in L];D['visible']=[mapping(L[i].difference(L[i+1]) if i<5 else L[i]) for i in range(6)];D['variant']='monolithic';D['fine_rivers_engraving']=mapping(fine)
(P/'terrain-geometry.json').write_text(json.dumps(D,ensure_ascii=False));report={'before_country_parts':before,'after_country_parts':after,'before_total':sum(before),'after_total':sum(after),'global_parts_before':[len(ps(g)) for g in old],'global_parts_after':[len(ps(g)) for g in L],'base_unchanged':True,'political_partition_unchanged':True,'palette_unchanged':True,'named_landmarks_preserved':[f['name'] for f in D['landmarks']],'main_rivers_kept_as_recesses':['Амазонка','Мадейра','Риу-Негру'],'fine_tributaries_engraving':True,'closing_mm':radius,'min_area_mm2':minimum}
(P/'Проверка-укрупнения.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(report,flush=True)
S='http://www.w3.org/2000/svg'
def root():return E.Element('svg',nsmap={None:S},width='1600mm',height='1000mm',viewBox='0 0 4251.9685 2657.4803125')
def path(r,g,id,color):
 from shapely.geometry.polygon import orient
 d=' '.join('M'+' L'.join(f'{x:.6f},{y:.6f}' for x,y in list(ring.coords)[:-1])+' Z' for p in ps(g) for ring in [orient(p,-1).exterior,*orient(p,-1).interiors])
 if d:E.SubElement(r,'path',id=id,d=d,fill=color,attrib={'fill-rule':'nonzero'})
def save(r,name):E.ElementTree(r).write(str(P/name),encoding='UTF-8',xml_declaration=True)
color=root();comparison=root()
for i,g in enumerate(L,1):
 r=root();path(r,g,f'L{i:02d}','#000');save(r,f'Слой-{i:02d}-резка.svg')
 e=root();path(e,shape(D['seam']).intersection(shape(D['visible'][i-1])),f'BORDERS_L{i}','#000');path(e,fine.intersection(shape(D['visible'][i-1])),f'RIVERS_L{i}','#000');save(e,f'Гравировка-слой-{i:02d}.svg')
 for c in D['countries']:
  cg=shape(c['geom']);code=c['id'];path(color,shape(D['visible'][i-1]).intersection(cg),f'{code}_L{i}',D['palette'][code][1]);part=root();path(part,g.intersection(cg),f'{code}_L{i}','#000');sub=P/'SVG-по-странам'/code;sub.mkdir(parents=True,exist_ok=True);E.ElementTree(part).write(str(sub/f'Слой-{i:02d}.svg'),encoding='UTF-8',xml_declaration=True)
path(color,shape(D['seam']),'BORDERS','#3a3028');save(color,'Южная-Америка-монолитная.svg')
with (P/'Сравнение-деталей.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f,lineterminator='\n');w.writerow(['Слой','Высота, мм','Было деталей по странам','Стало']);w.writerows((i+1,(i+1)*3,before[i],after[i]) for i in range(6))
