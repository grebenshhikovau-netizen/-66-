"""Retain the existing city set when a whole label must move to a neighbouring exposed ply."""
from pathlib import Path
code=(Path(__file__).parent/'labels.py').read_text().split('# Every source country')[0];exec(compile(code,'labels-placement','exec'))
labels=D['labels'];markers=D['city_markers'];seen={m['name']for m in markers};occupied=unary_union([shape(a['bbox']).buffer(.18)for a in labels]+[shape(m['geom']).buffer(.22)for m in city_candidates])
for m in city_candidates:
 if m['name']in seen:continue
 entry=add_label(m['id']+'_TEXT',m['name'],'city',Point(m['point_mm']),1.6,region=m['region'])
 assert entry,(m['name'],'existing city label lost');markers.append(m)
D['labels']=labels;D['city_markers']=markers;D['label_notes']=[n for n in D['label_notes']if n.get('city')not in {m['name']for m in markers}];(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));(P/'data/labels.json').write_text(json.dumps({'labels':labels,'markers':markers,'notes':D['label_notes']},ensure_ascii=False));print('ALL ORIGINAL CITIES RETAINED',len(markers),len(labels),flush=True)
