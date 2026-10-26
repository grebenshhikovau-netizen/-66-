"""Place every country title on one exposed physical ply, as editable text."""
import json,math
from pathlib import Path
import numpy as np
from shapely.geometry import shape,box,Point,Polygon,mapping
from shapely.ops import unary_union,polylabel
from shapely.affinity import translate,rotate,scale
from shapely.prepared import prep
from font_geometry import word_geom
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/production-plan.json'));result=[]
def ps(g):
 if g.geom_type=='Polygon':return[g]if not g.is_empty else[]
 return[p for q in getattr(g,'geoms',[])for p in ps(q)]
targets={'BRA':8,'ARG':5.8,'CHL':4.2,'BOL':4.5,'PER':4.4,'COL':4.8,'VEN':3.8,'ECU':2.8,'PRY':3,'URY':2.8,'GUY':2.8,'SUR':2.4,'GUF':2.1}
for code,name in D['country_names'].items():
 lines=['ФРАНЦУЗСКАЯ','ГВИАНА']if code=='GUF'else[name];rawlines=[];raws=[]
 for j,text in enumerate(lines):
  g=word_geom(text);x0,y0,x1,y1=g.bounds;dx=-(x0+x1)/2;dy=j*1.3;rawlines.append({'text':text,'x_em':dx,'y_em':dy});raws.append(translate(g,dx,dy))
 raw=unary_union(raws);bb=box(*raw.bounds);cx,cy=raw.centroid.x,raw.centroid.y;country=shape(D['territories'][code]);preferred=country.centroid;options=[]
 for row in D['pieces']:
  mask=shape(D['layer_country_masks'][row['tier']-1].get(code,mapping(Polygon())));available=shape(row['visible']).intersection(mask).buffer(-.4)
  if available.is_empty:continue
  points=[]
  for q in sorted(ps(available),key=lambda q:-q.area)[:4]:
   points.extend([q.representative_point(),polylabel(q,tolerance=.2)])
  l,t,r,b=available.bounds
  for x in np.arange(l,r+1,2):
   for y in np.arange(t,b+1,2):
    pt=Point(float(x),float(y))
    if available.covers(pt):points.append(pt)
  points=sorted(points,key=lambda q:q.distance(preferred));options.append((row,available,prep(available),points))
 angles=[-90,0]if code=='CHL'else[0]
 found=None
 for size in np.arange(targets[code],1.05,-.1):
  for angle in angles:
   rect=rotate(scale(bb,xfact=float(size),yfact=float(size),origin=(cx,cy)),angle,origin=(cx,cy));textgeom=rotate(scale(raw,xfact=float(size),yfact=float(size),origin=(cx,cy)),angle,origin=(cx,cy))
   for row,available,prepared,points in options:
    for pt in points:
     dx,dy=pt.x-cx,pt.y-cy
     if not prepared.covers(translate(rect,dx,dy)):continue
     distance=pt.distance(preferred);score=distance-(row['tier']-1)*.2
     if found is None or score<found[0]:found=(score,row,float(size),angle,pt,translate(textgeom,dx,dy))
     break
   if found:break
  if found:break
 assert found,(code,'title does not fit')
 _,row,size,angle,pt,outline=found;co,si=math.cos(math.radians(angle)),math.sin(math.radians(angle));e=pt.x-co*size*cx+si*size*cy;f=pt.y-si*size*cx-co*size*cy
 result.append({'id':'COUNTRY_'+code,'country':code,'text':name,'lines':rawlines,'piece':row['id'],'tier':row['tier'],'font_family':'Open Sans Light','font_size_mm':size,'angle_degrees':angle,'matrix':[co,si,-si,co,e,f],'geometry':mapping(outline),'source_position_mm':[pt.x,pt.y]})
 print('LABEL',code,row['id'],'font',round(size,2),'angle',angle,'point',round(pt.x,1),round(pt.y,1),flush=True)
for row in D['pieces']:row['engraving']=mapping(unary_union([shape(q['geometry'])for q in result if q['piece']==row['id']]))
D['labels']=result;(P/'data/production-plan.json').write_text(json.dumps(D,ensure_ascii=False));(P/'data/labels.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('ALL COUNTRY TITLES',len(result),flush=True)
