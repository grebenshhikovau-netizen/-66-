"""Laser sheets: exact approved geometry, translation only, RGB process colors."""
import json,re,csv,hashlib,math
from pathlib import Path
from collections import defaultdict
from shapely.geometry import shape,Polygon,mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely.affinity import translate,rotate,scale
from shapely import make_valid,set_precision
from lxml import etree as E
P=Path(__file__).resolve().parent.parent;SRC=P/'data'/'source';D=json.load(open(SRC/'production-plan.json'));R=json.load(open(SRC/'extracted.json'));N=json.load(open(P/'data'/'layout.json'));S='http://www.w3.org/2000/svg';INK_WIDTH=.12
COUNTRIES={'TEXT_081':'Аляска','TEXT_043':'США','TEXT_050':'Канада','TEXT_058':'Коста-Рика','TEXT_059':'Никарагуа','TEXT_060':'Сальвадор','TEXT_061':'Гватемала','TEXT_062':'Гондурас','TEXT_063':'Мексика','TEXT_064':'Панама','TEXT_065':'Белиз'}
def polys(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty and g.area>.00000001 else[]
 return[p for q in getattr(g,'geoms',[])for p in polys(q)]
def clean(g):return set_precision(set_precision(unary_union(polys(make_valid(g))),.01),0)
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[g]
 return[p for q in getattr(g,'geoms',[])for p in lines(q)]
# Exact country text location: preserve all changes already accepted in the model.
groups=defaultdict(list)
for row in R:
 if row['kind']=='engraving':groups[re.sub(r'\.\d+$','',row['name'])].append(shape(row['geom']))
blue_source={};moves={m['source_id']:m for m in D['annotation_moves']}
for id,name in COUNTRIES.items():
 raw=unary_union(groups[id]);g=clean(raw);m=moves.get(id)
 if m:
  if 'rotation_degrees'in m:
   g=scale(raw,xfact=m['scale'],yfact=m['scale'],origin='centroid');g=rotate(g,m['rotation_degrees'],origin='centroid')
  else:g=scale(g,xfact=m['scale'],yfact=m['scale'],origin='centroid')
  g=translate(g,m['dx_mm'],m['dy_mm'])
 blue_source[id]=g
# Reconstruct only non-cut political boundaries. Disjoint territories avoid double lines.
rr=defaultdict(list)
for row in R:
 if row['kind']=='wood' and row['name']not in D['excluded_misplaced_objects']:rr[row['region']].append(clean(shape(row['geom'])))
occupied=Polygon();territories={}
for id,gg in sorted(rr.items()):
 raw=unary_union(gg);territories[id]=raw.difference(occupied);occupied=unary_union([occupied,raw])
network=unary_union([g.boundary for g in territories.values()]);parts={p['id']:p for p in D['pieces']};translated=[];labels_table=[]
for loc in N['placements']:
 p=parts[loc['id']];ink=shape(p['engraving']);g=shape(p['geom']);v=unary_union(polys(make_valid(shape(p['visible']))));blue={}
 for id,b in blue_source.items():
  if ink.intersection(b).area<.0001:continue
  q=ink.intersection(b.buffer(.025))
  if q.area>.0001:blue[id]=q;labels_table.append({'id':id,'name':COUNTRIES[id],'part':p['id'],'sheet':loc['sheet'],'color':'#0000ff'})
 blueall=unary_union(list(blue.values()));red=ink.difference(blueall)
 # Render the red border as a closed 0.12 mm filled band so all red data can be scanned.
 upper=unary_union([shape(q['geom']).boundary for q in D['pieces']if q['tier']==p['tier']+1])
 internal=unary_union([network,upper]).intersection(g.buffer(-.08)).difference(g.boundary.buffer(.22)).difference(ink.buffer(.3))
 internal=unary_union(lines(internal)).buffer(INK_WIDTH/2,cap_style=2,join_style=2)
 if not internal.is_empty:internal=internal.intersection(set_precision(g,.000001)).difference(g.boundary.buffer(.18))
 def moved(a):return translate(a,loc['dx_mm'],loc['dy_mm'])
 translated.append({'id':p['id'],'tier':p['tier'],'sheet':loc['sheet'],'geom':mapping(moved(g)),'red_labels':mapping(moved(red)),'red_internal':mapping(moved(internal)),'blue':{id:mapping(moved(b))for id,b in blue.items()},'dx_mm':loc['dx_mm'],'dy_mm':loc['dy_mm'],'source_engraving':mapping(ink)})
 assert red.union(blueall).symmetric_difference(ink).area<.000001
 assert internal.difference(g).area<.000001
assert len(labels_table)==len(COUNTRIES),(len(labels_table),labels_table)
# Complete working page in millimetres. No stock frame, part numbers, or hidden objects.
def root():return E.Element('svg',nsmap={None:S,'inkscape':'http://www.inkscape.org/namespaces/inkscape'},width='740mm',height='740mm',viewBox='0 0 740 740',version='1.1')
def group(r,id,title):
 e=E.SubElement(r,'g',id=id);E.SubElement(e,'title').text=title;return e
def path(r,g,id,color,cut=False):
 rings=[]
 for q in polys(g):
  pp=orient(q,-1)
  for ring in [pp.exterior,*pp.interiors]:
   coords=[]
   for x,y in list(ring.coords)[:-1]:
    q=(round(x,6),round(y,6))
    if not coords or coords[-1]!=q:coords.append(q)
   if len(coords)<3:continue
   rings.append('M'+' L'.join(f'{x:.6f},{y:.6f}'for x,y in coords)+' Z')
 if not rings:return
 e=E.SubElement(r,'path',id=id,d=' '.join(rings),fill='none'if cut else color,attrib={'fill-rule':'nonzero'})
 if cut:e.set('stroke',color);e.set('stroke-width','0.05');e.set('stroke-linejoin','round')
 return e

def save(r,file):
 dest=P/file;dest.parent.mkdir(parents=True,exist_ok=True);E.ElementTree(r).write(str(dest),encoding='UTF-8',xml_declaration=True)
for si in sorted(set(p['sheet']for p in translated)):
 main=root();red=group(main,'RED_TEXT_CITIES','#ff0000 — надписи и метки городов');inner=group(main,'RED_INTERNAL_REGIONS','#ff0000 — внутренние политические области');blue=group(main,'BLUE_COUNTRY_NAMES','#0000ff — названия стран');cut=group(main,'BLACK_THROUGH_CUT','#000000 — сквозная резка')
 single={k:root()for k in ['Красный-надписи-и-метки','Красный-внутренние-области','Синий-названия-стран','Чёрный-сквозная-резка']}
 for p in translated:
  if p['sheet']!=si:continue
  g=shape(p['geom']);path(cut,g,p['id']+'_CUT','#000000',True);path(single['Чёрный-сквозная-резка'],g,p['id']+'_CUT','#000000',True)
  for dest in [red,single['Красный-надписи-и-метки']]:path(dest,shape(p['red_labels']),p['id']+'_TEXT','#ff0000')
  for dest in [inner,single['Красный-внутренние-области']]:path(dest,shape(p['red_internal']),p['id']+'_INTERNAL','#ff0000')
  for id,g in p['blue'].items():
   for dest in [blue,single['Синий-названия-стран']]:path(dest,shape(g),p['id']+'_'+id,'#0000ff')
 save(main,f'Поле-{si:02d}-740x740.svg')
 for name,r in single.items():save(r,f'Операции-по-цветам/Поле-{si:02d}-{name}.svg')
with open(P/'Расположение-деталей.csv','w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f);w.writerow(['Деталь','Слой фанеры','Поле','Перемещение X мм','Перемещение Y мм','Поворот градусов','Отражение','Масштаб'])
 for p in translated:w.writerow([p['id'],p['tier'],p['sheet'],p['dx_mm'],p['dy_mm'],0,'Нет',1])
with open(P/'Синие-названия-стран.csv','w',encoding='utf-8-sig',newline='')as f:
 w=csv.DictWriter(f,fieldnames=['id','name','part','sheet','color']);w.writeheader();w.writerows(labels_table)
output={'pieces':translated,'country_texts':COUNTRIES,'interior_mark_width_mm':INK_WIDTH,'internal_guides':'political boundaries and next-ply placement contours across each part','alaska_title_blue':True,'unique_annotations':D['unique_annotations'],'source_piece_count':len(parts),'source_sha256':hashlib.sha256((SRC/'production-plan.json').read_bytes()).hexdigest()};(P/'data'/'manufacturing.json').write_text(json.dumps(output,ensure_ascii=False));print('EXPORTED',len(translated),'parts;',len(labels_table),'country names; all original engraving retained',flush=True)
