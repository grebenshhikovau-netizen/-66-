"""Independently parse serialized cuts, single strokes, fills, colors and guides."""
import json,re,hashlib
from pathlib import Path
from lxml import etree as E
from shapely.geometry import Polygon,LineString,shape,box
from shapely.ops import unary_union
from shapely.affinity import translate
from pypdf import PdfReader
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/manufacturing.json'));N=json.load(open(P/'data/layout.json'));source=json.load(open(P/'data/source/production-plan.json'));original={q['id']:shape(q['geom'])for q in source['pieces']};A=json.load(open(P/'data/annotations.json'));locations={q['id']:q for q in N['placements']};report=[]
def rings(d):
 out=[]
 for seq in re.findall(r'M([^M]+)',d):
  v=[float(x)for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',seq)];out.append(list(zip(v[::2],v[1::2])))
 return out
def parse_fill(d):
 exteriors=[];holes=[]
 for ring in rings(d):
  a=sum(x*y2-x2*y for(x,y),(x2,y2)in zip(ring,ring[1:]+ring[:1]))/2
  (exteriors if a<0 else holes).append(ring)
 outer=[Polygon(r)for r in exteriors];assigned={i:[]for i in range(len(outer))}
 for h in holes:
  point=Polygon(h).representative_point();owners=[i for i,g in enumerate(outer)if g.covers(point)];assert owners
  assigned[min(owners,key=lambda i:outer[i].area)].append(h)
 return unary_union([Polygon(r,assigned[i])for i,r in enumerate(exteriors)])
def parse_stroke(d):return unary_union([LineString(r)for r in rings(d)if len(r)>1])
for si in sorted(set(q['sheet']for q in D['pieces'])):
 tree=E.parse(str(P/f'Поле-{si:02d}-740x740.svg'));root=tree.getroot();assert root.get('width')==root.get('height')=='740mm';assert root.get('viewBox')=='0 0 740 740';assert not root.xpath('//*[@transform]');assert not root.xpath('//*[local-name()="text" or local-name()="image"]')
 paths={p.get('id'):p for p in root.xpath('//*[local-name()="path"]')};cuts={};colors=set();textcount=0;markcount=0;bluecount=0;errors=[];lineerrors=[]
 for id,path in paths.items():
  color=path.get('stroke')or path.get('fill');colors.add(color)
  if id.endswith('_CUT'):
   assert color=='#000000' and path.get('fill')=='none' and path.get('d').rstrip().endswith('Z');cuts[id[:-4]]=parse_fill(path.get('d'))
 assert colors=={'#000000','#ff0000','#0000ff'}
 for part in [q for q in D['pieces']if q['sheet']==si]:
  id=part['id'];loc=locations[id];assert loc['rotation_degrees']==0 and not loc['mirrored'];g=cuts[id];expected=translate(original[part['source_id']],loc['dx_mm'],loc['dy_mm']);ee=g.symmetric_difference(expected).area;assert ee<.001;errors.append(ee);assert g.is_valid and box(5,5,735,735).covers(g)
  for aid,geom in part['red_strokes'].items():
   el=paths[id+'_'+aid];assert el.get('stroke')=='#ff0000' and el.get('fill')=='none';assert el.get('data-engraving')=='centerline';assert 'Z'not in el.get('d');actual=parse_stroke(el.get('d'));expected=shape(geom);err=actual.hausdorff_distance(expected);assert err<.000002,(aid,err);lineerrors.append(err);assert actual.difference(g.buffer(.025)).length<.03;textcount+=1
  for aid,geom in part['red_marks'].items():
   el=paths[id+'_'+aid];assert el.get('fill')=='#ff0000'and el.get('stroke')is None;actual=parse_fill(el.get('d'));assert actual.symmetric_difference(shape(geom)).area<.001;markcount+=1
  for aid,geom in part['blue'].items():
   assert aid in {'TEXT_043','TEXT_050','TEXT_063','TEXT_081'};el=paths[id+'_'+aid];assert el.get('fill')=='#0000ff'and el.get('stroke')is None;actual=parse_fill(el.get('d'));assert actual.symmetric_difference(shape(geom)).area<.001;bluecount+=1
  if not shape(part['red_internal']).is_empty:
   el=paths[id+'_INTERNAL'];assert el.get('stroke')=='#ff0000'and el.get('fill')=='none';assert 'Z'not in el.get('d');assert parse_stroke(el.get('d')).hausdorff_distance(shape(part['red_internal']))<.000002
  # Guides are evaluated in source assembly coordinates, not sheet coordinates.
  upper=unary_union([shape(q['geom'])for q in source['pieces']if q['tier']==part['tier']+1]);political=translate(shape(part['red_political']),-loc['dx_mm'],-loc['dy_mm']);assert political.intersection(upper.buffer(-.001)).length<.001
 distances=[g.distance(h)for id,g in cuts.items()for other,h in cuts.items()if id<other];assert min(distances)>=3
 page=PdfReader(P/f'Поле-{si:02d}-740x740.pdf').pages[0];size=[float(page.mediabox.width)*25.4/72,float(page.mediabox.height)*25.4/72];assert all(abs(x-740)<.001 for x in size)
 report.append({'sheet':si,'pieces':len(cuts),'red_single_line_labels':textcount,'red_city_markers':markcount,'blue_titles':bluecount,'colors':sorted(colors),'actual_min_gap_mm':min(distances),'max_cut_area_rounding_error_mm2':max(errors),'max_stroke_rounding_error_mm':max(lineerrors),'pdf_page_mm':size,'translation_only':True,'scale':1,'hidden_political_boundaries_removed':True})
assert sum(q['red_single_line_labels']for q in report)==82*D['sets'];assert sum(q['red_city_markers']for q in report)==72*D['sets'];assert sum(q['blue_titles']for q in report)==4*D['sets']
result={'passed':True,'sets':D['sets'],'physical_parts_per_set':28,'fields':report,'country_names_blue':D['country_texts'],'annotations_per_set':158,'red_text_is_actual_centerline_vectors':True,'source_plan_sha256':D['source_sha256'],'slit_repairs_report':'Исправление-щелей.json','density_attempts_file':'data/layout.json'};(P/'Проверка-раскроя.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('VERIFIED',report,flush=True)
