from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from shapely.geometry import Polygon
from shapely.ops import unary_union
P=Path(__file__).resolve().parent.parent
font=TTFont(P/'Шрифт/OpenSans-Light.ttf');glyphs=font.getGlyphSet();cmap=font.getBestCmap();upm=font['head'].unitsPerEm
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
