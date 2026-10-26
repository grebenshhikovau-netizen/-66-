import json
from pathlib import Path
from shapely.geometry import shape,box
from shapely.ops import unary_union
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from make_pdf import fill,trace,text
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));R=[q for q in json.load(open(P/'data/source/extracted.json'))if q['kind']=='wood'];window=box(828,-719,947,-625);raw=unary_union([shape(q['geom'])for q in R if q['hi_mm']>=5.95]);oldnet=unary_union([unary_union([shape(q['geom'])for q in R if q['region']==code]).boundary.intersection(window)for code in D['region_names']]);newnet=shape(D['political_network']).intersection(window);W,H=landscape(A3);c=canvas.Canvas(str(P/'Сглаживание-до-и-после.pdf'),pagesize=(W,H));text(c,30,H-40,'РОССИЯ / СГЛАЖИВАНИЕ / ДО И ПОСЛЕ',20);text(c,30,H-65,'Пример участка Урала: крупные очертания сохранены, мелкая зубчатость округлена.',11)
for x,heading,g,net in [(35,'ДО / исходные границы и второй слой',raw,oldnet),(620,'ПОСЛЕ / подготовлено для резки',shape(D['layers'][1]),newnet)]:
 text(c,x,H-110,heading,14);c.saveState();c.translate(x,H-145);c.scale(4,-4);c.translate(-828,719);clip=c.beginPath();clip.rect(828,-719,119,94);c.clipPath(clip,stroke=0);fill(c,g,(.91,.85,.73));trace(c,net,(.65,.13,.08));fill(c,g,(0,0,0),True);c.restoreState()
text(c,35,245,'Сглажены выступы и впадины субмиллиметрового масштаба, устранены паразитные швы.',11);text(c,35,220,'Радиусы обработки: закрытие 0,44 мм и скругление выступов 0,30 мм; предварительное упрощение 0,24 мм.',10);text(c,35,190,'Отдельные реальные острова не соединены искусственными перемычками. Два мелких речных островка удалены.',10);text(c,35,70,'Справочная иллюстрация. Рабочий файл — Поле-01-740x740.svg / .pdf, импорт 1:1.',9);c.save();print('SMOOTHING PREVIEW READY',flush=True)
