"""Install the shared generators in each independently reproducible cutting batch."""
from pathlib import Path
import json,gzip,shutil
from shapely.geometry import shape,mapping
from shapely.affinity import translate
from shapely.ops import unary_union
P=Path(__file__).resolve().parent.parent;S={k:json.load(gzip.open(P/f'data/source/{k}-approved-plan.json.gz','rt'))for k in ['RU','EU','AF']};C=json.load(open(P/'data/batch-countries.json'))
for o in sorted(q for q in P.iterdir()if q.is_dir()and q.name[:2]in ['01','02']):
 shutil.copytree(P/'tools',o/'tools',dirs_exist_ok=True);shutil.copytree(P/'Шрифт',o/'Шрифт',dirs_exist_ok=True)
 for name in ['requirements.txt','.gitignore']:shutil.copy2(P/name,o/name)
 D=json.load(open(o/'data/production-plan.json'));faces={}
 for tier in range(1,len(D['layers'])+1):
  gg=[]
  for k in (['RU','EU']if D['batch']=='EAST'else['AF','EU']):
   for row in S[k]['pieces']:
    if row['tier']!=tier:continue
    g=shape(row.get('red_pyramid_faces',{'type':'GeometryCollection','geometries':[]}))
    if k=='AF':g=translate(g,*C['africa_translation_mm'])
    gg.append(g)
  faces[str(tier)]=mapping(unary_union(gg))
 D['accent_faces_by_tier']=faces;(o/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False))
 (o/'ПРОЧТИ-МЕНЯ.txt').write_text(D['title']+'\nОбщие физические детали по высоте; водные вырезы во всех слоях. Центры снизу, гравировка следует за верхом. Скандинавия отдельным блоком во втором комплекте. SVG 740 × 740 мм, детали только перенесены, текст редактируется. Синий — страны, красный — города и границы, чёрный — сквозная резка.')
 print('BATCH TOOLS READY',o.name,flush=True)
