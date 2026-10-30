"""Keep approved editable labels where possible, moving whole words off new river slots."""
import json,math,copy
from pathlib import Path
import numpy as np
from shapely.geometry import shape,mapping,Polygon,Point,LineString,box
from shapely.affinity import translate,scale
from shapely.ops import unary_union,nearest_points,polylabel
from shapely.prepared import prep
from font_geometry import word_geom
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));pieces=D['pieces'];regions={c:shape(g)for c,g in D['regions'].items()};geom={p['id']:shape(p['geom'])for p in pieces};visible={p['id']:shape(p['visible'])for p in pieces};safe={p['id']:visible[p['id']].buffer(-.24).difference(shape(p['structural_engraving']).buffer(.28))for p in pieces};mark_safe={p['id']:visible[p['id']].buffer(-.32).difference(shape(p['structural_engraving']).buffer(.27))for p in pieces};RU=unary_union([g for c,g in regions.items()if c.startswith('RU_')or c.startswith('UA_')]);labels=[];markers=[];notes=[]
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty and g.area>1e-8 else[]
 return[p for q in getattr(g,'geoms',[])for p in ps(q)]
def domain(a,strict=False):
 if a.get('source_family')=='RU'and(a.get('kind')!='region'or a.get('callout')or strict):return RU
 c=a.get('province')or a.get('region');g=shape(D['china_province_regions'][c])if c in D.get('china_province_regions',{})else regions.get(c,unary_union(list(regions.values())))
 if a.get('callout')and a.get('kind')=='country':return g.buffer(12)
 if a.get('caption_callout'):return g.buffer(4)
 return g
# Add only major cities requested for China, alongside the seven approved Chinese cities.
if D['batch']=='EAST':
 proj=json.load(open(P.parent/'data/source/world-projection.json'));C=proj['projection'];M=proj['mm_per_unit'];MC=math.log(math.tan(math.pi/4+math.radians(C['latmin'])/2))
 def xy(lon,lat):return M*(C['source_xmin']+(lon-C['lonmin'])*C['kx_per_degree']),M*(C['source_ymax']-(math.log(math.tan(math.pi/4+math.radians(lat)/2))-MC)*C['ky_per_mercator'])-1000
 for i,(name,lon,lat)in enumerate([('Чунцин',106.5516,29.5630),('Ухань',114.3054,30.5931),('Харбин',126.6424,45.7560),('Куньмин',102.7123,25.0406),('Шэньчжэнь',114.0579,22.5431)]):
  pt=xy(lon,lat)
  if any(q['id']==f'CN_NEW_CITY_{i+1:02d}'for q in D['source_markers']):continue
  D['source_markers'].append({'id':f'CN_NEW_CITY_{i+1:02d}','name':name,'lon':lon,'lat':lat,'region':'CHN','source_family':'EU','point_mm':list(pt),'geographic_point_mm':list(pt),'new':True})
for source in D['source_markers']:
 a=copy.deepcopy(source);point=Point(a['geographic_point_mm']);old=Point(a['point_mm']);allow=domain(a,True);options=[]
 for p in pieces:
  if D['batch']=='WEST'and ((a.get('region')in ['NOR','SWE','FIN'])!=(p.get('block')=='SCAND')):continue
  s=mark_safe[p['id']]
  if s.is_empty or s.distance(point)>5:continue
  s=s.intersection(allow)
  if s.is_empty:continue
  q=old if s.covers(old)else nearest_points(point,s)[1];options.append((q.distance(point),p,q))
 assert options,(a['name'],'no exposed bank for city');dist,p,q=min(options,key=lambda v:v[0]);assert dist<5,(a['name'],dist);a.update({'piece':p['id'],'point_mm':[q.x,q.y],'geom':mapping(q.buffer(.20,quad_segs=8)),'bank_shift_mm':dist});markers.append(a)
occupied=unary_union([shape(a['geom']).buffer(.22)for a in markers]);marker_map={a['id']:a for a in markers}

def template(id,text,kind,target,preferred,region,province=None):
 words=text.split();lines=[];cur=''
 for w in words:
  if cur and len(cur)+len(w)+1>17:lines.append(cur);cur=w
  else:cur=(cur+' '+w).strip()
 if cur:lines.append(cur)
 parts=[];spec=[]
 for i,line in enumerate(lines):
  g=word_geom(line);x0,y0,x1,y1=g.bounds;xx=-(x0+x1)/2;yy=i*1.24;parts.append(translate(g,xx,yy));spec.append({'text':line,'x_em':xx,'y_em':yy})
 raw=unary_union(parts);cx,cy=raw.centroid.x,raw.centroid.y;gx,gy=preferred;g=translate(scale(raw,xfact=target,yfact=target,origin=(cx,cy)),gx-cx,gy-cy);b=translate(scale(box(*raw.bounds),xfact=target,yfact=target,origin=(cx,cy)),gx-cx,gy-cy)
 return {'id':id,'text':text,'kind':kind,'region':region,'province':province,'font_family':'Open Sans Light','font_size_mm':target,'matrix':[1,0,0,1,gx-target*cx,gy-target*cy],'lines':spec,'color':'#ff0000','geometry':mapping(g),'bbox':mapping(b),'center_mm':[gx,gy],'new':True}

def place(a):
 global occupied
 a=copy.deepcopy(a);preferred=Point(a['center_mm']);bbox=shape(a['bbox']);outline=shape(a['geometry']);marker=None
 if a['kind']=='city':
  mid=a['id'][:-5]if a['id'].endswith('_TEXT')else None;marker=marker_map.get(mid)
  if marker is not None:preferred=Point(marker['point_mm'])
 allow=domain(a);options=[]
 for p in pieces:
  if D['batch']=='WEST'and ((a.get('region')in ['NOR','SWE','FIN'])!=(p.get('block')=='SCAND')):continue
  if marker is not None and not a.get('caption_other_surface')and p['id']!=marker['piece']:continue
  s=safe[p['id']].intersection(allow)
  if s.area<1:continue
  if a['kind']=='city'and s.distance(preferred)>22:continue
  options.append((p,s,prep(s)))
 # Previously approved regional callouts may sit on the neighbouring open face.
 if not options and a.get('source_family')=='RU'and a['kind']=='region':
  for p in pieces:
   s=safe[p['id']].intersection(RU).intersection(preferred.buffer(18))
   if s.area>1:options.append((p,s,prep(s)))
 oldcx,oldcy=a['center_mm'];font=a['font_size_mm'];minimum=1.1 if a['kind']=='city'else 1.0;factors=[1.0]+[float(f)for f in np.arange(.95,minimum/font-.001,-.05)if f>0];found=None
 for f in factors:
  b=scale(bbox,xfact=f,yfact=f,origin=(oldcx,oldcy));w=b.bounds[2]-b.bounds[0];h=b.bounds[3]-b.bounds[1];centers=[(oldcx,oldcy)]
  if a['kind']=='city':
   x,y=preferred.x,preferred.y;centers +=[(x+w/2+.8,y),(x-w/2-.8,y),(x,y-h/2-.9),(x,y+h/2+.9)];offset=[(x+float(dx),y+float(dy))for dx in np.arange(-18,18.1,1.4)for dy in np.arange(-15,15.1,1.4)];offset.sort(key=lambda v:(v[0]-x)**2+(v[1]-y)**2);centers+=offset
   for cp,cs,cpr in options:
    local=cs.intersection(preferred.buffer(21))
    for part in sorted(ps(local),key=lambda g:-g.area)[:8]:
     pp=polylabel(part,tolerance=.12);centers.append((pp.x,pp.y));pp=part.representative_point();centers.append((pp.x,pp.y))
  else:
   for p,s,pr in options:
    for g in sorted(ps(s),key=lambda g:-g.area)[:4]:
     q=g.representative_point();r=polylabel(g,tolerance=.5);centers +=[(q.x,q.y),(r.x,r.y)]
    x0,y0,x1,y1=s.bounds;step=2.1 if a['kind']in ['region','province']else 3.0;centers +=[(float(x),float(y))for x in np.arange(x0,x1+.1,step)for y in np.arange(y0,y1+.1,step)]
   centers.sort(key=lambda v:(v[0]-preferred.x)**2+(v[1]-preferred.y)**2)
  for x,y in centers:
   candidate=translate(b,x-oldcx,y-oldcy);reserve=candidate.buffer(.18,join_style=2)
   if occupied.intersects(reserve):continue
   for p,s,pr in options:
    if not pr.covers(candidate):continue
    if marker is not None:
     stem=LineString([Point(marker['point_mm']),nearest_points(Point(marker['point_mm']),candidate)[1]])
     # A nearby caption may omit its leader when the straight stem crosses a river slot.
    found=(f,x,y,p,candidate,reserve);break
   if found:break
  if found:break
 if found is None and a['kind']=='city'and marker is not None and not a.get('caption_other_surface'):
  a['caption_other_surface']=True;return place(a)
 if found is None and a['kind']=='city'and a.get('caption_other_surface')and not a.get('caption_callout'):
  a['caption_callout']=True;return place(a)
 if found is None and a['kind']=='country'and not a.get('retry'):
  a['callout']=True;a['retry']=True;return place(a)
 if found is None and a['kind']=='region'and a.get('source_family')=='RU'and not a.get('retry'):
  a['callout']=True;a['retry']=True;return place(a)
 assert found,(a['id'],a['text'],'complete label does not fit')
 f,x,y,p,b,reserve=found;mat=a['matrix'][:];mat[4]=x+f*(mat[4]-oldcx);mat[5]=y+f*(mat[5]-oldcy);a.update({'piece':p['id'],'tier':p['tier'],'font_size_mm':font*f,'matrix':mat,'center_mm':[x,y],'bbox':mapping(b),'geometry':mapping(translate(scale(outline,xfact=f,yfact=f,origin=(oldcx,oldcy)),x-oldcx,y-oldcy))});a.pop('leader',None)
 if marker is not None:
  q=Point(marker['point_mm']);near=nearest_points(q,b)[1]
  if q.distance(near)>.65 and visible[p['id']].covers(LineString([q,near])):a['leader']=mapping(LineString([q,near]))
 elif a.get('callout'):
  q=nearest_points(regions.get(a.get('region'),allow),Point(x,y))[0];a['leader']=mapping(LineString([q,nearest_points(q,b)[1]]))
 labels.append(a);occupied=occupied.union(reserve)
 print('LABEL',a['id'],a['text'],p['id'],round(font*f,2),flush=True)
 if f<.999 or math.dist([oldcx,oldcy],[x,y])>.05:notes.append({'id':a['id'],'text':a['text'],'font_factor':f,'movement_mm':math.dist([oldcx,oldcy],[x,y])})

for a in sorted(D['source_labels'],key=lambda a:{'country':0,'city':1,'region':2}.get(a['kind'],3)):place(a)
for m in markers:
 if m.get('new'):place(template(m['id']+'_TEXT',m['name'],'city',1.6,m['point_mm'],'CHN'))
if D['batch']=='EAST':
 province_names={'CN_XJ':'СИНЬЦЗЯН','CN_XZ':'ТИБЕТ','CN_NM':'ВНУТРЕННЯЯ МОНГОЛИЯ','CN_QH':'ЦИНХАЙ','CN_GS':'ГАНЬСУ','CN_HL':'ХЭЙЛУНЦЗЯН','CN_SC':'СЫЧУАНЬ','CN_YN':'ЮНЬНАНЬ','CN_GX':'ГУАНСИ','CN_GD':'ГУАНДУН','CN_HB':'ХУБЭЙ','CN_HN':'ХУНАНЬ','CN_HA':'ХЭНАНЬ','CN_SN':'ШЭНЬСИ','CN_SD':'ШАНЬДУН','CN_JL':'ГИРИН','CN_LN':'ЛЯОНИН','CN_JS':'ЦЗЯНСУ','CN_ZJ':'ЧЖЭЦЗЯН','CN_FJ':'ФУЦЗЯНЬ'}
 for c,name in province_names.items():
  region=shape(D['china_province_regions'][c]);q=region.representative_point();place(template('CN_PROVINCE_'+c,name,'province',2.0,[q.x,q.y],'CHN',c))
 D['china_province_names']=province_names
D['labels']=labels;D['city_markers']=markers;D['annotation_changes']=notes;(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));(P/'Проверка-размещения-подписей.json').write_text(json.dumps({'labels':len(labels),'cities':len(markers),'changed_labels':notes,'source_labels_retained':len(D['source_labels'])},ensure_ascii=False,indent=2));print('ANNOTATIONS READY',len(labels),len(markers),flush=True)
