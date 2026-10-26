"""Vector detail comparison of the repaired slit and single-line lettering."""
import json
from pathlib import Path
from shapely.geometry import shape,box
from shapely.geometry.polygon import orient
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
P=Path(__file__).resolve().parent.parent;old=json.load(open(P/'data/source/plan-before-slit-repair.json'));new=json.load(open(P/'data/source/production-plan.json'));ann=json.load(open(P/'data/annotations.json'));prod=json.load(open(P/'data/manufacturing.json'))
pdfmetrics.registerFont(TTFont('Label','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'));W,H=landscape(A3);c=canvas.Canvas(str(P/'Исправления-крупно.pdf'),pagesize=(W,H));c.setTitle('Канада — исправление прорезей и однолинейный текст')
def text(x,y,s,size=11):c.setFillColorRGB(.12,.12,.12);c.setFont('Label',size);c.drawString(x,y,s)
def polys(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in polys(q)]
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in lines(q)]
def draw(g,fill=False,color=(0,0,0),width=.12):
 p=c.beginPath()
 for a in polys(g):
  a=orient(a,-1)
  for ring in [a.exterior,*a.interiors]:
   q=list(ring.coords);p.moveTo(*q[0])
   for xy in q[1:]:p.lineTo(*xy)
   p.close()
 c.setFillColorRGB(*color);c.setStrokeColorRGB(*color);c.setLineWidth(width);c.drawPath(p,stroke=not fill,fill=fill,fillMode=1)
def strokes(g,width=.08):
 p=c.beginPath()
 for a in lines(g):
  q=list(a.coords);p.moveTo(*q[0])
  for xy in q[1:]:p.lineTo(*xy)
 c.setStrokeColorRGB(1,0,0);c.setLineWidth(width);c.setLineCap(1);c.drawPath(p,stroke=1,fill=0)
text(30,H-40,'КАНАДА / ИСПРАВЛЕННЫЙ РАСКРОЙ',21);text(30,H-65,'Чёрный — только сквозные контуры. Красные буквы — линии по середине штрихов.',11)
window=box(630,-488,720,-389)
for x,label,data in [(35,'До: узкие прорези в основании',old),(600,'После: цельное основание',new)]:
 text(x,H-105,label,15);g=shape(next(q for q in data['pieces']if q['id']=='L01_P001')['geom']);c.saveState();c.translate(x,H-135);c.scale(3.1,-3.1);c.translate(-630,488);clip=c.beginPath();clip.rect(630,-488,90,99);c.clipPath(clip,stroke=0);draw(g,True,(.95,.90,.78));draw(g,False,(0,0,0),.15);c.restoreState()
text(35,335,'Щели шириной в доли миллиметра закрыты; крупные предусмотренные вырезы сохранены.',10)
a=next(q for q in ann if q['id']=='TEXT_070');g=shape(a['source_outline']);s=shape(a['geometry']);x0,y0,x1,y1=g.bounds
for x,label,kind in [(35,'До: две стороны каждого штриха','outline'),(600,'После: один проход по штриху','stroke')]:
 text(x,285,label,15);scale=400/(x1-x0);c.saveState();c.translate(x,240);c.scale(scale,-scale);c.translate(-x0,-y0)
 if kind=='outline':draw(g,False,(1,0,0),.012)
 else:strokes(s,.035)
 c.restoreState()
text(35,135,'82 красные надписи • 72 метки городов • 4 синих заголовка • 28 деталей',13);text(35,109,'Синие заголовки: США, КАНАДА, МЕКСИКА, АЛЯСКА. Их исходные контуры сохранены.',11);text(35,82,'Скрытые политические границы убраны; контуры установки следующего слоя оставлены.',11);text(35,42,'Справочная иллюстрация. Для станка использовать Поле-01-740x740.svg или .pdf, масштаб 1:1.',9)
c.save();print('DETAIL COMPARISON READY',flush=True)
