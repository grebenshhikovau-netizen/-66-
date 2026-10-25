"""Run inside Blender with a country root, wood or engraving selected."""
import bpy,tempfile,shutil
from pathlib import Path
from contextlib import ExitStack
SOURCE_NAME = ''
REGION_ID = ''

def descendants(col):
    for child in col.children:
        yield child
        yield from descendants(child)

def swap_region(region_id,source_path):
    scene=bpy.context.scene
    old=next((c for c in descendants(scene.collection) if c.get('Region_ID')==region_id),None)
    if old is None:raise RuntimeError('Не найдена страна: '+region_id)
    oldroot=next(o for o in old.objects if o.get('Role')=='RegionRoot')
    pose=oldroot.matrix_world.copy()
    material=next((o.data.materials[0] for o in old.all_objects if o.get('Role')=='PlywoodPiece' and o.data.materials),None)
    path=Path(source_path)
    if not path.is_file():raise RuntimeError('Положите рядом файл '+path.name)
    with ExitStack() as stack:
        lib=path
        if path.resolve()==Path(bpy.data.filepath).resolve():
            folder=Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='sa-country-swap-')));lib=folder/'source.blend';shutil.copyfile(path,lib)
        with bpy.data.libraries.load(str(lib),link=False) as (available,loaded):
            names=[n for n in available.collections if n.startswith('REG_'+region_id+'__')]
            if len(names)!=1:raise RuntimeError('В файле нет однозначного модуля '+region_id)
            loaded.collections=names
    new=loaded.collections[0]
    parent=next((c for c in descendants(scene.collection) if old.name in c.children),scene.collection)
    parent.children.link(new)
    root=next(o for o in new.objects if o.get('Role')=='RegionRoot');root.matrix_world=pose
    for ob in new.all_objects:
        if ob.get('Role')=='PlywoodPiece' and material:ob.data.materials[0]=material
    for ob in list(old.all_objects):bpy.data.objects.remove(ob,do_unlink=True)
    bpy.data.collections.remove(old)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True);bpy.context.view_layer.objects.active=root
    print('Заменена страна',region_id,'из',path.name,flush=True)
    return root

if __name__=='__main__':
    active=bpy.context.view_layer.objects.active
    region=REGION_ID or (active.get('Region_ID') if active else '')
    if not region:raise RuntimeError('Выберите страну, деревянную деталь или гравировку.')
    root=next(o for o in bpy.context.scene.objects if o.get('Role')=='RegionRoot' and o.get('Region_ID')==region)
    name=SOURCE_NAME or ('Южная-Америка-политическая.blend' if root['Вариант']=='relief' else 'Южная-Америка-рельеф-по-странам.blend')
    swap_region(region,Path(bpy.data.filepath).parent/name)
