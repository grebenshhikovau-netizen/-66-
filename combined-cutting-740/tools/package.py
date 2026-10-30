"""Package only reviewed manufacturing deliverables; verify archive payload hashes."""
import ast, gzip, hashlib, json, zipfile
from pathlib import Path

P = Path(__file__).resolve().parent.parent
SHA = lambda b: hashlib.sha256(b).hexdigest()
S = json.loads((P/'data/final-summary.json').read_text())

for src in json.loads((P/'data/source/sources.json').read_text()):
    b = gzip.decompress((P/f"data/source/{src['family']}-approved-plan.json.gz").read_bytes())
    assert SHA(b) == src['plan_sha256'] and len(b) == src['bytes']
for path in P.rglob('*.py'):
    ast.parse(path.read_text(), filename=str(path))

def allowed(f, kit):
    rel = f.relative_to(kit)
    return (f.is_file() and not any(x in ['data', 'tools', '__pycache__'] for x in rel.parts)
            and not f.name.startswith('.') and f.suffix not in ['.log', '.blend1', '.zip', '.pyc']
            and f.name not in ['manufacturing.json', 'requirements.txt', 'Контрольные-суммы.json',
                               'Проверка-планирования.json']
            and not (len(rel.parts) == 1 and f.name.startswith('Поле-')))

def manifest(files, root):
    return {str(f.relative_to(root)): {'bytes': f.stat().st_size, 'sha256': SHA(f.read_bytes())}
            for f in sorted(files)}

def archive(path, files, root):
    entries = manifest(files, root)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in files:
            z.write(f, str(f.relative_to(root)))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert set(z.namelist()) == set(entries)
        for name, expected in entries.items():
            b = z.read(name)
            assert SHA(b) == expected['sha256'] and len(b) == expected['bytes']
    print('ARCHIVE VERIFIED', path.name, round(path.stat().st_size/1e6, 2), 'MB', len(files), flush=True)

full_files = []
for s in S:
    kit = P/s['directory']
    D = json.loads((kit/'data/production-plan.json').read_text())
    for name in ['Проверка-раскроя.json', 'Проверка-стыков-красных-линий.json',
                 'Проверка-сохранённого-Blender.json', 'Проверка-речных-перемычек.json',
                 'Проверка-физического-объединения.json', 'Проверка-текста.json']:
        assert json.loads((kit/name).read_text())['passed'], (kit.name, name)
    native = json.loads((kit/'Проверка-сохранённого-Blender.json').read_text())
    assert native['wood_parts'] == len(D['pieces']) == s['parts']
    assert 'RENDERS COMPLETE' in (kit/'render.log').read_text()
    for i in range(1, s['sheets']+1):
        for ext in ['svg', 'pdf']:
            assert (kit/f'Поле-{i:02d}-740x740.{ext}').read_bytes() == (kit/f"{s['prefix']}-лист-{i:02d}-740x740.{ext}").read_bytes()
        assert (kit/f'Предпросмотр-лист-{i:02d}.png').stat().st_size > 1000
    files = [f for f in kit.rglob('*') if allowed(f, kit)]
    checksum = kit/'Контрольные-суммы.json'
    checksum.write_text(json.dumps({'files': manifest(files, kit)}, ensure_ascii=False, indent=2))
    files.append(checksum)
    archive(P/f"{s['prefix']}-740x740.zip", files, kit)
    full_files.extend(files)

full_files.append(P/'README.md')
checksum = P/'Контрольные-суммы.json'
checksum.write_text(json.dumps({'files': manifest(full_files, P)}, ensure_ascii=False, indent=2))
full_files.append(checksum)
archive(P/'Общие-слои-два-комплекта-740x740.zip', full_files, P)
