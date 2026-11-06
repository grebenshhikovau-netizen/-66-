import json,sys
from pathlib import Path
from lxml import etree as E
from shapely.geometry import shape
from shapely.geometry.polygon import orient
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'01-Islands/data/production-plan.json'));R=json.load(open(P/'data/island-roster.json'));NS='http://www.w3.org/2000/svg'
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in ps(q)]
def path(g):
 out=[]
 for p in ps(g):
  p=orient(p,-1)
  for ring in [p.exterior,*p.interiors]:out.append('M'+' L'.join(f'{x:.5f},{y:.5f}'for x,y in list(ring.coords)[:-1])+' Z')
 return ' '.join(out)
def text(parent,x,y,body,size=18,fill='#352c23'):
 t=E.SubElement(parent,'{'+NS+'}text',x=str(x),y=str(y),fill=fill,attrib={'font-family':'DejaVu Sans','font-size':str(size)});t.text=body
def atlas(entries,cols,cellw,cellh,out):
 rows=(len(entries)+cols-1)//cols;root=E.Element('{'+NS+'}svg',nsmap={None:NS},width=str(cols*cellw),height=str(rows*cellh+65),viewBox=f'0 0 {cols*cellw} {rows*cellh+65}')
 E.SubElement(root,'{'+NS+'}rect',width='100%',height='100%',fill='#f5f2eb');text(root,20,27,'Проверка подписей на самих деталях · схема не для резки',18)
 for j,r in enumerate(entries):
  x=(j%cols)*cellw;y=(j//cols)*cellh+45;g=shape(r['wood_geom']);b=g.bounds;s=min((cellw-32)/(b[2]-b[0]),(cellh-55)/(b[3]-b[1]));tx=x+(cellw-(b[2]-b[0])*s)/2-b[0]*s;ty=y+25+(cellh-55-(b[3]-b[1])*s)/2-b[1]*s
  E.SubElement(root,'{'+NS+'}rect',x=str(x+5),y=str(y+5),width=str(cellw-10),height=str(cellh-10),rx='8',fill='none',stroke='#d5cebf')
  text(root,x+14,y+22,f'{j+1:02d} · '+r['id'],12)
  gr=E.SubElement(root,'{'+NS+'}g',transform=f'matrix({s},0,0,{s},{tx},{ty})')
  for p in D['pieces']:
   if p.get('island_id')!=r['id']:continue
   E.SubElement(gr,'{'+NS+'}path',d=path(shape(p['geom'])),fill=['#e5c99e','#bda06c','#f0dbb4'][p['tier']-1],stroke='#59452b',attrib={'stroke-width':str(.65/s),'fill-rule':'evenodd'})
   E.SubElement(gr,'{'+NS+'}path',d=path(shape(p['engraving'])),fill='#352719',attrib={'fill-rule':'evenodd'})
  titles=[a for a in D['labels']if a.get('island_id')==r['id']and a.get('label_role')in['island_name','primary_island_name']]
  if not titles:text(root,x+14,y+cellh-16,'НЕТ ПОДПИСИ НА ДЕТАЛИ',13,'red')
 E.ElementTree(root).write(str(P/out),encoding='utf-8',xml_declaration=True)
atlas(R,7,260,275,'Острова-каталог-подписей.svg')
atlas([r for r in R if r['id']in ['ellesmere','baffin']],2,750,850,'Элсмир-и-Баффинова-проверка.svg')
print('PREVIEWS READY')
