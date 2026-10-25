import json,csv
from pathlib import Path
from shapely.geometry import shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from lxml import etree as E
P=Path(__file__).resolve().parent
if P.name=='tools':P=P.parent
D=json.load(open(P/'terrain-geometry.json'));old=json.load(open(P/'data/source-relief.json'));M=D['mm_per_unit'];objects=json.load(open(P/'model-data.json'))['objects'];SVG='http://www.w3.org/2000/svg'
def ps(g):
 if g.geom_type=='Polygon':return [g] if not g.is_empty and g.area>1e-8 else []
 return [p for q in getattr(g,'geoms',[]) for p in ps(q)]
def path(r,g,id,color,stroke=False):
 d=' '.join('M'+' L'.join(f'{x:.6f},{y:.6f}' for x,y in list(q.coords)[:-1])+' Z' for p in ps(g) for q in [orient(p,-1).exterior,*orient(p,-1).interiors])
 if not d:return
 e=E.SubElement(r,'path',id=id,d=d,fill=color,attrib={'fill-rule':'nonzero'})
 if stroke:e.set('stroke','#654c35');e.set('stroke-width','.38')
def root():return E.Element('svg',nsmap={None:SVG},width='1600mm',height='1000mm',viewBox='0 0 4251.9685 2657.4803125')
def save(r,f):E.ElementTree(r).write(str(P/f),encoding='UTF-8',xml_declaration=True)
masters={}
for o in objects:
 if o['kind']=='wood':masters.setdefault((o['country'],o['tier']),[]).append(shape(o['geom']))
color=root()
for i in range(1,7):
 whole=unary_union([g for (c,t),pp in masters.items() if t==i for g in pp]);out=root();path(out,whole,f'L{i:02d}','#000');save(out,f'Слой-{i:02d}-резка.svg')
 for c in D['countries']:
  code=c['id'];g=unary_union(masters.get((code,i),[]));out=root();path(out,g,code+f'_L{i:02d}','#000');save(out,f'SVG-по-странам/{code}/Слой-{i:02d}.svg');v=shape(D['visible'][i-1]).intersection(shape(c['geom']));path(color,v,code+f'_L{i:02d}',D['palette'][code][1],True)
path(color,shape(D['seam']),'BORDER_ENGRAVING','#3a3028');save(color,'Южная-Америка-монолитная.svg')
comp=E.Element('svg',nsmap={None:SVG});x0,y0,x1,y1=shape(D['base']).bounds;span=x1-x0+65;comp.set('viewBox',f'0 0 {2*span} {y1-y0+100}');colors=['#aa8558','#bf9c6b','#cfb07d','#dec598','#ead8b1','#f2e5c9']
for panel,(doc,title) in enumerate([(old,'Было: 146 деталей'),(D,'Стало: 78 деталей')]):
 text=E.SubElement(comp,'text',x=str(panel*span+20),y='28',fill='#46372a',attrib={'font-family':'Noto Sans','font-size':'23'});text.text=title
 group=E.SubElement(comp,'g',transform=f'translate({panel*span-x0+20},{60-y0})')
 for i,g in enumerate(doc['layers']):path(group,shape(g),f'C{panel}_L{i}',colors[i],True)
save(comp,'Сравнение-укрупнения.svg')
with (P/'Детали-по-странам.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f,lineterminator='\n');w.writerow(['Имя Blender','Страна','Слой','Площадь, мм²','Начало отсчёта']);w.writerows((o['id'],D['palette'][o['country']][0],o['tier'],round(shape(o['geom']).area*M*M,4),'Нижняя плоскость') for o in objects if o['kind']=='wood')
print('Finished closed vectors and comparison',flush=True)
