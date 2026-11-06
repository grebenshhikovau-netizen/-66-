"""Optional translation-only 740 mm engraving sections, with open clipped strokes.
Clip the coastline itself, never a filled polygon: no artificial closure at a tile edge.
"""
import json,math,csv
from pathlib import Path
from lxml import etree as E
from shapely.geometry import shape,box
from shapely.affinity import translate
from shapely.ops import unary_union
P=Path(__file__).resolve().parent.parent;g=shape(json.load(open(P/'data/acrylic-engraving.json'))['geom']).boundary;out=P/'Гравировка-участки-740';out.mkdir(exist_ok=True);b=g.bounds;x0=b[0]-2;y0=b[1]-2;pitch=730;ns='http://www.w3.org/2000/svg';report=[];reconstructed=[]
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[g]if g.length>1e-9 else[]
 return[l for q in getattr(g,'geoms',[])for l in lines(q)]
for row in range(math.ceil((b[3]-y0+2)/pitch)):
 for col in range(math.ceil((b[2]-x0+2)/pitch)):
  x=x0+col*pitch;y=y0+row*pitch;part=g.intersection(box(x,y,x+pitch,y+pitch))
  if part.is_empty:continue
  file=f'Гравировка-{row+1:02d}-{col+1:02d}-740.svg';root=E.Element('{'+ns+'}svg',nsmap={None:ns},width='740mm',height='740mm',viewBox='0 0 740 740');E.SubElement(root,'{'+ns+'}title').text=f'Гравировка на оргстекле: ряд {row+1}, колонка {col+1}; только красный'
  paths=[]
  for line in lines(translate(part,5-x,5-y)):paths.append('M'+' L'.join(f'{xx:.6f},{yy:.6f}'for xx,yy in line.coords))
  E.SubElement(root,'{'+ns+'}path',d=' '.join(paths),fill='none',stroke='#ff0000',attrib={'stroke-width':'.08','stroke-linecap':'round','stroke-linejoin':'round'})
  E.ElementTree(root).write(str(out/file),encoding='utf-8',xml_declaration=True);reconstructed.append(part);report.append({'file':file,'row':row+1,'column':col+1,'geographic_active_origin_mm':[x,y],'stock_mm':[740,740],'active_area_mm':[730,730],'margin_mm':5,'rotation':0,'scale':1})
joined=unary_union(reconstructed);assert g.difference(joined.buffer(.000001)).length<.001;assert joined.difference(g.buffer(.000001)).length<.001
(P/'data/acrylic-740-sections.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
with(out/'Положение-участков.csv').open('w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f,lineterminator='\n');w.writerow(['Файл','Ряд','Колонка','Начало X общей схемы, мм','Начало Y общей схемы, мм','Поле, мм','Рабочая зона, мм'])
 for r in report:w.writerow([r['file'],r['row'],r['column'],*r['geographic_active_origin_mm'],'740 × 740','730 × 730'])
(out/'ПРОЧТИ-МЕНЯ.txt').write_text('Гравировка мелких островов по участкам 740 × 740 мм. Это не раскрой фанеры. Только красные линии, без сквозного реза. Рабочая зона 730 × 730 мм, отступ 5 мм. Участки идут слева направо, сверху вниз. Координаты каждой зоны в общей географической схеме приведены в CSV. Размеры и ориентация сохранены; при переходе между зонами совмещать положение по общей схеме. Никаких замыкающих линий на краях зон не добавлено.\n')
print('ACRYLIC SECTIONS',len(report),'all original coast strokes retained; no artificial edge closures')
