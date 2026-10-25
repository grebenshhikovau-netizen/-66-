"""Check actual Blender meshes, through-water, recess floors and module exchange."""
import bpy,json,sys,math,os
sys.path.extend(p for p in os.environ.get('PYTHONPATH','').split(os.pathsep) if p and p not in sys.path)
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from shapely.geometry import shape,Point
from shapely.ops import unary_union

P=Path(__file__).resolve().parent.parent;G=json.load(open(P/'geometry.json'));D=json.load(open(P/'model-data.json'));S=G['mm_per_unit']/1000
def polygons(g):
 if g.geom_type=='Polygon':return [g] if not g.is_empty and g.area>1e-4 else []
 return [p for q in getattr(g,'geoms',[]) for p in polygons(q)]
verts=[];faces=[]
for ob in bpy.context.scene.objects:
 if ob.get('Role') not in ['PlywoodPiece','RussianReference']:continue
 offset=len(verts);verts.extend(ob.matrix_world@v.co for v in ob.data.vertices);faces.extend([offset+i for i in f.vertices] for f in ob.data.polygons)
bvh=BVHTree.FromPolygons(verts,faces,all_triangles=False)
def height(q):
 pos,normal,index,d=bvh.ray_cast(Vector((q.x*S,(2657.4803125-q.y)*S,.08)),Vector((0,0,-1)),.15)
 return None if pos is None else pos.z
land=shape(json.load(open(P/'data/base.json')));water_results={}
for name,geom in {**G['waters'],**G['fjords']}.items():
 part=shape(geom).intersection(land.buffer(-.1));pp=sorted(polygons(part),key=lambda p:-p.area)
 if not pp:continue
 samples=[p.representative_point() for p in pp[:3]]
 for q in samples:assert height(q) is None,('water blocked',name,q.x,q.y,height(q))
 water_results[name]=len(samples)
craters=[]
for c in G['craters']:
 q=shape(c['geom']).representative_point();z=height(q);expected=c['tier']*.003-.00035
 assert z is not None and abs(z-expected)<2e-5,('crater floor',c['name'],z,expected)
 craters.append({'name':c['name'],'floor_mm':round(z*1000,3)})
recesses=[]
for c in G['recesses']:
 q=shape(c['geom']).representative_point();z=height(q)
 assert z is not None,('dry depression is through',c['name'])
 recesses.append({'name':c['name'],'floor_mm':round(z*1000,3)})

sys.path.insert(0,str(P/'tools'));from swap_region import swap_region
tests=[]
for region in ['FRA',next(k for k in D['regions'] if k.startswith('CN_') and k not in ['CN_HK','CN_MO'])]:
 root=next(o for o in bpy.context.scene.objects if o.get('Role')=='RegionRoot' and o.get('Region_ID')==region)
 root.location.x+=.011;root.rotation_euler.z=.17;bpy.context.view_layer.update();before=root.matrix_world.copy()
 new=swap_region(region,P/'Евразия-политическая.blend')
 assert max(abs(new.matrix_world[i][j]-before[i][j]) for i in range(4) for j in range(4))<1e-6
 # Exchange back: identical roots allow mixing without touching adjacent modules.
 back=swap_region(region,P/'Евразия-рельеф-по-регионам.blend')
 assert max(abs(back.matrix_world[i][j]-before[i][j]) for i in range(4) for j in range(4))<1e-6
 country=back['Country_ID'];coatings={ob.data.materials[0].get('HEX') for ob in bpy.context.scene.objects if ob.get('Role')=='PlywoodPiece' and ob.get('Country_ID')==country}
 assert len(coatings)==1,(region,coatings)
 tests.append(region)
report={'actual_mesh_water_ray_tests':water_results,'crater_floor_ray_tests':craters,'dry_recess_floor_tests':recesses,'round_trip_module_exchange':tests,'moved_and_rotated_region_pose_preserved':True,'country_material_preserved_during_exchange':True}
(P/'Проверка-реальной-сцены.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('ACTUAL SCENE VERIFIED',len(water_results),'water objects',len(craters),'craters',tests,flush=True)
