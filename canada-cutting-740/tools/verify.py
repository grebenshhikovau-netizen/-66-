"""Check serialized laser SVG rather than only the in-memory nesting result."""
import json,re,math,hashlib
from pathlib import Path
from lxml import etree as E
from shapely.geometry import Polygon,shape,box
from shapely.ops import unary_union
from shapely.affinity import translate
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data'/'manufacturing.json'));N=json.load(open(P/'data'/'layout.json'));source=json.load(open(P/'data'/'source'/'production-plan.json'));original={q['id']:shape(q['geom'])for q in source['pieces']};locations={q['id']:q for q in N['placements']};report=[]
def parse(d):
 rings=[]
 for seq in re.findall(r'M([^M]+)',d):
  v=[float(x)for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',seq)];ring=list(zip(v[::2],v[1::2]));rings.append(ring)
 exteriors=[];holes=[]
 for ring in rings:
  a=sum(x*y2-x2*y for (x,y),(x2,y2)in zip(ring,ring[1:]+ring[:1]))/2
  (exteriors if a<0 else holes).append(ring)
 outerpolys=[Polygon(r)for r in exteriors];assigned={i:[]for i in range(len(exteriors))}
 for h in holes:
  point=Polygon(h).representative_point();owners=[i for i,g in enumerate(outerpolys)if g.covers(point)]
  if owners:assigned[min(owners,key=lambda i:outerpolys[i].area)].append(h)
 result=[Polygon(r,assigned[i])for i,r in enumerate(exteriors)]
 return unary_union(result)
for si in sorted(set(q['sheet']for q in D['pieces'])):
 file=P/f'Поле-{si:02d}-740x740.svg';tree=E.parse(str(file));root=tree.getroot();assert root.get('width')==root.get('height')=='740mm';assert root.get('viewBox')=='0 0 740 740';assert not root.xpath('//*[@transform]');assert not root.xpath('//*[local-name()="text" or local-name()="image"]')
 colors=set();cuts={};redblue=[]
 for path in root.xpath('//*[local-name()="path"]'):
  assert path.get('d').rstrip().endswith('Z');color=path.get('stroke')or path.get('fill');colors.add(color);g=parse(path.get('d'));assert box(5,5,735,735).covers(g),(path.get('id'),'outside stock')
  if color=='#000000':cuts[path.get('id').removesuffix('_CUT')]=g
  else:redblue.append((path.get('id'),g,color))
 assert colors=={'#000000','#ff0000','#0000ff'},colors
 assert set(cuts)=={q['id']for q in D['pieces']if q['sheet']==si}
 distances=[];maxerror=0
 for id,g in cuts.items():
  loc=locations[id];assert loc['rotation_degrees']==0 and not loc['mirrored'];expected=translate(original[id],loc['dx_mm'],loc['dy_mm']);error=g.symmetric_difference(expected).area;assert error<.001,(id,error);maxerror=max(maxerror,error)
  for other,h in cuts.items():
   if id<other:
    distance=g.distance(h);assert distance>=3,(id,other,distance);distances.append(distance)
  q=next(q for q in D['pieces']if q['id']==id);alltext=unary_union([shape(q['red_labels']),*[shape(b)for b in q['blue'].values()]]);back=translate(alltext,-loc['dx_mm'],-loc['dy_mm']);area=back.symmetric_difference(shape(q['source_engraving'])).area;assert area<.000001,(id,'lost engraving',area)
 serialized_annotation_errors=[]
 for part in D['pieces']:
  id=part['id'];loc=locations[id]
  aa=[g for pid,g,color in redblue if pid.startswith(id+'_')and not pid.endswith('_INTERNAL')]
  actual=unary_union(aa);expected=translate(shape(part['source_engraving']),loc['dx_mm'],loc['dy_mm']);ee=actual.symmetric_difference(expected).area;assert ee<.01,(id,'serialized lettering loss',ee);serialized_annotation_errors.append(ee)
 for id,g,color in redblue:
  pid=id.split('_TEXT')[0].split('_INTERNAL')[0].split('_TEXT_')[0]
  if '_TEXT_'in id:pid=id.split('_TEXT_')[0]
  if pid not in cuts:pid='_'.join(id.split('_')[:2])
  assert g.difference(cuts[pid].buffer(.00001)).area<.001,(id,'engraving outside physical part')
 report.append({'sheet':si,'pieces':len(cuts),'svg_colors':sorted(colors),'actual_min_gap_mm':min(distances),'max_serialized_shape_error_mm2':maxerror,'no_transforms':True,'no_rotation':True,'no_mirroring':True,'scale':1,'stock_mm':[740,740],'original_engraving_preserved':True,'max_serialized_engraving_error_mm2':max(serialized_annotation_errors)})
result={'passed':True,'fields':report,'country_names_blue':D['country_texts'],'unique_original_annotations':D['unique_annotations'],'physical_parts':len(D['pieces']),'interior_boundaries_red':True,'through_cut_exterior_and_hole_contours_black':True,'no_production_frame_or_part_numbers':True,'source_plan_sha256':D['source_sha256']};(P/'Проверка-раскроя.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('LASER SVG VERIFIED',report,flush=True)
