"""Verify the protected engraving zone and package the current production patterns."""
from pathlib import Path
import json,hashlib,zipfile,ast
from lxml import etree as E
from svgpathtools import parse_path
from shapely.geometry import shape
from shapely.affinity import translate

P=Path(__file__).resolve().parent.parent
L=json.loads((P/'layout.json').read_text());D={p['id']:p for p in json.loads((P/'parts.json').read_text())}
R=json.loads((P/'Проверка-раскладки.json').read_text());Q=json.loads((P/'Проверка-зоны-станка.json').read_text())
assert R['passed']and Q['passed'];assert R['repeat_main']==L['repeat']
els=[q for q in E.parse(str(P/'source.svg')).iter()if E.QName(q).localname in ['path','text']];K=25.4/72
bounds={}
for id,q in D.items():
 fine=[]
 for i in q['members']:
  e=els[i]
  if E.QName(e).localname!='path'or not any('stroke: '+c in e.get('style','')for c in ['#cc0033','#e30016']):continue
  a,b,c,d=parse_path(e.get('d')).bbox();a,b,c,d=[v*K for v in [a,b,c,d]]
  if .15<max(b-a,d-c)<=6:fine.append((i,a,c,b,d))
 bounds[id]=fine
for field in ['main','supplementary']:
 for row in L[field]:
  for i,x0,y0,x1,y1 in bounds[row['source_id']]:
   assert x0+row['dx_mm']>=220 or y0+row['dy_mm']>=220,(field,row,i,'fine bounds in protected zone')
Q['whole_fine_curve_bounding_boxes_clear_of_220mm_corner']=True
positions={}
for row in L['main']:
 id=row['source_id'];b=translate(shape(D[id]['geom']),row['dx_mm'],row['dy_mm']).bounds
 if id in ['P003','P008','P006']:
  assert b[3]>725;positions[id]=b
 if id in ['P002','P007']:
  assert max(b[2],b[3])>725;positions[id]=b
Q['important_group_bounds_mm']=positions
(P/'Проверка-зоны-станка.json').write_text(json.dumps(Q,ensure_ascii=False,indent=2))
source=P/'data/source/белый.cdr';R['source_cdr_sha256']=hashlib.sha256(source.read_bytes()).hexdigest();R['source_cdr_bytes']=source.stat().st_size
(P/'Проверка-раскладки.json').write_text(json.dumps(R,ensure_ascii=False,indent=2))
n=L['repeat'];word='набор'if n==1 else'набора'if n in [2,3,4]else'наборов';zname=f'Белый-раскрой-740x740-{n}-{word}.zip'
exports=json.loads((P/'exports.json').read_text());main,extra=[e['prefix']for e in exports]
gap=min(q['minimum_gap_mm']for q in L['checks'])
text=f'''# Белый набор — раскрой с учётом станка

**Поле 740 × 740 мм. Основной лист × {n} + дополнительный × 1 = {n} полных исходных наборов.**

[Скачать готовый комплект]({zname}) · [Схема и порядок запусков](Порядок-резки.pdf)

| Лист | SVG для CorelDRAW | Векторный PDF 1:1 | Прогонов за цикл |
|---|---|---|---:|
| 01 — основной | [Рабочий SVG]({main}.svg) | [PDF]({main}.pdf) | {n} |
| 02 — остаток × {n} | [Рабочий SVG]({extra}.svg) | [PDF]({extra}.pdf) | 1 |

Можно сначала вырезать дополнительный лист и разложить его содержимое на {n} одинаковых групп. Затем выполнить {n} прогонов основного листа. Получатся ровно {n} полных наборов, без лишних копий отдельных групп. Дополнительный лист на каждом прогоне основного повторять не нужно.

На основном листе **{len(L['main'])} групп размещения**. На дополнительном **{len(L['remaining'])} исходные группы повторены по {n} раза** — всего {len(L['supplementary'])} групп. Группа может включать несколько островов или контуров, связанных в исходнике; это не число всех физических островных деталей.

## Размещение с учётом станка

Все три густо подписанные российские части, включая европейскую часть с Москвой, среднюю часть с Уралом и крупную центральную часть с Красноярском, поставлены **у нижнего края**. Большая часть Африки стоит у нижнего края, США — у правого. Детали с мелкой разметкой размещались преимущественно ближе к правой и нижней стороне.

Для раскладки условно защищён **верхний левый квадрат 220 × 220 мм**. Ограничивающие рамки мелких красных элементов туда не заходят. В этой зоне могут находиться большие контуры, крупные надписи и участки деталей без мелкой гравировки. На справочной схеме участок отмечен пунктиром; в рабочих SVG/PDF этой рамки нет.

Проверка мелкой разметки использует красные элементы исходника с наибольшим размером рамки от 0,15 до 6 мм. Проверены полные рамки кривых, а не только центры. Учитывается качественное описание станка из задания; точные физические характеристики луча не измерялись.

Кратность выбрана среди найденных раскладок с этими ограничениями. Абсолютная математическая оптимальность не заявляется. Более плотная прежняя схема с семью повторами заменена текущей схемой ради расположения гравировки.

## Сохранность рисунка

Все **5357 исходных кривых и два текстовых объекта** сохранены в первоначальном виде после импорта CDR. Надписи не перенабирались и шрифты не заменялись. Команды путей, координаты узлов, цвета, стили, толщины линий и исходные разрывы совпадают с импортом. Кривые не сглаживались и не заменялись ломаными. Все элементы только перенесены вместе со своими группами.

**Поворот 0°, отражений нет, масштаб 1:1.** Существующие повороты надписей и островов остались исходными. Каждая страница SVG/PDF — ровно 740 × 740 мм. Минимальный измеренный зазор с учётом всей разметки — **{gap:.2f} мм**, отступ от границы поля не менее 5 мм. На рабочих листах нет дополнительных текстов, номеров или рамки резки.

Исходный CDR сохранён без изменений в `data/source/белый.cdr`. Рабочие файлы представлены в SVG и PDF; изменённый CDR не создавался. SVG открывается в CorelDRAW. Проверены записанные SVG и PDF; собственный импорт CorelDRAW здесь не проверялся, поскольку программа не установлена.

## Просмотр

![Основной лист]({main}.png)

![Дополнительный лист]({extra}.png)

В этих PNG для просмотра добавлена светлая заливка под детали и усилена видимая толщина линий. Рабочие SVG/PDF содержат только исходные элементы с исходными стилями.

## Проверки и генераторы

`Проверка-раскладки.json` подтверждает сохранность каждого исходного элемента, полноту наборов, зазоры и размеры страниц. `Проверка-зоны-станка.json` проверяет размещение ключевых групп и отсутствие мелких кривых в отведённом верхнем левом участке. Все переносы перечислены в `Переносы-деталей.csv`.

`source.svg` — полный импорт исходного CDR через libcdr/librevenge (`tools/import_cdr.cpp`), включая объекты за исходной страницей. Пересборка: extract.py → nest.py → сохранить layout.json как layout-before-machine-quality.json → nest_machine_quality.py → export.py → package.py. Скрипты лежат в tools/, зависимости — requirements.txt; для PDF/PNG нужен Inkscape. Короткие удерживающие разрывы временно замыкаются только в масках упаковки; исходные выходные кривые при этом не меняются.
'''
(P/'README.md').write_text(text);(P/'ПРОЧИТАТЬ.txt').write_text(text)
for path in (P/'tools').glob('*.py'):ast.parse(path.read_text())
files=[P/name for name in ['README.md','ПРОЧИТАТЬ.txt','Проверка-раскладки.json','Проверка-зоны-станка.json','Переносы-деталей.csv','Порядок-резки.pdf']]
for e in exports:
 for ext in ['svg','pdf','png']:files.append(P/(e['prefix']+'.'+ext))
checksum={f.name:{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}for f in files}
q=P/'Контрольные-суммы.json';q.write_text(json.dumps(checksum,ensure_ascii=False,indent=2));files.append(q)
with zipfile.ZipFile(P/zname,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
 for f in files:z.write(f,f.name)
with zipfile.ZipFile(P/zname)as z:
 assert z.testzip()is None
 for name,v in checksum.items():
  b=z.read(name);assert len(b)==v['bytes']and hashlib.sha256(b).hexdigest()==v['sha256']
print('PACKAGE VERIFIED',zname,n,'main runs + one supplementary',flush=True)
