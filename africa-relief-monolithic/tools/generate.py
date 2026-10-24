"""Manufacturing alternative: broad Africa terraces with fewer separate plywood pieces."""
import json,gzip,csv,copy
from pathlib import Path
from shapely.geometry import shape,mapping,Polygon
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
from lxml import etree as E
P=Path(__file__).resolve().parent;OUT=P.parent if P.name=='tools' else P;DATA=OUT/'data';D=json.load(gzip.open(DATA/'detailed-relief.json.gz','rt',encoding='utf-8'));m=D['mm_per_unit'];old=[shape(g) for g in D['layers']];egypt=shape(D['egypt_pyramid']['country']);water=shape(D['water']);rift=shape(D['rift']);falls=shape(D['waters']['Водопад Виктория']);kili=shape(D['kili_cap']);main=shape(D['mainland']);mad=shape(D['madagascar']);texture=shape(D['texture'])
def polys(g):
 if g.geom_type=='Polygon':return [g] if g.area>1e-8 else []
 return [p for c in getattr(g,'geoms',[]) for p in polys(c)]
# Millimetres are physical dimensions on the 1600 mm world-map page.
closing_mm=[0,2,5,5,3,0];minimum_area_mm2=[0,30,180,160,65,40];layers=[old[0]]
for i in range(1,6):
 g=old[i].difference(egypt)
 g=g.buffer(closing_mm[i]/m).buffer(-closing_mm[i]/m).buffer(-.5/m).buffer(.5/m).simplify(.22/m,preserve_topology=True)
 barrier=water
 if i>=2:barrier=unary_union([water,rift if i==2 else rift.buffer(1/m),falls.buffer(1/m)])
 g=g.intersection(old[0]).difference(barrier).difference(egypt)
 g=unary_union([p for p in polys(g) if p.area*m*m>=minimum_area_mm2[i]])
 # Preserve these deliberate accents, rather than filtering them as incidental small hills.
 kili_support=unary_union([p for p in polys(old[i]) if p.intersection(kili).area>1e-7])
 g=unary_union([g,kili_support,old[i].intersection(egypt)]).intersection(old[0]).difference(barrier)
 layers.append(g)
# Every upper terrace has a continuous supporting footprint on the preceding level.
for i in range(5,1,-1):layers[i-1]=unary_union([layers[i-1],layers[i]])
# Remove the redundant nodes introduced by closing and unions. Keep the source Nile
# apertures and exact Egypt footprint, and then restore support nesting.
refined=[layers[0]]
for i,g in enumerate(layers[1:],1):
 g=g.simplify(.10/m,preserve_topology=True).intersection(old[0]).difference(water)
 refined.append(unary_union([g.difference(egypt),old[i].intersection(egypt)]))
for i in range(5,1,-1):refined[i-1]=unary_union([refined[i-1],refined[i]])
layers=refined
visible=[layers[i].difference(layers[i+1]) if i<5 else layers[i] for i in range(6)]
S='http://www.w3.org/2000/svg';colors=[D['palette'][f'L{i}'][1] for i in range(1,7)]
def dpath(g):return ' '.join('M'+' L'.join(f'{x:.6f},{y:.6f}' for x,y in list(r.coords)[:-1])+' Z' for p in polys(g) for r in [orient(p,-1).exterior,*orient(p,-1).interiors])
def root():return E.Element('svg',nsmap={None:S},width='1600mm',height='1000mm',viewBox='0 0 4251.9685 2657.4803125')
def path(r,g,name,color,**kw):
 if not polys(g):return
 return E.SubElement(r,'path',id=name,d=dpath(g),fill=color,attrib={'fill-rule':'nonzero',**{k.replace('_','-'):str(v) for k,v in kw.items()}})
def write(r,n):E.ElementTree(r).write(str(OUT/n),encoding='UTF-8',xml_declaration=True)
assembly=root();plain=root();guide=root()
for i,g in enumerate(layers,1):
 for region,area,prefix in [('AFR',main,'Слой'),('MAD',mad,'Опция-Мадагаскар-слой')]:
  r=root();path(r,g.intersection(area),f'{region}_L{i:02d}','#000');write(r,f'{prefix}-{i:02d}-резка.svg')
 for r in [assembly,plain,guide]:path(r,g,f'L{i:02d}',colors[i-1],stroke='#6c5032',stroke_width='.48')
 r=root();path(r,texture.intersection(visible[i-1]),f'TEXTURE_L{i:02d}','#715134');write(r,f'Фактура-гравировка-уровень-{i}.svg')
path(assembly,texture,'Фактура','#826746');write(assembly,'Африка-монолитная.svg');write(plain,'Африка-монолитная-слои.svg')
r=root();path(r,water,'WATER_APERTURES','#000');write(r,'Сквозные-вырезы-реки-и-озёра.svg');r=root();path(r,texture,'TEXTURE','#000');write(r,'Фактура-гравировка-все.svg')
for i,p in enumerate(D['places'],1):
 E.SubElement(guide,'circle',cx=str(p['x']),cy=str(p['y']),r='5.5',fill='#f5eddc',stroke='#73472d',attrib={'stroke-width':'.6'});t=E.SubElement(guide,'text',x=str(p['x']),y=str(p['y']+2.4),fill='#4b3224',attrib={'font-size':'7','font-family':'sans-serif','text-anchor':'middle'});t.text=str(i)
write(guide,'Схема-природных-объектов.svg')
# Comparison uses the same scale in both panels and includes separate connected pieces at every height.
xmin,ymin,xmax,ymax=shape(D['source_outline']).bounds;span=xmax-xmin+70;hh=ymax-ymin+110
comparison=E.Element('svg',nsmap={None:S},viewBox=f'0 0 {span*2} {hh}')
counts_before=[len(polys(g)) for g in old];counts_after=[len(polys(g)) for g in layers]
for panel,(stack,title) in enumerate([(old,f'Детальный: {sum(counts_before)} детали'),(layers,f'Укрупнённый: {sum(counts_after)} детали')]):
 t=E.SubElement(comparison,'text',x=str(panel*span+25),y='30',fill='#46372a',attrib={'font-family':'sans-serif','font-size':'23'});t.text=title
 group=E.SubElement(comparison,'g',transform=f'translate({panel*span-xmin+25},{65-ymin})')
 for i,g in enumerate(stack):path(group,g,f'COMPARE_{panel}_{i}',colors[i],stroke='#6c5032',stroke_width='.45')
write(comparison,'Сравнение-детальности.svg')
def nodes(g):return sum(len(p.exterior.coords)+sum(len(r.coords) for r in p.interiors) for p in polys(g))
rows=[]
for i,(a,b) in enumerate(zip(old,layers),1):
 assert b.is_valid and not b.is_empty
 if i>1:assert b.difference(layers[i-2]).area<1e-7
 assert b.intersection(water).area<1e-7
 assert b.intersection(egypt).symmetric_difference(a.intersection(egypt)).area<1e-7
 rows.append({'tier':i,'before_parts':len(polys(a)),'after_parts':len(polys(b)),'before_nodes':nodes(a),'after_nodes':nodes(b),'mainland_parts':len(polys(b.intersection(main))),'madagascar_parts':len(polys(b.intersection(mad)))})
assert layers[0].symmetric_difference(old[0]).area<1e-8
assert kili.intersection(layers[5]).area*m*m>1
D['layers']=[mapping(g) for g in layers];D['visible']=[mapping(g) for g in visible];D['variant']='manufacturing_monolithic';D['manufacturing_parameters']={'closing_mm':closing_mm,'minimum_area_mm2':minimum_area_mm2,'outer_contour_simplify_mm':.22,'final_node_simplify_mm':.10,'protected_accents':['Egypt pyramid','Kilimanjaro'],'unchanged_base':True}
(OUT/'terrain-geometry.json').write_text(json.dumps(D,ensure_ascii=False))
report={'separate_alternative':True,'source_parts':sum(counts_before),'monolithic_parts':sum(counts_after),'reduction_percent':100*(1-sum(counts_after)/sum(counts_before)),'all_valid':True,'all_nested':True,'all_water_through':True,'base_unchanged':True,'egypt_pyramid_unchanged':True,'kilimanjaro_present':True,'before_nodes':sum(nodes(g) for g in old),'after_nodes':sum(nodes(g) for g in layers),'before_cut_length_mm':sum(g.length*m for g in old),'after_cut_length_mm':sum(g.length*m for g in layers),'layers':rows}
(OUT/'Проверка-укрупнения.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
with (OUT/'Сравнение-количества-деталей.csv').open('w',encoding='utf-8-sig',newline='') as f:
 c=csv.writer(f,lineterminator='\n');c.writerow(['Слой','Высота, мм','Было деталей','Стало деталей','Было узлов','Стало узлов','Материк','Мадагаскар']);c.writerows((v['tier'],v['tier']*3,v['before_parts'],v['after_parts'],v['before_nodes'],v['after_nodes'],v['mainland_parts'],v['madagascar_parts']) for v in rows)
with (OUT/'Природные-объекты.csv').open('w',encoding='utf-8-sig',newline='') as f:
 c=csv.writer(f,lineterminator='\n');c.writerow(['Номер','Название','Долгота','Широта']);c.writerows((i,p['name'],p['lon'],p['lat']) for i,p in enumerate(D['places'],1))
print('MONOLITHIC',counts_before,'→',counts_after,'TOTAL',sum(counts_before),'→',sum(counts_after),'NODES',report['before_nodes'],'→',report['after_nodes'],flush=True)
