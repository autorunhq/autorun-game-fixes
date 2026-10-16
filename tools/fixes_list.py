"""FIXES.md: every fix and settings profile the index publishes, for people.

tools/build-fixes.py writes it with the index, and tests/check_index.py checks
it is what the index says, so the list is never edited by hand and never out
of date. The README points to it rather than listing games, which it would
have to be edited for every new one."""
import json

REPOSITORY = 'https://github.com/autorunhq/autorun-game-fixes/tree/main'


def cell(text):
    return str(text).replace('|', '\\|').replace('\n', ' ')


def recognised_by(match):
    parts = []
    if match.get('exe'):
        parts.append(', '.join(f'`{name}`' for name in match['exe']))
    if match.get('version'):
        parts.append(', '.join(f'{key} "{value}"' for key, value in match['version'].items()))
    if match.get('timestamp') or match.get('size'):
        parts.append('specific builds only')
    if match.get('files'):
        parts.append('with ' + ', '.join(f'`{name}`' for name in match['files']) + ' beside it')
    return '; '.join(parts)


def render(index):
    fixes = sorted(index.get('fixes', []), key=lambda f: f['title'].lower())
    profiles = sorted(index.get('profiles', []), key=lambda p: p['match'].get('exe', [p['id']])[0].lower())
    lines = [
        '# Game fixes and settings profiles',
        '',
        '<!-- Written by tools/build-fixes.py from switch/wine/game-fixes/index.json. Do not edit. -->',
        '',
        f'What [Autorun](https://github.com/autorunhq/autorun) offers for each game, as published '
        f'(index serial {index.get("serial", 0)}). See the [README](README.md) for how it works and how to add one.',
        '',
        f'## Fixes ({len(fixes)})',
        '',
        'Offered before the game starts. **Required** means the game may not start without its fix.',
        '',
        '| Game | Fix | Version | Required | What it does | Recognised by |',
        '|---|---|---|---|---|---|',
    ]
    for fix in fixes:
        lines.append(f'| {cell(fix["title"])} | [`{fix["id"]}`]({REPOSITORY}/fixes/{fix["id"]}) | {fix["version"]} | '
                     f'{"Yes" if fix.get("required") else "No"} | {cell(fix["summary"])} | '
                     f'{cell(recognised_by(fix["match"]))} |')
    lines += [
        '',
        f'## Settings profiles ({len(profiles)})',
        '',
        "A game's settings screen in Autorun, written to the game's own settings file before it starts. "
        'A game Autorun has a profile built in for uses its built-in one.',
        '',
        '| Game | Profile | Version | Machine | Settings file | Settings |',
        '|---|---|---|---|---|---|',
    ]
    for profile in profiles:
        exe = profile['match'].get('exe', [profile['id']])[0]
        lines.append(f'| {cell(exe)} | [`{profile["id"]}`]({REPOSITORY}/profiles/{profile["id"]}.json) | '
                     f'{profile["version"]} | {profile["machine"]} | `{cell(profile["path"].split("/")[-1])}` | '
                     f'{len(profile["rows"])} |')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    import sys
    print(render(json.load(open(sys.argv[1]))), end='')
