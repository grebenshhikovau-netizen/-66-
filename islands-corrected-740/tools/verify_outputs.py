"""Artifact checks, including independent named-geography checks for the two polar islands."""
import json,math,re
from pathlib import Path
import numpy as np
from lxml import etree as E
from shapely.geometry import shape,box,Polygon
from shapely.ops import unary_union,transform
from shapely.affinity import translate
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'01-Islands/data/production-plan.json'));R=json.load(open(P/'data/island-roster.json'));L=json.load(open(P/'01-Islands/data/layout.json'));A=json.load(open(P/'data/acrylic-engraving.json'));reg=json.load(open(P/'data/source/named-geographic-regions.geojson'));proj=json.load(open(P/'data/source/world-projection.json'));byid={r['id']:r for r in R};pieces={r['id']:r for r in D['pieces']};locations={r['source_id']:r for r in L['placements']}
assert len(R)>=63 and len(pieces)==len(locations)
assert all(shape(p['geom']).is_valid and shape(p['geom']).geom_type=='Polygon'and shape(p['geom']).area>=15 for p in pieces.values())
def project(x,y):return proj['lon_to_x_mm']*np.asarray(x)+proj['x_offset_mm'],proj['y_offset_mm']-proj['mercator_to_y_mm']*np.log(np.tan(np.pi/4+np.radians(y)/2))
critical={}
for ident,name in [('ellesmere','ELLESMERE  ISLAND'),('baffin','BAFFIN ISLAND')]:
 ref=transform(project,shape(next(f['geometry']for f in reg['features']if f['properties']['NAME']==name)));source=shape(byid[ident]['source_geom']);fraction=source.intersection(ref).area/source.area;assert fraction>.65,(ident,'geographic identity mismatch',fraction);critical[ident]={'independent_named_region_overlap':fraction}
assert {'maldives','seychelles','mauritius','reunion','hawaii','galapagos','easter','tahiti','fiji','vanuatu','solomons','tonga','samoa','malta'}<=set(byid)
placed=[]
for id,row in pieces.items():
 g=shape(row['geom']);assert row['island_id']in byid
 assert g.difference(shape(byid[row['island_id']]['wood_geom'])).area<.001
 if row['tier']>1:assert g.difference(shape(D['layers'][row['tier']-2])).area<.001
 loc=locations[id];assert loc['rotation_degrees']==0 and not loc['mirrored']and loc['scale']==1
 h=translate(g,loc['dx_mm'],loc['dy_mm']);assert box(5,5,735,735).covers(h)
 for other in placed:assert h.distance(other)>=3
 placed.append(h)
owners={}
for a in D['labels']:
 row=pieces[a['piece']];assert row['island_id']==a['island_id'],(a['text'],'attached to a different island')
 ink=shape(a['outline_for_validation']);visible=shape(row['geom']).difference(shape(D['layers'][row['tier']])if row['tier']<3 else Polygon());assert ink.difference(visible).area<.00001,(a['text'],'crosses a coastline or hidden terrace')
 assert ink.difference(shape(byid[a['island_id']]['wood_geom'])).area<.00001
 assert a['color']==('#0000ff'if a['kind']=='country'else'#ff0000')
 if a.get('label_role')in ['island_name','primary_island_name']:
  assert a['font_size_mm']>=2.0;owners.setdefault(a['island_id'],[]).append(a)
assert set(owners)==set(byid),'every wooden focal island must have its own visible title'
assert any(pieces[a['piece']]['tier']==1 for a in owners['ellesmere'])
assert any(a['font_size_mm']>=5 for a in owners['ellesmere'])
assert any(pieces[a['piece']]['tier']==1 and a['font_size_mm']>=4.5 for a in owners['baffin'])
ns={'s':'http://www.w3.org/2000/svg'};root=E.parse(str(P/'01-Islands/Поле-01-740x740.svg'));assert len(root.xpath('//s:text',namespaces=ns))==len(D['labels']);assert not root.xpath('//s:image',namespaces=ns)
cuts=root.xpath('//s:path[@stroke="#000000"]',namespaces=ns);assert len(cuts)==len(pieces)
for node in cuts:
 d=node.get('d');assert d.count('M')==d.count('Z')and d.endswith('Z')
 for ring in re.findall(r'M([^MZ]+) Z',d):
  xy=[tuple(map(float,q.split(',')))for q in ring.split(' L')];g=Polygon(xy);assert g.is_valid and g.area>1e-8
acryl=E.parse(str(P/'Мелкие-острова-гравировка-оргстекла.svg'));assert not acryl.xpath('//s:*[@stroke="#000000"]',namespaces=ns);assert len(acryl.xpath('//s:path[@stroke="#ff0000"]',namespaces=ns))==1;assert len(A['islands'])>2000
assert shape(A['geom']).is_valid
for entry in A['islands']:
 if entry['country']=='RUS':assert shape(entry['geom']).centroid.x*D['atlas_registration_xy'][0]+D['atlas_registration_xy'][4]>990, 'Russian mainland fragment on wrong side of dateline'
report={'wooden_named_islands':len(R),'wood_parts':len(pieces),'layers':D['summary'],'editable_texts':len(D['labels']),'city_labels':sum(a['kind']=='city'for a in D['labels']),'named_islands_with_visible_wood_titles':len(owners),'main_title_min_font_size_mm':min(a['font_size_mm']for aa in owners.values()for a in aa),'critical_geographic_checks':critical,'minor_islands_engraved_on_acrylic':len(A['islands']),'acrylic_has_no_cut_paths':True,'one_740x740_sheet':True,'translation_only':True,'minimum_part_gap_mm':L['actual_min_gap_mm'],'removed_unlabelled_micro_slivers':len(D['removed_smoothing_slivers']),'all_caption_owners_match_named_islands':True,'all_cuts_closed_valid':True}
(P/'Проверка-исправления.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
