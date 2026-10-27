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
DATA=json.load(open(O/'manufacturing.json'));ROWS=DATA['pieces']
for si in sorted(set(p['sheet']for p in ROWS)):
 rows=[q for q in ROWS if q['sheet']==si];c=canvas.Canvas(str(O/f'Поле-{si:02d}-740x740.pdf'),pagesize=(740*M,740*M));c.setTitle(f'Африка / поле {si} / 740 x 740 мм / 1:1');c.saveState();c.translate(0,740*M);c.scale(M,-M);drawing(c,rows);c.restoreState();c.save()
 W,H=landscape(A3);c=canvas.Canvas(str(O/'Схема-раскладки-с-номерами.pdf'),pagesize=(W,H));text(c,24,H-32,'АФРИКА / РАСКРОЙ 740 × 740 ММ',19);text(c,24,H-52,f"{len(ROWS)} деталей / 6 уровней фанеры по 3 мм / без поворотов, отражений и изменения масштаба",10);s=(H-100)/740;x0=24;y0=22;c.saveState();c.translate(x0,y0+740*s);c.scale(s,-s);drawing(c,rows);c.setLineWidth(.2);c.setStrokeColorRGB(.6,.6,.6);c.rect(0,0,740,740,stroke=1,fill=0);c.restoreState();ordered=sorted(rows,key=lambda q:q['id']);numbers={q['id']:i+1 for i,q in enumerate(ordered)}
 for q in rows:
  point=shape(q['geom']).representative_point();x=x0+point.x*s;y=y0+(740-point.y)*s;c.setFillColorRGB(1,1,1);c.circle(x,y,4.3,fill=1,stroke=0);c.setFillColorRGB(0,0,0);c.setFont('Label',5.5);c.drawCentredString(x,y-1.8,str(numbers[q['id']]))
 tx=x0+740*s+22;y=H-90;text(c,tx,y,'ЦВЕТА ОПЕРАЦИЙ',11);y-=24
 for caption,col in [('Чёрный — сквозная резка',(0,0,0)),('Красный — города, фактура и разметка',(1,0,0)),('Синий — названия стран',(0,0,1))]:text(c,tx,y,caption,9,col);y-=20
 y-=12
 for caption in ['Все надписи — редактируемый текст.','Установить OpenSans-Light.ttf.','Импортировать в миллиметрах, 1:1.','Номера — только в справочной схеме.']:
  text(c,tx,y,caption,9);y-=18
 y-=25;per=math.ceil(len(ordered)/2)
 for col in [0,1]:
  x=tx+col*177;text(c,x,y,'№   Слой  Деталь',9)
  for k,q in enumerate(ordered[col*per:(col+1)*per]):text(c,x,y-20-k*15,f"{numbers[q['id']]:02d}     {q['tier']}      {q['id']}",8)
 c.save()
# A separate vector reference page for each source ply.
W,H=landscape(A3);c=canvas.Canvas(str(O/'Слои-и-сборка.pdf'),pagesize=(W,H));base=shape(D['layers'][0]).union(shape(D['water_base_union']));x0,y0,x1,y1=base.bounds;s=min((W-100)/(x1-x0),(H-180)/(y1-y0))
for tier in range(1,len(D['layers'])+1):
 rows=[q for q in D['pieces']if q['tier']==tier];text(c,35,H-40,f"АФРИКА / СЛОЙ {tier} / {len(rows)} деталей / верх {tier*3} мм",18);text(c,35,H-64,'Справочная схема. Положение исходное; красные линии — гравировка и установка следующего слоя.',10);c.saveState();c.translate(45,H-115);c.scale(s,-s);c.translate(-x0,-y0);fill(c,base,(.96,.96,.96))
 for q in rows:
  fill(c,shape(q['geom']),(.88,.80,.65));trace(c,shape(q['red_internal']));fill(c,shape(q['red_texture']),(1,0,0));fill(c,shape(q['geom']),(0,0,0),True)
  for a in D['labels']:
   if a['piece']==q['id']:title(c,a)
  for a in D['city_markers']:
   if a['piece']==q['id']:fill(c,shape(a['geom']),(1,0,0))
 c.restoreState();text(c,35,74,'Города и названия стран находятся на открытых поверхностях и не перекрываются верхними деталями.',10);text(c,35,52,'Политические границы под верхними слоями удалены; сохранены контуры установки непосредственного следующего слоя.',10);c.showPage()
c.save()
# Engineering water section and actual lake profiles, all vector geometry.
c=canvas.Canvas(str(O/'Водные-ступени.pdf'),pagesize=(W,H));text(c,35,H-40,'АФРИКА / ВОДА СТУПЕНЬКОЙ',20);text(c,35,H-66,'Реки: нижний вырез примерно вдвое уже верхнего. Озёра: нижний контур сужен по ширине.',11)
x=85;y=H-340;k=25;gap1=.9;gap2=1.8;cx=x+6*k
c.setFillColorRGB(.03,.48,.63);c.rect(x,y-15,12*k,15,fill=1,stroke=0)
for layer,gap in [(0,gap1),(1,gap2)]:
 c.setFillColorRGB(.89,.80,.64);top=y+layer*3*k;c.rect(x,top,(6-gap/2)*k,3*k,fill=1,stroke=0);c.rect(cx+gap/2*k,top,(6-gap/2)*k,3*k,fill=1,stroke=0)
text(c,x,y+6*k+20,'Верхний вырез рек: 1,2–1,7 мм',11);text(c,x,y-43,'Нижний вырез рек: 0,6–0,85 мм',11);text(c,x,y-66,'Фанера: 3 мм на слой. Снизу — оргстекло.',10)
for j,name in enumerate(['Нил','Танганьика']):
 upper=shape(D['upper_water'][name]);lower=shape(D['base_water'][name]);a,b,d,e=upper.bounds;ss=min(245/(d-a),270/(e-b));xx=500+j*320;yy=H-145;text(c,xx,yy+35,name.upper(),15);c.saveState();c.translate(xx,yy);c.scale(ss,-ss);c.translate(-a,-b);fill(c,upper,(.65,.83,.87));fill(c,lower,(.02,.43,.62));fill(c,upper,(0,0,0),True);fill(c,lower,(0,0,0),True);c.restoreState();text(c,xx,H-455,'Светлый контур — верхний вырез.',9);text(c,xx,H-475,'Тёмный — нижний сквозной.',9)
text(c,35,105,'Нил, Конго, Замбези и крупные озёра имеют суженную нижнюю прорезь.',11);text(c,35,82,'Под квадратным основанием пирамиды Египта Нил закрыт; ступени цельные.',10);text(c,35,58,'Масштаб этой схемы условный; для станка использовать рабочие SVG/PDF 740 × 740 мм.',10);c.save();print('PDF READY',len(ROWS),'parts',len(D['labels']),'texts',flush=True)
