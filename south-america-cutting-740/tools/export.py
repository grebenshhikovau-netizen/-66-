"""Export exact cuts, exposed political lines, immediate placement guides and live titles."""
import json,csv,math,hashlib
from pathlib import Path
from shapely.geometry import shape,mapping,Polygon
from shapely import set_precision
from shapely.geometry.polygon import orient
from shapely.ops import unary_union,linemerge
from shapely.affinity import translate
from lxml import etree as E
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));S='http://www.w3.org/2000/svg';labels=D['labels'];net=unary_union([shape(q).boundary for q in D['territories'].values()])
def polys(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for a in getattr(g,'geoms',[])for p in polys(a)]
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[g]if not g.is_empty and g.length>1e-6 else[]
 return[p for a in getattr(g,'geoms',[])for p in lines(a)]
for row in D['pieces']:
 g=shape(row['geom']);visible=shape(row['visible']);ink=unary_union([shape(q['geometry'])for q in labels if q['piece']==row['id']]);upperparts=[shape(q['geom'])for q in D['pieces']if q['tier']==row['tier']+1];upper=unary_union(upperparts);upper=upper if not upper.is_empty else Polygon()
 political=net.intersection(visible).difference(upper.buffer(.04)).difference(g.boundary.buffer(.2)).difference(ink.buffer(.3))
 guides=unary_union([q.boundary for q in upperparts]).intersection(g.buffer(-.1)).difference(g.boundary.buffer(.2)).difference(ink.buffer(.3)) if upperparts else Polygon().boundary
 internal=unary_union(lines(unary_union([political,guides])))
 if internal.geom_type=='MultiLineString':internal=linemerge(internal)
 row['red_political']=mapping(political);row['placement_guides']=mapping(guides);row['red_internal']=mapping(internal.simplify(.001));row['engraving']=mapping(unary_union([ink,internal.buffer(.025,cap_style=2,join_style=2)]))
 assert political.intersection(upper.buffer(-.001)).length<.001
(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False))
def root():return E.Element('svg',nsmap={None:S},width='740mm',height='740mm',viewBox='0 0 740 740',version='1.1')
def group(r,id,title):
 e=E.SubElement(r,'g',id=id);E.SubElement(e,'title').text=title;return e
def polygon_path(r,g,id,color,cut=False):
 rr=[]
 for p in polys(set_precision(g,.000001)):
  q=orient(p,-1)
  for ring in [q.exterior,*q.interiors]:
   xy=[]
   for x,y in list(ring.coords)[:-1]:
    pt=(round(x,6),round(y,6))
    if not xy or xy[-1]!=pt:xy.append(pt)
   if len(xy)>2:rr.append('M'+' L'.join(f'{x:.6f},{y:.6f}'for x,y in xy)+' Z')
 if not rr:return
 e=E.SubElement(r,'path',id=id,d=' '.join(rr),fill='none'if cut else color,attrib={'fill-rule':'nonzero'})
 if cut:e.set('stroke',color);e.set('stroke-width','.05');e.set('stroke-linejoin','round')
def stroke(r,g,id,color='#ff0000'):
 dd=['M'+' L'.join(f'{x:.6f},{y:.6f}'for x,y in q.coords)for q in lines(g)]
 if dd:E.SubElement(r,'path',id=id,d=' '.join(dd),fill='none',stroke=color,attrib={'stroke-width':'.05','stroke-linecap':'round','stroke-linejoin':'round'})
def text(r,a,id):
 attrs={'font-family':'Open Sans Light','font-size':format(a['font_size_mm'],'.9f'),'font-weight':'300','font-style':'normal','font-kerning':'none','letter-spacing':'0','transform':'matrix('+','.join(format(x,'.12f')for x in a['matrix'])+')','style':"font-kerning:none;font-feature-settings:'kern' 0"}
 el=E.SubElement(r,'text',id=id,fill='#0000ff',stroke='none',attrib=attrs)
 if len(a['lines'])==1:
  el.set('x',format(a['lines'][0]['x_em']*a['font_size_mm'],'.9f'));el.set('y',format(a['lines'][0]['y_em']*a['font_size_mm'],'.9f'));el.text=a['lines'][0]['text']
 else:
  for ln in a['lines']:
   t=E.SubElement(el,'tspan',x=format(ln['x_em']*a['font_size_mm'],'.9f'),y=format(ln['y_em']*a['font_size_mm'],'.9f'));t.text=ln['text']
 return el
def save(root,file):
 file.parent.mkdir(parents=True,exist_ok=True);E.ElementTree(root).write(str(file),encoding='UTF-8',xml_declaration=True)
def rgb(col):return'#'+''.join(f'{round(max(0,min(1,12.92*c if c<.0031308 else 1.055*c**(1/2.4)-.055))*255):02x}'for c in col)
def export(folder,layoutfile):
 folder.mkdir(parents=True,exist_ok=True);N=json.load(open(layoutfile));partmap={q['id']:q for q in D['pieces']};translated=[]
 for loc in N['placements']:
  p=partmap[loc['source_id']]
  def move(g):return translate(g,loc['dx_mm'],loc['dy_mm'])
  titles=[]
  for a in labels:
   if a['piece']!=p['id']:continue
   q={**a,'matrix':a['matrix'][:]};q['matrix'][4]+=loc['dx_mm'];q['matrix'][5]+=loc['dy_mm'];q['geometry']=mapping(move(shape(a['geometry'])));titles.append(q)
  translated.append({**loc,'tier':p['tier'],'geom':mapping(move(shape(p['geom']))),'visible':mapping(move(shape(p['visible']))),'red_political':mapping(move(shape(p['red_political']))),'placement_guides':mapping(move(shape(p['placement_guides']))),'red_internal':mapping(move(shape(p['red_internal']))),'blue_titles':titles,'regions':p['regions'],'paint':{coat:{'visible':mapping(move(shape(m['visible']))),'with_overlap':mapping(move(shape(m['with_overlap']))),'paint':m['paint']}for coat,m in p['paint'].items()}})
 for si in sorted(set(q['sheet']for q in translated)):
  main=root();red=group(main,'RED_INTERNAL_AND_PLACEMENT','Видимые границы и контуры установки следующего слоя');blue=group(main,'BLUE_COUNTRY_TITLES','Редактируемые названия стран и территорий');black=group(main,'BLACK_THROUGH_CUT','Сквозная резка');ops={'Красный-разметка':root(),'Синий-названия':root(),'Чёрный-резка':root()};paint=root();paintMasks={c:root()for c in D['colors']if c!='NATURAL'}
  for row in translated:
   if row['sheet']!=si:continue
   for target in [black,ops['Чёрный-резка']]:polygon_path(target,shape(row['geom']),row['id']+'_CUT','#000000',True)
   for target in [red,ops['Красный-разметка']]:stroke(target,shape(row['red_internal']),row['id']+'_INTERNAL')
   for title in row['blue_titles']:
    for target in [blue,ops['Синий-названия']]:text(target,title,row['id']+'_'+title['id'])
   polygon_path(paint,shape(row['geom']),row['id']+'_WOOD','#eee6d8')
   for c,mask in row['paint'].items():
    polygon_path(paint,shape(mask['with_overlap']),row['id']+'_'+c,rgb(D['colors'][c]))
    if c!='NATURAL':polygon_path(paintMasks[c],shape(mask['with_overlap']),row['id']+'_'+c,'#000000')
   polygon_path(paint,shape(row['geom']),row['id']+'_EDGE','#444444',True)
  save(main,folder/f'Поле-{si:02d}-740x740.svg');save(paint,folder/'Покраска'/f'Поле-{si:02d}-цвета-и-напуски.svg')
  for name,r in ops.items():save(r,folder/'Операции-по-цветам'/f'Поле-{si:02d}-{name}.svg')
  for c,r in paintMasks.items():save(r,folder/'Покраска'/f'Поле-{si:02d}-маска-{c}.svg')
 with open(folder/'Расположение-деталей.csv','w',encoding='utf-8-sig',newline='')as f:
  w=csv.writer(f);w.writerow(['Деталь','Исходная деталь','Комплект','Слой','Поле','Перенос X мм','Перенос Y мм','Поворот','Отражение','Масштаб','Страны'])
  for q in translated:w.writerow([q['id'],q['source_id'],q['kit'],q['tier'],q['sheet'],q['dx_mm'],q['dy_mm'],0,'Нет',1,' '.join(q['regions'])])
 output={'pieces':translated,'kits':N['kits'],'parts_per_kit':len(D['pieces']),'country_titles_per_kit':len(labels),'red_texts_in_source':0,'live_text':True,'stock_mm':[740,740],'layout_checks':N,'colors':D['colors'],'source_plan_sha256':hashlib.sha256((P/'data/production-plan.json').read_bytes()).hexdigest()};(folder/'manufacturing.json').write_text(json.dumps(output,ensure_ascii=False));print('EXPORTED',folder.name,N['kits'],'kits',len(translated),'parts',flush=True)
export(P,P/'data/layout.json');export(P/'Один-комплект',P/'data/layout-single.json')
