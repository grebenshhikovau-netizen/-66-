"""Grow only the named small focal islands until every wood title fits at >=2 mm."""
import json,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parent.parent
over=json.load(open(P/'data/readability-scale-overrides.json'))if(P/'data/readability-scale-overrides.json').exists()else{}
for attempt in range(6):
 print('TITLE FIT PASS',attempt+1,flush=True)
 subprocess.run([sys.executable,str(P/'tools/build_islands.py')],check=True)
 d=json.load(open(P/'01-Islands/data/production-plan.json'));r=json.load(open(P/'data/island-roster.json'));ids={x['island_id']for x in d['labels']if x.get('label_role')in['island_name','primary_island_name']};missing=[x for x in r if x['id']not in ids]
 if not missing:print('ALL',len(r),'NAMED WOODEN ISLANDS HAVE READABLE TITLES',flush=True);break
 for x in missing:
  assert x['width']>0,('large island could not be captioned',x['id'])
  over[x['id']]=over.get(x['id'],1)*1.3
 (P/'data/readability-scale-overrides.json').write_text(json.dumps(over,ensure_ascii=False,indent=2));print('GROW FOR CAPTION',[x['id']for x in missing],flush=True)
else:raise RuntimeError('Some islands still lack a readable title')
