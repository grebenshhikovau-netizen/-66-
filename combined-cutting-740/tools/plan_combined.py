"""Physically merge approved height fields into two country-defined cutting batches."""
import json,gzip,math,copy
from pathlib import Path
from collections import Counter
from shapely.geometry import shape,mapping,Polygon,Point,LineString,box
from shapely.affinity import translate
from shapely.ops import unary_union,nearest_points
from shapely import make_valid,set_precision
P=Path(__file__).resolve().parent.parent;CFG=json.load(open(P/'data/batch-countries.json'));SRC={k:json.load(gzip.open(P/f'data/source/{k}-approved-plan.json.gz','rt'))for k in ['RU','EU','AF']};WEST=set(CFG['west']);E=SRC['EU'];AFDX,AFDY=CFG['africa_translation_mm'];EMPTY=Polygon()
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty and g.area>1e-8 else[]
 return[p for q in getattr(g,'geoms',[])for p in ps(q)]
def ls(g):
 if g.geom_type in ['LineString','LinearRing']:return[LineString(g)]if g.length>1e-8 else[]
 return[p for q in getattr(g,'geoms',[])for p in ls(q)]
def valid(g):return set_precision(unary_union(ps(make_valid(g))),.001)
def mv(g,k):return translate(shape(g),AFDX,AFDY)if k=='AF'else shape(g)
def polygon_shell(g):return unary_union([Polygon(p.exterior)for p in ps(g)])
PARTITION=json.load(open(P/'data/source/batch-partition-masks.json'));SM=shape(PARTITION['scandinavia_mask']);WM=shape(PARTITION['west_mask']);RUEN=polygon_shell(shape(SRC['RU']['layers'][0])).union(shape(SRC['RU']['water_base_union']))
# The approved files use the same millimetre scale. Africa needs only one rigid translation.
REG={};NAMES={};BASE={};UPPER={}
for key,D in SRC.items():
 for code,g in D['regions'].items():REG[code]=mv(g,key);NAMES[code]=D['region_names'][code]
 for name,g in D['base_water'].items():BASE.setdefault(name,[]).append(mv(g,key))
 for name,g in D['upper_water'].items():UPPER.setdefault(name,[]).append(mv(g,key))
PYRAMID=mv(SRC['AF']['pyramid_block'],'AF');BASE={k:valid(unary_union(v))for k,v in BASE.items()};UPPER={k:valid(unary_union(v))for k,v in UPPER.items()}
# The Egyptian pyramid and all of its supports remain solid, as approved.
for name in list(BASE):
 if name in SRC['AF']['base_water']:BASE[name]=valid(BASE[name].difference(PYRAMID));UPPER[name]=valid(UPPER[name].difference(PYRAMID))
BB=valid(unary_union(list(BASE.values())));UB=valid(unary_union(list(UPPER.values())))

def repair(g,tier,report):
 g=valid(g)
 for iteration in range(4):
  out=[];changed=False
  for p in ps(g):
   rings=[p.exterior,*p.interiors];owners={}
   for ri,r in enumerate(rings):
    for pt in list(r.coords)[:-1]:owners.setdefault(pt,[]).append(ri)
   contacts={pt:ii for pt,ii in owners.items()if len(ii)>1}
   if not contacts:out.append(p);continue
   holes={i for ii in contacts.values()for i in ii if i>0};void=unary_union([Polygon(r).buffer(.035,quad_segs=6)if i in holes else Polygon(r)for i,r in enumerate(rings)if i>0]);new=valid(Polygon(p.exterior).difference(void));changed=True;out.extend(ps(new));report.append({'tier':tier,'kind':'ring contact','clearance_mm':.035,'removed_area_mm2':p.difference(new).area})
  g=valid(unary_union(out))
  if not changed:break
 counts=Counter(pt for p in ps(g)for r in [p.exterior,*p.interiors]for pt in list(r.coords)[:-1]);touch=[Point(xy)for xy,n in counts.items()if n>1]
 if touch:
  clear=unary_union([q.buffer(.07,quad_segs=6)for q in touch]);report.append({'tier':tier,'kind':'point contact','count':len(touch),'clearance_mm':.07,'removed_area_mm2':g.intersection(clear).area});g=valid(g.difference(clear))
 return valid(g.simplify(.015,preserve_topology=True))

def stock_split(part,upper,regions,tier,records):
 pending=[part];out=[];maxspan=CFG['max_part_extent_mm']
 while pending:
  g=pending.pop();x0,y0,x1,y1=g.bounds
  if max(x1-x0,y1-y0)<=maxspan:out.append(g);continue
  candidates=[]
  def consider(mask,kind):
   a=valid(g.intersection(mask));b=valid(g.difference(mask));pp=ps(a)+ps(b)
   if a.area<500 or b.area<500 or any(p.area<30 for p in pp):return
   if max(max(p.bounds[2]-p.bounds[0],p.bounds[3]-p.bounds[1])for p in pp)>=max(x1-x0,y1-y0)-.1:return
   seam=a.boundary.intersection(b.boundary.buffer(.002));visible=seam.difference(upper.buffer(-.3)).length;score=visible*10+seam.length*.08+len(pp)*18;candidates.append((score,pp,seam,kind,visible))
  if x1-x0>maxspan:
   lo=x1-maxspan+2;hi=x0+maxspan-2
   for k in range(15):
    xx=lo+(hi-lo)*k/14;consider(box(x0-5,y0-5,xx,y1+5),f'vertical {xx:.2f}')
  if y1-y0>maxspan:
   lo=y1-maxspan+2;hi=y0+maxspan-2
   for k in range(15):
    yy=lo+(hi-lo)*k/14;consider(box(x0-5,y0-5,x1+5,yy),f'horizontal {yy:.2f}')
  for delta in [-.8,0,.8]:consider(RUEN.buffer(delta,quad_segs=6),f'Russian boundary offset {delta}')
  mid=(x0+x1)/2;western=unary_union([r for r in regions.values()if r.centroid.x<mid]);consider(polygon_shell(western).buffer(.5 if tier==1 else 0), 'country group boundary')
  assert candidates,('oversized part could not be divided',tier,g.bounds)
  _,pp,seam,kind,visible=min(candidates,key=lambda v:v[0]);records.append({'tier':tier,'kind':kind,'seam':mapping(seam),'visible_seam_mm':visible,'total_seam_mm':seam.length});pending.extend(pp)
 return out

BATCHES=[('01-Россия-Азия','Россия + Азия','EAST',4),('02-Африка-Европа-Ближний-Восток','Африка + Европа + Ближний Восток','WEST',6)]
for folder,title,side,nlevels in BATCHES:
 O=P/folder;(O/'data/source').mkdir(parents=True,exist_ok=True);removed=[];repairs=[];stock=[];joining=[];raw=[];L=[];families=['RU','EU']if side=='EAST'else['AF','EU'];regions={c:r for c,r in REG.items()if(c in SRC['RU']['regions']and side=='EAST')or(c in SRC['AF']['regions']and side=='WEST')or(c in E['regions']and((c in WEST)==(side=='WEST')))}
 def mask_eu(g):return valid(g.difference(WM))if side=='EAST'else valid(g.intersection(WM).difference(RUEN))
 for i in range(nlevels):
  inputs=[]
  for family in families:
   D=SRC[family]
   if i>=len(D['layers']):continue
   g=mv(D['layers'][i],family);g=mask_eu(g)if family=='EU'else g;inputs.append(g)
  before=valid(unary_union(inputs));raw.append(before);g=before
  if len(inputs)>1 and not any(q.is_empty for q in inputs):
   roi=inputs[0].buffer(.8).intersection(inputs[1].buffer(.8));joined=valid(g.buffer(.30,quad_segs=6).buffer(-.30,quad_segs=6).intersection(roi));addition=joined.difference(g);g=valid(g.union(addition));joining.append({'tier':i+1,'between':families,'added_area_mm2':addition.area})
  if side=='WEST'and i==0:
   # Join the real Sinai land connection, compensating only source-file registration rounding.
   af=mv(SRC['AF']['layers'][0],'AF');isr=REG['ISR'].intersection(mask_eu(shape(E['layers'][0])));a,b=nearest_points(af,isr);roi=a.buffer(8).union(b.buffer(8));j=g.buffer(1.0,quad_segs=8).buffer(-1.0,quad_segs=8).intersection(roi);add=j.difference(g);g=valid(g.union(add));joining.append({'tier':1,'between':['AF','EU-Sinai'],'africa_translation_mm':[AFDX,AFDY],'initial_gap_mm':af.distance(isr),'added_area_mm2':add.area})
  water=BB if i==0 else UB;g=repair(g.difference(water),i+1,repairs);minimum=CFG['minimum_base_piece_mm2']if i==0 else CFG['minimum_upper_piece_mm2'];keep=[]
  for part in ps(g):
   if part.area<minimum:removed.append({'tier':i+1,'area_mm2':part.area,'geom':mapping(part)});continue
   keep.append(part)
  L.append(valid(unary_union(keep)))
 print('LAYERS',side,[len(ps(g))for g in L],flush=True)
 # Keep the specifically approved exposed painting separations, dissolving other old seams.
 pieces=[];paintseams=[]
 for i,layer in enumerate(L):
  domains=[];rest=layer
  if side=='WEST':
   cut=valid(rest.intersection(SM));domains.append(('Скандинавия — отдельный блок',cut));rest=valid(rest.difference(cut))
  if side=='WEST'and i==1:
   mask=shape(next(q['geom']for q in E['pieces']if q['id']=='L02_P007'));cut=valid(rest.intersection(polygon_shell(mask).buffer(.005)));domains.append(('Венгрия-Румыния-Сербия',cut));rest=valid(rest.difference(cut))
  if side=='EAST'and i==2:
   for name,sourceid in [('Туркмения','L03_P009'),('Лаос-Камбоджа','L03_P014')]:
    mask=polygon_shell(shape(next(q['geom']for q in E['pieces']if q['id']==sourceid))).buffer(.005);cut=valid(rest.intersection(mask));domains.append((name,cut));rest=valid(rest.difference(cut))
  domains.append(('Общий массив',rest));out=[]
  for group,g in domains:
   for part in ps(g):
    for q in stock_split(part,L[i+1]if i+1<len(L)else EMPTY,regions,i+1,stock):
     if q.area<CFG['minimum_upper_piece_mm2']and i:removed.append({'tier':i+1,'area_mm2':q.area,'reason':'paint seam numerical fragment','geom':mapping(q)});continue
     out.append((group,q))
  for j,(group,g)in enumerate(sorted(out,key=lambda q:-q[1].area),1):
   pieces.append({'id':f'L{i+1:02d}_P{j:03d}','tier':i+1,'geom':mapping(g),'visible':mapping(valid(g.difference(L[i+1])))if i+1<len(L)else mapping(g),'regions':[c for c,r in regions.items()if r.intersection(g).area>.4],'paint':{},'engraving':mapping(EMPTY),'area_mm2':g.area,'paint_group':group,'block':'SCAND'if group.startswith('Скандинавия')else'MAIN'})
 # Source annotations remain geographic; later placement retains them where the new slots allow.
 labels=[];markers=[]
 for family in families:
  SD=SRC[family]
  for kind,dest in [('labels',labels),('city_markers',markers)]:
   for old in SD[kind]:
    c=old.get('region');include=family!='EU'or((c in WEST)==(side=='WEST'))
    if not include:continue
    a=copy.deepcopy(old);a['id']=family+'_'+a['id'];a['source_family']=family;a['source_piece']=a['piece'];a['piece']=None
    if family=='AF':
     for key in ['geometry','bbox','leader','geom']:
      if a.get(key):a[key]=mapping(mv(a[key],family))
     for key in ['center_mm','point_mm','geographic_point_mm']:
      if key in a:a[key]=[a[key][0]+AFDX,a[key][1]+AFDY]
     if 'matrix'in a:a['matrix'][4]+=AFDX;a['matrix'][5]+=AFDY
    dest.append(a)
 networks=[mv(SRC[f]['political_network'],f)for f in families];network=unary_union(networks);terraces=[mapping(mv(g,'AF'))for g in SRC['AF']['pyramid_terraces']]if side=='WEST'else[]
 summary=[{'tier':i+1,'pieces':sum(p['tier']==i+1 for p in pieces),'raw_vertices':sum(len(r.coords)for p in ps(raw[i])for r in [p.exterior,*p.interiors]),'smoothed_vertices':sum(len(r.coords)for p in ps(g)for r in [p.exterior,*p.interiors]),'raw_perimeter_mm':raw[i].length,'smoothed_perimeter_mm':g.length}for i,g in enumerate(L)]
 D={'title':title,'batch':side,'scandinavia_separate':side=='WEST','layers':[mapping(g)for g in L],'visible':[mapping(valid(g.difference(L[i+1])))if i+1<len(L)else mapping(g)for i,g in enumerate(L)],'pieces':pieces,'regions':{c:mapping(g)for c,g in regions.items()},'region_names':{c:NAMES[c]for c in regions},'political_network':mapping(network),'network_smoothing_version':'approved shared country and regional networks','base_water':{k:mapping(g)for k,g in BASE.items()if g.intersects(raw[0])},'upper_water':{k:mapping(g)for k,g in UPPER.items()if g.intersects(raw[0])},'water_base_union':mapping(valid(BB.intersection(raw[0].buffer(1)))),'water_upper_union':mapping(valid(UB.intersection(raw[0].buffer(1)))),'pyramid_block':mapping(PYRAMID)if side=='WEST'else mapping(EMPTY),'pyramid_terraces':terraces,'colors':{'NATURAL':[.72,.59,.40]},'summary':summary,'ply_mm':3,'levels_mm':[3*(i+1)for i in range(nlevels)],'parameters':CFG,'stock_seams':stock,'removed_micro_parts':removed,'topology_repairs':repairs,'source_labels':labels,'source_markers':markers,'labels':[],'city_markers':[],'label_notes':[],'joining':joining,'source_part_count':sum(len(SRC[f]['pieces'])for f in families)}
 D['water_base_union']=mapping(valid(unary_union([shape(g)for g in D['base_water'].values()])));D['water_upper_union']=mapping(valid(unary_union([shape(g)for g in D['upper_water'].values()])))
 (O/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));(O/'data/water-reference.json').write_text(json.dumps([{'name':'Оргстекло под водными прорезями — справочно','geom':mapping(shape(D['water_base_union']).intersection(polygon_shell(L[0].buffer(1.2))))}],ensure_ascii=False));(O/'data/source/texture-reference.json').write_text('{"type":"GeometryCollection","geometries":[]}');(O/'Проверка-планирования.json').write_text(json.dumps({'batch':side,'title':title,'parts':len(pieces),'layers':summary,'joins':joining,'stock_seams':stock,'removed':removed,'repairs':repairs},ensure_ascii=False,indent=2));print('BATCH READY',title,len(pieces),[q['pieces']for q in summary],'STOCK SEAMS',len(stock),flush=True)
