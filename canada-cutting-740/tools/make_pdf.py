import json
from pathlib import Path
from shapely.geometry import shape
from shapely.geometry.polygon import orient
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data'/'manufacturing.json'));M=72/25.4

def polygons(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in polygons(q)]
def draw(c,g,rgb,cut=False):
 p=c.beginPath()
 for q in polygons(g):
  pp=orient(q,-1)
  for ring in [pp.exterior,*pp.interiors]:
   coords=list(ring.coords);p.moveTo(*coords[0])
   for xy in coords[1:]:p.lineTo(*xy)
   p.close()
 c.setFillColorRGB(*rgb);c.setStrokeColorRGB(*rgb);c.setLineWidth(.05);c.drawPath(p,fill=0 if cut else 1,stroke=1 if cut else 0,fillMode=1)
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in lines(q)]
def draw_strokes(c,g):
 p=c.beginPath()
 for q in lines(g):
  coords=list(q.coords)
  if len(coords)<2:continue
  p.moveTo(*coords[0])
  for xy in coords[1:]:p.lineTo(*xy)
 c.setStrokeColorRGB(1,0,0);c.setLineWidth(.05);c.setLineCap(1);c.setLineJoin(1);c.drawPath(p,stroke=1,fill=0)
def drawing(c,parts):
 for row in parts:

  for a in row.get('red_texts',{}).values():
   c.saveState();c.transform(*a['matrix']);c.scale(1,-1);c.setFillColorRGB(1,0,0);c.setFont('LiveText',a['font_size_mm']);c.drawString(0,0,a['text']);c.restoreState()
  for q in row['red_marks'].values():draw(c,shape(q),(1,0,0))
  draw_strokes(c,shape(row['red_internal']))
  for b in row['blue'].values():draw(c,shape(b),(0,0,1))
 for row in parts:draw(c,shape(row['geom']),(0,0,0),True)
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';pdfmetrics.registerFont(TTFont('Noto',font));pdfmetrics.registerFont(TTFont('LiveText',str(P/'Шрифт/OpenSans-Light.ttf')))
for sheet in sorted(set(p['sheet']for p in D['pieces'])):
 parts=[p for p in D['pieces']if p['sheet']==sheet]
 c=canvas.Canvas(str(P/f'Поле-{sheet:02d}-740x740.pdf'),pagesize=(740*M,740*M));c.setTitle(f'Канада: поле {sheet}, 740 × 740 мм, 1:1');c.saveState();c.translate(0,740*M);c.scale(M,-M);drawing(c,parts);c.restoreState();c.save()
 # Separate non-production diagram: part identifiers must never enter the laser file.
 W,H=landscape(A3);c=canvas.Canvas(str(P/'Схема-раскладки-с-номерами.pdf'),pagesize=(W,H));c.setTitle('Схема раскладки с номерами — справочно');c.setFont('Noto',18);c.drawString(24,H-32,'Канада / поле 740 × 740 мм / только перемещение деталей');c.setFont('Noto',9);c.drawString(24,H-51,f'{len(parts)} деталей • 3 слоя фанеры по 3 мм • без поворотов, отражений и изменения масштаба')
 s=(H-100)/740;x0=24;y0=25;c.saveState();c.translate(x0,y0+740*s);c.scale(s,-s);drawing(c,parts);c.setStrokeColorRGB(.65,.65,.65);c.setLineWidth(.25);c.rect(0,0,740,740,fill=0,stroke=1);c.restoreState()
 numbers={row['id']:i+1 for i,row in enumerate(sorted(parts,key=lambda q:q['id']))}
 for row in parts:
  q=shape(row['geom']).representative_point();x=x0+q.x*s;y=y0+(740-q.y)*s;c.setFillColorRGB(1,1,1);c.circle(x,y,5.1,fill=1,stroke=0);c.setFillColorRGB(.15,.15,.15);c.setFont('Noto',6);c.drawCentredString(x,y-2,str(numbers[row['id']]))
 x=x0+740*s+30;y=H-100
 def text(t,size=9,rgb=(.15,.15,.15)):
  global y
  c.setFont('Noto',size);c.setFillColorRGB(*rgb);c.drawString(x,y,t);y-=17
 text('ЦВЕТА ОПЕРАЦИЙ',12);y-=7
 text('Чёрный — сквозная резка',10,(0,0,0));text('Красный — надписи, города и внутренние области',9,(1,0,0));text('Синий — США, Канада, Мексика, Аляска',10,(0,0,1));y-=12
 text('Только 3 рабочих цвета в SVG и PDF.');text('Красные надписи — редактируемый текст.');text('Поле — 740 × 740 мм; импортировать 1:1.');text('Зазор между деталями — не менее 5 мм.');text('Все детали направлены как в исходной сборке.');y-=12
 text('№    ДЕТАЛЬ                СЛОЙ',10)
 for row in sorted(parts,key=lambda p:p['id']):text(f'{numbers[row["id"]]:02d}    {row["id"]}              {row["tier"]}',8)
 y-=8;text('Номера есть только в этой схеме,',8);text('в рабочих файлах они отсутствуют.',8);text('Для станка: Поле-01-740x740.svg / .pdf',8)
 c.save()
print('PDF READY: exact 740 mm production page and separate numbered guide',flush=True)
