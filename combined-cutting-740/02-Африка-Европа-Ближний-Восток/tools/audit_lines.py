"""Check that geographic engraving is joined and every real edge is traversed once."""
import json
from pathlib import Path
from collections import Counter
from shapely.geometry import shape,Point
from shapely import union_all
from shapely.ops import unary_union
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'))
def lines(g):
 if g.geom_type=='LineString':return[g]if g.length>1e-7 else[]
 return[l for a in getattr(g,'geoms',[])for l in lines(a)]
rows=[]
for row in D['pieces']:
 g=shape(row['geom']);red=shape(row['red_structural']);ll=lines(union_all(lines(red),grid_size=.001));degree=Counter()
 for l in ll:
  for xy in [l.coords[0],l.coords[-1]]:degree[(round(xy[0],3),round(xy[1],3))]+=1
 loose=[{'xy':q,'distance_to_cut_mm':Point(q).distance(g.boundary)}for q,n in degree.items()if n==1 and Point(q).distance(g.boundary)>.015];duplicate=max(0,sum(l.length for l in lines(red))-unary_union(lines(red)).length);rows.append({'part':row['id'],'free_geographic_ends':loose,'duplicate_length_mm':duplicate,'continuous_trails':len(lines(red))})
r={'passed':all(not x['free_geographic_ends']and x['duplicate_length_mm']<.001 for x in rows),'physical_parts':len(D['pieces']),'free_geographic_end_count':sum(len(x['free_geographic_ends'])for x in rows),'duplicate_geographic_length_mm':sum(x['duplicate_length_mm']for x in rows),'rows':rows};(P/'Проверка-стыков-красных-линий.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print('LINE AUDIT',r['passed'],r['free_geographic_end_count'],'loose ends',flush=True)
assert r['passed'],[x for x in rows if x['free_geographic_ends']or x['duplicate_length_mm']>=.001]
