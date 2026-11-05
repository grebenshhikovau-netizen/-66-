"""Check actual one-kit SVG, approved material, exposed paint and the narrower base slot."""
import json,gzip,re
from pathlib import Path
from collections import Counter
from lxml import etree as E
from shapely.geometry import shape,box,Polygon
from shapely.ops import unary_union
from shapely.affinity import translate
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));L=json.load(open(P/'data/layout.json'));OLD=json.load(gzip.open(P/'data/source/approved-plan.json.gz','rt'));svg=E.parse(str(P/'Поле-01-740x740.svg'))
assert svg.getroot().get('width')=='740mm'and svg.getroot().get('height')=='740mm'
assert L['kits']==1 and len(L['placements'])==len(D['pieces'])==17
gmap={p['id']:shape(p['geom'])for p in D['pieces']};rows={p['id']:p for p in D['pieces']};placed=[]
for loc in L['placements']:
 assert loc['rotation_degrees']==0 and not loc['mirrored']and loc['scale']==1
 node=svg.xpath('//*[@id="'+loc['id']+'_CUT"]');assert len(node)==1
 d=node[0].get('d');assert re.fullmatch(r'[MLZ0-9eE+,\.\-\s]+',d)
 g=Polygon()
 for ring in re.findall(r'M([^M]+?)Z',d):
  nums=[float(x)for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',ring)];poly=Polygon(list(zip(nums[::2],nums[1::2])));assert poly.is_valid and poly.area>0
  g=g.symmetric_difference(poly)
 expected=gmap[loc['id']];assert g.symmetric_difference(expected).area<.01,(loc['id'],'serialized contour changed')
 g=translate(g,loc['dx_mm'],loc['dy_mm']);assert box(5,5,735,735).covers(g)
 for h in placed:assert g.distance(h)>=3
 placed.append(g)
for r in D['pieces']:
 assert gmap[r['id']].geom_type=='Polygon'and gmap[r['id']].is_valid
 if r['tier']==3:assert not('CHL'in r['regions']and'ARG'in r['regions'])
for a in D['labels']:
 bb=box(*shape(a['geometry']).bounds);assert shape(rows[a['piece']]['visible']).buffer(.00001).covers(bb),(a['text'],'hidden/overhang')
texts=svg.xpath('//*[local-name()="text"]');assert len(texts)==len(D['labels'])
assert Counter(a['text']for a in D['labels'])==Counter(a['text']for a in OLD['labels'])
for i in [1,2]:assert shape(D['layers'][i]).symmetric_difference(shape(OLD['layers'][i])).area<.0001
actual=shape(OLD['layers'][0]).difference(shape(D['layers'][0]));assert actual.area>50 and actual.symmetric_difference(shape(D['base_water_union'])).area<.0001
upper=shape(D['layers'][1]);assert actual.intersection(upper.buffer(.149)).area<.00001
for r in D['pieces']:
 paint=list(r['paint'].items())
 for j,(coat,p)in enumerate(paint):
  v=shape(p['visible']).buffer(-.02)
  for c,q in paint[:j]:
   w=shape(q['visible']).buffer(-.02);assert v.is_empty or w.is_empty or v.distance(w)>=.75-1e-5
  assert shape(p['with_overlap']).difference(shape(p['visible'])).difference(shape(D['layers'][r['tier']])if r['tier']<3 else Polygon()).area<.001
report={'passed':True,'kits':1,'parts':17,'layers':[4,5,8],'live_texts':len(texts),'city_names':len(D['city_markers']),
 'all_previous_annotations_preserved':True,'each_part_single_connected_polygon':True,'upper_Chile_and_Argentina_separate':True,
 'approved_second_and_third_height_fields_unchanged':True,'base_slot_visible_and_narrower_than_upper_valley':True,
 'minimum_step_bank_mm':.15,'new_base_water_cut_mm2':actual.area,'base_bridges':len(D['river_bridges']),
 'painting_conflicts':0,'translation_only':True,'minimum_gap_mm':L['actual_min_gap_mm']}
(P/'Проверка-раскроя.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('CUTTING VERIFIED',report,flush=True)
