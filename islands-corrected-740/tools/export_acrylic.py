"""Acrylic engraving in assembled geographic placement; this is not a nesting sheet."""
import json,csv,math
from pathlib import Path
from lxml import etree as E
from shapely.geometry import shape
from shapely.geometry.polygon import orient
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/acrylic-engraving.json'));R=json.load(open(P/'data/island-roster.json'));T=json.load(open(P/'data/world-registration.json'))['russia-asia']['affine'];s=T[0];NS='http://www.w3.org/2000/svg'
x0,y0=(-120-T[4])/s,-T[5]/s;w,h=2240/s,1370/s
root=E.Element('{'+NS+'}svg',nsmap={None:NS},width=f'{w:.6f}mm',height=f'{h:.6f}mm',viewBox=f'{x0:.9f} {y0:.9f} {w:.9f} {h:.9f}',version='1.1')
E.SubElement(root,'{'+NS+'}title').text='Мелкие острова: гравировка на оргстекле в общей географической расстановке'
E.SubElement(root,'{'+NS+'}desc').text='Красный — гравировка. Сквозных резов нет. Схема согласована с общей сборкой; это файл географического размещения, не раскладка 740 × 740 мм. Величина мелкого знака увеличена до читаемой гравировочной точки.'
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in ps(q)]
paths=[]
for p in ps(shape(D['geom'])):
 p=orient(p,-1)
 for ring in [p.exterior,*p.interiors]:paths.append('M'+' L'.join(f'{x:.6f},{y:.6f}'for x,y in list(ring.coords)[:-1])+' Z')
E.SubElement(root,'{'+NS+'}path',id='ENGRAVE_ACRYLIC_MINOR_ISLANDS',d=' '.join(paths),fill='none',stroke='#ff0000',attrib={'stroke-width':'.08','stroke-linejoin':'round','stroke-linecap':'round'})
E.ElementTree(root).write(str(P/'Мелкие-острова-гравировка-оргстекла.svg'),encoding='utf-8',xml_declaration=True)
with(P/'Реестр-увеличений.csv').open('w',encoding='utf-8-sig',newline='')as f:
 writer=csv.writer(f,lineterminator='\n');writer.writerow(['Остров / архипелаг','Страна','Локальное увеличение','Увеличение группы','Итоговое увеличение силуэта','Смещение X мм в схеме','Смещение Y мм в схеме','Исходная долгота','Исходная широта'])
 for r in R:writer.writerow([r['name'],r['country'],round(r['local_scale'],3),r['cluster_scale'],round(r['local_scale']*r['cluster_scale'],3),round(r['display_shift_mm'][0]/s,2),round(r['display_shift_mm'][1]/s,2),r['lon'],r['lat']])
print('ACRYLIC SVG READY',len(D['islands']),'minor source islands')
