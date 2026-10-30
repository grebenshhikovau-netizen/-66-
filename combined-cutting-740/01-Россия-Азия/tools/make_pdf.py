import json,math,os
from pathlib import Path
from shapely.geometry import shape,box
from shapely import set_precision
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
P=Path(__file__).resolve().parent.parent;M=72/25.4;D=json.load(open(P/'data/production-plan.json'));O=Path(os.environ.get('AFRICA_OUTPUT',str(P)));O.mkdir(parents=True,exist_ok=True);pdfmetrics.registerFont(TTFont('Label','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'));pdfmetrics.registerFont(TTFont('Live',str(P/'Шрифт/OpenSans-Light.ttf')))
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for a in getattr(g,'geoms',[])for p in ps(a)]
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[g]if not g.is_empty else[]
 return[p for a in getattr(g,'geoms',[])for p in lines(a)]
def fill(c,g,color,stroke=False,width=.05):
 p=c.beginPath()
 for q in ps(set_precision(g,.000001)):
  q=orient(q,-1)
  for ring in [q.exterior,*q.interiors]:
   xy=list(ring.coords);p.moveTo(*xy[0])
   for pt in xy[1:]:p.lineTo(*pt)
   p.close()
 c.setFillColorRGB(*color);c.setStrokeColorRGB(*color);c.setLineWidth(width);c.drawPath(p,fill=not stroke,stroke=stroke,fillMode=1)
def trace(c,g,color=(1,0,0)):
 p=c.beginPath()
 for q in lines(g):
  xy=list(q.coords);p.moveTo(*xy[0])
  for pt in xy[1:]:p.lineTo(*pt)
 c.setStrokeColorRGB(*color);c.setLineWidth(.05);c.setLineCap(1);c.setLineJoin(1);c.drawPath(p,stroke=1,fill=0)
def title(c,a,color=None):
 if color is None:color=(0,0,1)if a['color']=='#0000ff'else(1,0,0)
 c.saveState();c.transform(*a['matrix']);c.scale(1,-1);c.setFillColorRGB(*color);c.setFont('Live',a['font_size_mm'])
 for ln in a['lines']:c.drawString(ln['x_em']*a['font_size_mm'],-ln['y_em']*a['font_size_mm'],ln['text'])
 c.restoreState()
def drawing(c,rows):
 for q in rows:
  trace(c,shape(q['red_internal']));fill(c,shape(q['red_texture']),(1,0,0))
  for a in q['labels']:title(c,a)
  for a in q['markers']:fill(c,shape(a['geom']),(1,0,0))
 for q in rows:fill(c,shape(q['geom']),(0,0,0),True)
def text(c,x,y,s,size=10,color=(.14,.14,.14)):
 c.setFillColorRGB(*color);c.setFont('Label',size);c.drawString(x,y,s)
DATA=json.load(open(O/'manufacturing.json'));ROWS=DATA['pieces'];sheets=sorted({p['sheet']for p in ROWS});numbers={p['id']:i+1 for i,p in enumerate(sorted(ROWS,key=lambda q:q['id']))}
for si in sheets:
 rows=[p for p in ROWS if p['sheet']==si];c=canvas.Canvas(str(O/f'Поле-{si:02d}-740x740.pdf'),pagesize=(740*M,740*M));c.setTitle(f"{D['title']} / поле {si} / 740 × 740 мм / 1:1");c.saveState();c.translate(0,740*M);c.scale(M,-M);drawing(c,rows);c.restoreState();c.save()
W,H=landscape(A3);c=canvas.Canvas(str(O/'Схема-раскладки-с-номерами.pdf'),pagesize=(W,H))
for si in sheets:
 rows=[p for p in ROWS if p['sheet']==si];text(c,25,H-32,D['title'].upper(),17);text(c,25,H-54,f"Поле {si} из {len(sheets)} / {len(rows)} деталей / только перенос, без поворотов и изменения масштаба",10);s=(H-105)/740;xx=25;yy=22;c.saveState();c.translate(xx,yy+740*s);c.scale(s,-s);drawing(c,rows);c.setLineWidth(.2);c.setStrokeColorRGB(.6,.6,.6);c.rect(0,0,740,740,stroke=1,fill=0);c.restoreState()
 for p in rows:
  q=shape(p['geom']).representative_point();x=xx+q.x*s;y=yy+(740-q.y)*s;c.setFillColorRGB(1,1,1);c.circle(x,y,4.3,fill=1,stroke=0);c.setFillColorRGB(0,0,0);c.setFont('Label',5.5);c.drawCentredString(x,y-1.8,str(numbers[p['id']]))
 tx=xx+740*s+20;y=H-100;text(c,tx,y,'ЦВЕТА ОПЕРАЦИЙ',11)
 for caption,col in [('Чёрный — сквозная резка',(0,0,0)),('Красный — города, области, разметка',(1,0,0)),('Синий — названия стран',(0,0,1))]:y-=25;text(c,tx,y,caption,9,col)
 for caption in ['Номера — только на этой схеме.','Соответствие номеров — на следующих страницах.','Рабочие SVG/PDF: 740 × 740 мм, 1:1.','Установить OpenSans-Light.ttf.']:y-=25;text(c,tx,y,caption,9)
 c.showPage()
ordered=sorted(ROWS,key=lambda p:p['id'])
for start in range(0,len(ordered),90):
 page=ordered[start:start+90];text(c,28,H-35,D['title']+' / соответствие номеров и деталей',17);per=math.ceil(len(page)/3)
 for col in range(3):
  x=28+col*(W-56)/3;text(c,x,H-80,'№     Поле    Слой     Деталь',11)
  for j,p in enumerate(page[col*per:(col+1)*per]):text(c,x,H-108-j*20,f"{numbers[p['id']]:02d}       {p['sheet']}         {p['tier']}       {p['id']}",10)
 text(c,28,32,'Толщина каждой детали — 3 мм. Нумерация справочная; эти страницы не отправляются на резку.',9);c.showPage()
c.save()
# Each height is shown as the physically merged approved assembly, before nesting.
c=canvas.Canvas(str(O/'Слои-и-сборка.pdf'),pagesize=(W,H));base=shape(D['layers'][0]);x0,y0,x1,y1=base.bounds;s=min((W-90)/(x1-x0),(H-170)/(y1-y0))
for i in range(len(D['layers'])):
 rows=[p for p in D['pieces']if p['tier']==i+1];text(c,30,H-35,f"{D['title']} / слой {i+1} / верх {(i+1)*3} мм / {len(rows)} деталей",17);text(c,30,H-58,'Общие физические детали; положение сборки. Цвет Скандинавии — только для различения отдельного блока.',9);c.saveState();c.translate(45,H-100);c.scale(s,-s);c.translate(-x0,-y0);fill(c,base,(.96,.96,.96))
 for p in rows:
  g=shape(p['geom']);fill(c,g,(.70,.82,.87)if p.get('block')=='SCAND'else(.91,.84,.71));fill(c,g,(.12,.12,.12),True,.15);trace(c,shape(p['red_internal']),(.65,.16,.1))
  for a in D['labels']:
   if a['piece']==p['id']:title(c,a,(.20,.15,.10))
 c.restoreState();text(c,30,45,'Красные линии на рабочем файле — гравировка. Под закрывающими слоями границ нет.',9);c.showPage()
c.save()
if D.get('scandinavia_separate'):
 pp=[p for p in D['pieces']if p.get('block')=='SCAND'];base=unary_union([shape(p['geom'])for p in pp if p['tier']==1]);x0,y0,x1,y1=base.bounds;s=min((W-100)/(x1-x0),(H-170)/(y1-y0));c=canvas.Canvas(str(O/'Скандинавия-отдельный-блок.pdf'),pagesize=(W,H))
 for tier in sorted({p['tier']for p in pp}):
  text(c,30,H-38,f'НОРВЕГИЯ + ШВЕЦИЯ + ФИНЛЯНДИЯ / слой {tier}',18);text(c,30,H-62,'Самостоятельный блок. Общих физических деталей с Россией, Европой и Африкой нет.',10);c.saveState();c.translate(45,H-110);c.scale(s,-s);c.translate(-x0,-y0);fill(c,base,(.96,.96,.96))
  for p in pp:
   if p['tier']!=tier:continue
   fill(c,shape(p['geom']),(.71,.83,.88));fill(c,shape(p['geom']),(.1,.1,.1),True,.15);trace(c,shape(p['red_internal']))
   for a in D['labels']:
    if a['piece']==p['id']:title(c,a,(.15,.15,.15))
  c.restoreState();c.showPage()
 c.save()
c=canvas.Canvas(str(O/'Водные-ступени.pdf'),pagesize=(W,H));text(c,35,H-40,'РЕКИ: СКВОЗНЫЕ РУСЛА И СОГЛАСОВАННЫЕ ПЕРЕМЫЧКИ',20);text(c,35,H-67,'Узкий нижний пропил и более широкие верхние русла. В отдельных накладках оставлены верхние перемычки.',11);x=150;y=H-430;k=25;gap=.70;uppergap=1.4;c.setFillColorRGB(.03,.48,.63);c.rect(x,y-16,15*k,16,fill=1,stroke=0)
for layer,w in [(0,gap),(1,uppergap),(2,uppergap)]:
 c.setFillColorRGB(.89,.8,.64);c.rect(x,y+layer*3*k,(7.5-w/2)*k,3*k,fill=1,stroke=0);c.rect(x+(7.5+w/2)*k,y+layer*3*k,(7.5-w/2)*k,3*k,fill=1,stroke=0)
text(c,610,y+195,'Накладки: широкое русло',14);text(c,610,y+117,'Накладки: широкое русло',14);text(c,610,y+40,'Основание: узкий пропил',14);text(c,35,155,'Сечение обычного открытого участка. Верхние перемычки показаны отдельно в Перемычки-на-реках.pdf.',11)
if D['batch']=='WEST':text(c,35,125,'Исключение: пирамида Египта и её опоры цельные; Нил прерывается на этом участке, как утверждено.',11)
text(c,35,95,'Синее — справочное оргстекло под водой. Его производственный контур в этот раскрой не входит.',10);c.save();print('PDF READY',len(ROWS),'parts',len(sheets),'sheets',len(D['labels']),'texts',flush=True)
