#!/usr/bin/env python3
"""The published index against what is published: every file it names is in
switch/wine/game-fixes/<id>/ at its size and SHA-256, nothing else is there,
and every fix in fixes/ is in it at the version its fix.json gives. Needs no
toolchain, so it runs on every push; tools/build-fixes.py is what makes it so."""
from pathlib import Path
import hashlib
import json

repo = Path(__file__).resolve().parents[1]
out = repo / 'switch/wine/game-fixes'
index = json.loads((out / 'index.json').read_text())
assert index['schema'] == 1 and index['serial'] >= 1, 'index schema 1 with a serial'

listed = set()
for fix in index['fixes']:
    spec = json.loads((repo / 'fixes' / fix['id'] / 'fix.json').read_text())
    assert spec['version'] == fix['version'] and spec['title'] == fix['title'], \
        f'{fix["id"]}: fix.json and the index differ; run tools/build-fixes.py'
    for f in fix['files']:
        path = out / fix['id'] / f['name']
        data = path.read_bytes()
        assert len(data) == f['size'] and hashlib.sha256(data).hexdigest() == f['sha256'], \
            f'{path.relative_to(repo)} is not what the index says; run tools/build-fixes.py'
        listed.add(path)
    if 'run' in fix:
        assert any(f['name'] == fix['run'] for f in fix['files']), f'{fix["id"]}: runs a file it does not list'
    for item in fix.get('install', []):
        assert any(f['name'] == item['file'] for f in fix['files']), f'{fix["id"]}: installs a file it does not list'

fixes = {p.name for p in (repo / 'fixes').iterdir() if (p / 'fix.json').is_file()}
assert fixes == {f['id'] for f in index['fixes']}, f'fixes not in the index: {fixes ^ {f["id"] for f in index["fixes"]}}'
stray = {p for p in out.rglob('*') if p.is_file() and p.name != 'index.json'} - listed
assert not stray, f'files the index does not name: {sorted(str(p.relative_to(repo)) for p in stray)}'
print(f'index serial {index["serial"]}: {len(index["fixes"])} fixes, {len(listed)} files, all as listed')
