"""Verify actual serialized cut paths, live labels, city markers and stepped water."""
import json,re,math,os
from pathlib import Path
from lxml import etree as E
from shapely.geometry import Polygon,LineString,shape,box,Point
from shapely.ops import unary_union
from shapely.affinity import translate
from pypdf import PdfReader
from fontTools.ttLib import TTFont
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));O=Path(os.environ.get('AFRICA_OUTPUT',str(P)));M=json.load(open(O/'manufacturing.json'));source={q['id']:q for q in D['pieces']};cmap=TTFont(P/'Шрифт/OpenSans-Light.ttf').getBestCmap()
def parse(d,closed=True):
 rings=[]
 for seq in re.findall(r'M([^M]+)',d):
  v=[float(x)for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',seq)];rings.append(list(zip(v[::2],v[1::2])))
 if not closed:return unary_union([LineString(q)for q in rings if len(q)>1])
 ex=[];holes=[]
 for q in rings:
  area=sum(x*y2-x2*y for(x,y),(x2,y2)in zip(q,q[1:]+q[:1]))
  (ex if area<0 else holes).append(q)
 outer=[Polygon(q)for q in ex];owners={i:[]for i in range(len(outer))}
 for h in holes:
  point=Polygon(h).representative_point();ii=[i for i,q in enumerate(outer)if q.covers(point)];assert ii;owners[min(ii,key=lambda i:outer[i].area)].append(h)
 return unary_union([Polygon(q,owners[i])for i,q in enumerate(ex)])
fields=[]
for sheet in sorted(set(q['sheet']for q in M['pieces'])):
 tree=E.parse(str(O/f'Поле-{sheet:02d}-740x740.svg'));root=tree.getroot();assert root.get('width')==root.get('height')=='740mm'and root.get('viewBox')=='0 0 740 740';assert not root.xpath('//*[local-name()="image"]');paths={el.get('id'):el for el in root.xpath('//*[local-name()="path"]')};texts={el.get('id'):el for el in root.xpath('//*[local-name()="text"]')};colors={el.get('stroke')if el.get('stroke')not in [None,'none']else el.get('fill')for el in [*paths.values(),*texts.values()]};assert colors<={'#000000','#ff0000','#0000ff'}and'#000000'in colors;cuts={};errors=[];lineserrors=[];markcount=0;wordcount=0
 for row in [q for q in M['pieces']if q['sheet']==sheet]:
  p=source[row['source_id']];el=paths[row['id']+'_CUT'];assert el.get('fill')=='none'and el.get('stroke')=='#000000'and el.get('transform')is None and el.get('d').rstrip().endswith('Z');g=parse(el.get('d'));expected=translate(shape(p['geom']),row['dx_mm'],row['dy_mm']);assert g.is_valid,(row['id'],'invalid cut');error=g.symmetric_difference(expected).area;assert error<.002,(row['id'],'changed geometry',error);errors.append(error);cuts[row['id']]=g;assert box(5,5,735,735).covers(g);assert row['rotation_degrees']==0 and not row['mirrored']and row['scale']==1
  visible=translate(shape(p['visible']),row['dx_mm'],row['dy_mm'])
  if not shape(row['red_internal']).is_empty:
   el=paths[row['id']+'_INTERNAL'];assert el.get('stroke')=='#ff0000'and el.get('fill')=='none';actual=parse(el.get('d'),False);error=actual.hausdorff_distance(shape(row['red_internal']));assert error<.000002;lineserrors.append(error);assert actual.difference(g.buffer(.002)).length<.001
  for a in row['labels']:
   el=texts[row['id']+'_'+a['id']];word=''.join(el.itertext());assert re.sub(r'\s+','',word)==re.sub(r'\s+','',a['text']);assert el.get('fill')==a['color']and el.get('stroke')=='none';assert el.get('font-family')=='Open Sans Light';assert all(ch.isspace()or ord(ch)in cmap for ch in a['text']);matrix=[float(x)for x in el.get('transform')[7:-1].split(',')];assert max(abs(x-y)for x,y in zip(matrix,a['matrix']))<1e-10;assert abs(float(el.get('font-size'))-a['font_size_mm'])<1e-8;assert shape(a['geometry']).difference(visible.buffer(.00001)).area<.0001;assert shape(a['bbox']).difference(visible.buffer(.00001)).area<.0001;wordcount+=1
  for a in row['markers']:
   el=paths[row['id']+'_'+a['id']+'_MARK'];assert el.get('fill')=='#ff0000'and not el.get('stroke');actual=parse(el.get('d'));assert actual.symmetric_difference(shape(a['geom'])).area<.00001;assert actual.difference(visible.buffer(.00001)).area<.00001;markcount+=1
 distances=[g.distance(h)for id,g in cuts.items()for other,h in cuts.items()if id<other];assert min(distances)>=3
 page=PdfReader(O/f'Поле-{sheet:02d}-740x740.pdf').pages[0];size=[float(page.mediabox.width)*25.4/72,float(page.mediabox.height)*25.4/72];assert all(abs(v-740)<.001 for v in size);content=re.sub(r'\s+','',page.extract_text())
 for row in M['pieces']:
  if row['sheet']!=sheet:continue
  for a in row['labels']:assert re.sub(r'\s+','',a['text'])in content,(a['id'],'PDF lost editable text')
 fields.append({'sheet':sheet,'parts':len(cuts),'editable_texts':wordcount,'city_marks':markcount,'svg_colors':sorted(colors),'actual_min_gap_mm':min(distances),'max_serialized_cut_error_mm2':max(errors),'max_serialized_red_line_error_mm':max(lineserrors,default=0),'page_mm':size,'all_parts_translation_only':True,'all_text_bboxes_fit_one_exposed_surface':True,'pdf_text_is_searchable':True})
assert sum(q['parts']for q in fields)==len(D['pieces'])*M['layout']['kits'];assert sum(q['editable_texts']for q in fields)==len(D['labels'])*M['layout']['kits'];assert sum(q['city_marks']for q in fields)==len(D['city_markers'])*M['layout']['kits']
# Check complete words and city marks against the final exposed surfaces.
for i,a in enumerate(D['labels']):
 bb=shape(a['bbox']);assert a['color']==('#0000ff'if a['kind']=='country'else'#ff0000')
 for b in D['labels'][:i]:assert bb.intersection(shape(b['bbox'])).area<.00001,(a['id'],b['id'],'text overlap')
 for m in D['city_markers']:assert bb.intersection(shape(m['geom'])).area<.00001,(a['id'],m['name'],'marker under text')
source_ids={a['id']for a in D['source_labels']};assert source_ids<={a['id']for a in D['labels']};assert len(D['city_markers'])>=len(D['source_markers'])
# Every planned broad water slot is open through every upper ply.
BB=shape(D['water_base_union']);UB=shape(D['water_upper_union']);layer_checks=[]
for i,layer in enumerate(D['layers']):
 actual=unary_union([shape(p['geom'])for p in D['pieces']if p['tier']==i+1]);mask=BB if i==0 else UB;bridges=unary_union([shape(b['footprint'])for b in D.get('river_bridges',[])if b['tier']==i+1]);area=actual.intersection(mask.buffer(-.03)).difference(bridges.buffer(.03)).area;assert area<.03,(i,'water blocked',area)
 geometry_error=actual.symmetric_difference(shape(layer)).area;removed=unary_union([shape(r['geom'])for r in D['removed_micro_parts']if r['tier']==i+1 and 'geom'in r]);unexplained=actual.symmetric_difference(shape(layer)).difference(removed.buffer(.003)).area;assert unexplained<.35,(i,'layer mismatch',unexplained)
 if i:
  lower=unary_union([shape(p['geom'])for p in D['pieces']if p['tier']==i]);overhang=actual.difference(lower.buffer(.10)).difference(removed.buffer(.01)).difference(bridges.buffer(.04)).area;assert overhang<.2,(i,'unsupported upper area',overhang)
 layer_checks.append({'layer':i+1,'parts':sum(p['tier']==i+1 for p in D['pieces']),'water_blocked_mm2':area,'layer_union_error_mm2':geometry_error})
# Scand is packed with the western set but cannot share any physical piece with it.
scand=[]
if D['batch']=='WEST':
 partition=json.load(open(P.parent/'data/source/batch-partition-masks.json'));mask=shape(partition['scandinavia_mask']);main=[p for p in D['pieces']if p.get('block')!='SCAND'];scand=[p for p in D['pieces']if p.get('block')=='SCAND'];assert scand
 for p in main:assert shape(p['geom']).intersection(mask.buffer(-.003)).area<.01,(p['id'],'shared Scand/main piece')
 for p in scand:assert shape(p['geom']).difference(mask.buffer(.003)).area<.01
 for c in ['NOR','SWE','FIN']:assert c in D['regions']
 pyramid=shape(D['pyramid_block']);assert pyramid.intersection(UB).area<.001,'pyramid water cut';assert all(shape(t).difference(unary_union([shape(p['geom'])for p in D['pieces']if p['tier']==i+3]).buffer(.10)).area<.1 for i,t in enumerate(D['pyramid_terraces']))
else:
 assert not any(c in D['regions']for c in ['NOR','SWE','FIN']);assert all(p.get('block')!='SCAND'for p in D['pieces']);assert 'CHN'in D['regions']and'IRN'in D['regions'];assert 'TUR'not in D['regions']
 assert len(D.get('china_province_regions',{}))==33
# Geometric change audit: approved wood may be removed only for water or reported small remnants.
import gzip
from shapely.affinity import translate
S={k:json.load(gzip.open(P.parent/f'data/source/{k}-approved-plan.json.gz','rt'))for k in ['RU','EU','AF']};cfg=json.load(open(P.parent/'data/batch-countries.json'));partition=json.load(open(P.parent/'data/source/batch-partition-masks.json'));westmask=shape(partition['west_mask']);ru0=shape(S['RU']['layers'][0]);ruen=unary_union([Polygon(p.exterior)for p in (list(ru0.geoms)if hasattr(ru0,'geoms')else[ru0])]).union(shape(S['RU']['water_base_union']));material=[]
for i in range(len(D['layers'])):
 inp=[]
 for family in (['RU','EU']if D['batch']=='EAST'else['AF','EU']):
  if i>=len(S[family]['layers']):continue
  q=shape(S[family]['layers'][i])
  if family=='EU':q=q.difference(westmask)if D['batch']=='EAST'else q.intersection(westmask).difference(ruen)
  if family=='AF':q=translate(q,*cfg['africa_translation_mm'])
  inp.append(q)
 raw=unary_union(inp);actual=unary_union([shape(p['geom'])for p in D['pieces']if p['tier']==i+1]);water=BB if i==0 else UB;removed=unary_union([shape(r['geom'])for r in D['removed_micro_parts']if r['tier']==i+1 and 'geom'in r]);loss=raw.buffer(-.12).difference(actual.buffer(.003)).difference(water.buffer(.12)).difference(removed.buffer(.05)).area;assert loss<.25,(i,'unapproved relief removed',loss);material.append({'layer':i+1,'unapproved_deep_material_loss_mm2':loss,'new_water_removed_mm2':raw.intersection(water).area})
report={'passed':True,'title':D['title'],'batch':D['batch'],'sheets':len(fields),'parts':len(D['pieces']),'parts_by_layer':[s['pieces']for s in D['summary']],'fields':fields,'all_text_objects':len(D['labels']),'source_labels_retained':len(source_ids),'cities':len(D['city_markers']),'max_city_shift_mm':max(m['bank_shift_mm']for m in D['city_markers']),'layers':layer_checks,'water_open_except_approved_local_bridges':True,'approved_bridge_count':len(D.get('river_bridges',[])),'material_audit':material,'scandinavia_separate_pieces':len(scand),'physical_stock_seams':len(D['stock_seams']),'source_hash_matches':M['source_plan_sha256']==__import__('hashlib').sha256((P/'data/production-plan.json').read_bytes()).hexdigest()};assert report['source_hash_matches'];(O/'Проверка-раскроя.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('VERIFIED',D['title'],len(D['pieces']),'parts',len(fields),'sheets',len(D['labels']),'editable texts',flush=True)
