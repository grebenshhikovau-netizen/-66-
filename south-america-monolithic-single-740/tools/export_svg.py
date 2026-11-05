"""One kit; each editable physical part keeps its cuts, engraving and live text together."""
import json,csv
from pathlib import Path
from lxml import etree as E
from shapely.geometry import shape
from shapely.geometry.polygon import orient
from shapely import set_precision
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));L=json.load(open(P/'data/layout.json'));S='http://www.w3.org/2000/svg'
root=E.Element('{'+S+'}svg',nsmap={None:S},width='740mm',height='740mm',viewBox='0 0 740 740',version='1.1')
def polygons(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in polygons(q)]
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[g]if g.length>.001 else[]
 return[l for q in getattr(g,'geoms',[])for l in lines(q)]
def path(g):
 out=[]
 for p in polygons(set_precision(g,.000001)):
  p=orient(p,-1)
  for ring in [p.exterior,*p.interiors]:
   out.append('M'+' L'.join(f'{x:.6f},{y:.6f}'for x,y in list(ring.coords)[:-1])+' Z')
 return ' '.join(out)
layers={i:E.SubElement(root,'{'+S+'}g',id=f'LAYER_{i:02d}')for i in [1,2,3]}
loc={p['source_id']:p for p in L['placements']}
for r in D['pieces']:
 p=loc[r['id']];g=E.SubElement(layers[r['tier']],'{'+S+'}g',id=r['id'],transform=f"translate({p['dx_mm']:.9f},{p['dy_mm']:.9f})")
 E.SubElement(g,'{'+S+'}title').text=f"Слой {r['tier']} / {r['id']} / "+', '.join(D['country_names'][c]for c in r['regions'])
 dd=' '.join('M'+' L'.join(f'{x:.6f},{y:.6f}'for x,y in l.coords)for l in lines(shape(r['red_internal'])))
 if dd:E.SubElement(g,'{'+S+'}path',id=r['id']+'_ENGRAVE',d=dd,fill='none',stroke='#ff0000',attrib={'stroke-width':'.05','stroke-linecap':'round','stroke-linejoin':'round'})
 for a in D['labels']:
  if a['piece']!=r['id']:continue
  e=E.SubElement(g,'{'+S+'}text',id=r['id']+'_'+a['id'],fill=a.get('color','#0000ff'),stroke='none',attrib={
   'font-family':'Open Sans Light','font-size':f"{a['font_size_mm']:.9f}",'font-weight':'300','font-kerning':'none',
   'style':"font-kerning:none;font-feature-settings:'kern' 0",'transform':'matrix('+','.join(f'{v:.12f}'for v in a['matrix'])+')'})
  for ln in a['lines']:E.SubElement(e,'{'+S+'}tspan',x=f"{ln['x_em']*a['font_size_mm']:.9f}",y=f"{ln['y_em']*a['font_size_mm']:.9f}").text=ln['text']
 for m in D['city_markers']:
  if m['piece']==r['id']:
   x,y=m['point'];E.SubElement(g,'{'+S+'}circle',id=r['id']+'_'+m['id'],cx=f'{x:.6f}',cy=f'{y:.6f}',r='.22',fill='#ff0000',stroke='none')
 E.SubElement(g,'{'+S+'}path',id=r['id']+'_CUT',d=path(shape(r['geom'])),fill='none',stroke='#000000',attrib={'stroke-width':'.05','stroke-linejoin':'round'})
E.ElementTree(root).write(str(P/'Поле-01-740x740.svg'),encoding='utf-8',xml_declaration=True)
with (P/'Детали-и-слои.csv').open('w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f);w.writerow(['Деталь','Слой','Страны','Площадь мм²','Перенос X мм','Перенос Y мм'])
 for r in D['pieces']:
  p=loc[r['id']];w.writerow([r['id'],r['tier'],', '.join(D['country_names'][c]for c in r['regions']),round(r['area_mm2'],2),p['dx_mm'],p['dy_mm']])
print('SVG EXPORTED',len(D['pieces']),'parts',len(D['labels']),'texts',flush=True)
