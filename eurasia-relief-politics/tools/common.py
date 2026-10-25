import json, math
from pathlib import Path
import numpy as np
from lxml import etree as E
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, transform
from shapely import make_valid, set_precision

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'data'
C=json.load(open(DATA/'config.json')); M=C['mm_per_unit']; PR=C['projection']
MC=math.log(math.tan(math.pi/4+math.radians(PR['latmin'])/2))
SVG='http://www.w3.org/2000/svg'
def xy(x,y):
 x=np.asarray(x); y=np.clip(np.asarray(y),-85,85)
 return PR['source_xmin']+(x-PR['lonmin'])*PR['kx_per_degree'],PR['source_ymax']-(np.log(np.tan(np.pi/4+np.deg2rad(y)/2))-MC)*PR['ky_per_mercator']
def project(g):return make_valid(transform(lambda x,y,z=None:xy(x,y),g))
def polys(g):
 if g.geom_type=='Polygon':return [g] if not g.is_empty and g.area>1e-5 else []
 return [p for c in getattr(g,'geoms',[]) for p in polys(c)]
def polygonal(g):return set_precision(unary_union(polys(make_valid(g))),.001)
def clean(g,area=0,join=0,neck=0,simplify=None,holes=0):
 g=polygonal(g)
 if join:g=g.buffer(join/M).buffer(-join/M)
 if neck:g=g.buffer(-neck/2/M).buffer(neck/2/M)
 if simplify is not None:g=g.simplify(simplify/M,preserve_topology=True)
 return unary_union([Polygon(p.exterior,[r.coords for r in p.interiors if Polygon(r).area*M*M>=holes]) for p in polys(g) if p.area*M*M>=area])
def dpath(g):
 return ' '.join('M'+' L'.join(f'{x:.6f},{y:.6f}' for x,y in list(r.coords)[:-1])+' Z' for p in polys(g) for r in [orient(p,-1).exterior,*orient(p,-1).interiors])
def svgroot():return E.Element('svg',nsmap={None:SVG},width='1600mm',height='1000mm',viewBox='0 0 4251.9685 2657.4803125')
def svgpath(root,g,id,fill,**kwargs):
 if not polys(g):return
 return E.SubElement(root,'path',id=id,d=dpath(g),fill=fill,attrib={'fill-rule':'nonzero',**{k.replace('_','-'):str(v) for k,v in kwargs.items()}})
def savesvg(root,name):
 target=ROOT/name;target.parent.mkdir(exist_ok=True,parents=True);E.ElementTree(root).write(str(target),encoding='UTF-8',xml_declaration=True)
def dump(name,data):
 p=ROOT/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(data,ensure_ascii=False))
