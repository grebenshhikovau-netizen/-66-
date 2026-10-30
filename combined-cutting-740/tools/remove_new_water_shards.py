"""Drop new insignificant bank fragments, preserving all approved small peaks and islands."""
import gzip,json
from pathlib import Path
from shapely.geometry import shape,mapping
from shapely.ops import unary_union
from shapely.affinity import translate
P=Path(__file__).resolve().parent.parent;S={k:json.load(gzip.open(P/f'data/source/{k}-approved-plan.json.gz','rt'))for k in ['RU','EU','AF']};cfg=json.load(open(P/'data/batch-countries.json'))
for O in sorted(p for p in P.iterdir()if p.is_dir()and p.name[:2]in ['01','02']):
 D=json.load(open(O/'data/production-plan.json'));water=shape(D['water_upper_union']);removed=[];oldsmall={}
 for family in (['RU','EU']if D['batch']=='EAST'else['AF','EU']):
  for row in S[family]['pieces']:
   if row['tier']<2 or row['area_mm2']>60:continue
   g=shape(row['geom']);g=translate(g,*cfg['africa_translation_mm'])if family=='AF'else g;oldsmall.setdefault(row['tier'],[]).append(g)
 keep=[]
 for q in D['pieces']:
  g=shape(q['geom']);isapproved=any(g.intersection(old).area>.8*min(old.area,g.area)for old in oldsmall.get(q['tier'],[]))
  if q['tier']>1 and g.area<40 and g.distance(water)<.1 and not isapproved:removed.append({'tier':q['tier'],'id':q['id'],'area_mm2':g.area,'geom':q['geom'],'reason':'new nonessential riverbank fragment under 40 mm²'});continue
  keep.append(q)
 D['pieces']=keep;D['removed_micro_parts']+=removed;D['new_bank_fragment_limit_mm2']=40
 for i in range(len(D['layers'])):D['layers'][i]=mapping(unary_union([shape(q['geom'])for q in keep if q['tier']==i+1]))
 for q in keep:
  g=shape(q['geom']);q['visible']=mapping(g.difference(shape(D['layers'][q['tier']])))if q['tier']<len(D['layers'])else q['geom']
 for s in D['summary']:s['pieces']=sum(q['tier']==s['tier']for q in keep)
 (O/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));print('BANK FRAGMENTS REMOVED',O.name,len(removed),'parts left',len(keep),flush=True)
