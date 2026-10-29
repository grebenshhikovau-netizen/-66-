"""Vector reference for the removable paint groups; not a laser operation."""
import json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import unary_union
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));R={c:shape(g)for c,g in D['regions'].items()};pdfmetrics.registerFont(TTFont('RU',str(P/'Шрифт/OpenSans-Light.ttf')));W,H=landscape(A3);c=canvas.Canvas(str(P/'Группы-покраски.pdf'),pagesize=(W,H));palette={'Общий слой':(.92,.90,.85),'Основной массив':(.87,.78,.61),'Венгрия':(.78,.39,.32),'Греция-Албания-Турция':(.35,.63,.58),'Туркмения':(.65,.43,.31),'Лаос':(.36,.56,.75)}
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in ps(q)]
def path(g):
 p=c.beginPath()
 for q in ps(g):
  for ring in [q.exterior,*q.interiors]:
   co=list(ring.coords);p.moveTo(*co[0])
   for xy in co[1:]:p.lineTo(*xy)
   p.close()
 return p
pages=[('Второй слой — группы покраски',list(R),2),('Европа — соединения второго слоя',['FRA','POL','AUT','HUN','GRC','ALB','TUR','CZE','SVK','ROU','BGR','ITA'],2),('Туркмения отдельно от Казахстана',['TKM','KAZ','UZB','KGZ','TJK'],3),('Лаос отдельно от Китая',['LAO','CHN','VNM','THA','KHM'],3)]
for heading,codes,tier in pages:
 c.setFont('RU',20);c.drawString(28,H-40,heading);c.setFont('RU',10);c.drawString(28,H-63,'Справочная схема. Цвет обозначает группу деталей, а не обязательную краску.');view=unary_union([R[k]for k in codes]);x0,y0,x1,y1=view.bounds;pad=7;x0-=pad;y0-=pad;x1+=pad;y1+=pad;s=min((W-340)/(x1-x0),(H-125)/(y1-y0));left=25;top=H-90
 c.saveState();c.translate(left,top);c.scale(s,-s);c.translate(-x0,-y0);clip=c.beginPath();clip.rect(x0,y0,x1-x0,y1-y0);c.clipPath(clip,stroke=0)
 c.setFillColorRGB(.96,.96,.95);c.setStrokeColorRGB(.8,.8,.8);c.setLineWidth(.12);c.drawPath(path(shape(D['layers'][0])),stroke=1,fill=1,fillMode=0)
 for row in D['pieces']:
  if row['tier']!=tier:continue
  g=shape(row['geom']);c.setFillColorRGB(*palette[row['paint_group']]);c.setStrokeColorRGB(.15,.13,.10);c.setLineWidth(.24);c.drawPath(path(g),stroke=1,fill=1,fillMode=0)
  if g.intersection(view).area>15:
   pt=g.intersection(view).representative_point();c.saveState();c.translate(pt.x,pt.y);c.scale(1,-1);c.setFillColorRGB(.1,.1,.1);c.setFont('RU',7/s);c.drawCentredString(0,0,row['id']);c.restoreState()
 c.restoreState();xx=W-290;yy=H-105
 for name in ['Основной массив','Венгрия','Греция-Албания-Турция','Туркмения','Лаос']:
  c.setFillColorRGB(*palette[name]);c.rect(xx,yy-10,14,14,fill=1,stroke=0);c.setFillColorRGB(.1,.1,.1);c.setFont('RU',10);c.drawString(xx+22,yy-5,name);yy-=35
 for line in ['Австрия + Франция + Польша — вместе.','Венгрия — отдельная деталь.','Греция + Албания + Турция — вместе.','Туркмения и Лаос — отдельные накладки.','Слой 1 остаётся общим.','Точные номера — в Группы-покраски.csv.']:
  c.setFont('RU',9);c.drawString(xx,yy,line);yy-=22
 c.showPage()
c.save();print('PAINT REFERENCE READY')
