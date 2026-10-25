import bpy,json,sys,os
sys.path.extend(p for p in os.environ.get('PYTHONPATH','').split(os.pathsep) if p)
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from shapely.geometry import shape
P=Path(__file__).resolve().parent
if P.name=='tools':P=P.parent
old=json.load(open(P/'data/source-relief.json'));new=json.load(open(P/'terrain-geometry.json'));D=json.load(open(P/'model-data.json'));woods={o['id']:o for o in D['objects'] if o['kind']=='wood'};vertices=[];faces=[]
for name in woods:
 ob=bpy.data.objects[name];n=len(vertices);vertices.extend(ob.matrix_world@v.co for v in ob.data.vertices);faces.extend([n+i for i in f.vertices] for f in ob.data.polygons)
bvh=BVHTree.FromPolygons(vertices,faces);scale=D['mm_per_unit']/1000;checks=[]
for f in new['landmarks']:
 q=shape(f['geom']).representative_point();expected=max((i+1)*3 for i,g in enumerate(old['layers']) if shape(g).covers(q));hit=bvh.ray_cast(Vector((q.x*scale,(2657.4803125-q.y)*scale,.08)),Vector((0,0,-1)),.15)[0];assert hit is not None and abs(hit.z*1000-expected)<.02,(f['name'],hit,expected);checks.append({'landmark':f['name'],'expected_floor_or_top_mm':expected,'actual_mm':round(hit.z*1000,4)})
assert new['countries']==old['countries'];assert new['palette']==old['palette'];assert shape(new['layers'][0]).symmetric_difference(shape(old['layers'][0])).area<1e-6
(P/'Проверка-природных-объектов-Blender.json').write_text(json.dumps({'actual_scene_ray_tests':checks,'country_partition_unchanged':True,'palette_unchanged':True,'base_unchanged':True,'passed':True},ensure_ascii=False,indent=2));print('REAL SCENE VERIFIED',checks,flush=True)
