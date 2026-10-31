"""Translate immutable source elements and export the two production patterns."""
import json,copy,hashlib,subprocess,os,csv,shutil
from pathlib import Path
from collections import Counter
from lxml import etree as E
from shapely.geometry import shape,box
from shapely.affinity import translate
from pypdf import PdfReader
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

P=Path(__file__).resolve().parent.parent;S='http://www.w3.org/2000/svg';K=25.4/72
L=json.loads((P/'layout.json').read_text());parts={p['id']:p for p in json.loads((P/'parts.json').read_text())}
root=E.parse(str(P/'source.svg')).getroot();source=[q for q in root.iter()if E.QName(q).localname in ['path','text']]
def fingerprint(e):
 return (e.tag,tuple(sorted(e.attrib.items())),e.text,tuple(fingerprint(q)for q in e))
def polygons(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in polygons(q)]
def path(g):
 out=[]
 for p in polygons(g):
  for r in [p.exterior,*p.interiors]:out.append('M'+' L'.join(f'{x:.5f},{y:.5f}'for x,y in r.coords)+' Z')
 return ' '.join(out)

n=L['repeat'];specs=[('main','Белый-01-основной-740x740')]
word='набор'if n==1 else'набора'if n in [2,3,4]else'наборов'
if L['supplementary']:specs.append(('supplementary',f'Белый-02-дополнительный-на-{n}-{word}-740x740'))
exports=[];report={'passed':True,'stock_mm':[740,740],'source_objects':len(source),
 'all_original_path_commands_and_attributes_preserved':True,'all_original_text_content_and_attributes_preserved':True,
 'rotation_degrees':0,'mirrored':False,'scale':1,'source_svg_sha256':hashlib.sha256((P/'source.svg').read_bytes()).hexdigest(),
 'repeat_main':n,'repeat_supplementary':1 if L['supplementary']else 0,'fields':[]}

with (P/'Переносы-деталей.csv').open('w',encoding='utf-8-sig',newline='')as f:
 writer=csv.writer(f);writer.writerow(['Лист','Группа исходника','Копия','Перенос X, мм','Перенос Y, мм','Поворот','Отражение','Масштаб'])
 for field,prefix in specs:
  out=E.Element('{'+S+'}svg',nsmap=root.nsmap,version='1.1',width='740mm',height='740mm',viewBox='0 0 740 740')
  expected=[];placed=[]
  for row in L[field]:
   group=E.SubElement(out,'{'+S+'}g',id=f"{row['source_id']}_copy{row['copy']:02d}",transform=f"matrix({K:.15f},0,0,{K:.15f},{row['dx_mm']:.9f},{row['dy_mm']:.9f})")
   for i in parts[row['source_id']]['members']:
    element=copy.deepcopy(source[i])
    group.append(element);expected.append(fingerprint(source[i]))
   g=translate(shape(parts[row['source_id']]['geom']),row['dx_mm'],row['dy_mm']);placed.append(g)
   writer.writerow([field,row['source_id'],row['copy'],row['dx_mm'],row['dy_mm'],0,'нет',1])
  dest=P/(prefix+'.svg');E.ElementTree(out).write(str(dest),encoding='utf-8',xml_declaration=True)
  reread=E.parse(str(dest));actual=[q for q in reread.iter()if E.QName(q).localname in ['path','text']]
  assert [fingerprint(q)for q in actual]==expected
  gap=1e9
  for j,g in enumerate(placed):
   assert box(5,5,735,735).covers(g)
   for h in placed[:j]:gap=min(gap,g.distance(h));assert gap>=3
  # Actual vector PDF retains the imported curves and the exact page size.
  env=dict(os.environ,XDG_CACHE_HOME='/tmp/ru-font-cache')
  with (P/'inkscape-export.log').open('a')as log:
   subprocess.run(['inkscape',str(dest),'--export-type=pdf',f'--export-filename={P/(prefix+".pdf")}'],check=True,env=env,stdout=log,stderr=log)
  pdf=PdfReader(P/(prefix+'.pdf'));b=pdf.pages[0].mediabox
  assert len(pdf.pages)==1 and abs(float(b.width)*K-740)<.01 and abs(float(b.height)*K-740)<.01
  # A separate visual aid adds light fills; it is never used for cutting.
  view=copy.deepcopy(out)
  fills=E.Element('{'+S+'}g',id='REFERENCE_FILLS')
  for g in placed:E.SubElement(fills,'{'+S+'}path',d=path(g),fill='#f3eee5',stroke='none')
  view.insert(0,fills)
  style=E.SubElement(view,'{'+S+'}style');style.text='g:not(#REFERENCE_FILLS) path { stroke-width:0.5 !important; }'
  preview_svg=P/(prefix+'-предпросмотр.svg');E.ElementTree(view).write(str(preview_svg),encoding='utf-8',xml_declaration=True)
  with (P/'inkscape-export.log').open('a')as log:
   subprocess.run(['inkscape',str(preview_svg),'--export-type=png','--export-width=2300','--export-background=white',f'--export-filename={P/(prefix+".png")}'],check=True,env=env,stdout=log,stderr=log)
  preview_svg.unlink()
  check={'field':field,'file':dest.name,'groups':len(placed),'objects':len(actual),'minimum_gap_mm':gap,
         'paths':sum(E.QName(q).localname=='path'for q in actual),'live_texts':sum(E.QName(q).localname=='text'for q in actual),
         'exact_original_content_in_translated_groups':True,'pdf_page_mm':[740,740]}
  report['fields'].append(check);exports.append({'field':field,'prefix':prefix});print('EXPORTED',check,flush=True)

mainids={q['source_id']for q in L['main']};extraids={q['source_id']for q in L['supplementary']}
assert not(mainids&extraids)and mainids|extraids==set(parts)
assert all(v==1 for v in Counter(q['source_id']for q in L['main']).values())
if extraids:assert all(v==n for v in Counter(q['source_id']for q in L['supplementary']).values())
source_indices=[i for p in parts.values()for i in p['members']];assert sorted(source_indices)==list(range(len(source)))
report['each_source_object_present_once_per_complete_set']=True
(P/'Проверка-раскладки.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(P/'exports.json').write_text(json.dumps(exports,ensure_ascii=False,indent=2))

pdfmetrics.registerFont(TTFont('RU','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
w,h=landscape(A3);c=canvas.Canvas(str(P/'Порядок-резки.pdf'),pagesize=(w,h));c.setFont('RU',20);c.drawString(30,h-38,'БЕЛЫЙ НАБОР / 740 × 740 ММ')
c.setFont('RU',12)
if extraids:
 c.drawString(30,h-65,f'Основной лист × {n} + дополнительный лист × 1 = {n} полных наборов.')
else:c.drawString(30,h-65,'Один прогон основного листа = один полный набор.')
c.setFont('RU',10);c.drawString(30,h-83,'Учитывается станок: центральная Россия внизу; мелкая разметка отведена от верхнего левого участка.')
for i,e in enumerate(exports):
 x=30+i*580;c.setFont('RU',13);c.drawString(x,h-109,'ОСНОВНОЙ ЛИСТ'if e['field']=='main'else f'ДОПОЛНИТЕЛЬНЫЙ: {n} КОПИЙ ОСТАТКА')
 c.drawImage(str(P/(e['prefix']+'.png')),x,150,width=530,height=530)
 c.saveState();c.setStrokeColorRGB(.5,.5,.5);c.setLineWidth(.7);c.setDash(4,3)
 side=530*220/740;c.rect(x,680-side,side,side,stroke=1,fill=0);c.setDash()
 c.setFont('RU',8);c.setFillColorRGB(.4,.4,.4);c.drawString(x+5,665,'220 × 220 мм');c.restoreState()
c.setFont('RU',11)
for i,t in enumerate(['На рабочих SVG/PDF нет справочной рамки и номеров. Надписи и исходные кривые не редактировались.',
 'Все группы только перенесены: поворот 0°, без отражения и изменения масштаба. Зазор не менее 3 мм, край не менее 5 мм.',
 'В этих картинках усилена толщина линий для просмотра; в рабочих SVG/PDF сохранены исходные толщины.']):c.drawString(30,105-i*21,t)
c.save()
print('VERIFIED',len(parts),'source groups',len(source),'objects',flush=True)
