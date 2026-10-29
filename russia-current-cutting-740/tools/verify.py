"""Verify actual serialized cut paths, live labels, city markers and stepped water."""
import json,re,math
from pathlib import Path
from lxml import etree as E
from shapely.geometry import Polygon,LineString,shape,box,Point
from shapely.ops import unary_union
from shapely.affinity import translate
from pypdf import PdfReader
from fontTools.ttLib import TTFont
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));M=json.load(open(P/'manufacturing.json'));source={q['id']:q for q in D['pieces']};cmap=TTFont(P/'Шрифт/OpenSans-Light.ttf').getBestCmap()
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
 tree=E.parse(str(P/f'Поле-{sheet:02d}-740x740.svg'));root=tree.getroot();assert root.get('width')==root.get('height')=='740mm'and root.get('viewBox')=='0 0 740 740';assert not root.xpath('//*[local-name()="image"]');paths={el.get('id'):el for el in root.xpath('//*[local-name()="path"]')};texts={el.get('id'):el for el in root.xpath('//*[local-name()="text"]')};colors={el.get('stroke')if el.get('stroke')not in [None,'none']else el.get('fill')for el in [*paths.values(),*texts.values()]};assert colors=={'#000000','#ff0000','#0000ff'};cuts={};errors=[];lineserrors=[];markcount=0;wordcount=0
 for row in [q for q in M['pieces']if q['sheet']==sheet]:
  p=source[row['id']];el=paths[row['id']+'_CUT'];assert el.get('fill')=='none'and el.get('stroke')=='#000000'and el.get('transform')is None and el.get('d').rstrip().endswith('Z');g=parse(el.get('d'));expected=translate(shape(p['geom']),row['dx_mm'],row['dy_mm']);assert g.is_valid,(row['id'],'invalid cut');error=g.symmetric_difference(expected).area;assert error<.002,(row['id'],'changed geometry',error);errors.append(error);cuts[row['id']]=g;assert box(5,5,735,735).covers(g);assert row['rotation_degrees']==0 and not row['mirrored']and row['scale']==1
  visible=translate(shape(p['visible']),row['dx_mm'],row['dy_mm'])
  if not shape(row['red_internal']).is_empty:
   el=paths[row['id']+'_INTERNAL'];assert el.get('stroke')=='#ff0000'and el.get('fill')=='none';actual=parse(el.get('d'),False);error=actual.hausdorff_distance(shape(row['red_internal']));assert error<.000002;lineserrors.append(error);assert actual.difference(g.buffer(.002)).length<.001
  for a in row['labels']:
   el=texts[row['id']+'_'+a['id']];word=''.join(el.itertext());assert re.sub(r'\s+','',word)==re.sub(r'\s+','',a['text']);assert el.get('fill')==a['color']and el.get('stroke')=='none';assert el.get('font-family')=='Open Sans Light';assert all(ord(ch)in cmap for ch in a['text']);matrix=[float(x)for x in el.get('transform')[7:-1].split(',')];assert max(abs(x-y)for x,y in zip(matrix,a['matrix']))<1e-10;assert abs(float(el.get('font-size'))-a['font_size_mm'])<1e-8;assert shape(a['geometry']).difference(visible.buffer(.00001)).area<.0001;assert shape(a['bbox']).difference(visible.buffer(.00001)).area<.0001;wordcount+=1
  for a in row['markers']:
   el=paths[row['id']+'_'+a['id']+'_MARK'];assert el.get('fill')=='#ff0000'and not el.get('stroke');actual=parse(el.get('d'));assert actual.symmetric_difference(shape(a['geom'])).area<.00001;assert actual.difference(visible.buffer(.00001)).area<.00001;markcount+=1
 distances=[g.distance(h)for id,g in cuts.items()for other,h in cuts.items()if id<other];assert min(distances)>=3
 page=PdfReader(P/f'Поле-{sheet:02d}-740x740.pdf').pages[0];size=[float(page.mediabox.width)*25.4/72,float(page.mediabox.height)*25.4/72];assert all(abs(v-740)<.001 for v in size);content=re.sub(r'\s+','',page.extract_text())
 for row in M['pieces']:
  if row['sheet']!=sheet:continue
  for a in row['labels']:assert re.sub(r'\s+','',a['text'])in content,(a['id'],'PDF lost editable text')
 fields.append({'sheet':sheet,'parts':len(cuts),'editable_texts':wordcount,'city_marks':markcount,'svg_colors':sorted(colors),'actual_min_gap_mm':min(distances),'max_serialized_cut_error_mm2':max(errors),'max_serialized_red_line_error_mm':max(lineserrors,default=0),'page_mm':size,'all_parts_translation_only':True,'all_text_bboxes_fit_one_exposed_surface':True,'pdf_text_is_searchable':True})
assert sum(q['parts']for q in fields)==len(D['pieces']);assert sum(q['editable_texts']for q in fields)==len(D['labels'])==172;assert sum(q['city_marks']for q in fields)==90
# Every source region is named, including the three city-regions represented by city labels.
regional={q['region']for q in D['labels']if q['kind']=='region'};aliases={q['region']for q in D['label_notes']};assert regional|aliases==set(D['region_names']);assert len(regional)==81 and len(aliases)==3;assert len({q['name']for q in D['city_markers']})==90
# Non-overlapping annotation bounding boxes; the marker dots are also protected.
for i,a in enumerate(D['labels']):
 bb=shape(a['bbox'])
 for b in D['labels'][:i]:assert bb.intersection(shape(b['bbox'])).area<.00001,(a['id'],b['id'],'text overlap')
 for marker in D['city_markers']:assert bb.intersection(shape(marker['geom'])).area<.00001,(a['id'],marker['name'],'text hides city marker')
BB=shape(D['water_base_union']);UB=shape(D['water_upper_union']);assert BB.difference(UB.buffer(.00001)).area<.001
for i,layer in enumerate(D['layers']):
 water=BB if i==0 else UB;g=shape(layer);assert g.intersection(water.buffer(-.002)).area<.001
 if i:assert g.difference(shape(D['layers'][i-1]).buffer(.002)).area<.001
for name in ['Байкал','Таймыр']:
 lower=shape(D['base_water'][name]);upper=shape(D['upper_water'][name]);assert lower.area>3 and lower.difference(upper.buffer(.00001)).area<.001;assert upper.area>lower.area*1.3
for name in ['Ладожское','Онежское']:assert name not in D['base_water']
confluences=[]
for a,b in [('Ангара','Байкал'),('Ангара','Енисей'),('Иртыш','Обь'),('Вилюй','Лена'),('Кама','Волга')]:
 lo=shape(D['base_water'][a]).intersection(shape(D['base_water'][b])).area;hi=shape(D['upper_water'][a]).intersection(shape(D['upper_water'][b])).area;assert lo>.001 and hi>.001,(a,b,'disconnected water');confluences.append({'a':a,'b':b,'lower_connection_area_mm2':lo,'upper_connection_area_mm2':hi})
for p in D['pieces']:
 upper=unary_union([shape(q['geom'])for q in D['pieces']if q['tier']==p['tier']+1]);assert shape(p['red_political']).intersection(upper.buffer(-.001)).length<.001
report={'passed':True,'physical_parts':len(D['pieces']),'parts_by_layer':[s['pieces']for s in D['summary']],'top_heights_mm':[3,6,9],'fields':fields,'cities':90,'regions_named':84,'regional_text_objects':81,'city_regions_named_by_city_text':3,'all_text_objects':172,'water_lower_nominal_width_mm':[.8,.9],'water_upper_nominal_width_mm':[1.6,1.8],'required_lakes':['Байкал','Таймыр'],'no_new_karelian_lake_cuts':True,'confluences':confluences,'no_text_overlap':True,'max_city_bank_shift_mm':max(q['bank_shift_mm']for q in D['city_markers']),'hidden_political_borders_removed':True,'removed_tiny_river_islets':D.get('removed_river_islets',[])};(P/'Проверка-раскроя.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('VERIFIED',len(D['pieces']),'parts',fields,flush=True)
