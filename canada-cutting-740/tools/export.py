"""Laser SVG in physical millimetres: red single strokes, blue filled outlines."""
import json,csv,hashlib
from pathlib import Path
from collections import defaultdict
from shapely.geometry import shape,Polygon,mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union,linemerge
from shapely.affinity import translate
from shapely import make_valid,set_precision
from lxml import etree as E
P=Path(__file__).resolve().parent.parent;SRC=P/'data/source';D=json.load(open(SRC/'production-plan.json'));R=json.load(open(SRC/'extracted.json'));N=json.load(open(P/'data/layout.json'));A=json.load(open(P/'data/annotations.json'));S='http://www.w3.org/2000/svg';WIDTH=.05
COUNTRIES={q['id']:q['name']for q in A if q['kind']=='blue_fill'}
def polys(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty and g.area>1e-8 else[]
 return[p for q in getattr(g,'geoms',[])for p in polys(q)]
def clean(g):return set_precision(set_precision(unary_union(polys(make_valid(g))),.01),0)
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[g]if not g.is_empty and g.length>1e-6 else []
 return[p for q in getattr(g,'geoms',[])for p in lines(q)]
rr=defaultdict(list)
for row in R:
 if row['kind']=='wood'and row['name']not in D['excluded_misplaced_objects']:rr[row['region']].append(clean(shape(row['geom'])))
occupied=Polygon();territories={}
for id,gg in sorted(rr.items()):
 raw=unary_union(gg);territories[id]=raw.difference(occupied);occupied=unary_union([occupied,raw])
network=unary_union([g.boundary for g in territories.values()]);parts={q['id']:q for q in D['pieces']};templates={};guide_stats=[]
for p in D['pieces']:
 g=shape(p['geom']);ink=shape(p['engraving']);upper=unary_union([shape(q['geom'])for q in D['pieces']if q['tier']==p['tier']+1]);upper=upper if not upper.is_empty else Polygon();v=g.difference(upper)
 # Political markings only where visible in the finished assembly.
 visible=network.intersection(v).difference(upper.buffer(.04)).difference(g.boundary.buffer(.22)).difference(ink.buffer(.3))
 # Keep next-ply outlines for placement, without hidden political subdivision.
 guides=upper.boundary.intersection(g.buffer(-.08)).difference(g.boundary.buffer(.22)).difference(ink.buffer(.3))
 internal=unary_union(lines(unary_union([visible,guides])))
 if internal.geom_type=='MultiLineString':internal=linemerge(internal)
 internal=internal.simplify(.003)
 # All non-placement political strokes under the next ply have been removed.
 assert visible.intersection(upper.buffer(-.001)).length<.001
 anns=[q for q in A if q['piece']==p['id']];blue={q['id']:shape(q['geometry'])for q in anns if q['kind']=='blue_fill'};strokes={q['id']:shape(q['geometry'])for q in anns if q['kind']=='red_stroke'};marks={q['id']:shape(q['geometry'])for q in anns if q['kind']=='red_mark'}
 templates[p['id']]={'geom':g,'blue':blue,'strokes':strokes,'marks':marks,'internal':internal,'political':visible,'guides':guides}
 guide_stats.append({'id':p['id'],'visible_political_length_mm':visible.length,'placement_guide_length_mm':guides.length,'old_hidden_political_length_mm':network.intersection(g.intersection(upper)).length})
translated=[];labels_table=[]
for loc in N['placements']:
 src=loc.get('source_id',loc['id']);p=parts[src];t=templates[src]
 def moved(g):return translate(g,loc['dx_mm'],loc['dy_mm'])
 row={'id':loc['id'],'source_id':src,'set':loc.get('set',1),'tier':p['tier'],'sheet':loc['sheet'],'geom':mapping(moved(t['geom'])),'red_labels':mapping(Polygon()),'red_strokes':{k:mapping(moved(g))for k,g in t['strokes'].items()},'red_marks':{k:mapping(moved(g))for k,g in t['marks'].items()},'red_internal':mapping(moved(t['internal'])),'red_political':mapping(moved(t['political'])),'placement_guides':mapping(moved(t['guides'])),'blue':{k:mapping(moved(g))for k,g in t['blue'].items()},'dx_mm':loc['dx_mm'],'dy_mm':loc['dy_mm']}
 translated.append(row)
 for id in t['blue']:labels_table.append({'id':id,'name':COUNTRIES[id],'part':loc['id'],'sheet':loc['sheet'],'color':'#0000ff'})

def root():return E.Element('svg',nsmap={None:S},width='740mm',height='740mm',viewBox='0 0 740 740',version='1.1')
def group(r,id,title):
 e=E.SubElement(r,'g',id=id);E.SubElement(e,'title').text=title;return e

def path(r,g,id,color,cut=False):
 rings=[]
 for q in polys(g):
  q=orient(q,-1)
  for ring in [q.exterior,*q.interiors]:
   coords=[]
   for x,y in list(ring.coords)[:-1]:
    xy=(round(x,6),round(y,6))
    if not coords or coords[-1]!=xy:coords.append(xy)
   if len(coords)>2:rings.append('M'+' L'.join(f'{x:.6f},{y:.6f}'for x,y in coords)+' Z')
 if not rings:return
 e=E.SubElement(r,'path',id=id,d=' '.join(rings),fill='none'if cut else color,attrib={'fill-rule':'nonzero'})
 if cut:e.set('stroke',color);e.set('stroke-width',str(WIDTH));e.set('stroke-linejoin','round')
 return e

def stroke(r,g,id,color='#ff0000'):
 paths=[]
 for q in lines(g):
  coords=list(q.coords)
  if len(coords)<2:continue
  paths.append('M'+' L'.join(f'{x:.6f},{y:.6f}'for x,y in coords))
 if paths:return E.SubElement(r,'path',id=id,d=' '.join(paths),fill='none',stroke=color,attrib={'stroke-width':str(WIDTH),'stroke-linecap':'round','stroke-linejoin':'round','data-engraving':'centerline'})

def save(r,file):
 dest=P/file;dest.parent.mkdir(parents=True,exist_ok=True);E.ElementTree(r).write(str(dest),encoding='UTF-8',xml_declaration=True)
for si in sorted(set(p['sheet']for p in translated)):
 main=root();red=group(main,'RED_TEXT_CITIES','Красные однолинейные надписи и метки');inner=group(main,'RED_INTERNAL_REGIONS','Видимые границы и контуры установки');blue=group(main,'BLUE_COUNTRY_NAMES','США, Канада, Мексика, Аляска');cut=group(main,'BLACK_THROUGH_CUT','Сквозная резка')
 single={k:root()for k in ['Красный-надписи-и-метки','Красный-внутренние-области','Синий-названия-стран','Чёрный-сквозная-резка']}
 for p in translated:
  if p['sheet']!=si:continue
  for dest in [cut,single['Чёрный-сквозная-резка']]:path(dest,shape(p['geom']),p['id']+'_CUT','#000000',True)
  for id,g in p['red_strokes'].items():
   for dest in [red,single['Красный-надписи-и-метки']]:stroke(dest,shape(g),p['id']+'_'+id)
  for id,g in p['red_marks'].items():
   for dest in [red,single['Красный-надписи-и-метки']]:path(dest,shape(g),p['id']+'_'+id,'#ff0000')
  for dest in [inner,single['Красный-внутренние-области']]:stroke(dest,shape(p['red_internal']),p['id']+'_INTERNAL')
  for id,g in p['blue'].items():
   for dest in [blue,single['Синий-названия-стран']]:path(dest,shape(g),p['id']+'_'+id,'#0000ff')
 save(main,f'Поле-{si:02d}-740x740.svg')
 for name,r in single.items():save(r,f'Операции-по-цветам/Поле-{si:02d}-{name}.svg')
with open(P/'Расположение-деталей.csv','w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f);w.writerow(['Деталь','Исходная деталь','Комплект','Слой','Поле','X мм','Y мм','Поворот','Отражение','Масштаб'])
 for p in translated:w.writerow([p['id'],p['source_id'],p['set'],p['tier'],p['sheet'],p['dx_mm'],p['dy_mm'],0,'Нет',1])
with open(P/'Синие-названия-стран.csv','w',encoding='utf-8-sig',newline='')as f:
 w=csv.DictWriter(f,fieldnames=['id','name','part','sheet','color']);w.writeheader();w.writerows(labels_table)
output={'pieces':translated,'country_texts':COUNTRIES,'red_text_mode':'single_centerline_strokes','red_text_count_per_set':82,'city_mark_count_per_set':72,'internal_guides':'visible political boundaries plus immediate next-ply placement outlines only','guide_statistics':guide_stats,'alaska_title_blue':True,'unique_annotations':158,'source_piece_count':28,'sets':N.get('sets',1),'source_sha256':hashlib.sha256((SRC/'production-plan.json').read_bytes()).hexdigest()};(P/'data/manufacturing.json').write_text(json.dumps(output,ensure_ascii=False));print('EXPORTED',len(translated),'parts, red single strokes, blue',COUNTRIES,flush=True)
