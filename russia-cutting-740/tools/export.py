import json,csv,hashlib
from pathlib import Path
from lxml import etree as E
from shapely.geometry import shape,mapping,Polygon
from shapely.geometry.polygon import orient
from shapely.affinity import translate
from shapely import set_precision
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));N=json.load(open(P/'data/layout.json'));S='http://www.w3.org/2000/svg'
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for a in getattr(g,'geoms',[])for p in ps(a)]
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[g]if not g.is_empty and g.length>1e-6 else[]
 return[p for a in getattr(g,'geoms',[])for p in lines(a)]
def root():return E.Element('svg',nsmap={None:S},width='740mm',height='740mm',viewBox='0 0 740 740',version='1.1')
def group(r,id,title):
 e=E.SubElement(r,'g',id=id);E.SubElement(e,'title').text=title;return e
def polygon(r,g,id,color,cut=False):
 rings=[]
 for q in ps(set_precision(g,.000001)):
  q=orient(q,-1)
  for ring in [q.exterior,*q.interiors]:
   coords=[]
   for x,y in list(ring.coords)[:-1]:
    xy=(round(x,6),round(y,6))
    if not coords or coords[-1]!=xy:coords.append(xy)
   if len(coords)>2:rings.append('M'+' L'.join(f'{x:.6f},{y:.6f}'for x,y in coords)+' Z')
 if not rings:return
 el=E.SubElement(r,'path',id=id,d=' '.join(rings),fill='none'if cut else color,attrib={'fill-rule':'nonzero'})
 if cut:el.set('stroke',color);el.set('stroke-width','.05');el.set('stroke-linejoin','round')
def stroke(r,g,id):
 paths=['M'+' L'.join(f'{x:.6f},{y:.6f}'for x,y in q.coords)for q in lines(g)]
 if paths:E.SubElement(r,'path',id=id,d=' '.join(paths),fill='none',stroke='#ff0000',attrib={'stroke-width':'.05','stroke-linecap':'round','stroke-linejoin':'round'})
def text(r,a,id):
 el=E.SubElement(r,'text',id=id,fill=a['color'],stroke='none',attrib={'font-family':'Open Sans Light','font-size':format(a['font_size_mm'],'.9f'),'font-weight':'300','font-style':'normal','font-kerning':'none','letter-spacing':'0','transform':'matrix('+','.join(format(x,'.12f')for x in a['matrix'])+')','style':"font-kerning:none;font-feature-settings:'kern' 0"})
 for ln in a['lines']:
  e=E.SubElement(el,'tspan',x=format(ln['x_em']*a['font_size_mm'],'.9f'),y=format(ln['y_em']*a['font_size_mm'],'.9f'));e.text=ln['text']
def save(r,file):
 file.parent.mkdir(parents=True,exist_ok=True);E.ElementTree(r).write(str(file),encoding='UTF-8',xml_declaration=True)
parts={p['id']:p for p in D['pieces']};translated=[]
for loc in N['placements']:
 p=parts[loc['id']]
 def move(g):return translate(g,loc['dx_mm'],loc['dy_mm'])
 ll=[];mm=[]
 for a in D['labels']:
  if a['piece']!=p['id']:continue
  q={**a,'matrix':a['matrix'][:]};q['matrix'][4]+=loc['dx_mm'];q['matrix'][5]+=loc['dy_mm'];q['geometry']=mapping(move(shape(a['geometry'])));q['bbox']=mapping(move(shape(a['bbox'])));ll.append(q)
 for a in D['city_markers']:
  if a['piece']==p['id']:mm.append({**a,'geom':mapping(move(shape(a['geom'])))})
 translated.append({**loc,'tier':p['tier'],'geom':mapping(move(shape(p['geom']))),'visible':mapping(move(shape(p['visible']))),'red_internal':mapping(move(shape(p['red_internal']))),'red_political':mapping(move(shape(p['red_political']))),'placement_guides':mapping(move(shape(p['placement_guides']))),'labels':ll,'markers':mm})
for si in sorted(set(p['sheet']for p in translated)):
 main=root();red=group(main,'RED_TEXT_AND_CITIES','Редактируемые подписи регионов и городов, метки городов');internal=group(main,'RED_INTERNAL','Видимые границы, выноски и контуры установки');blue=group(main,'BLUE_COUNTRY','Название страны');cut=group(main,'BLACK_THROUGH_CUT','Сквозная резка');ops={name:root()for name in ['Красный-текст-и-города','Красный-разметка','Синий-страна','Чёрный-резка']}
 for p in translated:
  if p['sheet']!=si:continue
  for r in [cut,ops['Чёрный-резка']]:polygon(r,shape(p['geom']),p['id']+'_CUT','#000000',True)
  for r in [internal,ops['Красный-разметка']]:stroke(r,shape(p['red_internal']),p['id']+'_INTERNAL')
  for a in p['labels']:
   for r in ([blue,ops['Синий-страна']]if a['color']=='#0000ff'else[red,ops['Красный-текст-и-города']]):text(r,a,p['id']+'_'+a['id'])
  for a in p['markers']:
   for r in [red,ops['Красный-текст-и-города']]:polygon(r,shape(a['geom']),p['id']+'_'+a['id']+'_MARK','#ff0000')
 save(main,P/f'Поле-{si:02d}-740x740.svg')
 for name,r in ops.items():save(r,P/'Операции-по-цветам'/f'Поле-{si:02d}-{name}.svg')
output={'pieces':translated,'stock_mm':[740,740],'physical_parts':len(translated),'layers':[q['pieces']for q in D['summary']],'country_titles':1,'city_titles':90,'regional_titles':81,'regions_represented':84,'all_titles_editable':True,'layout':N,'source_plan_sha256':hashlib.sha256((P/'data/production-plan.json').read_bytes()).hexdigest()};(P/'manufacturing.json').write_text(json.dumps(output,ensure_ascii=False))
with open(P/'Расположение-деталей.csv','w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f);w.writerow(['Деталь','Слой','Поле','X мм','Y мм','Поворот','Отражение','Масштаб'])
 for p in translated:w.writerow([p['id'],p['tier'],p['sheet'],p['dx_mm'],p['dy_mm'],0,'Нет',1])
with open(P/'Надписи.csv','w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f);w.writerow(['ID','Текст','Тип','Деталь','Слой','Размер шрифта мм','Выноска'])
 for a in D['labels']:w.writerow([a['id'],a['text'],a['kind'],a['piece'],a['tier'],round(a['font_size_mm'],3),'Да'if a.get('leader')else'Нет'])
with open(P/'Города.csv','w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f);w.writerow(['Город','Долгота','Широта','Код области','Метка на детали','Смещение на берег мм'])
 for a in D['city_markers']:w.writerow([a['name'],a['lon'],a['lat'],a['region'],a['piece'],round(a['bank_shift_mm'],3)])
print('EXPORTED',len(translated),'parts',len(D['labels']),'live texts',len(D['city_markers']),'city marks',flush=True)
