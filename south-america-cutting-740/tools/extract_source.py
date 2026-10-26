import bpy,json,sys,os,math
sys.path.extend(p for p in os.environ.get('PYTHONPATH','').split(os.pathsep)if p and p not in sys.path)
from pathlib import Path
from collections import Counter
from shapely.geometry import Polygon,mapping
from shapely.ops import unary_union
from shapely import make_valid,set_precision
P=Path(__file__).resolve().parent.parent;bpy.context.preferences.filepaths.use_scripts_auto_execute=False
source=str(P/'data/source/Исходная-сборка.blend');bpy.ops.wm.open_mainfile(filepath=source);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();out=[];mats={}
def colour(socket,visited=None):
 visited=set()if visited is None else visited
 if not socket.is_linked:return list(socket.default_value)[:3]
 node=socket.links[0].from_node
 if node.name in visited:raise ValueError('Cyclic color shader')
 visited.add(node.name)
 if node.type=='BRIGHTCONTRAST':
  col=colour(node.inputs['Color'],visited);br=node.inputs['Bright'].default_value if 'Bright'in node.inputs else node.inputs['Brightness'].default_value;con=node.inputs['Contrast'].default_value;a=1+con;b=br-con*.5;return [max(a*v+b,0)for v in col]
 if node.type=='VALTORGB':return [sum(e.color[i]for e in node.color_ramp.elements)/len(node.color_ramp.elements)for i in range(3)]
 if node.type=='RGB':return list(node.outputs[0].default_value)[:3]
 if node.type=='REROUTE':return colour(node.inputs[0],visited)
 raise ValueError(('Unsupported color node',node.type,node.name))
for o in bpy.context.scene.objects:
 if o.get('Role')not in ['PlywoodPiece','Engraving']or not o.visible_get()or o.hide_render:continue
 eg=o.evaluated_get(dg);mesh=eg.to_mesh();world=eg.matrix_world;verts=[world@v.co for v in mesh.vertices];lo=min(v.z for v in verts)*1000;hi=max(v.z for v in verts)*1000;faces=[];topindices=Counter()
 for f in mesh.polygons:
  pp=[(round(verts[i].x*1000,6),round(-verts[i].y*1000,6))for i in f.vertices];p=Polygon(pp)
  if p.area<1e-9:continue
  faces.append(p if p.is_valid else make_valid(p))
  if min(verts[i].z*1000 for i in f.vertices)>hi-.0002:topindices[f.material_index]+=1
 g=set_precision(make_valid(unary_union(faces)),.001)
 if g.is_empty:eg.to_mesh_clear();continue
 role=o.get('Role');color=None;matname=None
 if role=='PlywoodPiece':
  index=topindices.most_common(1)[0][0];mat=mesh.materials[index];matname=mat.name
  if mat.use_nodes:
   bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');color=colour(bs.inputs['Base Color'])
  else:color=list(mat.diffuse_color)[:3]
  mats[matname]={'color_linear':color,'diffuse':list(mat.diffuse_color)[:3],'top_material_indices':dict(topindices),'shader_nodes':[(n.name,n.type)for n in mat.node_tree.nodes]if mat.use_nodes else []}
 out.append({'name':o.name,'country':o.get('Country_ID'),'kind':'wood'if role=='PlywoodPiece'else'boundary_engraving','lo_mm':lo,'hi_mm':hi,'legacy_tier':o.get('Tier'),'color_linear':color,'material':matname,'geom':mapping(g),'area_mm2':g.area});eg.to_mesh_clear();print('EXTRACT',o.name,round(g.area,3),lo,hi,color,flush=True)
(P/'data/source/extracted.json').write_text(json.dumps(out,ensure_ascii=False));(P/'data/source/materials.json').write_text(json.dumps(mats,ensure_ascii=False,indent=2));print('EXTRACTED',len(out),flush=True)
