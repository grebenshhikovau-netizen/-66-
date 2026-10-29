"""Package verified production deliverables, keeping source data in the repository."""
import ast
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

P = Path(__file__).resolve().parent.parent
ARCHIVE = P / 'Евразия-78-деталей-740x740.zip'
MANIFEST = P / 'Контрольные-суммы.json'

for name in (
    'Проверка-раскроя.json', 'Проверка-сохранённого-Blender.json', 'Проверка-выданного-SVG.json', 'Проверка-групп-покраски.json',
    'Проверка-стыков-красных-линий.json', 'Проверка-монтажных-контуров.json',
    'Проверка-полных-монтажных-форм.json', 'Проверка-текста.json',
):
    assert json.loads((P / name).read_text())['passed'], name
for script in (P / 'tools').glob('*.py'):
    ast.parse(script.read_text(), filename=str(script))
source = json.loads((P / 'data/source/source-info.json').read_text())
assert hashlib.sha256((P / 'data/source/Исходная-сборка.blend').read_bytes()).hexdigest() == source['sha256']

files = []
for f in sorted(P.rglob('*')):
    if not f.is_file() or f in (MANIFEST, ARCHIVE):
        continue
    rel = f.relative_to(P)
    if rel.parts[0] in ('tools', 'data') or f.name.startswith('.'):
        continue
    if f.suffix in ('.log', '.blend1', '.pyc') or f.name in ('manufacturing.json', 'requirements.txt'):
        continue
    files.append(f)
manifest = {
    'archive': ARCHIVE.name,
    'original_source': source,
    'wood_parts': len(json.loads((P/'data/production-plan.json').read_text())['pieces']),
    'layer_part_counts': [q['pieces']for q in json.loads((P/'data/production-plan.json').read_text())['summary']],
    'stock_mm': [740, 740],
    'transform': 'translations only',
    'files': [
        {'path': f.relative_to(P).as_posix(), 'bytes': f.stat().st_size,
         'sha256': hashlib.sha256(f.read_bytes()).hexdigest()}
        for f in files
    ],
}
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
with ZipFile(ARCHIVE, 'w', ZIP_DEFLATED, compresslevel=6) as z:
    for f in files + [MANIFEST]:
        z.write(f, f.relative_to(P).as_posix())
with ZipFile(ARCHIVE) as z:
    assert z.testzip() is None
    for row in manifest['files']:
        assert hashlib.sha256(z.read(row['path'])).hexdigest() == row['sha256'], row['path']
print(json.dumps({'archive': ARCHIVE.name, 'files': len(files) + 1,
                  'bytes': ARCHIVE.stat().st_size,
                  'sha256': hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()}, ensure_ascii=False))
