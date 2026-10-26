"""Recreate editable UTF-8 text in the accepted word positions, with a supplied font."""
import json,math
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from shapely.geometry import Polygon,mapping,shape
from shapely.ops import unary_union
from shapely.affinity import affine_transform,rotate
P=Path(__file__).resolve().parent.parent;A=json.load(open(P/'data/annotations.json'));C=json.load(open(P/'data/text-content.json'));angles={q['id']:q['angle']for q in json.load(open(P/'data/text-geometry.json'))};D=json.load(open(P/'data/source/production-plan.json'));font=TTFont(P/'Шрифт/OpenSans-Light.ttf');glyphs=font.getGlyphSet();cmap=font.getBestCmap();upm=font['head'].unitsPerEm
class Pen(BasePen):
 def __init__(self):super().__init__(glyphs);self.rings=[];self.points=[]
 def _moveTo(self,p):
  if self.points:self._closePath()
  self.points=[p]
 def _lineTo(self,p):self.points.append(p)
 def _curveToOne(self,p1,p2,p3):
  p0=self._getCurrentPoint()
  for i in range(1,21):
   t=i/20;s=1-t;self.points.append(tuple(s**3*p0[j]+3*s*s*t*p1[j]+3*s*t*t*p2[j]+t**3*p3[j]for j in [0,1]))
 def _qCurveToOne(self,p1,p2):
  p0=self._getCurrentPoint()
  for i in range(1,21):
   t=i/20;s=1-t;self.points.append(tuple(s*s*p0[j]+2*s*t*p1[j]+t*t*p2[j]for j in [0,1]))
 def _closePath(self):
  if len(self.points)>2:self.rings.append(self.points)
  self.points=[]
 def _endPath(self):self._closePath()
def word_geom(text):
 xpos=0;chars=[]
 for ch in text:
  assert ord(ch)in cmap,(ch,'font has no glyph');gn=cmap[ord(ch)];pen=Pen();glyphs[gn].draw(pen);pen._endPath();rings=[[(x/upm+xpos,-y/upm)for x,y in r]for r in pen.rings];areas=[sum(x*y2-x2*y for(x,y),(x2,y2)in zip(r,r[1:]+r[:1]))for r in rings]
  if rings:
   sign=1 if areas[max(range(len(areas)),key=lambda i:abs(areas[i]))]>0 else -1;outer=[Polygon(r)for r,area in zip(rings,areas)if area*sign>0];holes=[Polygon(r)for r,area in zip(rings,areas)if area*sign<0];g=unary_union(outer).difference(unary_union(holes));chars.append(g)
  xpos+=font['hmtx'][gn][0]/upm
 return unary_union(chars)
out=[]
for a in A:
 if a['kind']!='red_stroke':continue
 id=a['id'];text=C[id];g=shape(a['source_outline']);angle=angles[id];local=rotate(g,-angle,origin=(0,0));l,t,r,b=local.bounds;raw=word_geom(text);x0,y0,x1,y1=raw.bounds;sx=(r-l)/(x1-x0);sy=(b-t)/(y1-y0);rad=math.radians(angle);co,si=math.cos(rad),math.sin(rad);owner=next(q for q in D['pieces']if q['id']==a['piece']);visible=shape(owner['visible'])
 for factor in [1,.99,.98,.97,.96,.95,.94,.92,.90,.88,.85]:
  fx,fy=sx*factor,sy*factor;e=(l+r)/2-fx*(x0+x1)/2;f=(t+b)/2-fy*(y0+y1)/2;matrix=[co*fx,si*fx,-si*fy,co*fy,co*e-si*f,si*e+co*f];actual=affine_transform(raw,[matrix[0],matrix[2],matrix[1],matrix[3],matrix[4],matrix[5]])
  if actual.difference(visible.buffer(.015)).area<.0002:break
 else:raise ValueError((id,'text does not fit',actual.difference(visible).area))
 # Actual font size in SVG user units (mm); matrix retains rotation / width only.
 svg_matrix=[matrix[0]/fy,matrix[1]/fy,matrix[2]/fy,matrix[3]/fy,matrix[4],matrix[5]]
 out.append({'id':id,'text':text,'piece':a['piece'],'font_family':'Open Sans Light','font_size_mm':fy,'matrix':svg_matrix,'angle_degrees':angle,'fit_factor':factor,'outline_for_validation':mapping(actual),'original_local_bounds_mm':[l,t,r,b]})
 print('LIVE TEXT',id,text,'fit',factor,flush=True)
assert len(out)==82
(P/'data/live-text.json').write_text(json.dumps(out,ensure_ascii=False));print('EDITABLE TEXT READY',len(out),flush=True)
