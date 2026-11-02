"""Append editable red city/state annotations; leave existing cuts and layout byte-identical."""
import json,copy,hashlib
from pathlib import Path
from lxml import etree as E
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.affinity import translate
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));L=json.load(open(P/'data/layout.json'));S='http://www.w3.org/2000/svg'
base=E.parse(str(P/'data/source/Поле-01-740x740.svg'));root=base.getroot()
red=E.SubElement(root,'{'+S+'}g',id='RED_CITIES_AND_BRAZIL_STATES')
def lines(g):
 if g.geom_type in ['LineString','LinearRing']:return[g]if g.length>.01 else[]
 return[l for q in getattr(g,'geoms',[])for l in lines(q)]
def trace(g,id):
 dd=' '.join('M'+' L'.join(f'{x:.6f},{y:.6f}'for x,y in q.coords)for q in lines(g))
 if dd:E.SubElement(red,'{'+S+'}path',id=id,d=dd,fill='none',stroke='#ff0000',attrib={'stroke-width':'.05','stroke-linecap':'round','stroke-linejoin':'round'})
def text(a,id,dx,dy):
 mat=a['matrix'][:];mat[4]+=dx;mat[5]+=dy
 e=E.SubElement(red,'{'+S+'}text',id=id,fill='#ff0000',stroke='none',attrib={
  'font-family':'Open Sans Light','font-size':f"{a['font_size_mm']:.9f}",'font-weight':'300','font-kerning':'none',
  'style':"font-kerning:none;font-feature-settings:'kern' 0",'transform':'matrix('+','.join(f'{v:.12f}'for v in mat)+')'})
 for ln in a['lines']:
  t=E.SubElement(e,'{'+S+'}tspan',x=f"{ln['x_em']*a['font_size_mm']:.9f}",y=f"{ln['y_em']*a['font_size_mm']:.9f}");t.text=ln['text']
rows={p['id']:p for p in D['pieces']}
for loc in L['placements']:
 id=loc['source_id'];dx,dy=loc['dx_mm'],loc['dy_mm'];row=rows[id]
 trace(translate(shape(row['brazil_state_lines']),dx,dy),loc['id']+'_STATE_BORDERS')
 for a in D['labels']:
  if a['piece']==id and a['kind']!='country':text(a,loc['id']+'_'+a['id'],dx,dy)
 for m in D['city_markers']:
  if m['piece']==id:
   x,y=m['point'];E.SubElement(red,'{'+S+'}circle',id=loc['id']+'_'+m['id'],cx=f'{x+dx:.6f}',cy=f'{y+dy:.6f}',r='.22',fill='#ff0000',stroke='none')
out=P/'Поле-01-740x740.svg';base.write(str(out),encoding='utf-8',xml_declaration=True)
old=E.parse(str(P/'data/source/Поле-01-740x740.svg'));new=E.parse(str(out))
def cuts(doc):return[E.tostring(q,method='c14n')for q in doc.xpath('//*[local-name()="g" and @id="BLACK_THROUGH_CUT"]/*')]
assert cuts(old)==cuts(new)
def blue(doc):return[E.tostring(q,method='c14n')for q in doc.xpath('//*[local-name()="g" and @id="BLUE_COUNTRY_TITLES"]/*')]
assert blue(old)==blue(new)
report={'passed':True,'stock_mm':[740,740],'kits':3,'wood_parts_per_kit':18,'total_cut_parts':54,
 'black_cut_elements_identical_to_previous_SVG':True,'existing_country_text_identical':True,
 'city_names_per_kit':len(D['city_markers']),'state_names_per_kit':sum(a['kind']=='state'for a in D['labels']),
 'live_texts_in_field':len(new.xpath('//*[local-name()="text"]')),'city_markers_in_field':len(new.xpath('//*[local-name()="circle"]'))}
assert report['live_texts_in_field']==len(D['labels'])*3
# Independently verify whole words on one exposed carrier and no label collisions.
boxes=[]
from shapely.geometry import box
for a in D['labels']:
 bb=box(*shape(a['geometry']).bounds);row=rows[a['piece']];assert shape(row['visible']).buffer(.001).covers(bb),(a['text'],'not on exposed surface')
 for b in boxes:assert not bb.intersects(b),(a['text'],'caption collision')
 boxes.append(bb)
for m in D['city_markers']:assert shape(rows[m['piece']]['visible']).buffer(.001).covers(shape(m['geometry'])),m['name']
report['whole_words_on_exposed_single_parts']=True;report['no_label_bbox_collisions']=True
(P/'Проверка-SVG.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('SVG VERIFIED',report,flush=True)
