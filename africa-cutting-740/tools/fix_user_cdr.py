"""Keep the user's CDR lettering/cutting edits; replace only thin red geographic linework."""
import json,re,math,copy,hashlib
from pathlib import Path
from lxml import etree as E
from shapely.geometry import shape,LineString,MultiLineString,Point
from shapely.ops import unary_union
from shapely.affinity import translate
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));LOC=json.load(open(P/'data/layout.json'))['placements'];S='http://www.w3.org/2000/svg';K=72/25.4;src=E.parse(str(P/'data/source/Из-CDR.svg'));root=src.getroot()
# Definitions only: use the same edge-priority rule as the canonical production files.
context={'__file__':str(P/'tools/clean_structure.py')};code=(P/'tools/clean_structure.py').read_text().split('allgraph=[];stats=[]')[0];exec(compile(code,'line-cleaning','exec'),context);drop_parallel=context['drop_parallel'];snap_ends=context['snap_ends'];heal=context['heal']
def lines(g):
 if g.geom_type=='LineString':return[g]if g.length>1e-7 else[]
 return[l for a in getattr(g,'geoms',[])for l in lines(a)]
def dline(g):
 return ' '.join('M'+' L'.join(f'{x*K:.6f},{y*K:.6f}'for x,y in (list(q.coords)[:-1]if q.is_ring else q.coords))+(' Z'if q.is_ring else'')for q in lines(g))
def thin_red(e):return E.QName(e).localname=='path'and'stroke: #ff0000'in e.get('style','')and'stroke-width: 0.1417;'in e.get('style','')
def black(e):return E.QName(e).localname=='path'and'stroke: #000000'in e.get('style','')
bl=[]
for el in root.iter():
 if not black(el):continue
 for seq in re.findall(r'M([^M]+)',el.get('d','')):
  nums=[float(v)/K for v in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',seq)];cc=list(zip(nums[::2],nums[1::2]));
  if 'Z'in seq and cc[-1]!=cc[0]:cc.append(cc[0])
  if len(cc)>1:bl.append(LineString(cc))
blacknetwork=unary_union(bl);beforeblack=[el.get('d')for el in root.iter()if black(el)];beforetexts=[E.tostring(el)for el in root.xpath('//*[local-name()="text"]')];full=copy.deepcopy(root);removed=0
for el in list(full.iter()):
 if thin_red(el):el.getparent().remove(el);removed+=1
replacement=E.SubElement(full,'{'+S+'}g',id='CONTINUOUS_RED_GEOGRAPHY');partbyid={q['id']:q for q in D['pieces']};instances=[{'source_id':q['source_id'],'dx_mm':q['dx_mm']-265,'dy_mm':q['dy_mm']-221.5}for q in LOC]
# The off-page duplicate in the supplied CDR is kept in the full review drawing.
instances.append({'source_id':'L03_P001','dx_mm':-249.25749712509844,'dy_mm':1127.6992014272314})
for i,pos in enumerate(instances):
 row=partbyid[pos['source_id']];g=translate(shape(row['geom']),pos['dx_mm'],pos['dy_mm']);red=translate(shape(row['red_structural']),pos['dx_mm'],pos['dy_mm']);local=blacknetwork.intersection(g.envelope.buffer(2));red=drop_parallel(red,local,.35);red=snap_ends(red,local,.9);red=heal(red.intersection(g),g)
 E.SubElement(replacement,'{'+S+'}path',id=f'GEO_{i+1:02d}_{row["id"]}',d=dline(red),fill='none',stroke='#ff0000',attrib={'stroke-width':f'{.05*K:.6f}','stroke-linecap':'round','stroke-linejoin':'round'})
assert [el.get('d')for el in full.iter()if black(el)]==beforeblack;assert [E.tostring(el)for el in full.xpath('//*[local-name()="text"]')]==beforetexts
# Main working page returns the original 740 mm layout; the off-page comparison copy stays in a separate review file.
main=E.Element('{'+S+'}svg',nsmap=root.nsmap,version='1.1',width='740mm',height='740mm',viewBox='0 0 740 740');body=E.SubElement(main,'{'+S+'}g',transform=f'matrix({1/K:.12f},0,0,{1/K:.12f},265,221.5)')
def min_y(el):
 yy=[]
 for q in el.iter():
  if E.QName(q).localname=='path':
   nums=[float(v)/K for v in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',q.get('d',''))];yy.extend(nums[1::2])
  elif q.get('y'):
   try:yy.append(float(q.get('y'))/K)
   except ValueError:pass
 return min(yy)if yy else -1e9
for child in full:
 if child is replacement:
  group=copy.deepcopy(child)
  for e in list(group):
   if e.get('id','').startswith('GEO_16_'):group.remove(e)
  body.append(group)
 elif min_y(child)<250:body.append(copy.deepcopy(child))
# Full review drawing includes every source object, with a page that encompasses the drawing.
x0,y0,x1,y1=blacknetwork.bounds;full.set('width',f'{x1-x0+10:.6f}mm');full.set('height',f'{y1-y0+10:.6f}mm');full.set('viewBox',f'{(x0-5)*K:.6f} {(y0-5)*K:.6f} {(x1-x0+10)*K:.6f} {(y1-y0+10)*K:.6f}')
for name,tree in [('Африка-твои-правки-740x740.svg',main),('CDR-полный-чертёж-исправлено.svg',full)]:E.ElementTree(tree).write(str(P/name),encoding='UTF-8',xml_declaration=True)
(P/'Проверка-правок-CDR.json').write_text(json.dumps({'source_file':'Африка на доработке.cdr','removed_old_thin_red_paths':removed,'replacement_geographic_instances':len(instances),'all_source_black_paths_preserved_in_full_review':True,'all_source_text_objects_preserved_in_full_review':True,'source_text_objects':len(beforetexts),'source_single_line_lettering_and_blue_letter_curves_preserved':True,'main_page_mm':[740,740],'off_page_duplicate_kept_in_full_review_only':True},ensure_ascii=False,indent=2));print('USER CDR LINEWORK REPLACED',removed,'old paths',flush=True)
