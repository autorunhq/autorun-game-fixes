#!/usr/bin/env python3
"""Build the game fixes: every fixes/<id>/fix.json into the card tree under
switch/wine/game-fixes, with the index Autorun reads.

    tools/build-fixes.py [--autorun PATH]

A fix is what a game needs to start or play well on the Switch that is not
Autorun's to do for every game: registry keys an installer would have written,
a settings file the game's own launcher would have, controls. Autorun's
launcher recognises a game by its executable and files beside it, says a fix
is there, and applies it before the game starts once the player says so.

fix.json, in each fix's folder:

    title     the game's name, as the launcher shows it
    version   a whole number, raised whenever what the fix puts on a card
              changes, so a card that has an earlier one is offered it again
    required  true when the game may not start without the fix
    summary   what it does, in a sentence or three, for the launcher's question
    match     what the game is recognised by; every kind given must match:
              exe: the executable names it is for (any case), any of them;
              version: strings of the executable's version resource, such as
              {"ProductName": "Warcraft III", "OriginalFilename": "war3.exe"},
              compared without case, a * at the end matching any rest -- these
              recognise a renamed executable, and exe may then be left out;
              timestamp: PE link times and size: file sizes, any of them, to
              pin builds; files: paths, relative to the executable's folder,
              that must all be there too ("../TSData" for one folder up).
              When more than one fix matches, the one asking more wins, so a
              fix for one build can stand beside one for every build.
              tools/describe-exe.py prints all of these for an executable
    run       a setup program: source (a C file here, built without a C
              runtime as Autorun's own setups are), exe (its name on the card)
              and libs; the launcher runs it before the game with the game's
              executable as its one argument
    data      more files here, put beside the setup program on the card
    install   files here put somewhere else: file, to and keep. to begins with
              {game} (the executable's folder) or {drive_c}, and may name
              {stem} (the executable's name without .exe); keep leaves a file
              already there alone
    settings  the game's own launcher settings, key to value, as its
              .wine-nx.txt holds them ("d3d": "wine", "cpu": "box64")

Everything is written to switch/wine/game-fixes/<id>/, and the index to
switch/wine/game-fixes/index.json with each file's size and SHA-256. The
index's serial rises with every change, so a card keeps whichever of the
index it downloaded and the one its Autorun build ships is newer.

Setup programs are compiled with Autorun's llvm-mingw, from the Autorun
checkout this repository is a submodule of (--autorun or AUTORUN otherwise).
Committing and pushing is what publishes a fix.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

repo = Path(__file__).resolve().parents[1]
fixes = repo / 'fixes'
out = repo / 'switch/wine/game-fixes'
index_path = out / 'index.json'

# What source/game_fixes.h in Autorun reads; past these a card leaves a fix out.
LIMITS = dict(exe=8, match_files=8, files=16, install=8, settings=16, version=4, builds=8)
ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,30}$')
NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._+-]{0,62}$')
SETTING = re.compile(r'^[a-z0-9][a-z0-9-]{0,30}$')


def fail(fix, message):
    raise SystemExit(f'{fix}: {message}')


def checkout():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--autorun', type=Path, help='the Autorun checkout whose toolchain builds the setups')
    args = parser.parse_args()
    if args.autorun:
        return args.autorun.resolve()
    if os.environ.get('AUTORUN'):
        return Path(os.environ['AUTORUN']).resolve()
    found = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--show-superproject-working-tree'],
                           text=True, stdout=subprocess.PIPE).stdout.strip()
    if not found:
        raise SystemExit('not inside an Autorun checkout; pass --autorun PATH or set AUTORUN')
    return Path(found)


def relative_ok(path, allow_up):
    parts = path.split('/')
    return (path and not path.startswith('/') and '\\' not in path and ':' not in path and
            all(part and part != '.' and (allow_up or part != '..') for part in parts))


def compile_setup(compiler, source, output, libs):
    """One of the small i386 programs a card runs, as Autorun's own setups are built."""
    subprocess.run([str(compiler), '-Os', '-Wall', '-Wextra', '-Werror', '-fno-builtin', '-nostdlib',
                    '-I', str(repo / 'include'), '-Wl,--entry,_start@0', '-Wl,--image-base,0x10000000',
                    '-Wl,--dynamicbase', '-Wl,--no-insert-timestamp', '-o', str(output), str(source),
                    *libs, '-lkernel32', '-lntdll'], check=True)


def read_fix(folder):
    fix = folder.name
    if not ID.match(fix):
        fail(fix, 'a fix folder is named in lowercase letters, digits and dashes')
    spec = json.loads((folder / 'fix.json').read_text())
    known = {'title', 'version', 'required', 'summary', 'match', 'run', 'data', 'install', 'settings'}
    if set(spec) - known:
        fail(fix, f'unknown keys {sorted(set(spec) - known)}')
    title, summary = spec.get('title', ''), spec.get('summary', '')
    if not isinstance(title, str) or not 0 < len(title.encode()) < 96:
        fail(fix, 'title is required, under 96 bytes')
    if not isinstance(summary, str) or not 0 < len(summary.encode()) < 640:
        fail(fix, 'summary is required, under 640 bytes')
    version = spec.get('version')
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        fail(fix, 'version is a whole number from 1')
    if not isinstance(spec.get('required', False), bool):
        fail(fix, 'required is true or false')

    match = spec.get('match') or {}
    exes, marks = match.get('exe', []), match.get('files', [])
    versions = match.get('version', {})
    if set(match) - {'exe', 'files', 'version', 'timestamp', 'size'}:
        fail(fix, 'match has exe, version, timestamp, size and files only')
    if not isinstance(versions, dict) or len(versions) > LIMITS['version'] or not all(
            isinstance(k, str) and 0 < len(k) < 32 and isinstance(v, str) and 0 < len(v.encode()) < 96
            for k, v in versions.items()):
        fail(fix, f'match.version is up to {LIMITS["version"]} "Key": "value" strings')
    for kind in ('timestamp', 'size'):
        values = match.get(kind, [])
        if not isinstance(values, list) or len(values) > LIMITS['builds'] or not all(
                isinstance(v, int) and not isinstance(v, bool) and 0 < v < (2**32 if kind == 'timestamp' else 2**63)
                for v in values):
            fail(fix, f'match.{kind} is up to {LIMITS["builds"]} whole numbers')
    if not exes and not versions:
        fail(fix, 'match names the executable, by exe or version, or every program beside its files would match')
    if len(exes) > LIMITS['exe'] or not all(
            isinstance(e, str) and len(e) < 64 and e.lower().endswith('.exe') and '/' not in e and '\\' not in e
            for e in exes):
        fail(fix, f'match.exe names up to {LIMITS["exe"]} executables')
    if len(marks) > LIMITS['match_files'] or not all(
            isinstance(m, str) and len(m) < 128 and relative_ok(m, True) for m in marks):
        fail(fix, f'match.files names up to {LIMITS["match_files"]} relative paths')

    files = []          # (name, source path or None for the setup, ...)
    run = spec.get('run')
    if run is not None:
        if set(run) - {'source', 'exe', 'libs'} or not NAME.match(run.get('exe', '')) or \
                not run['exe'].lower().endswith('.exe') or not (folder / run.get('source', '')).is_file():
            fail(fix, 'run has a source here, an exe name and libs')
        files.append(run['exe'])
    for name in spec.get('data', []):
        if not NAME.match(name) or not (folder / name).is_file():
            fail(fix, f'data file {name!r} is not here')
        files.append(name)
    install = spec.get('install', [])
    if len(install) > LIMITS['install']:
        fail(fix, f'at most {LIMITS["install"]} install entries')
    for item in install:
        if set(item) - {'file', 'to', 'keep'} or not NAME.match(item.get('file', '')) or \
                not (folder / item['file']).is_file():
            fail(fix, f'install entry {item} names a file here, where to and keep')
        to = item.get('to', '')
        rest = to.split('/', 1)[1] if '/' in to else ''
        if not (to.startswith('{game}/') or to.startswith('{drive_c}/')) or len(to) >= 256 or \
                not relative_ok(rest, False) or re.search(r'\{(?!stem\})', rest):
            fail(fix, f'install to {to!r} begins {{game}}/ or {{drive_c}}/, names only {{stem}} after, no ..')
        if item['file'] not in files:
            files.append(item['file'])
    settings = spec.get('settings', {})
    if len(settings) > LIMITS['settings'] or not all(
            SETTING.match(k) and isinstance(v, str) and len(v) < 64 and '\n' not in v and '\r' not in v
            for k, v in settings.items()):
        fail(fix, f'settings are up to {LIMITS["settings"]} key: "value" pairs')
    if not files and not settings:
        fail(fix, 'a fix runs a setup, puts files on the card or changes settings')
    if len(files) > LIMITS['files']:
        fail(fix, f'at most {LIMITS["files"]} files')
    return spec, files


def main():
    root = checkout()
    compiler = Path(os.environ.get('WINE_NX_LLVM_MINGW',
                                   root / 'horizon-wine/toolchains/llvm-mingw-20260505-ucrt-macos-universal')) \
        / 'bin/i686-w64-mingw32-clang'
    if not compiler.is_file():
        raise SystemExit(f'{compiler} is missing; is {root} an Autorun checkout with its toolchain?')
    old = json.loads(index_path.read_text()) if index_path.is_file() else {'serial': 0, 'fixes': []}
    old_fixes = {f['id']: f for f in old.get('fixes', [])}

    entries = []
    built = set()
    for folder in sorted(p for p in fixes.iterdir() if p.is_dir()):
        spec, files = read_fix(folder)
        fix = folder.name
        target = out / fix
        target.mkdir(parents=True, exist_ok=True)
        run = spec.get('run')
        for name in files:
            if run and name == run['exe']:
                compile_setup(compiler, folder / run['source'], target / name, run.get('libs', []))
            else:
                shutil.copyfile(folder / name, target / name)
            built.add((fix, name))
        entry = {
            'id': fix,
            'title': spec['title'],
            'version': spec['version'],
            'required': spec.get('required', False),
            'summary': spec['summary'],
            'match': {k: spec['match'][k] for k in ('exe', 'version', 'timestamp', 'size', 'files')
                      if spec['match'].get(k)},
        }
        if run:
            entry['run'] = run['exe']
        entry['files'] = [{'name': name, 'size': (target / name).stat().st_size,
                           'sha256': hashlib.sha256((target / name).read_bytes()).hexdigest()} for name in files]
        if spec.get('install'):
            entry['install'] = [{'file': i['file'], 'to': i['to'], 'keep': bool(i.get('keep', False))}
                                for i in spec['install']]
        if spec.get('settings'):
            entry['settings'] = spec['settings']

        # What a card gets from the fix changed: the version has to say so, or
        # a card that applied the earlier one never hears of it.
        previous = old_fixes.get(fix)
        payload = lambda e: (e.get('run'), e.get('files'), e.get('install'), e.get('settings'))
        if previous and payload(previous) != payload(entry) and entry['version'] <= previous['version']:
            fail(fix, f'what it puts on a card changed; raise its version above {previous["version"]}')
        if previous and entry['version'] < previous['version']:
            fail(fix, f'version went down from {previous["version"]}')
        entries.append(entry)

    # Files and fixes no longer here.
    for path in sorted(out.rglob('*'), reverse=True):
        rel = path.relative_to(out).parts
        if path.is_file() and len(rel) == 2 and (rel[0], rel[1]) not in built:
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()

    index = {'schema': 1, 'serial': old.get('serial', 0), 'fixes': entries}
    if index['fixes'] != old.get('fixes'):
        index['serial'] += 1
    out.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=1, ensure_ascii=False) + '\n')
    print(f'{len(entries)} fixes, serial {index["serial"]}: {index_path.relative_to(repo)}')


if __name__ == '__main__':
    sys.exit(main())
