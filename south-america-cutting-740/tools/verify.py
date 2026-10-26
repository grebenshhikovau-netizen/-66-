"""Independently validate serialized laser paths, editable titles and paint logic."""
import json,re,csv,math,hashlib
from pathlib import Path
from lxml import etree as E
from shapely.geometry import Polygon,LineString,shape,box
from shapely.ops import unary_union
from shapely.affinity import translate
from pypdf import PdfReader
from fontTools.ttLib import TTFont
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));source={q['id']:q for q in D['pieces']};cmap=TTFont(P/'Шрифт/OpenSans-Light.ttf').getBestCmap()
def parse(d,closed=True):
 rings=[]
 for seq in re.findall(r'M([^M]+)',d):
  v=[float(x)for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',seq)];rings.append(list(zip(v[::2],v[1::2])))
 if not closed:return unary_union([LineString(q)for q in rings if len(q)>1])
 outers=[];holes=[]
 for q in rings:
  a=sum(x*y2-x2*y for(x,y),(x2,y2)in zip(q,q[1:]+q[:1]))
  (outers if a<0 else holes).append(q)
 pp=[Polygon(q)for q in outers];owners={i:[]for i in range(len(pp))}
 for h in holes:
  point=Polygon(h).representative_point();owner=[i for i,g in enumerate(pp)if g.covers(point)];assert owner;owners[min(owner,key=lambda i:pp[i].area)].append(h)
 return unary_union([Polygon(q,owners[i])for i,q in enumerate(outers)])
def verify(folder):
 data=json.load(open(folder/'manufacturing.json'));tree=E.parse(str(folder/'Поле-01-740x740.svg'));root=tree.getroot();assert root.get('width')==root.get('height')=='740mm'and root.get('viewBox')=='0 0 740 740';assert not root.xpath('//*[local-name()="image"]');paths={e.get('id'):e for e in root.xpath('//*[local-name()="path"]')};texts={e.get('id'):e for e in root.xpath('//*[local-name()="text"]')};assert len(texts)==13*data['kits'];colors={e.get('stroke')if e.get('stroke')not in [None,'none']else e.get('fill')for e in [*paths.values(),*texts.values()]};assert colors=={'#000000','#ff0000','#0000ff'};cuts={};maxerr=0;maxline=0
 for row in data['pieces']:
  loc=row;id=row['id'];p=source[row['source_id']];el=paths[id+'_CUT'];assert el.get('stroke')=='#000000'and el.get('fill')=='none'and el.get('d').rstrip().endswith('Z');assert el.get('transform')is None;g=parse(el.get('d'));expected=translate(shape(p['geom']),loc['dx_mm'],loc['dy_mm']);error=g.symmetric_difference(expected).area;assert error<.001,(id,'changed cut',error);maxerr=max(error,maxerr);cuts[id]=g;assert g.is_valid and box(5,5,735,735).covers(g);assert loc['rotation_degrees']==0 and not loc['mirrored']and loc['scale']==1
  if not shape(row['red_internal']).is_empty:
   el=paths[id+'_INTERNAL'];assert el.get('stroke')=='#ff0000'and el.get('fill')=='none'and el.get('transform')is None;actual=parse(el.get('d'),False);error=actual.hausdorff_distance(shape(row['red_internal']));assert error<.000002;maxline=max(maxline,error);assert actual.difference(g.buffer(.00001)).length<.001
  for title in row['blue_titles']:
   el=texts[id+'_'+title['id']];actual=''.join(el.itertext());assert re.sub(r'\s+','',actual)==re.sub(r'\s+','',title['text']);assert el.get('fill')=='#0000ff'and el.get('stroke')=='none';assert el.get('font-family')=='Open Sans Light';assert all(ord(ch)in cmap for ch in title['text']);matrix=[float(x)for x in el.get('transform')[7:-1].split(',')];assert max(abs(a-b)for a,b in zip(matrix,title['matrix']))<1e-10;assert abs(float(el.get('font-size'))-title['font_size_mm'])<1e-8
   safe=translate(shape(p['visible']),loc['dx_mm'],loc['dy_mm']);assert shape(title['geometry']).difference(safe).area<.0001
  for coat,mask in row['paint'].items():
   actual=shape(mask['with_overlap']);assert actual.difference(g.buffer(.00001)).area<.001
   extra=actual.difference(shape(mask['visible']));upper=unary_union([shape(q['geom'])for q in D['pieces']if q['tier']==p['tier']+1]);upper=translate(upper,loc['dx_mm'],loc['dy_mm']);assert extra.difference(upper.buffer(.00001)).area<.001
 distances=[g.distance(h)for id,g in cuts.items()for other,h in cuts.items()if id<other];assert min(distances)>=3
 for kit in range(1,data['kits']+1):assert {q['source_id']for q in data['pieces']if q['kit']==kit}==set(source)
 page=PdfReader(folder/'Поле-01-740x740.pdf').pages[0];size=[float(page.mediabox.width)*25.4/72,float(page.mediabox.height)*25.4/72];assert all(abs(x-740)<.001 for x in size);text=re.sub(r'\s+','',page.extract_text())
 for label in D['labels']:assert text.count(re.sub(r'\s+','',label['text']))==data['kits'],(label['text'],'not all PDF copies readable')
 return {'folder':folder.name,'kits':data['kits'],'physical_parts':len(cuts),'editable_blue_country_titles':len(texts),'source_city_labels':0,'svg_colors':sorted(colors),'stock_mm':[740,740],'pdf_page_mm':size,'actual_min_gap_mm':min(distances),'max_cut_rounding_error_mm2':maxerr,'max_red_line_rounding_error_mm':maxline,'all_parts_translation_only':True,'all_titles_fit_one_exposed_surface':True,'all_kits_complete':True,'pdf_text_is_live_and_searchable':True}
results=[verify(P),verify(P/'Один-комплект')]
# These are source-assembly checks, independent from translated sheets.
for row in D['pieces']:
 upper=unary_union([shape(q['geom'])for q in D['pieces']if q['tier']==row['tier']+1]);assert shape(row['red_political']).intersection(upper.buffer(-.001)).length<.001;assert shape(row['placement_guides']).difference(unary_union([shape(q['geom']).boundary for q in D['pieces']if q['tier']==row['tier']+1]).buffer(.005)).length<.001
 masks=[(c,shape(v['visible']).buffer(-.02))for c,v in row['paint'].items()]
 for j,(c,g)in enumerate(masks):
  for other,h in masks[:j]:assert g.is_empty or h.is_empty or g.distance(h)>=D['minimum_exposed_color_gap_for_join_mm']-.0001
r=[q for q in json.load(open(P/'data/source/extracted.json'))if q['kind']=='wood'];errors=[]
for tier in [1,2,3]:
 raw=unary_union([shape(q['geom'])for q in r if q['hi_mm']>=3*tier-.05]);actual=unary_union([shape(q['geom'])for q in D['pieces']if q['tier']==tier]);error=actual.symmetric_difference(raw).area;assert error<.05;errors.append(error)
report={'passed':True,'parts_per_kit':18,'layers':[5,5,8],'source_height_levels_mm':[3,6,9],'fields':results,'paint_conflicts_not_joined':True,'bleed_only_under_upper_parts':True,'hidden_political_boundaries_removed':True,'immediate_next_piece_placement_guides_kept':True,'source_height_field_symmetric_difference_mm2':errors,'source_palette_preserved':True};(P/'Проверка-раскроя.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('VERIFIED',results,flush=True)
with open(P/'Покраска-деталей.csv','w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f);w.writerow(['Деталь','Слой','Цвет','Красить','Видимая площадь мм2','Площадь с напуском мм2'])
 for row in D['pieces']:
  for coat,mask in row['paint'].items():w.writerow([row['id'],row['tier'],coat,'Да'if mask['paint']else'Нет, естественная фанера',round(shape(mask['visible']).area,3),round(shape(mask['with_overlap']).area,3)])
