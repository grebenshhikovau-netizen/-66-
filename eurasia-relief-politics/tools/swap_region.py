"""Run inside Blender with any part of the desired region selected."""
import bpy
from pathlib import Path
import tempfile,shutil
from contextlib import ExitStack

# Leave empty to switch between the two principal variants in the same folder.
# For an LED-compatible flat insert use: Евразия-политическая-с-водой.blend
SOURCE_NAME = ''
REGION_ID = ''

def swap_region(region_id,source_path):
    scene=bpy.context.scene
    def descendants(root):
        for child in root.children:
            yield child
            yield from descendants(child)
    old=next((c for c in descendants(scene.collection) if c.get('Region_ID')==region_id),None)
    if old is None:raise RuntimeError('Политическая часть не найдена: '+region_id)
    oldroot=next(o for o in old.objects if o.get('Role')=='RegionRoot')
    country=oldroot['Country_ID'];pose=oldroot.matrix_world.copy();parent=oldroot.parent
    source_path=Path(source_path)
    if not source_path.is_file():raise RuntimeError('Положите рядом исходный файл: '+source_path.name)
    # Blender's library loader can crash when appending from the file currently
    # open in this session. A temporary byte copy avoids that self-load path.
    with ExitStack() as stack:
        library_path=source_path
        if source_path.resolve()==Path(bpy.data.filepath).resolve():
            temporary=Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='eurasia-append-')))
            library_path=temporary/'source.blend';shutil.copyfile(source_path,library_path)
        with bpy.data.libraries.load(str(library_path),link=False) as (available,target):
            wanted=[n for n in available.collections if n.startswith('REG_'+region_id+'__')]
            if len(wanted)!=1:raise RuntimeError('В исходном файле нет однозначной части '+region_id)
            target.collections=wanted
    new=target.collections[0]
    destination=next((c for c in descendants(scene.collection) if old.name in c.children),scene.collection)
    destination.children.link(new)
    newroot=next(o for o in new.objects if o.get('Role')=='RegionRoot')
    appended_parent=newroot.parent;newroot.parent=parent;newroot.matrix_world=pose
    # Parent controllers are shared between region collections. Keep the existing
    # controller instead of adding another country-wide pivot at the same place.
    if appended_parent is not None and appended_parent is not parent:
        for c in list(appended_parent.users_collection):c.objects.unlink(appended_parent)
        if appended_parent.users==0:bpy.data.objects.remove(appended_parent)
    if parent is not None and parent.name not in new.objects:new.objects.link(parent)
    existing_material=next((m for m in bpy.data.materials if m.get('Country_ID')==country and m.name.startswith('ПОКРЫТИЕ_') and not m.name.endswith('.001')),None)
    if existing_material:
        for ob in new.objects:
            if ob.get('Role')=='PlywoodPiece' and ob.data.materials:
                ob.data.materials[0]=existing_material
    for o in list(old.all_objects):
        if o.get('Role')!='CountryRoot':bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.collections.remove(old)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT');newroot.select_set(True);bpy.context.view_layer.objects.active=newroot
    print('Заменена часть',region_id,'из',source_path.name,flush=True)
    return newroot

if __name__=='__main__':
    active=bpy.context.view_layer.objects.active
    region=REGION_ID or (active.get('Region_ID') if active else '')
    if not region:raise RuntimeError('Выберите деталь или контейнер нужной страны / провинции.')
    root=next(o for o in bpy.context.scene.objects if o.get('Role')=='RegionRoot' and o.get('Region_ID')==region)
    source_name=SOURCE_NAME or ('Евразия-политическая.blend' if root.get('Вариант')=='relief' else 'Евразия-рельеф-по-регионам.blend')
    swap_region(region,Path(bpy.data.filepath).parent/source_name)
