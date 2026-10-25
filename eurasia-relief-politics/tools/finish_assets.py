"""Manufacturing masks and source-preservation checks for the completed build."""
import csv,json,hashlib
from collections import defaultdict
from shapely.geometry import shape
from shapely.ops import unary_union
from lxml import etree as E
from common import *

D=json.load(open(ROOT/'geometry.json'));countries=defaultdict(list)
MODEL=json.load(open(ROOT/'model-data.json'));masters=defaultdict(list)
for ob in MODEL['objects']:
 if ob['variant']!='reference':masters[(ob['variant'],ob['region'],ob['tier'])].append(shape(ob['geom']))
RU=json.load(open(DATA/'russia-reference.json'));assembly=svgroot();political=svgroot();wet=svgroot()
for i,g in enumerate(RU['layers'],1):svgpath(assembly,shape(g),f'RUSSIA_REFERENCE_L{i:02d}',RU['palette'][f'L{i}'][1])
for r in D['regions']:
 svgpath(political,shape(r['geom']),r['id'],r['color'],stroke='#493a2d',stroke_width='.22')
 svgpath(wet,unary_union(masters[('political_water',r['id'],1)]),r['id'],r['color'],stroke='#493a2d',stroke_width='.22')
 for i,g in enumerate(D['visible'],1):svgpath(assembly,shape(g).intersection(shape(r['geom'])),r['id']+f'_L{i:02d}',r['color'],stroke='#493a2d',stroke_width='.3')
savesvg(assembly,'Евразия-рельеф-цветной.svg');savesvg(political,'Евразия-политическая.svg');savesvg(wet,'Евразия-политическая-с-водой.svg')
for r in D['regions']:countries[r['country']].append(r)
for code,rr in countries.items():
 g=unary_union([shape(r['geom']) for r in rr]);out=svgroot()
 svgpath(out,g,'PAINT_'+code,rr[0]['color']);savesvg(out,'Маски-покрытия/'+code+'.svg')
 assert len({r['color'] for r in rr})==1
guide=E.parse(str(ROOT/'Евразия-рельеф-цветной.svg')).getroot()
for i,f in enumerate(D['landmarks'],1):
 E.SubElement(guide,'circle',cx=str(f['x']),cy=str(f['y']),r='6',fill='#f5e9d1',stroke='#352c24',attrib={'stroke-width':'.7'})
 t=E.SubElement(guide,'text',x=str(f['x']),y=str(f['y']+2.6),fill='#352c24',attrib={'font-size':'7','font-family':'Noto Sans','text-anchor':'middle'});t.text=str(i)
savesvg(guide,'Схема-природных-объектов.svg')
for region,gg in D['region_layers'].items():
 for i,g in enumerate(gg,1):
  g=unary_union(masters[('relief',region,i)])
  p=ROOT/'SVG-по-регионам'/region/f'Слой-{i:02d}.svg'
  if not polys(g):
   if p.exists():p.unlink()
  else:
   out=svgroot();svgpath(out,g,region+f'_L{i:02d}','#000');savesvg(out,str(p.relative_to(ROOT)))
 for variant,folder in [('political','Политические-SVG'),('political_water','Политические-SVG-с-водой')]:
  out=svgroot();svgpath(out,unary_union(masters[(variant,region,1)]),region,'#000');savesvg(out,f'{folder}/{region}.svg')

# The closed module contours above are the editable masters. These auxiliary
# common-line cuts remove duplicate shared national/provincial boundaries.
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return [g]
 return [p for q in getattr(g,'geoms',[]) for p in lines(q)]
for i in range(6):
 edges=unary_union([g.boundary for (variant,region,tier),pp in masters.items() if variant=='relief' and tier==i+1 for g in pp]);out=svgroot()
 for j,line in enumerate(lines(edges)):
  E.SubElement(out,'path',id=f'CUT_{j}',d='M'+' L'.join(f'{x:.6f},{y:.6f}' for x,y in line.coords),fill='none',stroke='#000',attrib={'stroke-width':'.12'})
 savesvg(out,f'Резка-без-дублей/Слой-{i+1:02d}.svg')
 whole=unary_union([g for (variant,region,tier),pp in masters.items() if variant=='relief' and tier==i+1 for g in pp]);out=svgroot();svgpath(out,whole,f'GLOBAL_L{i+1:02d}','#000');savesvg(out,f'Общий-рельеф-слой-{i+1:02d}.svg')
 out=svgroot()
 for r in D['regions']:svgpath(out,unary_union(masters[('relief',r['id'],i+1)]),r['id']+f'_L{i+1:02d}',r['color'])
 savesvg(out,f'Слой-{i+1:02d}-по-политическим-регионам.svg')
 out=svgroot();svgpath(out,shape(D['texture']).intersection(shape(D['visible'][i])),f'DUNES_L{i+1:02d}','#000')
 for j,crater in enumerate(D['craters']):
  if crater['tier']==i+1:svgpath(out,shape(crater['geom']),f'CRATER_{j}','#000')
 savesvg(out,f'Гравировка-уровень-{i+1:02d}.svg')
out=svgroot();svgpath(out,shape(D['water']),'THROUGH_WATER','#000');savesvg(out,'Реки-и-озёра-сквозные.svg')
counts=[]
for i in range(1,7):
 pp=[g for (variant,region,tier),gg in masters.items() if variant=='relief' and tier==i for g in gg];whole=unary_union(pp)
 counts.append({'tier':i,'height_mm':i*3,'parts_before_political_split':len(polys(whole)),'area_mm2':whole.area*M*M,'physical_parts':len(pp)})
report=json.load(open(ROOT/'Проверка-геометрии.json'));report['global_layer_counts']=counts;report['parts_after_political_split_by_level']=[r['physical_parts'] for r in counts];report['parts_after_political_split']=sum(r['physical_parts'] for r in counts);dump('Проверка-геометрии.json',report)
with (ROOT/'Состав-слоёв.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f,lineterminator='\n');w.writerow(['Слой','Верх, мм','Объединённых природных массивов','Физических политических деталей']);w.writerows((r['tier'],r['height_mm'],r['parts_before_political_split'],r['physical_parts']) for r in counts)

protected=json.load(open(DATA/'protected-existing-files.json'));repo=next((p for p in [ROOT.parent,ROOT.parent.parent/'-66-'] if all((p/n).is_file() for n in protected)),None)
if repo:
 unchanged=[name for name,digest in protected.items() if hashlib.sha256((repo/name).read_bytes()).hexdigest()==digest]
 assert len(unchanged)==len(protected),'Existing Russia/Africa files were modified'
 dump('Проверка-сохранности-материков.json',{'verified_sha256_files':len(unchanged),'all_unchanged':True})
else:print('Source-preservation audit skipped: original continent folders are absent in this standalone copy',flush=True)
print('PAINT MASKS',len(countries),'PHYSICAL RELIEF PARTS',sum(r['physical_parts'] for r in counts),flush=True)
