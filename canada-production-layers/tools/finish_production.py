import json,csv,math
from pathlib import Path
from collections import defaultdict
from shapely.geometry import shape,Polygon,box,mapping
from shapely.ops import unary_union,linemerge
from lxml import etree as E
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'production-plan.json'));rows=json.load(open(P/'extracted.json'))
S='http://www.w3.org/2000/svg';INK='#3e2b20'
def polys(g):
 if g.geom_type=='Polygon':return [g]if not g.is_empty and g.area>1e-8 else []
 return [p for q in getattr(g,'geoms',[]) for p in polys(q)]
X0,Y0,X1,Y1=shape(D['layers'][0]).bounds

def root():return E.Element('svg',nsmap={None:S},width=f'{X1-X0}mm',height=f'{Y1-Y0}mm',viewBox=f'{X0} {Y0} {X1-X0} {Y1-Y0}')
def path(r,g,id,fill,stroke=None,width=.15):
 from shapely.geometry.polygon import orient
 d=' '.join('M'+' L'.join(f'{x:.6f},{y:.6f}'for x,y in list(ring.coords)[:-1])+' Z'for p in polys(g)for ring in [orient(p,-1).exterior,*orient(p,-1).interiors])
 if not d:return
 e=E.SubElement(r,'path',d=d,id=id,fill=fill,attrib={'fill-rule':'nonzero'})
 if stroke:e.set('stroke',stroke);e.set('stroke-width',str(width))
 return e

def save(r,name):E.ElementTree(r).write(str(P/name),encoding='UTF-8',xml_declaration=True)
def rgb(c):return '#'+''.join(f'{round((v*12.92 if v<.0031308 else 1.055*v**(1/2.4)-.055)*255):02x}'for v in c)
used=sorted(set(c for p in D['pieces']for c in p['paint'] if c!='NATURAL'));codes={c:f'C{i+1:02d}'for i,c in enumerate(used)};codes['NATURAL']='NATURAL'
report={'total_pieces':len(D['pieces']),'layers':D['summary'],'checks':{},'annotations_moved':D['annotation_moves'],'annotations_requiring_review':D['annotations_requiring_review'],'excluded_misplaced_objects':D['excluded_misplaced_objects'],'point_contact_repairs':D['point_contact_repairs'],'paint_overlap_mm':2,'source_scale_width_mm':X1-X0,'source_scale_height_mm':Y1-Y0,'kerf_compensated':False,'sheet_nesting':False}
for i in range(1,4):
 pp=[p for p in D['pieces']if p['tier']==i];eng=root()
 for p in pp:
  g=shape(p['engraving']);path(eng,g,p['id']+'_INK','#000');one=root();path(one,g,p['id']+'_INK','#000');save(one,str(Path('Детали')/p['id']/'Гравировка.svg'));assert g.difference(shape(p['visible'])).area<.03,(p['id'],'engraving outside visible shelf')
 save(eng,f'Слой-{i:02d}-гравировка.svg')
 gs=[shape(p['geom'])for p in pp];layer=shape(D['layers'][i-1]);merged=unary_union(gs);area=sum(g.area for g in gs);lines=unary_union([g.boundary for g in gs]);paths=[]
 def linear(g):
  if g.geom_type in ['LineString','LinearRing']:return [g]
  return [p for q in getattr(g,'geoms',[])for p in linear(q)]
 for q in linear(lines):paths.append('M'+' L'.join(f'{x:.6f},{y:.6f}'for x,y in q.coords))
 r=root();E.SubElement(r,'path',id=f'LASER_L{i:02d}',d=' '.join(paths),fill='none',stroke='#000',attrib={'stroke-width':'0.1'});save(r,f'Слой-{i:02d}-лазер-без-повторов.svg')
 unionerror=merged.symmetric_difference(layer).area;overlap=area-merged.area;assert unionerror<.1 and abs(overlap)<.01,(i,unionerror,overlap)
 badpaint=0
 for p in pp:
  for c,m in p['paint'].items():
   extra=shape(m['with_overlap']).difference(shape(m['visible']));badpaint+=extra.difference(shape(D['layers'][i])if i<3 else Polygon()).area
 assert badpaint<.001,(i,badpaint)
 report['checks'][f'layer_{i}']={'reconstruction_error_mm2':unionerror,'duplicate_area_mm2':overlap,'paint_outside_upper_cover_mm2':badpaint,'valid_closed_polygons':all(g.is_valid for g in gs)}
 # Visible colours and black lettering: precise 2D production preview.
 r=root()
 for p in pp:
  path(r,shape(p['geom']),p['id'],'#d9bf94',INK,.12)
  for c,v in p['paint'].items():path(r,shape(v['visible']),p['id']+'_'+c,rgb(D['colors'][c]))
  inkg=shape(p['engraving']);dark=unary_union([shape(v['visible'])for k,v in p['paint'].items()if sum(a*b for a,b in zip(D['colors'][k],[.2126,.7152,.0722]))<.1]);path(r,inkg.difference(dark),p['id']+'_INK',INK);path(r,inkg.intersection(dark),p['id']+'_LIGHT_INK','#dec79f')
 save(r,f'Слой-{i:02d}-видимая-покраска.svg')
# Whole map top-view vector with contour edges between plies.
r=root()
for p in D['pieces']:
 path(r,shape(p['geom']),p['id'],'#dec8a3',INK,.16)
 for c,v in p['paint'].items():path(r,shape(v['visible']),p['id']+'_'+c,rgb(D['colors'][c]))
 inkg=shape(p['engraving']);dark=unary_union([shape(v['visible'])for k,v in p['paint'].items()if sum(a*b for a,b in zip(D['colors'][k],[.2126,.7152,.0722]))<.1]);path(r,inkg.difference(dark),p['id']+'_INK',INK);path(r,inkg.intersection(dark),p['id']+'_LIGHT_INK','#dec79f')
save(r,'Карта-в-сборе-вектор.svg')
# Protect exposed Arizona where the base crosses to Mexico.
arizona=unary_union([shape(x['geom'])for x in rows if x['kind']=='wood' and x['region']=='REG_23_Arizona'])
mexico=unary_union([shape(x['geom'])for x in rows if x['kind']=='wood' and x['region']=='REG_08_Mexico'])
mask=arizona.intersection(mexico.buffer(8));r=root();path(r,mask,'PROTECT_ARIZONA','#000');save(r,'Маска-Аризона-Мексика.svg')
# The source uses two orange staining intensities inside Canada.
labrador=unary_union([shape(x['geom'])for x in rows if x['kind']=='wood' and x['region']=='REG_13_Labrador']);quebec=unary_union([shape(x['geom'])for x in rows if x['kind']=='wood' and x['region']=='REG_04_Quebec']);r=root();path(r,labrador.intersection(quebec.buffer(8)),'PROTECT_LABRADOR','#000');save(r,'Маска-Лабрадор-Квебек.svg')
# Compact, readable production tables. Per-part mask names use C01 etc.
for p in D['pieces']:
 folder=P/'Детали'/p['id']
 for old in folder.glob('Покраска-*.svg'):old.unlink()
 for coat,v in p['paint'].items():
  r=root();path(r,shape(v['with_overlap']),p['id']+'_'+codes[coat],'#000');save(r,str(Path('Детали')/p['id']/(f'Покраска-{codes[coat]}.svg'if v['paint']else'Без-покраски-NATURAL.svg')))
with open(P/'Палитра.csv','w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f);w.writerow(['Код','sRGB ориентир','Действие','Исходное покрытие'])
 for c in ['NATURAL']+used:w.writerow([codes[c],rgb(D['colors'][c]),'Оставить фанеру'if c=='NATURAL'else'Окрасить',c])
with open(P/'Детали-и-покрытия.csv','w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f);w.writerow(['Деталь','Слой','Низ Z мм','Верх Z мм','Площадь мм²','Покрытия','Политические части'])
 for p in D['pieces']:w.writerow([p['id'],p['tier'],(p['tier']-1)*3,p['tier']*3,round(p['area_mm2'],3),', '.join(codes[c]for c in p['paint']),'; '.join(p['regions'])])
# Exact label clipping was replaced by complete per-surface annotations.
assert not D['annotations_requiring_review'],D['annotations_requiring_review']
report['checks']['all_annotations_on_single_exposed_surface']=True
(P/'Проверка-производственных-слоёв.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('CHECKS OK',report['total_pieces'],report['checks'],flush=True)
