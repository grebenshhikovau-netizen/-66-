"""Closed vector lettering, placed whole on wood and bound to each political piece."""
import json,math
from collections import defaultdict
from pathlib import Path
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from svgpathtools import parse_path
from shapely.geometry import shape,mapping,Polygon,Point,LineString
from shapely.ops import unary_union,polygonize,polylabel
from shapely.affinity import scale,translate,rotate
from common import *

D=json.load(open(ROOT/'geometry.json'));font=TTFont(str(DATA/'NotoSans-Regular.ttf'));glyphs=font.getGlyphSet();cmap=font.getBestCmap();upm=font['head'].unitsPerEm;cap=getattr(font['OS/2'],'sCapHeight',upm*.72);adv=font['hmtx'].metrics
def outline(text):
 pen=SVGPathPen(glyphs)
 for row,line in enumerate(text.split('\n')):
  width=sum(adv[cmap.get(ord(c),'space')][0]+cap*.055 for c in line);x=-width/2
  for c in line:
   name=cmap.get(ord(c),'space');p=TransformPen(pen,(1,0,0,-1,x,row*cap*1.35));glyphs[name].draw(p);x+=adv[name][0]+cap*.055
 path=parse_path(pen.getCommands());rings=[]
 for part in path.continuous_subpaths():
  pts=[]
  for s in part:
   n=max(1,math.ceil(s.length()/cap*18));pts.extend((s.point(j/n).real/cap,s.point(j/n).imag/cap) for j in range(n))
  pts.append((part.end.real/cap,part.end.imag/cap));poly=Polygon(pts)
  if poly.is_valid and poly.area>1e-8:
   a=sum(x*y2-x2*y for (x,y),(x2,y2) in zip(pts[:-1],pts[1:]));rings.append((poly,1 if a>0 else -1))
 if not rings:return Polygon()
 faces=polygonize(unary_union([p.boundary for p,s in rings]));out=[]
 for p in faces:
  q=p.representative_point()
  if sum(s for r,s in rings if r.covers(q))!=0:out.append(p)
 return unary_union(out)

country_regions=defaultdict(list)
for r in D['regions']:country_regions[r['country']].append(r)
available=shape(D['base']);L=[shape(g) for g in D['layers']];V=[shape(g) for g in D['visible']];labels=[];omitted=[]
short={'ARE':'ОАЭ','PRK':'КНДР','KOR':'КОРЕЯ','GBR':'ВЕЛИКОБРИТАНИЯ','BIH':'БОСНИЯ И\nГЕРЦЕГОВИНА','SAU':'САУДОВСКАЯ\nАРАВИЯ','MKD':'СЕВЕРНАЯ\nМАКЕДОНИЯ','TLS':'ВОСТОЧНЫЙ\nТИМОР'}
for code,rr in country_regions.items():
 country=unary_union([shape(r['geom']) for r in rr]);name=short.get(code,rr[0]['country_name'].upper());shape0=outline(name)
 area=country.area*M*M
 if shape0.is_empty or area<9:omitted.append({'country':code,'reason':'below useful lettering scale'});continue
 maxfont=min(6,max(2.2,math.sqrt(area)*.09));chosen=None
 options=[]
 for tier,vis in enumerate(V,1):
  for p in sorted(polys(vis.intersection(country)),key=lambda p:-p.area)[:4]:options.append((p,tier))
 options.sort(key=lambda p:-p[0].area)
 options+= [(p,0) for p in sorted(polys(country.intersection(available)),key=lambda p:-p.area)[:2]]
 for p,tier in options:
  room=p.buffer(-.45/M)
  if room.is_empty:continue
  largest=max(polys(room),key=lambda p:p.area);seat=polylabel(largest,tolerance=.45/M);candidate_points=[seat,largest.representative_point(),largest.centroid]
  for fontmm in np.arange(maxfont,1.54,-.28):
   glyph=scale(shape0,xfact=fontmm/M,yfact=fontmm/M,origin=(0,0));x0,y0,x1,y1=glyph.bounds;glyph=translate(glyph,yoff=-(y0+y1)/2)
   for angle in [0,20,-20,70,90]:
    g=rotate(glyph,angle,origin=(0,0))
    for q in candidate_points:
     placed=translate(g,xoff=q.x,yoff=q.y)
     if largest.covers(placed):chosen=(placed,fontmm,tier);break
    if chosen:break
   if chosen:break
  if chosen:break
 if not chosen:omitted.append({'country':code,'reason':'no complete word fits without cropping'});continue
 g,size,tier=chosen;labels.append({'country':code,'name':name,'font_mm':size,'preferred_tier':tier,'geom':mapping(g)});print('LABEL',code,round(size,2),tier,flush=True)
dump('labels.json',{'labels':labels,'omitted':omitted,'font':'Noto Sans Regular','all_letter_outlines_closed':True,'whole_words_fit_wood':True})
r=svgroot()
for row in labels:svgpath(r,shape(row['geom']),'LABEL_'+row['country'],'#000')
savesvg(r,'Подписи-стран-в-кривых.svg')
print('CLOSED LABELS',len(labels),'omitted',len(omitted),flush=True)
