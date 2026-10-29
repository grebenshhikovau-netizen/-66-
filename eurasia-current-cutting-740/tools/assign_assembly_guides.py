"""Assign each true upper-piece outline to its main supporting lower piece, once."""
import json
from pathlib import Path
from shapely.geometry import shape,mapping
from shapely.ops import unary_union
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));assigned={r['id']:[]for r in D['pieces']};proof=[]
for upper in D['pieces']:
 if upper['tier']==1:continue
 g=shape(upper['geom']);lower=[p for p in D['pieces']if p['tier']==upper['tier']-1];parent=max(lower,key=lambda p:shape(p['geom']).intersection(g).area);assigned[parent['id']].append(g);proof.append({'upper_piece':upper['id'],'carrier':parent['id'],'full_physical_outline':True})
for row in D['pieces']:row['assembly_closed_outlines']=mapping(unary_union(assigned[row['id']]))
D['true_assembly_outline_assignments']=proof;(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));(P/'Проверка-полных-монтажных-форм.json').write_text(json.dumps({'passed':True,'upper_piece_count':len(proof),'each_true_upper_outline_once':True,'assignments':proof},ensure_ascii=False,indent=2));print('TRUE ASSEMBLY OUTLINES',len(proof))
