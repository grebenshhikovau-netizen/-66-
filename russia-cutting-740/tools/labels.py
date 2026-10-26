"""Editable country, regional and city lettering; whole words on exposed plies."""
import json,math
from pathlib import Path
import numpy as np
from shapely.geometry import shape,box,Point,Polygon,LineString,mapping
from shapely.ops import unary_union,nearest_points,polylabel
from shapely.affinity import translate,scale
from shapely.prepared import prep
from font_geometry import word_geom
from geo import xy
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));cities=json.load(open(P/'data/cities.json'));source_texts=json.load(open(P/'data/source/source-texts.json'));pieces=D['pieces'];labels=[];markers=[];occupied=Polygon();sourceNames={q['region']:q['text']for q in source_texts};overrides=json.load(open(P/'data/region-name-overrides.json'));D['region_names'].update(overrides);regions={c:shape(g)for c,g in D['regions'].items()};safe={q['id']:shape(q['visible']).buffer(-.24)for q in pieces};prepared={k:prep(g)for k,g in safe.items()};notes=[]
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty and g.area>1e-7 else[]
 return[p for a in getattr(g,'geoms',[])for p in ps(a)]
def wrap(text,limit=18):
 words=text.split();out=[];current=''
 for word in words:
  if current and len(current)+len(word)+1>limit:out.append(current);current=word
  else:current=(current+' '+word).strip()
 if current:out.append(current)
 # Keep long names whole; line breaks at a hyphen preserve every letter.
 if len(out)==1 and len(out[0])>23 and '-'in out[0]:
  k=out[0].find('-')+1;out=[out[0][:k],out[0][k:]]
 return out
def raw_text(lines):
 specs=[];gg=[]
 for i,text in enumerate(lines):
  g=word_geom(text);x0,y0,x1,y1=g.bounds;dx=-(x0+x1)/2;dy=i*1.24;specs.append({'text':text,'x_em':dx,'y_em':dy});gg.append(translate(g,dx,dy))
 raw=unary_union(gg);return raw,specs
# Exact geographic points are shifted only to a nearby bank if they fall in a water cut.
marker_safe={row['id']:shape(row['visible']).buffer(-.34)for row in pieces}
print('MARKER SURFACES READY',flush=True)
for i,(name,lon,lat,region)in enumerate(cities):
 anchor=Point(xy(lon,lat));best=None
 for row in pieces:
  area=marker_safe[row['id']]
  if area.is_empty:continue
  point=anchor if area.covers(anchor)else nearest_points(anchor,area)[1];distance=point.distance(anchor);score=distance-row['tier']*.002
  if best is None or score<best[0]:best=(score,row,point,distance)
 assert best and best[3]<3.5,(name,'geographic point too far from source coast',best[3]if best else None)
 _,row,point,distance=best;marker=point.buffer(.21,quad_segs=8);m={'id':f'CITY_{i+1:03d}','name':name,'lon':lon,'lat':lat,'region':region,'point_mm':[point.x,point.y],'geographic_point_mm':[anchor.x,anchor.y],'bank_shift_mm':distance,'piece':row['id'],'geom':mapping(marker)};markers.append(m)
 print('MARKER',name,round(distance,2),flush=True)
occupied=unary_union([shape(q['geom']).buffer(.25)for q in markers])
def add_label(id,text,kind,preferred,target=1.8,region=None,marker=None,color='#ff0000'):
 global occupied
 raw,specs=raw_text(wrap(text,19 if kind=='region'else 20));cx,cy=raw.centroid.x,raw.centroid.y;bb=box(*raw.bounds);options=[]
 for row in pieces:
  area=safe[row['id']]
  if area.is_empty:continue
  if kind=='city'and area.distance(preferred)>18:continue
  if region is not None:
   area=area.intersection(regions[region])
  if area.area<1:continue
  options.append((row,area,prep(area)))
 found=None
 # Largest readable font first; prioritize a local position, with no clipping.
 for size in list(np.arange(target,.89,-.1)):
  rect=scale(bb,xfact=float(size),yfact=float(size),origin=(cx,cy));r0,r1,r2,r3=rect.bounds;w,h=r2-r0,r3-r1
  if kind=='city':
   centers=[(preferred.x+w/2+.8,preferred.y),(preferred.x-w/2-.8,preferred.y),(preferred.x,preferred.y-h/2-.9),(preferred.x,preferred.y+h/2+.9)]
   offsets=[(x,y)for x in np.arange(-17,17.1,1.5)for y in np.arange(-13,13.1,1.5)];offsets.sort(key=lambda v:v[0]**2+v[1]**2);centers +=[(preferred.x+float(x),preferred.y+float(y))for x,y in offsets]
  else:
   centers=[]
   for row,area,pr in options:
    for g in sorted(ps(area),key=lambda q:-q.area)[:5]:
     centers.extend([(g.representative_point().x,g.representative_point().y),(polylabel(g,tolerance=.4).x,polylabel(g,tolerance=.4).y)])
    x0,y0,x1,y1=area.bounds;step=2.2 if kind=='region'else 4
    for x in np.arange(x0,x1+.1,step):
     for y in np.arange(y0,y1+.1,step):centers.append((float(x),float(y)))
   centers.sort(key=lambda q:(q[0]-preferred.x)**2+(q[1]-preferred.y)**2)
  for x,y in centers:
   dx,dy=x-cx,y-cy;candidate=translate(rect,dx,dy);reserve=candidate.buffer(.18,join_style=2)
   if occupied.intersects(reserve):continue
   for row,area,pr in options:
    if pr.covers(candidate):found=(row,float(size),x,y,candidate,reserve);break
   if found:break
  if found:break
 # Small administrative city-regions and narrow territories use a nearby callout.
 if found is None and region is not None:
  ans=add_label(id,text,'city',preferred,min(target,1.5),region=None,color=color)
  ans['kind']='region';ans['region']=region;ans['callout']=True;ans['leader']=mapping(LineString([preferred,nearest_points(preferred,shape(ans['bbox']))[1]]));return ans
 assert found,(id,text,'no exposed surface for a complete word')
 row,size,x,y,rect,reserve=found;outline=translate(scale(raw,xfact=size,yfact=size,origin=(cx,cy)),x-cx,y-cy);matrix=[1,0,0,1,x-size*cx,y-size*cy]
 entry={'id':id,'text':text,'kind':kind,'region':region,'piece':row['id'],'tier':row['tier'],'font_family':'Open Sans Light','font_size_mm':size,'matrix':matrix,'lines':specs,'color':color,'geometry':mapping(outline),'bbox':mapping(rect),'center_mm':[x,y]};labels.append(entry);occupied=occupied.union(reserve)
 if marker is not None:
  p=Point(marker['point_mm']);q=nearest_points(p,rect)[1]
  if p.distance(q)>.65:entry['leader']=mapping(LineString([p,q]))
 print('TEXT',kind,id,text,'layer',row['tier'],'font',round(size,2),flush=True)
 return entry
# Country title is one blue object; everything else is red editable text.
add_label('COUNTRY_RUSSIA','РОССИЯ','country',Point(1120,-755),6.2,color='#0000ff')
for i,city in enumerate(cities):
 name,lon,lat,code=city;m=markers[i];add_label(m['id']+'_TEXT',name,'city',Point(m['point_mm']),2.0 if i<16 else 1.7,marker=m)
city_alias={'RU_MOS':'Москва','RU_SPE':'Санкт-Петербург','UA_40':'Севастополь'}
for code,name in sorted(D['region_names'].items(),key=lambda q:-regions[q[0]].area):
 if code in city_alias:
  notes.append({'region':code,'name':name,'represented_by_city_text':city_alias[code]});continue
 word=overrides.get(code,sourceNames.get(code,name.upper())).upper();region=regions[code];target=min(3.2,max(1.3,region.area**.25*.37));preferred=region.representative_point();add_label('REGION_'+code,word,'region',preferred,target,region=code)
D['labels']=labels;D['city_markers']=markers;D['label_notes']=notes
for row in pieces:row['engraving']=mapping(unary_union([shape(q['geometry'])for q in labels if q['piece']==row['id']]+[shape(m['geom'])for m in markers if m['piece']==row['id']]))
(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));(P/'data/labels.json').write_text(json.dumps({'labels':labels,'markers':markers,'region_aliases':notes},ensure_ascii=False));print('ALL LABELS',len(labels),'CITIES',len(markers),'REGIONS',sum(q['kind']=='region'for q in labels),'SOURCE REGION WORDINGS',len(sourceNames),flush=True)
