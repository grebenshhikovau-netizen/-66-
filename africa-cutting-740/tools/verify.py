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
 tree=E.parse(str(O/f'Поле-{sheet:02d}-740x740.svg'));root=tree.getroot();assert root.get('width')==root.get('height')=='740mm'and root.get('viewBox')=='0 0 740 740';assert not root.xpath('//*[local-name()="image"]');paths={el.get('id'):el for el in root.xpath('//*[local-name()="path"]')};texts={el.get('id'):el for el in root.xpath('//*[local-name()="text"]')};colors={el.get('stroke')if el.get('stroke')not in [None,'none']else el.get('fill')for el in [*paths.values(),*texts.values()]};assert colors=={'#000000','#ff0000','#0000ff'};cuts={};errors=[];lineserrors=[];markcount=0;wordcount=0
 for row in [q for q in M['pieces']if q['sheet']==sheet]:
  p=source[row['source_id']];el=paths[row['id']+'_CUT'];assert el.get('fill')=='none'and el.get('stroke')=='#000000'and el.get('transform')is None and el.get('d').rstrip().endswith('Z');g=parse(el.get('d'));expected=translate(shape(p['geom']),row['dx_mm'],row['dy_mm']);assert g.is_valid,(row['id'],'invalid cut');error=g.symmetric_difference(expected).area;assert error<.002,(row['id'],'changed geometry',error);errors.append(error);cuts[row['id']]=g;assert box(5,5,735,735).covers(g);assert row['rotation_degrees']==0 and not row['mirrored']and row['scale']==1
  visible=translate(shape(p['visible']),row['dx_mm'],row['dy_mm'])
  if not shape(row['red_internal']).is_empty:
   el=paths[row['id']+'_INTERNAL'];assert el.get('stroke')=='#ff0000'and el.get('fill')=='none';actual=parse(el.get('d'),False);error=actual.hausdorff_distance(shape(row['red_internal']));assert error<.000002;lineserrors.append(error);assert actual.difference(g.buffer(.00001)).length<.001
  for a in row['labels']:
   el=texts[row['id']+'_'+a['id']];word=''.join(el.itertext());assert re.sub(r'\s+','',word)==re.sub(r'\s+','',a['text']);assert el.get('fill')==a['color']and el.get('stroke')=='none';assert el.get('font-family')=='Open Sans Light';assert all(ord(ch)in cmap for ch in a['text']);matrix=[float(x)for x in el.get('transform')[7:-1].split(',')];assert max(abs(x-y)for x,y in zip(matrix,a['matrix']))<1e-10;assert abs(float(el.get('font-size'))-a['font_size_mm'])<1e-8;assert shape(a['geometry']).difference(visible.buffer(.00001)).area<.0001;assert shape(a['bbox']).difference(visible.buffer(.00001)).area<.0001;wordcount+=1
  for a in row['markers']:
   el=paths[row['id']+'_'+a['id']+'_MARK'];assert el.get('fill')=='#ff0000'and not el.get('stroke');actual=parse(el.get('d'));assert actual.symmetric_difference(shape(a['geom'])).area<.00001;assert actual.difference(visible.buffer(.00001)).area<.00001;markcount+=1
 distances=[g.distance(h)for id,g in cuts.items()for other,h in cuts.items()if id<other];assert min(distances)>=3
 page=PdfReader(O/f'Поле-{sheet:02d}-740x740.pdf').pages[0];size=[float(page.mediabox.width)*25.4/72,float(page.mediabox.height)*25.4/72];assert all(abs(v-740)<.001 for v in size);content=re.sub(r'\s+','',page.extract_text())
 for row in M['pieces']:
  if row['sheet']!=sheet:continue
  for a in row['labels']:assert re.sub(r'\s+','',a['text'])in content,(a['id'],'PDF lost editable text')
 fields.append({'sheet':sheet,'parts':len(cuts),'editable_texts':wordcount,'city_marks':markcount,'svg_colors':sorted(colors),'actual_min_gap_mm':min(distances),'max_serialized_cut_error_mm2':max(errors),'max_serialized_red_line_error_mm':max(lineserrors,default=0),'page_mm':size,'all_parts_translation_only':True,'all_text_bboxes_fit_one_exposed_surface':True,'pdf_text_is_searchable':True})
assert sum(q['parts']for q in fields)==len(D['pieces'])*M['layout']['kits'];assert sum(q['editable_texts']for q in fields)==len(D['labels'])*M['layout']['kits'];assert sum(q['city_marks']for q in fields)==len(D['city_markers'])*M['layout']['kits']
country={q['region']for q in D['labels']if q['kind']=='country'};assert country==set(D['region_names']);assert all(q['color']=='#0000ff'for q in D['labels']if q['kind']=='country');assert all(q['color']=='#ff0000'for q in D['labels']if q['kind']=='city');assert len({q['name']for q in D['city_markers']})==len(D['city_markers'])
# Non-overlapping annotation bounding boxes; the marker dots are also protected.
for i,a in enumerate(D['labels']):
 bb=shape(a['bbox'])
 for b in D['labels'][:i]:assert bb.intersection(shape(b['bbox'])).area<.00001,(a['id'],b['id'],'text overlap')
 for marker in D['city_markers']:assert bb.intersection(shape(marker['geom'])).area<.00001,(a['id'],marker['name'],'text hides city marker')
BB=shape(D['water_base_union']);UB=shape(D['water_upper_union']);assert BB.difference(UB.buffer(.00001)).area<.001
for i,layer in enumerate(D['layers']):
 water=BB if i==0 else UB;g=shape(layer);assert g.intersection(water.buffer(-.002)).area<.001
 if i:assert g.difference(shape(D['layers'][i-1]).buffer(.002)).area<.001
lakechecks=[]
for name in ['Виктория','Танганьика','Малави','Туркана','Альберт','Тана']:
 lo=shape(D['base_water'][name]);hi=shape(D['upper_water'][name]);assert lo.is_valid and lo.geom_type=='Polygon';assert lo.area>.2 and lo.difference(hi.buffer(.00001)).area<.001;assert hi.area>lo.area*1.25;lakechecks.append({'lake':name,'lower_connected':True,'lower_area_mm2':lo.area,'upper_area_mm2':hi.area})
block=shape(D['pyramid_block']);nile=shape(D['upper_water']['Нил']);assert nile.intersection(block.buffer(-.002)).area<.001
pyramidchecks=[]
for j,g in enumerate(D['pyramid_terraces']):
 footprint=shape(g);layer=shape(D['layers'][j+2]);assert footprint.buffer(-.40).difference(layer).area<.01
 candidate=[q for q in D['pieces']if q['tier']==j+3 and shape(q['geom']).covers(footprint.centroid)];assert len(candidate)==1
 part=shape(candidate[0]['geom']);assert len(part.interiors)==0,(candidate[0]['id'],'pyramid is cut');pyramidchecks.append({'tier':j+3,'part':candidate[0]['id'],'one_piece':True,'no_holes':True})
riftchecks=[]
for q in D['rift_fills']:
 fill=shape(q['geom']);actual=shape(D['layers'][q['tier']-1]);expected=fill.difference(UB).buffer(-.50);loss=expected.difference(actual).area;assert loss<.1,(q['tier'],'rift slit not closed',loss);riftchecks.append({'tier':q['tier'],'filled_area_mm2':q['filled_area_mm2'],'interior_not_reopened':True})
confluences=[]
for a,b in [('Нил','Альберт'),('Нил','Тана'),('Замбези','Водопад Виктория')]:
 lo=shape(D['base_water'][a]).intersection(shape(D['base_water'][b])).area;hi=shape(D['upper_water'][a]).intersection(shape(D['upper_water'][b])).area;assert lo>.001 and hi>.001,(a,b,'disconnected water');confluences.append({'a':a,'b':b,'lower_connection_area_mm2':lo,'upper_connection_area_mm2':hi})
for p in D['pieces']:
 upper=unary_union([shape(q['geom'])for q in D['pieces']if q['tier']==p['tier']+1]);assert shape(p['red_political']).intersection(upper.buffer(-.001)).length<.001
report={'passed':True,'kits':M['layout']['kits'],'physical_parts':len(M['pieces']),'parts_per_kit':len(D['pieces']),'parts_by_layer':[s['pieces']for s in D['summary']],'top_heights_mm':D['levels_mm'],'fields':fields,'cities':len(D['city_markers']),'countries_and_territories_named':len(country),'all_text_objects':len(D['labels']),'pyramid':pyramidchecks,'closed_rift_strip':riftchecks,'water_steps':D['water_steps'],'lake_profiles':lakechecks,'confluences':confluences,'no_text_overlap':True,'max_city_surface_shift_mm':max(q['bank_shift_mm']for q in D['city_markers']),'hidden_political_borders_removed':True,'removed_micro_parts':D['removed_micro_parts']};(O/'Проверка-раскроя.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('VERIFIED',len(M['pieces']),'placed parts',fields,flush=True)
