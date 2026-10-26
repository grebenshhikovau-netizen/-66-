import json
from pathlib import Path
from shapely.geometry import shape,box
from shapely.geometry.polygon import orient
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4,landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'Соединение-палочек.json'));OLD=json.load(open(P/'data'/'source'/'plan-before-joining.json'));window=box(738,-268,762,-236);support=shape(OLD['layers'][1]).intersection(window);W,H=landscape(A4);c=canvas.Canvas(str(P/'Палочки-до-и-после.pdf'),pagesize=(W,H));pdfmetrics.registerFont(TTFont('Noto','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
def text(x,y,t,size=12):c.setFont('Noto',size);c.setFillColor('#30251d');c.drawString(x,y,t)
def polys(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in polys(q)]
def draw(g,color,outline=False):
 p=c.beginPath()
 for a in polys(g):
  a=orient(a,-1)
  for ring in[a.exterior,*a.interiors]:
   pts=list(ring.coords);p.moveTo(*pts[0])
   for xy in pts[1:]:p.lineTo(*xy)
   p.close()
 c.setFillColor(color);c.setStrokeColor('#4c3827');c.setLineWidth(.12);c.drawPath(p,fill=1,stroke=int(outline),fillMode=1)
text(35,H-32,'Палочки присоединены к детали «Бойсе — Хелена»',17)
for i,(key,title)in enumerate([('before_geom','Было: три отдельные детали'),('after_geom','Стало: одна цельная деталь')]):
 x=48+i*405;y=105;s=11.2;text(x,H-67,title,13);c.saveState();c.translate(x,y+32*s);c.scale(s,-s);c.translate(-738,268);draw(support,'#eeeeeb');draw(shape(D[key]).intersection(window),'#e7d3ac',True);c.restoreState();text(x,y-20,'Второй слой — серым; верхняя деталь — фанерным.',8)
text(35,55,'Палочки не сдвигались. Общая перемычка и отросток — шириной 3,2 мм.',10);text(35,37,'Соединения полностью опираются на второй слой. Отдельно эти две палочки клеить не потребуется.',10);c.save();print('PRONG PREVIEW READY')
