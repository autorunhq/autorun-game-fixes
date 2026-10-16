#!/usr/bin/env python3
"""What a fix can match a game's executable by: its name, size, link time and
the strings in its version resource, printed as a fix.json "match" to start
from.

    tools/describe-exe.py GAME.EXE [...]

Autorun reads the same fields (source/game_fixes.c): the version strings from
the US English table first, then any other; the link time from the PE header.
A name alone is matched by any game.exe; ProductName or OriginalFilename say
which game it is even when the file is renamed; the link time or the size pin
one build of it, for a fix that only that build needs.
"""
from pathlib import Path
import json
import struct
import sys

RT_VERSION = 16
KEYS = ('ProductName', 'CompanyName', 'FileDescription', 'OriginalFilename', 'InternalName',
        'FileVersion', 'ProductVersion')


def sections(data, nt):
    count, optional_size = struct.unpack_from('<H', data, nt + 6)[0], struct.unpack_from('<H', data, nt + 20)[0]
    first = nt + 24 + optional_size
    for i in range(count):
        va, raw_size, raw_offset = struct.unpack_from('<III', data, first + i * 40 + 12)
        virtual_size = struct.unpack_from('<I', data, first + i * 40 + 8)[0]
        yield va, raw_offset, min(raw_size, virtual_size) if virtual_size else raw_size


def at_rva(data, nt, rva, size):
    for va, offset, length in sections(data, nt):
        if va <= rva and rva + size <= va + length:
            return data[offset + rva - va:offset + rva - va + size]
    raise ValueError(f'RVA {rva:#x} is in no section')


def resource(data, nt, root_rva, kind):
    """The first resource of this type, whatever its id and language."""
    def entries(dir_rva):
        named, ids = struct.unpack_from('<HH', at_rva(data, nt, root_rva + dir_rva + 12, 4))
        table = at_rva(data, nt, root_rva + dir_rva + 16, (named + ids) * 8)
        return [struct.unpack_from('<II', table, i * 8) for i in range(named + ids)]
    level = [value for name, value in entries(0) if name == kind]
    if not level:
        return None
    for _ in range(2):
        value = level[0]
        if not value & 0x80000000:
            return None
        level = [v for _, v in entries(value & 0x7fffffff)]
        if not level:
            return None
    rva, size = struct.unpack_from('<II', at_rva(data, nt, root_rva + level[0], 8))
    return at_rva(data, nt, rva, size)


def version_strings(block):
    """StringFileInfo's tables: {language: {key: value}}."""
    def blocks(data, start, end):
        while start + 6 <= end:
            length, value_length, kind = struct.unpack_from('<HHH', data, start)
            if length < 6:
                return
            key_end = start + 6
            while key_end + 1 < start + length and data[key_end:key_end + 2] != b'\0\0':
                key_end += 2
            key = data[start + 6:key_end].decode('utf-16-le')
            value_start = (key_end + 2 + 3) & ~3
            yield key, data, value_start, value_length, kind, start + length
            start = (start + length + 3) & ~3

    tables = {}
    for key, data, value, value_length, _, end in blocks(block, 0, len(block)):
        children = (value + value_length + 3) & ~3
        for info, _, info_value, _, _, info_end in blocks(block, children, end):
            if info != 'StringFileInfo':
                continue
            for language, _, table_value, _, _, table_end in blocks(block, info_value, info_end):
                strings = tables.setdefault(language, {})
                for name, _, string_value, length, _, _ in blocks(block, table_value, table_end):
                    text = block[string_value:string_value + length * 2].decode('utf-16-le', 'replace')
                    strings[name] = text.split('\0')[0].strip()
    return tables


def describe(path):
    data = Path(path).read_bytes()
    if data[:2] != b'MZ':
        raise SystemExit(f'{path}: not a Windows executable')
    nt = struct.unpack_from('<I', data, 0x3c)[0]
    if data[nt:nt + 4] != b'PE\0\0':
        raise SystemExit(f'{path}: not a PE image')
    timestamp = struct.unpack_from('<I', data, nt + 8)[0]
    magic = struct.unpack_from('<H', data, nt + 24)[0]
    directories = nt + 24 + (96 if magic == 0x10b else 112)
    resource_rva = struct.unpack_from('<I', data, directories + 2 * 8)[0]
    tables = {}
    if resource_rva:
        block = resource(data, nt, resource_rva, RT_VERSION)
        if block:
            tables = version_strings(block)
    strings = {}
    for language in sorted(tables, key=lambda language: not language.lower().startswith('0409')):
        for key, value in tables[language].items():
            strings.setdefault(key, value)

    print(f'{path}: {len(data)} bytes, linked {timestamp} (0x{timestamp:08x})')
    for key in KEYS:
        if strings.get(key):
            print(f'  {key}: {strings[key]}')
    match = {'exe': [Path(path).name]}
    picked = {k: strings[k] for k in ('ProductName', 'OriginalFilename') if strings.get(k)}
    if picked:
        match['version'] = picked
    print('  "match":', json.dumps(match, ensure_ascii=False))
    print(f'  this build only: "timestamp": [{timestamp}] or "size": [{len(data)}]')


for name in sys.argv[1:] or sys.exit(__doc__):
    describe(name)
