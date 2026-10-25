import json,math,csv
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from shapely.geometry import shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'production-plan.json'));X0,Y0,X1,Y1=shape(D['layers'][0]).bounds;W,H=landscape(A3)
pdfmetrics.registerFont(TTFont('Noto','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'));pdfmetrics.registerFont(TTFont('NotoBold','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
c=canvas.Canvas(str(P/'Схема-сборки-и-покраски.pdf'),pagesize=(W,H));c.setTitle('Северная Америка — слои, покраска и сборка')
def text(x,y,t,size=10,bold=False,color='#44372d'):
 c.setFillColor(color);c.setFont('NotoBold' if bold else 'Noto',size);c.drawString(x,y,t)
def polys(g):
 if g.geom_type=='Polygon':return [g] if not g.is_empty else []
 return [p for q in getattr(g,'geoms',[])for p in polys(q)]
def rgb(a):return tuple((v*12.92 if v<.0031308 else 1.055*v**(1/2.4)-.055)for v in a)
def draw(g,col,stroke=False):
 path=c.beginPath()
 for pp in polys(g):
  p=orient(pp,-1)
  for ring in [p.exterior,*p.interiors]:
   cc=list(ring.coords);path.moveTo(*cc[0])
   for q in cc[1:]:path.lineTo(*q)
   path.close()
 if isinstance(col,str):c.setFillColor(col)
 else:c.setFillColorRGB(*col)
 c.setStrokeColor('#4d3829');c.setLineWidth(.12);c.drawPath(path,stroke=int(stroke),fill=1,fillMode=1)
def header(title,subtitle):
 text(35,H-40,title,22,True);text(35,H-63,subtitle,10);c.setStrokeColor('#d9cbb9');c.line(35,H-79,W-35,H-79)
def startmap():
 s=min(785/(X1-X0),(H-140)/(Y1-Y0));left=35;bottom=35
 c.saveState();c.translate(left,bottom+(Y1-Y0)*s);c.scale(s,-s);c.translate(-X0,-Y0)
 return s,left,bottom
used=sorted(set(k for p in D['pieces']for k in p['paint']if k!='NATURAL'));codes={k:f'C{i+1:02d}'for i,k in enumerate(used)};codes['NATURAL']='NATURAL'
header('Северная Америка / 3 производственных слоя',f'{len(D["pieces"])} деревянных деталей • 3 / 6 / 9 мм • исходные контуры и цвета сборки')
s,left,bottom=startmap()
for p in D['pieces']:
 draw(shape(p['geom']),'#d8c09b',True)
 for coat,v in p['paint'].items():draw(shape(v['visible']),rgb(D['colors'][coat]))
 eng=shape(p['engraving']);dark=unary_union([shape(v['visible'])for k,v in p['paint'].items()if sum(a*b for a,b in zip(D['colors'][k],[.2126,.7152,.0722]))<.1]);draw(eng.difference(dark),'#40291d');draw(eng.intersection(dark),'#dec79f')
c.restoreState()
x=870;y=H-130
for line in ['Слой 1 — одна общая основа.',f'Слой 2 — {D["summary"][1]["pieces"]} крупных деталей.',f'Слой 3 — {D["summary"][2]["pieces"]} деталей.','','Краску можно заводить на 2 мм','только под следующий слой.','','Юкон — оранжевый, как Альберта.','США — натуральная фанера.','','Аризона / Мексика и Лабрадор / Квебек:','использовать малярную маску.','','Нумерация и рабочие контуры','даны в SVG и в папке «Детали».','','PDF — схема, не масштаб 1:1.','Рабочие SVG имеют размеры в мм.']:
 text(x,y,line,9);y-=19
c.showPage()
for tier in [1,2,3]:
 pp=[p for p in D['pieces']if p['tier']==tier];header(f'Слой {tier} / покраска и сборка',f'{len(pp)} деталей • низ {(tier-1)*3} мм / верх {tier*3} мм • штриховой контур — следующий слой')
 s,left,bottom=startmap()
 for p in pp:
  draw(shape(p['geom']),'#e0cfb1',True)
  for coat,v in p['paint'].items():draw(shape(v['with_overlap']),rgb(D['colors'][coat]))
  eng=shape(p['engraving']);dark=unary_union([shape(v['visible'])for k,v in p['paint'].items()if sum(a*b for a,b in zip(D['colors'][k],[.2126,.7152,.0722]))<.1]);draw(eng.difference(dark),'#3a271b');draw(eng.intersection(dark),'#dec79f')
 if tier<3:
  c.setDash(1.3,1.3);c.setStrokeColor('#786b5c');c.setLineWidth(.25)
  for p in polys(shape(D['layers'][tier])):
   z=c.beginPath()
   for ring in [p.exterior,*p.interiors]:
    cc=list(ring.coords);z.moveTo(*cc[0])
    for q in cc[1:]:z.lineTo(*q)
   c.drawPath(z,fill=0,stroke=1)
 c.restoreState()
 for p in pp:
  q=shape(p['geom']).representative_point();px=left+(q.x-X0)*s;py=bottom+(Y1-q.y)*s
  c.setFillColorRGB(1,1,1);c.roundRect(px-25,py-6,50,13,2,stroke=0,fill=1);text(px-23,py-2,p['id'],7.2,True)
 x=870;y=H-130;text(x,y,'ПАЛИТРА',12,True);y-=26
 for coat in ['NATURAL']+used:
  if not any(coat in p['paint']for p in pp):continue
  c.setFillColorRGB(*rgb(D['colors'][coat]));c.rect(x,y-2,18,13,stroke=0,fill=1);text(x+28,y,codes[coat],9,True);y-=20
  if coat=='NATURAL':text(x+28,y,'Без цветной краски',8);y-=20
 y-=20
 for line in ['Цветные участки включают напуск.','Скрытые зоны красок могут','перекрываться между собой.','','Сначала сухая примерка.','Окраска — до склейки.','Не красить видимую соседнюю','поверхность другого цвета.','','Гравировка — только на открытых','поверхностях этого слоя.','','Точные границы отдельных красок:','Детали / Lxx_Pxxx / Покраска-Cxx.svg']:
  text(x,y,line,8.3);y-=18
 if tier==1:
  y-=12;text(x,y,'ВАЖНО: АРИЗОНА / МЕКСИКА',9,True,color='#9a431f');y-=20
  text(x,y,'Два открытых перехода на общей основе.',8.2);y-=17;text(x,y,'Для них приложены отдельные маски.',8.2)
 c.showPage()
header('Ведомость деталей','Коды покрытий соответствуют палитре и индивидуальным SVG-маскам')
y=H-115
for x,t in [(40,'Деталь'),(165,'Слой'),(235,'Площадь, мм²'),(370,'Покрытия')]:text(x,y,t,10,True)
y-=23
for p in D['pieces']:
 vals=[(40,p['id']),(165,str(p['tier'])),(235,f'{p["area_mm2"]:.1f}'),(370,', '.join(codes[q]for q in p['paint']))]
 for x,t in vals:text(x,y,t,9)
 y-=19
text(40,55,'Производственные SVG: исходный масштаб; компенсация ширины реза и раскладка под лист не выполнены.',9)
c.save();print('PDF READY')
