"""Export full closed upper-ply outlines separately from the cleaned visible engraving."""
import json,os
from pathlib import Path
from shapely.geometry import shape
from shapely.affinity import translate
from lxml import etree as E
P=Path(__file__).resolve().parent.parent
# Use a single shared namespace for helper globals.
ns={'__file__':str(P/'tools/export.py')};exec(compile((P/'tools/export.py').read_text().split("parts={p['id']")[0],'svg-helpers','exec'),ns)
D=ns['D'];O=ns['P'];N=ns['N'];r=ns['root']();only=ns['root']();parts={q['id']:q for q in D['pieces']};count=0
for loc in N['placements']:
 q=parts[loc['source_id']];g=translate(shape(q['geom']),loc['dx_mm'],loc['dy_mm']);ns['polygon'](r,g,loc['id']+'_CUT','#000000',True);upper=shape(q['assembly_closed_outlines'])
 if upper.is_empty:continue
 upper=translate(upper,loc['dx_mm'],loc['dy_mm']);ns['polygon'](r,upper,loc['id']+'_MONTAGE','#ff0000',True);ns['polygon'](only,upper,loc['id']+'_MONTAGE','#ff0000',True);count+=1
ns['save'](r,O/'Полные-монтажные-контуры-740x740.svg');ns['save'](only,O/'Операции-по-цветам/Красный-полные-монтажные-контуры.svg')
for el in r.xpath('//*[local-name()="path"]'):
 if el.get('stroke')=='#ff0000':assert all(v.strip().endswith('Z')for v in el.get('d').split('M')if v.strip())
(O/'Проверка-монтажных-контуров.json').write_text(json.dumps({'passed':True,'all_upper_ply_outlines_closed_with_Z':True,'carriers_with_closed_outlines':count,'same_layout_coordinates':True,'part_rotation_or_scaling':False},ensure_ascii=False,indent=2));print('CLOSED MONTAGE OUTLINES',count)
