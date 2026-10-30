"""Vector assembly reference showing the explicitly approved local wooden river bridges."""
import json,math,csv
from pathlib import Path
from shapely.geometry import shape
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));pdfmetrics.registerFont(TTFont('RU','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'));pdfmetrics.registerFont(TTFont('Live',str(P/'Шрифт/OpenSans-Light.ttf')));W,H=landscape(A3);c=canvas.Canvas(str(P/'Перемычки-на-реках.pdf'),pagesize=(W,H))
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in ps(q)]
def draw(g,fill,stroke=None,width=.1):
 p=c.beginPath()
 for q in ps(g):
  for ring in [q.exterior,*q.interiors]:
   xy=list(ring.coords);p.moveTo(*xy[0])
   for pt in xy[1:]:p.lineTo(*pt)
   p.close()
 c.setFillColorRGB(*fill);c.setStrokeColorRGB(*(stroke or fill));c.setLineWidth(width);c.drawPath(p,fill=1,stroke=bool(stroke),fillMode=0)
def word(x,y,s,size=11):c.setFont('RU',size);c.setFillColorRGB(.1,.1,.1);c.drawString(x,y,s)
for group in D['bridge_groups']:
 row=next(p for p in D['pieces']if p['id']==group['result_piece']);g=shape(row['geom']);bridges=[b for b in D['river_bridges']if b['group']==group['group']];x0,y0,x1,y1=g.bounds;s=min((W-400)/(x1-x0),(H-155)/(y1-y0));word(28,H-35,'ПЕРЕМЫЧКИ / '+group['group'],18);word(28,H-59,f"Слой {group['tier']}, деталь {row['id']}: цельная накладка, перемычек {len(bridges)}",11);c.saveState();c.translate(35,H-100);c.scale(s,-s);c.translate(-x0,-y0);river=shape(D['upper_water'][bridges[0]['river']]).intersection(g.envelope.buffer(3));draw(river,(.25,.70,.86));draw(g,(.91,.83,.69),(.12,.1,.08),.10)
 for b in bridges:draw(shape(b['footprint']).intersection(g),(.32,.65,.43),(.12,.35,.18),.10)
 for a in D['labels']:
  if a['piece']!=row['id']:continue
  c.saveState();c.transform(*a['matrix']);c.scale(1,-1);c.setFillColorRGB(0,0,.6)if a['kind']=='country'else c.setFillColorRGB(.35,.1,.1);c.setFont('Live',a['font_size_mm'])
  for ln in a['lines']:c.drawString(ln['x_em']*a['font_size_mm'],-ln['y_em']*a['font_size_mm'],ln['text'])
  c.restoreState()
 c.restoreState();x=W-330;y=H-115
 for line in ['СПРАВОЧНО, НЕ ФАЙЛ РЕЗКИ','Зелёное — деревянная перемычка.','Голубое — сквозной участок русла.','Номинальная ширина перемычек — 2,2 мм.','Нижний слой сохраняет сквозную щель.','Контур детали — в рабочем SVG/PDF.']:
  word(x,y,line,10);y-=25
 for b in bridges:word(x,y,f"{b['id']}: {b['river']}",10);y-=22
 c.showPage()
c.save()
with (P/'Перемычки.csv').open('w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f);w.writerow(['ID','Река','Группа','Слой','Ширина мм','Пролёт между берегами мм','Добавлено дерева мм²'])
 for b in D['river_bridges']:w.writerow([b['id'],b['river'],b['group'],b['tier'],b['width_mm'],round(b['bank_gap_mm'],3),round(b['added_wood_mm2'],3)])
print('BRIDGE REFERENCE READY',len(D['river_bridges']),flush=True)
