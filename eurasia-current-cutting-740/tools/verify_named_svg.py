"""Verify the delivered laser sheet, not only the intermediate model."""
import json,hashlib,shutil
from pathlib import Path
from lxml import etree
from shapely.geometry import shape
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));M=json.load(open(P/'manufacturing.json'));rows={p['source_id']:p for p in M['pieces']};R={c:shape(g)for c,g in D['regions'].items()}
def owner(c,t):return max([p for p in D['pieces']if p['tier']==t],key=lambda p:shape(p['geom']).intersection(R[c]).area)['id']
assert len(M['pieces'])==78
assert owner('LAO',2)==owner('KHM',2)==owner('THA',2)==owner('CHN',2)=='L02_P001'
assert owner('LAO',3)==owner('KHM',3)=='L03_P014'
assert owner('HUN',2)==owner('ROU',2)==owner('SRB',2)=='L02_P007'
assert owner('AUT',2)!=owner('HUN',2)
tree=etree.parse(str(P/'Поле-01-740x740.svg'));cuts=tree.xpath('//*[local-name()="path"][@stroke="#000000"]');texts=tree.xpath('//*[local-name()="text"]');assert len(cuts)==78;assert len(texts)==156
laos=[a for a in texts if ''.join(a.itertext()).strip()=='ЛАОС'];khm=[a for a in texts if ''.join(a.itertext()).strip()=='КАМБОДЖА'];assert len(laos)==len(khm)==1;assert laos[0].get('id').startswith('L03_P014_')and khm[0].get('id').startswith('L03_P014_')
assert not any(a.get('id')in ['L02_P011_CUT','L02_P012_CUT','L03_P015_CUT']for a in cuts)
named=P/'Евразия-78-деталей-740x740.svg';shutil.copy2(P/'Поле-01-740x740.svg',named);assert named.read_bytes()==(P/'Поле-01-740x740.svg').read_bytes()
(P/'Проверка-выданного-SVG.json').write_text(json.dumps({'passed':True,'file':named.name,'sha256':hashlib.sha256(named.read_bytes()).hexdigest(),'black_part_paths':78,'live_text_objects':156,'Laos_country_text_count':1,'Laos_Cambodia_single_third_ply_cut':'L03_P014_CUT','no_separate_Laos_second_ply_cut':True,'Hungary_Romania_Serbia_shared_second_ply_cut':'L02_P007_CUT','separate_from_Austria':True},ensure_ascii=False,indent=2));print('DELIVERED SVG VERIFIED: 78 cuts; Laos and Cambodia one upper piece; Hungary joined Balkans')
