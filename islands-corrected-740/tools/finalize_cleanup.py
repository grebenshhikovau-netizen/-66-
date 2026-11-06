"""Discard unlabelled detached smoothing slivers; do not change named main parts."""
import json
from pathlib import Path
from shapely.geometry import shape,mapping
from shapely.ops import unary_union
from shapely.affinity import affine_transform
P=Path(__file__).resolve().parent.parent;F=P/'01-Islands/data/production-plan.json';D=json.load(open(F));R=json.load(open(P/'data/island-roster.json'));T=D['atlas_registration_xy']
tiny=[r for r in D['pieces']if shape(r['geom']).area<15];tinyids={r['id']for r in tiny}
assert not any(a['piece']in tinyids for a in D['labels'])
D['pieces']=[r for r in D['pieces']if r['id']not in tinyids]
D['layers']=[mapping(unary_union([shape(r['geom'])for r in D['pieces']if r['tier']==i]))for i in [1,2,3]]
D['summary']=[{'tier':i,'pieces':sum(r['tier']==i for r in D['pieces'])}for i in [1,2,3]]
D['removed_smoothing_slivers']=[{'id':r['id'],'island':r['island_name'],'area_mm2':r['area_mm2']}for r in tiny]
for r in R:
 g=unary_union([shape(p['geom'])for p in D['pieces']if p['tier']==1 and p['island_id']==r['id']]);r['wood_geom']=mapping(g);r['geom']=mapping(affine_transform(g,T))
F.write_text(json.dumps(D,ensure_ascii=False));(P/'data/island-roster.json').write_text(json.dumps(R,ensure_ascii=False))
print('UNLABELLED SLIVERS REMOVED',len(tiny),'FINAL PHYSICAL PARTS',len(D['pieces']))
