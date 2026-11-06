"""Independent checks of emitted CNC geometry, SVG, captions and placement."""
import json,math,re
from pathlib import Path
from lxml import etree as E
from shapely.geometry import shape,box,Polygon
from shapely.ops import unary_union
from shapely.affinity import translate,affine_transform
P=Path(__file__).resolve().parent.parent
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in ps(q)]
C={x['code']:x for x in json.load(open(P/'data/source/master-countries.json'))};report=[]
for key in ['01-Islands','02-Greenland','03-Australia']:
 d=json.load(open(P/key/'data/production-plan.json'));layout=json.load(open(P/key/'data/layout.json'));loc={x['source_id']:x for x in layout['placements']};geom={x['id']:shape(x['geom'])for x in d['pieces']};placed=[];nodes=0;maxlabelerr=0
 assert len(loc)==len(geom)and layout['kits']==1 and layout['stock_mm']==[740,740]
 for r in d['pieces']:
  g=geom[r['id']];assert g.is_valid and g.geom_type=='Polygon'and g.area>0
  assert abs(g.area-r['area_mm2'])<.02
  nodes+=len(g.exterior.coords)+sum(len(q.coords)for q in g.interiors)
  for ring in [g.exterior,*g.interiors]:assert ring.is_ring and ring.is_simple
  if r['tier']>1:assert g.difference(shape(d['layers'][r['tier']-2])).area<.02
  visible=g.difference(shape(d['layers'][r['tier']])if r['tier']<3 else Polygon())
  assert shape(r['red_internal']).difference(visible.buffer(.0001)).length<.001
  assert shape(r['engraving']).difference(visible.buffer(.0001)).area<.001
  p=loc[r['id']];assert p['rotation_degrees']==0 and p['mirrored']is False and p['scale']==1
  q=translate(g,p['dx_mm'],p['dy_mm']);assert box(5,5,735,735).covers(q)
  for old in placed:assert q.distance(old)>=3
  placed.append(q)
 for tier in [1,2,3]:
  gg=[geom[r['id']]for r in d['pieces']if r['tier']==tier]
  assert sum(g.area for g in gg)-unary_union(gg).area<.01
 for a in d['labels']:
  r=next(x for x in d['pieces']if x['id']==a['piece']);g=geom[a['piece']];v=g.difference(shape(d['layers'][r['tier']])if r['tier']<3 else Polygon());ink=shape(a['outline_for_validation']);err=ink.difference(v).area;maxlabelerr=max(maxlabelerr,err);assert err<.0001,(key,a['text'],err)
  assert a['color']==('#0000ff'if a['kind']=='country'else'#ff0000')
  assert not ink.intersects(shape(r['red_internal']).buffer(.1)),(key,a['text'],'crosses a border')
  if 'source_country'in a:
   source=ps(shape(C[a['source_country']]['geom']))[a['source_component']];reg=d['atlas_registration_xy'];s=reg[0];inv=[1/s,0,0,1/s,-reg[4]/s,-reg[5]/s];allowed=affine_transform(source,inv);assert ink.difference(allowed).area<.0001,(a['text'],'wrong island/country')
 root=E.parse(str(P/key/'Поле-01-740x740.svg')).getroot();ns={'s':'http://www.w3.org/2000/svg'}
 assert root.get('width')=='740mm'and root.get('height')=='740mm'
 texts=root.xpath('//s:text',namespaces=ns);assert len(texts)==len(d['labels']);assert not root.xpath('//s:image',namespaces=ns)
 cuts=root.xpath('//s:path[@stroke="#000000"]',namespaces=ns);assert len(cuts)==len(d['pieces'])
 for cut in cuts:
  data=cut.get('d');assert data.strip().endswith('Z')and data.count('M')==data.count('Z')
  for ring in re.findall(r'M([^MZ]+) Z',data):
   xy=[tuple(map(float,v.split(',')))for v in ring.split(' L')];q=Polygon(xy);assert q.is_valid and q.area>1e-8,(key,cut.get('id'),'invalid emitted ring')
 for a,t in zip(d['labels'],sorted(texts,key=lambda x:int(re.search(r'TEXT_(\d+)',x.get('id')).group(1)))):
  assert '\n'.join(t.itertext())==a['text']
 report.append({'kit':key,'physical_pieces':len(geom),'layers':d['summary'],'city_captions':sum(a['kind']=='city'for a in d['labels']),'total_editable_texts':len(texts),'cutting_vertices':nodes,'stock_mm':[740,740],'sheets':1,'kits':1,'translation_only':True,'minimum_gap_mm':layout['actual_min_gap_mm'],'all_cut_rings_valid':True,'captions_on_exposed_surfaces':True,'cities_on_correct_islands':True,'border_text_collisions':0})
(P/'Проверка-раскроя.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
