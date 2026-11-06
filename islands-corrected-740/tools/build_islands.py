"""Named islands, readable wooden focal islands, minor islands engraved on acrylic.
Every island is selected by geographic point, never by a mutable polygon index.
"""
import json,gzip,math
from pathlib import Path
from collections import Counter
import numpy as np
from shapely.geometry import shape,mapping,Point,Polygon,LineString,box
from shapely.ops import unary_union,transform,nearest_points,polylabel
from shapely.affinity import scale,translate,affine_transform
import common as G
P=G.P;R=P.parent;Q=G.PROJ
NE=json.load(gzip.open(P/'data/source/natural-earth-10m-countries.geojson.gz','rt'))['features'];NC={f['properties']['ADM0_A3']:f for f in NE}
T=json.load(open(P/'data/world-registration.json'));S=T['russia-asia']['affine'][0];TX,TY=T['russia-asia']['affine'][4:];INV=[1/S,0,0,1/S,-TX/S,-TY/S]
def dump(path,x):path.write_text(json.dumps(x,ensure_ascii=False))
def projected(poly,anchor_lon=None):
 # Unwrap individual dateline components around the associated island group.
 lon=poly.centroid.x;shift=0 if anchor_lon is None else 360*round((anchor_lon-lon)/360)
 return transform(lambda x,y,z=None:G.project(np.asarray(x)+shift,y),poly)
def merc_point(lon,lat,display_lon=None):return Point(*G.project(lon if display_lon is None else display_lon,lat))
def select(code,lon,lat,source='ne'):
 data=G.C[code]['geom']if source=='master'else NC[code]['geometry'];parts=G.ps(shape(data))
 if source=='master':
  p=merc_point(lon,lat);chosen=min(parts,key=lambda g:g.distance(p));assert chosen.distance(p)<8,(code,lon,lat,chosen.distance(p));return chosen
 if code=='RUS'and lon>175 and 70<lat<73:
  wrapped=unary_union([projected(p,180)for p in parts if 70<p.centroid.y<73 and abs(p.centroid.x)>175]);pt=merc_point(lon,lat);return min(G.ps(wrapped),key=lambda q:q.distance(pt))
 pp=Point(lon,lat);chosen=min(parts,key=lambda g:g.distance(pp));assert chosen.distance(pp)<.35,(code,lon,lat,chosen.distance(pp));return projected(chosen,lon)

# Local cluster magnification keeps engraved neighbours visible beside a larger focal island.
F={}
def family(id,lon,lat,codes,posscale=1,radius=20,display_lon=None):
 F[id]={'id':id,'lon':lon if display_lon is None else display_lon,'lat':lat,'anchor':merc_point(lon,lat,display_lon),'codes':codes,'scale':posscale,'radius':radius,'dx':0.,'dy':0.}
family('maldives',73.51,4.18,['MDV'],1,65)
family('seychelles',55.46,-4.67,['SYC'],4,18)
family('mascarene',56.5,-20.7,['MUS','FRA'],2.2,17)
family('comoros',44.0,-12.1,['COM','FRA'],2.0,12)
family('fiji',178.1,-17.8,['FJI'],3,55)
family('samoa',-171.8,-13.8,['WSM','ASM'],3,20,display_lon=188.2)
family('tonga',-175.2,-21.2,['TON'],2.5,35,display_lon=184.8)
family('vanuatu',167,-15.4,['VUT'],2.3,35)
family('solomons',160,-9.5,['SLB'],2.4,50)
family('galapagos',-91,-.5,['ECU'],3,18)
family('canaries',-16,28.3,['ESP'],2.2,20)
family('azores',-27.9,38.5,['PRT'],1.6,35)
family('trinidad',-61.3,10.5,['TTO'],2.5,16)
family('zanzibar',39.3,-6.1,['TZA'],2,12)
def find_family(code,g):
 options=[]
 for f in F.values():
  if code not in f['codes']:continue
  p=projected(g,f['lon']);dist=p.centroid.distance(f['anchor'])
  if dist<f['radius']:options.append((dist,f))
 return min(options,key=lambda x:x[0])[1]if options else None
def fam_geom(g,f,shift=True):
 if f is None:return g
 g=scale(g,xfact=f['scale'],yfact=f['scale'],origin=f['anchor'])
 return translate(g,f['dx'],f['dy'])if shift else g

# Read actual approved wood rather than excluding an entire country by ISO code.
oldwood=[shape(t['base'])for t in T.values()]
oldroot=R/'world-final-parts-740'
for key in ['02-Greenland','03-Australia']:
 d=json.load(open(oldroot/key/'data/production-plan.json'));oldwood.append(affine_transform(shape(d['layers'][0]),T['russia-asia']['affine']))
OLD=unary_union(oldwood).simplify(.05)

rows=[]
def add(id,name,code,lon,lat,width=0,source='ne',family_id=None,caption=None,country=False,arctic=False,force=False):
 rows.append({'id':id,'name':name,'country':code,'lon':lon,'lat':lat,'width':width,'source':source,'family':family_id,'caption':caption or name,'country_caption':country,'arctic':arctic,'force':force})
for x in [
 ('ellesmere','Элсмир',-79.5,80.0),('baffin','Баффинова Земля',-72,67.5),('victoria','Виктория',-110,71.3),('axel-heiberg','Аксель-Хейберг',-90,79.8),('devon','Девон',-87,75.2),('banks','Банкс',-122,73),('melville','Мелвилл',-111,75.4),('prince-wales','Принца Уэльского',-99,72.6),('somerset','Сомерсет',-94,73.6),('prince-patrick','Принс-Патрик',-119.5,76.7),('bathurst','Батерст',-99,76),('southampton','Саутгемптон',-84.5,64),('bylot','Байлот',-79,73.3),('ellef-ringnes','Эллеф-Рингнес',-102,79),('amund-ringnes','Амунд-Рингнес',-96.5,78.6),('cornwallis','Корнуоллис',-95,75)]:
 add(x[0],x[1],'CAN',x[2],x[3],source='master',arctic=True,caption='БАФФИНОВА\nЗЕМЛЯ'if x[0]=='baffin'else'ЭЛСМИР'if x[0]=='ellesmere'else x[1].replace('Принца Уэльского','Принца\nУэльского'))
add('png','Папуа — Новая Гвинея','PNG',147,-8,source='master',caption='Папуа —\nНовая Гвинея',country=True)
add('new-britain','Новая Британия','PNG',151,-5.7,36,source='master',caption='Новая Британия')
add('nz-north','Северный остров','NZL',176,-38,source='master')
add('nz-south','Южный остров','NZL',170.5,-44,source='master',caption='Новая Зеландия',country=True)
add('cuba','Куба','CUB',-79.5,22,source='master',country=True,caption='КУБА')
add('hispaniola','Гаити / Эспаньола','DOM',-70.5,19,source='master',caption='Доминикана',country=True)
add('jamaica','Ямайка','JAM',-77.3,18.1,18,caption='Ямайка',country=True)
add('puerto-rico','Пуэрто-Рико','PRI',-66.5,18.2,17,caption='Пуэрто-Рико',country=True)
add('new-caledonia','Новая Каледония','NCL',165.3,-21.3,28,source='master')
add('falkland-east','Восточный Фолкленд','FLK',-58.8,-51.7,16,caption='Восточный\nФолкленд')
add('falkland-west','Западный Фолкленд','FLK',-60.2,-51.8,15,caption='Западный\nФолкленд')
add('maldives','Мальдивы','MDV',73.424,-.294,14,'ne','maldives',country=True,force=True)
add('seychelles','Сейшелы','SYC',55.46,-4.67,14,'ne','seychelles',country=True,force=True)
add('mauritius','Маврикий','MUS',57.55,-20.28,14,'ne','mascarene',country=True,force=True)
add('reunion','Реюньон','FRA',55.53,-21.11,14,'ne','mascarene',force=True)
add('malta','Мальта','MLT',14.44,35.9,14,country=True,force=True)
add('hawaii','Гавайи','USA',-155.6,19.6,16,force=True)
add('oahu','Оаху','USA',-158,21.47,14,force=True)
add('galapagos','Галапагосы','ECU',-91.1,-.5,14,'ne','galapagos',force=True)
add('easter','Остров Пасхи','CHL',-109.35,-27.12,14,caption='о. Пасхи',force=True)
add('tahiti','Таити','PYF',-149.43,-17.66,14,force=True)
add('bora-bora','Бора-Бора','PYF',-151.74,-16.5,12,force=True)
add('fiji','Фиджи','FJI',178,-17.8,17,'ne','fiji',country=True,force=True)
add('vanuatu','Вануату','VUT',166.9,-15.2,14,'ne','vanuatu',country=True,force=True)
add('solomons','Соломоновы острова','SLB',160,-9.6,18,'ne','solomons',caption='Соломоновы\nострова',country=True,force=True)
add('samoa','Самоа','WSM',-171.8,-13.9,15,'ne','samoa',country=True,force=True)
add('tonga','Тонга','TON',-175.18,-21.17,14,'ne','tonga',country=True,force=True)
add('trinidad','Тринидад и Тобаго','TTO',-61.3,10.45,16,'ne','trinidad',caption='Тринидад\nи Тобаго',country=True,force=True)
add('barbados','Барбадос','BRB',-59.56,13.16,12,country=True,force=True)
add('bahamas','Багамы','BHS',-77.4,25.03,17,country=True,force=True)
add('cape-verde','Кабо-Верде','CPV',-23.6,15.1,14,caption='Кабо-Верде',country=True,force=True)
add('sao-tome','Сан-Томе и Принсипи','STP',6.62,.22,14,caption='Сан-Томе\nи Принсипи',country=True,force=True)
add('comoros','Коморы','COM',43.34,-11.65,14,'ne','comoros',country=True,force=True)
add('mayotte','Майотта','FRA',45.16,-12.83,12,'ne','comoros',force=True)
add('zanzibar','Занзибар','TZA',39.3,-6.1,12,'ne','zanzibar',force=True)
add('socotra','Сокотра','YEM',53.9,12.5,18,force=False)
add('madeira','Мадейра','PRT',-16.97,32.75,16,force=False)
add('azores','Азорские острова','PRT',-25.5,37.77,18,'ne','azores',caption='Азоры',force=False)
add('canaries','Канарские острова','ESP',-16.6,28.3,16,'ne','canaries',caption='Канары',force=False)
add('svalbard','Шпицберген','NOR',15,78,24,force=False)

# The remaining large Russian Arctic islands belong in the named wooden set.
add('novaya-north','Новая Земля — Северный остров','RUS',58.725,75.126,80,caption='Новая Земля\nСеверный о.')
add('novaya-south','Новая Земля — Южный остров','RUS',53.417,71.981,35,caption='Новая Земля\nЮжный о.')
add('kotelny','Котельный','RUS',139.659,75.443,45)
add('new-siberia','Новая Сибирь','RUS',148.206,75.182,28)
add('komsomolets','Комсомолец','RUS',94.998,80.634,36)
add('october-revolution','Октябрьской Революции','RUS',97.002,79.476,39,caption='Октябрьской\nРеволюции')
add('bolshevik','Большевик','RUS',102.798,78.677,33)
add('franz-josef','Земля Франца-Иосифа','RUS',49.451,80.502,29,caption='Земля\nФранца-Иосифа')
add('wrangel','Остров Врангеля','RUS',179.8,71.2,28,caption='о. Врангеля')

overrides=json.load(open(P/'data/readability-scale-overrides.json'))if(P/'data/readability-scale-overrides.json').exists()else{}
for row in rows:row['width']*=overrides.get(row['id'],1)
included=[];existing=[];used=[]
for r in rows:
 original=select(r['country'],r['lon'],r['lat'],r['source'])
 if r['id']=='hispaniola':original=unary_union([original,shape(G.C['HTI']['geom'])])
 cover=OLD.intersection(original).area/original.area
 if cover>.70 and not r['force']:
  existing.append({k:v for k,v in r.items()if k not in ['geom']});continue
 assert all(original.symmetric_difference(g).area>.001 for g in used),(r['id'],'same island selected twice');used.append(original)
 f=F.get(r['family']);g=G.smooth(original,.22,.12,.00001)if original.area>20 else G.polygonal(original).simplify(.0005,preserve_topology=True)
 if f:
  # The source may have negative longitudes while the display cluster is unwrapped.
  period=360*Q['lon_to_x_mm'];dx=period*round((f['anchor'].x-g.centroid.x)/period);g=translate(g,dx,0)
  original=translate(original,dx,0)
 g=fam_geom(g,f,False);c=g.centroid;w=g.bounds[2]-g.bounds[0];factor=max(1,r['width']/w)if r['width']else 1
 g=scale(g,xfact=factor,yfact=factor,origin=c);g=G.smooth(g,.24,.12,.5)
 # Find the nearest clear sea position for an enlarged silhouette.
 prior=unary_union([shape(q['geom'])for q in included]);obstacles=unary_union([OLD.buffer(.5),prior.buffer(1.0)]);best=(0,0,0,g)if r['source']=='master'and factor==1 and f is None else None
 limit=30 if factor>1.01 else 12
 for dy in range(-limit,limit+1,2):
  for dx in range(-limit,limit+1,2):
   dist=dx*dx+dy*dy
   if best is not None and dist>=best[0]:continue
   candidate=translate(g,dx,dy)
   # Keep unchanged original large coasts even where approximate source registration
   # creates a submillimetre overlap. Enlarged islands must be fully in clear space.
   overlap=candidate.intersection(obstacles).area
   if overlap>(.005 if factor>1.01 else max(3,g.area*.003)):continue
   best=(dist,dx,dy,candidate)
 if best is None:
  assert factor==1,(r['id'],'cannot find a safe enlarged position');best=(0,0,0,g)
 _,dx,dy,g=best
 if f:
  f['dx']+=dx;f['dy']+=dy
  # Other focal islands in the same family use its accumulated common translation.
  # At present each family contains one focal island, except the nearby Mascarenes.
 r.update({'geom':mapping(g),'source_geom':mapping(original),'local_scale':factor,'cluster_scale':f['scale']if f else 1,'local_origin':[c.x,c.y],'display_shift_mm':[dx,dy],'original_overlap_fraction':cover})
 included.append(r);print('ISLAND',r['id'],'area',round(g.area),'local enlargement',round(factor,2),'shift',dx,dy,flush=True)

# Reconcile the Mascarenes after both focal islands were positioned: each island has
# its own displacement, while unselected neighbours use the corresponding nearest host.
base=unary_union([shape(r['geom'])for r in included]);midparts=[];topparts=[]
for r in included:
 original=shape(r['source_geom']);g=shape(r['geom'])
 if original.area<450:continue
 mid=G.polygonal(G.terrace(original,300,38,1.7).intersection(original.buffer(-2.8)))
 top=G.polygonal(G.terrace(original,950,45,1.7).intersection(mid.buffer(-.7)))if original.area>1500 or r['id']=='png'else Polygon()
 # Preserve the exact source-to-display uniform mapping of the coast for every ply.
 f=F.get(r['family']);c=original.centroid
 # For the large islands used here family scaling is one; retain a general affine fit.
 fscale=(f['scale']if f else 1)*r['local_scale'];ox,oy=original.centroid.coords[0];gx,gy=g.centroid.coords[0]
 def moved(q):return translate(scale(q,xfact=fscale,yfact=fscale,origin=(ox,oy)),gx-ox,gy-oy)
 midparts.extend(G.ps(moved(mid)));topparts.extend(G.ps(moved(top)))
mid=unary_union(midparts).intersection(base);top=unary_union(topparts).intersection(mid)
k=G.Kit('01-Islands','Острова — исправленный полный набор',base,[base,mid,top])
for p in k.pieces:
 owners=sorted(included,key=lambda r:-p['_g'].intersection(shape(r['geom'])).area);owner=owners[0];assert p['_g'].intersection(shape(owner['geom'])).area>p['_g'].area*.99
 p['island_id']=owner['id'];p['island_name']=owner['name'];p['country']=owner['country']
def caption(r,text=None,kind=None,sizes=None,tiers=None,maxdistance=65):
 g=shape(r['geom']);ids=[p['id']for p in k.pieces if p['island_id']==r['id']and(tiers is None or p['tier']in tiers)]
 if not ids:return False
 target=max([p for p in k.pieces if p['id']in ids],key=lambda p:p['_visible'].area)['_visible'].representative_point()
 count=len(k.failed);ok=k.label(text or r['caption'],(target.x,target.y),kind or('country'if r['country_caption']else'region'),g,sizes=sizes or([7,6,5,4,3.4]if r['id']in ['ellesmere','baffin']else[4,3.4,3,2.6,2.2]),maxdistance=max(maxdistance,math.hypot(g.bounds[2]-g.bounds[0],g.bounds[3]-g.bounds[1])),only_tiers=tiers,owner_ids=ids)
 if ok:
  k.labels[-1]['island_id']=r['id'];k.labels[-1]['label_role']='island_name';k.failed=[q for q in k.failed if q['text']!=(text or r['caption'])]
 if ok:print('CAPTION',r['id'],k.labels[-1]['piece'],round(k.labels[-1]['font_size_mm'],2),flush=True)
 return ok
for r in included:
 # Put the big island title on its own visible base whenever possible. Ellesmere
 # additionally gets a clearly readable large caption on its main upper massif.
 if r['id']=='ellesmere':
  assert caption(r,'Элсмир',sizes=[3.6,3.2,2.8,2.4],tiers=[1],maxdistance=110)
  candidates=[p for p in k.pieces if p['island_id']==r['id']and p['tier']==3];largest=max(candidates,key=lambda p:p['_visible'].area);target=largest['_visible'].representative_point();ok=k.label('ЭЛСМИР',(target.x,target.y),'region',shape(r['geom']),sizes=[7,6,5.5,5],maxdistance=45,owner_ids=[largest['id']]);assert ok;k.labels[-1].update({'island_id':r['id'],'label_role':'primary_island_name'})
 else:
  ok=caption(r,tiers=[1])
  if not ok:ok=caption(r)
  if not ok:print('MISSING CAPTION',r['id'],flush=True)

index={r['id']:r for r in included}
cities=[('ellesmere','Грис-Фьорд',-82.90,76.42),('baffin','Икалуит',-68.52,63.75),('victoria','Кеймбридж-Бей',-105.06,69.12),('banks','Сакс-Харбор',-125.25,71.99),('cuba','Гавана',-82.37,23.11),('cuba','Сантьяго-де-Куба',-75.82,20.02),('hispaniola','Санто-Доминго',-69.93,18.49),('hispaniola','Порт-о-Пренс',-72.34,18.54),('jamaica','Кингстон',-76.79,17.97),('puerto-rico','Сан-Хуан',-66.11,18.47),('png','Порт-Морсби',147.18,-9.44),('png','Лаэ',146.99,-6.72),('png','Маданг',145.79,-5.22),('nz-north','Окленд',174.76,-36.85),('nz-north','Веллингтон',174.78,-41.29),('nz-south','Крайстчерч',172.64,-43.53),('nz-south','Данидин',170.50,-45.87),('new-caledonia','Нумеа',166.45,-22.27),('maldives','Фувахмулах',73.424,-.294),('seychelles','Виктория',55.45,-4.62),('mauritius','Порт-Луи',57.5,-20.16),('oahu','Гонолулу',-157.86,21.31),('tahiti','Папеэте',-149.57,-17.54),('fiji','Сува',178.44,-18.14),('solomons','Хониара',159.95,-9.43),('samoa','Апиа',-171.75,-13.83),('bahamas','Нассау',-77.35,25.06)]
for ident,name,lon,lat in cities:
 if ident not in index:continue
 r=index[ident];original=shape(r['source_geom']);g=shape(r['geom']);f=F.get(r['family']);p=merc_point(lon,lat)
 if f:
  period=360*Q['lon_to_x_mm'];p=translate(p,period*round((original.centroid.x-p.x)/period),0)
 factor=(f['scale']if f else 1)*r['local_scale'];p=scale(p,xfact=factor,yfact=factor,origin=original.centroid);p=translate(p,g.centroid.x-original.centroid.x,g.centroid.y-original.centroid.y)
 ids=[q['id']for q in k.pieces if q['island_id']==ident]
 allowed=g
 if ident=='hispaniola':allowed=g.intersection(shape(G.C['HTI'if name=='Порт-о-Пренс'else'DOM']['geom']))
 if k.label(name,(p.x,p.y),'city',allowed,sizes=[2.2,2,1.8,1.6,1.5],maxdistance=10,owner_ids=ids):k.labels[-1].update({'island_id':ident,'label_role':'city'})

# Extra country title in eastern Hispaniola is already present; make the west clear.
if 'hispaniola'in index:
 r=index['hispaniola'];g=G.smooth(shape(G.C['HTI']['geom']),.22,.12,.001).intersection(shape(r['geom']));p=g.representative_point()
 if k.label('Гаити',(p.x,p.y),'country',g,sizes=[2.4,2,1.8,1.5],maxdistance=12):k.labels[-1].update({'island_id':'hispaniola','label_role':'country'})
D=k.save('Крупные и интересные острова — отдельные деревянные детали с подписями. Элсмир подписан на видимой части основания и крупно на главном верхнем массиве; Баффинова Земля — на собственном основании. Названия жёстко связаны с именованными островами. Интересные малые острова увеличены; остальные мелкие острова вынесены в отдельный файл гравировки на оргстекле. Поворотов при раскладке нет. Увеличения и смещения перечислены в реестре.')

# Persist both original and display footprints, plus an explicit manufacturing-space
# ownership mask for every caption, so checks do not merely test the chosen object.
for r in included:r['wood_geom']=mapping(affine_transform(shape(r['geom']),INV))
dump(P/'data/island-roster.json',included);dump(P/'data/islands-already-in-continental-kits.json',existing)
dump(P/'data/cluster-display-transforms.json',[{key:([f['anchor'].x,f['anchor'].y]if key=='anchor'else val)for key,val in f.items()}for f in F.values()])

# Remaining offshore islands: engraving only. Never convert an absent country into
# an omission because its individual land polygons fall below a plywood area rule.
referencewood=unary_union([OLD,base]);safe=referencewood.buffer(.3);engraved=[];overlays=[];source_counts=Counter()
selected_originals=unary_union([shape(r['source_geom'])for r in included]);samples=0
for feat in NE:
 code=feat['properties']['ADM0_A3']
 if code=='ATA':continue
 for j,poly in enumerate(G.ps(shape(feat['geometry']))):
  if poly.area>80:continue  # continental bodies, never an island engraving
  f=find_family(code,poly);g=projected(poly,f['lon']if f else 180 if code=='RUS'else -120 if code=='USA'else None)
  # Match focal islands in geographic space before the display enlargement.
  if selected_originals.intersection(g).area>g.area*.70:continue
  oldcover=OLD.intersection(g).area/g.area
  if oldcover>.5 or g.distance(OLD)<.10:continue
  if g.area<1e-10:continue
  g=fam_geom(g,f)
  if g.area<.09:g=g.centroid.buffer(.16,quad_segs=8)
  else:g=G.polygonal(g.simplify(.025,preserve_topology=True))
  if g.is_empty or g.intersects(safe):continue
  engraved.append(g);source_counts[code]+=1
  overlays.append({'country':code,'source_component':j,'geom':mapping(affine_transform(g,INV))})
engraved=G.polygonal(unary_union(engraved));dump(P/'data/acrylic-engraving.json',{'geom':mapping(affine_transform(engraved,INV)),'islands':overlays,'by_country':dict(source_counts),'note':'Красная гравировка на оргстекле; эти контуры не режутся из фанеры.'})
print('COMPLETE',len(included),'named wooden islands',len(D['pieces']),'wood pieces',len(D['labels']),'captions;',len(overlays),'engraved minor islands; already in mainland kits',len(existing),flush=True)
