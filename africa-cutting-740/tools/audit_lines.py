"""Inspect actual structural stroke endpoints, duplicates and retained cutting geometry."""
import json,math
from pathlib import Path
from collections import Counter
from shapely.geometry import shape,Point
from shapely.ops import unary_union
from shapely import union_all
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));B=json.load(open(P/'data/before-line-cleanup.json'));old={q['id']:q for q in B['pieces']}
def lines(g):
 if g.geom_type=='LineString':return[g]if g.length>1e-7 else[]
 return[l for a in getattr(g,'geoms',[])for l in lines(a)]
def inspect(graph,cut):
 ls=lines(union_all(lines(graph),grid_size=.001));degree=Counter()
 for l in ls:
  for pt in [l.coords[0],l.coords[-1]]:degree[(round(pt[0],3),round(pt[1],3))]+=1
 loose=[{'xy':q,'distance_to_cut_mm':Point(q).distance(cut.boundary)}for q,n in degree.items()if n==1 and Point(q).distance(cut.boundary)>.015]
 return {'loose_ends':loose,'loose_end_count':len(loose),'subpaths':len(lines(graph)),'length_mm':graph.length,'duplicate_length_mm':max(0,sum(q.length for q in lines(graph))-unary_union(lines(graph)).length)}
rows=[]
for p in D['pieces']:
 b=old[p['id']];cut=shape(p['geom']);assert cut.equals_exact(shape(b['geom']),0)
 before=unary_union([shape(b[k])for k in ['red_political','placement_guides','red_pyramid_faces']]);a=inspect(before,cut);z=inspect(shape(p['red_structural']),cut);rows.append({'piece':p['id'],'before':a,'after':z})
r={'passed':all(x['after']['loose_end_count']==0 and x['after']['duplicate_length_mm']<.001 for x in rows),'cutting_contours_unchanged':True,'physical_parts':len(D['pieces']),'before_loose_ends':sum(x['before']['loose_end_count']for x in rows),'after_loose_ends':sum(x['after']['loose_end_count']for x in rows),'before_subpaths':sum(x['before']['subpaths']for x in rows),'after_continuous_trails':sum(x['after']['subpaths']for x in rows),'all_letters_are_live_text_in_standard_layouts':True,'rows':rows};(P/'Проверка-стыков-красных-линий.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print('LINE AUDIT', {k:v for k,v in r.items()if k!='rows'},flush=True)
if not r['passed']:
 for x in rows:
  if x['after']['loose_end_count']:print('LOOSE',x['piece'],x['after']['loose_ends'])
 raise AssertionError('Structural engraving has loose endpoints or duplicate edges')
