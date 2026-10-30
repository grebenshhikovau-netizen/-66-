"""Open every actual stock SVG in Inkscape, preserve live text, and render previews."""
import json, os, subprocess, tempfile, xml.etree.ElementTree as ET
from pathlib import Path

P = Path(__file__).resolve().parent.parent
NS = '{http://www.w3.org/2000/svg}'

def words(path):
    return sorted(''.join(q.itertext()).strip() for q in ET.parse(path).iter(NS+'text'))

for kit in sorted(P.glob('0*')):
    summary = json.loads((kit/'Проверка-раскроя.json').read_text())
    results = []
    with tempfile.TemporaryDirectory(prefix='combined-svg-') as temp:
        for field in range(1, summary['sheets']+1):
            source = kit/f'Поле-{field:02d}-740x740.svg'
            saved = Path(temp)/source.name
            preview = kit/f'Предпросмотр-лист-{field:02d}.png'
            env = dict(os.environ, XDG_CACHE_HOME='/tmp/ru-font-cache')
            with (kit/'inkscape-check.log').open('a') as log:
                subprocess.run(['inkscape', str(source), '--export-plain-svg',
                                '--export-type=svg', f'--export-filename={saved}'],
                               check=True, env=env, stdout=log, stderr=log)
                subprocess.run(['inkscape', str(source), '--export-type=png',
                                '--export-width=1900', '--export-background=white',
                                f'--export-filename={preview}'],
                               check=True, env=env, stdout=log, stderr=log)
            original, reopened = words(source), words(saved)
            assert original == reopened, (source, 'Live text changed in Inkscape')
            results.append({'field': field, 'editable_texts': len(original),
                            'Inkscape_plain_SVG_text_preserved': True})
    expected = json.loads((kit/'data/production-plan.json').read_text())['labels']
    assert sum(q['editable_texts'] for q in results) == len(expected)
    (kit/'Проверка-текста.json').write_text(json.dumps(
        {'passed': True, 'all_texts_editable': True, 'fields': results},
        ensure_ascii=False, indent=2))
    print(kit.name, results, flush=True)
