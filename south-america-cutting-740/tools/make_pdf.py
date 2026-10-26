import json,math
from pathlib import Path
from shapely.geometry import shape
from shapely import set_precision
from shapely.geometry.polygon import orient
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
P=Path(__file__).resolve().parent.parent;M=72/25.4;D=json.load(open(P/'data/production-plan.json'));pdfmetrics.registerFont(TTFont('Label','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'));pdfmetrics.registerFont(TTFont('Live',str(P/'Шрифт/OpenSans-Light.ttf')))
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
def title(c,a,color=(0,0,1)):
 c.saveState();c.transform(*a['matrix']);c.scale(1,-1);c.setFillColorRGB(*color);c.setFont('Live',a['font_size_mm'])
 for ln in a['lines']:c.drawString(ln['x_em']*a['font_size_mm'],-ln['y_em']*a['font_size_mm'],ln['text'])
 c.restoreState()
def drawing(c,rows):
 for q in rows:
  trace(c,shape(q['red_internal']))
  for a in q['blue_titles']:title(c,a)
 for q in rows:fill(c,shape(q['geom']),(0,0,0),True)
def text(c,x,y,s,size=10,color=(.14,.14,.14)):
 c.setFillColorRGB(*color);c.setFont('Label',size);c.drawString(x,y,s)
def write(folder):
 data=json.load(open(folder/'manufacturing.json'));rows=data['pieces'];c=canvas.Canvas(str(folder/'Поле-01-740x740.pdf'),pagesize=(740*M,740*M));c.setTitle('Южная Америка: 740 × 740 мм / '+str(data['kits'])+' комплекта');c.saveState();c.translate(0,740*M);c.scale(M,-M);drawing(c,rows);c.restoreState();c.save()
 W,H=landscape(A3);c=canvas.Canvas(str(folder/'Схема-раскладки-с-номерами.pdf'),pagesize=(W,H));c.setTitle('Справочная схема раскладки');text(c,24,H-31,'ЮЖНАЯ АМЕРИКА / РАСКЛАДКА 740 × 740 ММ',18);text(c,24,H-51,f"{data['kits']} полных комплекта • {len(rows)} деталей • только перенос, без поворотов и отражений",10)
 s=(H-100)/740;x0=24;y0=22;c.saveState();c.translate(x0,y0+740*s);c.scale(s,-s);drawing(c,rows);c.setStrokeColorRGB(.6,.6,.6);c.setLineWidth(.2);c.rect(0,0,740,740,fill=0,stroke=1);c.restoreState();sortedrows=sorted(rows,key=lambda q:(q['kit'],q['source_id']));numbers={q['id']:i+1 for i,q in enumerate(sortedrows)}
 for q in rows:
  pt=shape(q['geom']).representative_point();x=x0+pt.x*s;y=y0+(740-pt.y)*s;c.setFillColorRGB(1,1,1);c.circle(x,y,4.2,fill=1,stroke=0);c.setFillColorRGB(0,0,0);c.setFont('Label',5.5);c.drawCentredString(x,y-1.8,str(numbers[q['id']]))
 tx=x0+740*s+24;y=H-90;text(c,tx,y,'ЦВЕТА ОПЕРАЦИЙ',11);y-=24
 for caption,col in [('Чёрный — сквозная резка',(0,0,0)),('Красный — границы и установка слоёв',(1,0,0)),('Синий — все названия стран',(0,0,1))]:text(c,tx,y,caption,9,col);y-=20
 y-=15;text(c,tx,y,'Надписи — редактируемый текст.',9);y-=18;text(c,tx,y,'Установить OpenSans-Light.ttf.',9);y-=18;text(c,tx,y,'Импорт листа в миллиметрах, 1:1.',9);y-=18;text(c,tx,y,'Номера — только в справочной схеме.',9);y-=34
 ncol=2 if len(rows)>32 else 1;per=math.ceil(len(rows)/ncol)
 for col in range(ncol):
  x=tx+col*177;text(c,x,y,'№   К-т  Слой  Деталь',9)
  for k,q in enumerate(sortedrows[col*per:(col+1)*per]):text(c,x,y-20-k*15,f"{numbers[q['id']]:02d}   {q['kit']:02d}     {q['tier']}     {q['source_id']}",7.4)
 c.save();print('PDF',folder.name,'kits',data['kits'],flush=True)
write(P);write(P/'Один-комплект')
# Painting and assembly in the original shared map coordinates; reference only.
W,H=landscape(A3);c=canvas.Canvas(str(P/'Схема-слоёв-и-покраски.pdf'),pagesize=(W,H));text(c,25,H-35,'ЮЖНАЯ АМЕРИКА / ТРИ СЛОЯ / ПОКРАСКА',18);text(c,25,H-57,'Цвета исходной сборки. Напуск до 2 мм только под следующим слоем. Справочная схема, не файл резки.',10)
base=shape(D['layers'][0]);x0,y0,x1,y1=base.bounds;s=min((H-220)/(y1-y0),(W/3-45)/(x1-x0));width=W/3
for tier in [1,2,3]:
 x=(tier-1)*width+25;y=H-100;text(c,x,y,f"СЛОЙ {tier} / {D['summary'][tier-1]['pieces']} деталей / верх {tier*3} мм",12);c.saveState();c.translate(x+((width-45)-(x1-x0)*s)/2,y-20);c.scale(s,-s);c.translate(-x0,-y0)
 rows=[q for q in D['pieces']if q['tier']==tier]
 for q in rows:
  fill(c,shape(q['geom']),(.9,.85,.76))
  for coat,mask in q['paint'].items():
   col=D['colors'][coat];srgb=[12.92*v if v<.0031308 else 1.055*v**(1/2.4)-.055 for v in col];fill(c,shape(mask['with_overlap']),srgb)
  trace(c,shape(q['red_internal']));fill(c,shape(q['geom']),(0,0,0),True)
  for a in D['labels']:
   if a['piece']==q['id']:title(c,a)
 c.restoreState()
text(c,25,90,'18 физических деталей на один комплект: 5 + 5 + 8. Толщина каждого листа — 3 мм.',11);text(c,25,67,'Разные соприкасающиеся видимые цвета разделены разрезами; скрытые политические границы удалены.',10);text(c,25,45,'В исходнике не было текстовых подписей городов. Добавлены 13 названий стран и территорий, все синим текстом.',10);c.save()
print('ALL PDF READY',flush=True)
