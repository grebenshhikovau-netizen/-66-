"""Verify editable Unicode SVG text while preserving every cut and non-text mark."""
import json,re,hashlib
from pathlib import Path
from lxml import etree as E
from shapely.geometry import shape,Polygon,box
from shapely.ops import unary_union
from shapely.affinity import translate
from pypdf import PdfReader
from fontTools.ttLib import TTFont
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/manufacturing.json'));C=json.load(open(P/'data/text-content.json'));before=json.load(open(P/'data/unchanged-geometry-before-live-text.json'));plan=json.load(open(P/'data/source/production-plan.json'));source={q['id']:q for q in plan['pieces']};font=TTFont(P/'Шрифт/OpenSans-Light.ttf');cmap=font.getBestCmap();reports=[]
def parse(d):
 rings=[]
 for seq in re.findall(r'M([^M]+)',d):
  v=[float(x)for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',seq)];rings.append(list(zip(v[::2],v[1::2])))
 outer=[];holes=[]
 for r in rings:
  a=sum(x*y2-x2*y for(x,y),(x2,y2)in zip(r,r[1:]+r[:1]))
  (outer if a<0 else holes).append(r)
 pp=[Polygon(r)for r in outer];assigned={i:[]for i in range(len(pp))}
 for h in holes:
  owners=[i for i,g in enumerate(pp)if g.covers(Polygon(h).representative_point())];assert owners;assigned[min(owners,key=lambda i:pp[i].area)].append(h)
 return unary_union([Polygon(r,assigned[i])for i,r in enumerate(outer)])
for sheet in sorted(set(p['sheet']for p in D['pieces'])):
 tree=E.parse(str(P/f'Поле-{sheet:02d}-740x740.svg'));root=tree.getroot();assert root.get('width')==root.get('height')=='740mm';assert root.get('viewBox')=='0 0 740 740';assert not root.xpath('//*[local-name()="image"]');texts=root.xpath('//*[local-name()="text"]');assert len(texts)==82*D['sets'];elements={e.get('id'):e for e in texts}
 paths={e.get('id'):e for e in root.xpath('//*[local-name()="path"]')};assert set(paths)==set(before)
 for id,attrs in before.items():assert dict(paths[id].attrib)==attrs,(id,'non-text geometry changed')
 assert not root.xpath('//*[local-name()="path"][@transform]');cuts={id[:-4]:parse(el.get('d'))for id,el in paths.items()if id.endswith('_CUT')};assert len(cuts)==28*D['sets'];errors=[]
 for p in D['pieces']:
  if p['sheet']!=sheet:continue
  expected=translate(shape(source[p['source_id']]['geom']),p['dx_mm'],p['dy_mm']);g=cuts[p['id']];error=g.symmetric_difference(expected).area;assert error<.001;errors.append(error);assert g.is_valid and box(5,5,735,735).covers(g)
  for id,a in p['red_texts'].items():
   key=p['id']+'_'+id;el=elements[key];assert el.text==C[id]==a['text'];assert len(el)==0;assert el.get('fill')=='#ff0000'and el.get('stroke')=='none';assert el.get('font-family')=='Open Sans Light';assert all(ord(ch)in cmap for ch in el.text);assert float(el.get('font-size'))>0
   values=[float(x)for x in el.get('transform').removeprefix('matrix(').removesuffix(')').split(',')];assert max(abs(x-y)for x,y in zip(values,a['matrix']))<1e-10;assert abs(float(el.get('font-size'))-a['font_size_mm'])<1e-8
   visible=translate(shape(source[p['source_id']]['visible']),p['dx_mm'],p['dy_mm']);assert shape(a['outline_for_validation']).difference(visible.buffer(.015)).area<.0002,(id,'outside exposed surface')
 distances=[g.distance(h)for id,g in cuts.items()for other,h in cuts.items()if id<other];assert min(distances)>=3
 pdf=PdfReader(P/f'Поле-{sheet:02d}-740x740.pdf');page=pdf.pages[0];width=float(page.mediabox.width)*25.4/72;height=float(page.mediabox.height)*25.4/72;assert abs(width-740)<.001 and abs(height-740)<.001;content=re.sub(r'\s+','',page.extract_text());expectedtext=[a['text']for p in D['pieces']for a in p['red_texts'].values()]
 for word in expectedtext:assert re.sub(r'\s+','',word)in content,(word,'PDF is missing searchable text')
 reports.append({'sheet':sheet,'editable_red_text_objects':len(texts),'text_stored_as':'UTF-8 SVG text elements','font':'Open Sans Light','font_file_supplied':True,'pdf_contains_searchable_unicode_text':True,'all_non_text_paths_unchanged':True,'black_cut_parts':len(cuts),'max_cut_rounding_error_mm2':max(errors),'actual_min_gap_mm':min(distances),'page_mm':[width,height],'part_rotation':0,'part_reflection':False,'part_scale':1,'blue_titles_unchanged':['США','КАНАДА','МЕКСИКА','АЛЯСКА']})
result={'passed':True,'fields':reports,'all_original_wordings_transcribed_from_source':True,'cdr_source_already_contained_outlines':True,'coreldraw_not_available_for_native_application_test':True,'pdf_import_instruction':'Import text as text; do not choose curves.'};(P/'Проверка-раскроя.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('EDITABLE TEXT AND UNCHANGED CUTS VERIFIED',reports,flush=True)
