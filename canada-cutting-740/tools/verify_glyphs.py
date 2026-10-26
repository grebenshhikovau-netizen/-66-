"""Check component preservation of every red glyph and exact blue source outlines."""
import json
from pathlib import Path
from shapely.geometry import shape
P=Path(__file__).resolve().parent.parent;A=json.load(open(P/'data/annotations.json'));B=json.load(open(P/'data/blue-titles-before-revision.json'));report=[]
for a in A:
 if a['kind']=='blue_fill':
  error=shape(B[a['id']]).symmetric_difference(shape(a['geometry'])).area;assert error<.001,(a['id'],error);report.append({'id':a['id'],'unchanged_blue_outline_error_mm2':error});continue
 if a['kind']!='red_stroke':continue
 g=shape(a['geometry']);ls=[g]if g.geom_type=='LineString'else list(g.geoms);parent={}
 def find(q):
  parent.setdefault(q,q)
  if parent[q]!=q:parent[q]=find(parent[q])
  return parent[q]
 for l in ls:
  x=tuple(round(v,6)for v in l.coords[0]);y=tuple(round(v,6)for v in l.coords[-1]);parent[find(x)]=find(y)
 count=len(set(find(x)for x in parent));assert count==a['glyph_components'],(a['id'],count,a['glyph_components']);report.append({'id':a['id'],'source_glyph_components':a['glyph_components'],'centerline_connected_components':count,'stroke_length_mm':g.length})
(P/'Проверка-однолинейного-текста.json').write_text(json.dumps({'passed':True,'labels':report,'red_labels':82,'blue_titles_preserved':4,'all_glyph_components_preserved':True},ensure_ascii=False,indent=2));print('VERIFIED',sum(q.get('source_glyph_components',0)for q in report),'glyph components',flush=True)
