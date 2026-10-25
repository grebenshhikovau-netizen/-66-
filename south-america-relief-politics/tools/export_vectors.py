import json,csv
from pathlib import Path
from shapely.geometry import shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from lxml import etree as E
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data'/'compatibility.json'));S='http://www.w3.org/2000/svg'
def polygons(g):
 if g.geom_type=='Polygon':return [g] if not g.is_empty and g.area>1e-8 else []
 return [p for q in getattr(g,'geoms',[])for p in polygons(q)]
def root():return E.Element('svg',nsmap={None:S},width='1600mm',height='1000mm',viewBox='0 0 4251.9685 2657.4803125')
def path(r,g,id,fill,stroke=False):
 d=' '.join('M'+' L'.join(f'{x:.6f},{y:.6f}'for x,y in list(ring.coords)[:-1])+' Z'for pp in polygons(g)for p in [orient(pp,-1)]for ring in [p.exterior,*p.interiors])
 if not d:return
 e=E.SubElement(r,'path',id=id,d=d,fill=fill,attrib={'fill-rule':'nonzero'})
 if stroke:e.set('stroke','#3c3027');e.set('stroke-width','.15')
def save(r,name):
 q=P/name;q.parent.mkdir(parents=True,exist_ok=True);E.ElementTree(r).write(str(q),encoding='UTF-8',xml_declaration=True)
colored=root();cut=root();engraving=root();seam=shape(D['seam']);comparison=[]
for code,row in D['countries'].items():
 g=shape(row['geom']);assert g.is_valid;ink=seam.intersection(g);name,h,desc=D['palette'][code];path(colored,g,code,h,True);path(cut,g,code,'#000');path(engraving,ink,'BORDER_'+code,'#000');r=root();path(r,g,code,'#000');save(r,'SVG-политические/'+code+'/Резка.svg');r=root();path(r,ink,'BORDER_'+code,'#000');save(r,'SVG-политические/'+code+'/Гравировка.svg')
 comparison.append([code,name,desc,h,*row['origin'],row['base_id'],'POL_'+code+'__'+name])
path(colored,seam,'BORDERS','#352b26');save(colored,'Политическая-окраска.svg');save(cut,'Политическая-резка.svg');save(engraving,'Политическая-гравировка.svg')
with open(P/'Страны-и-совмещение.csv','w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f);w.writerow(['Код','Страна','Покрытие','sRGB','Центр X м','Центр Y м','Низ Z м','Основание рельефа','Плоская деталь']);w.writerows(comparison)
print('VECTORS',len(comparison),'modules',flush=True)
