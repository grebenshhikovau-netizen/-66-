"""Vector before/after comparison using the uploaded height geometry and actual corrected contours."""
import json
from pathlib import Path
from shapely.geometry import shape,box
from shapely.ops import unary_union
from make_pdf import fill,trace,text,title,canvas,landscape,A3
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));R=json.load(open(P/'data/source/extracted.json'));wood=[q for q in R if q['kind']=='wood'];raw=[unary_union([shape(q['geom'])for q in wood if q['hi_mm']>=i*3-.05])for i in range(1,7)];after=[shape(g)for g in D['layers']];base=raw[0].union(shape(D['water_base_union']));W,H=landscape(A3);c=canvas.Canvas(str(P/'Сравнение-до-и-после.pdf'),pagesize=(W,H));palette=[(.92,.84,.69),(.84,.73,.57),(.74,.60,.43),(.63,.48,.32),(.51,.36,.22),(.95,.84,.62)]
for heading,roi in [('Сглаживание и объединение',box(*base.bounds)),('Египет: цельная ступенчатая пирамида',box(995,-576,1069,-511)),('Кения и Эфиопия: закрытая рифтовая полоса',box(1024,-490,1100,-385)),('Мелкие зубцы границ: Западная Африка',box(813,-495,920,-433))]:
 text(c,30,H-35,'АФРИКА / '+heading,18);text(c,30,H-58,'Слева — присланная геометрия. Справа — подготовленные слои. Размер и ориентация карты сохранены.',10);x0,y0,x1,y1=roi.bounds;scale=min((W/2-70)/(x1-x0),(H-155)/(y1-y0))
 for col,layers in enumerate([raw,after]):
  px=30+col*W/2;py=H-110;text(c,px,H-84,'ДО'if col==0 else'ПОСЛЕ',14);c.saveState();c.translate(px,py);c.scale(scale,-scale);c.translate(-x0,-y0)
  if col:fill(c,shape(D['water_base_union']).intersection(roi),(.02,.48,.63))
  for layer,color in zip(layers,palette):
   g=layer.intersection(roi);fill(c,g,color);fill(c,g,(.23,.18,.13),True,width=.04)
  c.restoreState()
 text(c,30,37,'15 деталей вместо 143 исходных объектов; 52 названия стран/территорий и 58 городов. Рабочие контуры находятся в SVG/PDF 740 × 740 мм.',10);c.showPage()
c.save();print('COMPARISON READY',flush=True)
