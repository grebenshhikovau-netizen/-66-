"""Large vector before/after panels of the actual engraving, preserving the same black cuts."""
import json
from pathlib import Path
from shapely.geometry import shape,box
from make_pdf import fill,trace,text,title,canvas,landscape,A3
P=Path(__file__).resolve().parent.parent;A=json.load(open(P/'data/before-line-cleanup.json'));B=json.load(open(P/'data/production-plan.json'));W,H=landscape(A3);c=canvas.Canvas(str(P/'Красные-линии-до-и-после.pdf'),pagesize=(W,H))
for id,heading,window in [('L01_P001','Западная Африка: стыки границ',(800,-500,940,-430)),('L02_P001','Египет: контуры пирамиды и границы',(995,-577,1065,-510)),('L03_P001','Алжир, Мали и Нигер: соединение линий',(800,-600,980,-479)),('L01_P001','Восточная Африка: русла и озёра',(1015,-440,1070,-335))]:
 x0,y0,x1,y1=window;roi=box(*window);s=min((W/2-65)/(x1-x0),(landscape(A3)[1]-145)/(y1-y0));H=min(landscape(A3)[1],(y1-y0)*s+145);c.setPageSize((W,H));text(c,28,H-32,'КРАСНЫЕ ЛИНИИ / '+heading,16)
 for col,D in enumerate([A,B]):
  row=next(q for q in D['pieces']if q['id']==id);px=28+col*W/2;text(c,px,H-60,'ДО'if col==0 else'ПОСЛЕ',14);c.saveState();c.translate(px,H-88);c.scale(s,-s);c.translate(-x0,-y0);clip=c.beginPath();clip.rect(x0,y0,x1-x0,y1-y0);c.clipPath(clip,stroke=0,fill=0);fill(c,shape(row['geom']).intersection(roi),(.98,.97,.94));fill(c,shape(row['geom']).intersection(roi),(0,0,0),True,width=.07);trace(c,shape(row['red_internal']).intersection(roi))
  for a in D['labels']:
   if a['piece']==id:title(c,a)
  for m in D['city_markers']:
   if m['piece']==id:fill(c,shape(m['geom']),(1,0,0))
  c.restoreState()
 text(c,28,38,'Чёрная геометрия деталей не менялась. Красная сеть собрана заново; полные монтажные контуры есть отдельным файлом.',10);c.showPage()
c.save();print('LINE COMPARISON PDF READY')
