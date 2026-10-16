# AGENTS.md: everything a game fix can do

This file is for agents (and people) writing or changing fixes in this
repository. It lists every field, what Autorun does with it, the limits, and
what a fix cannot do. [README.md](README.md) is the short introduction;
[FIXES.md](FIXES.md) lists what is published (it is generated, never edit it).

## The rule before everything else

A fix only **sets up a copy of the game the player already owns**. Never add a
game's files, its executables, DLLs or data, a cracked or modified executable,
or anything else the repository has no right to share. Codecs, runtimes and
other third-party files are only shipped when their license allows it: a fix
can register or point to a file the player supplies, as `sims2` does with the
VP6 codec, instead of shipping it.

## How Autorun uses this repository

- The **index** is `switch/wine/game-fixes/index.json`, read from
  `https://raw.githubusercontent.com/autorunhq/autorun-game-fixes/main/switch/wine/game-fixes/index.json`.
  Each fix's files are downloaded from beside it: `switch/wine/game-fixes/<id>/<file>`.
- Every Autorun build ships the index it was built with, as
  `sdmc:/switch/wine/game-fixes/bundled.json`. The launcher downloads the
  published one in the background at every start and keeps it as `index.json`
  when its **serial** is higher. Whichever of the two has the higher serial is
  used, so an offline card still knows which games have a fix.
- When a game in the library **matches** a fix, the launcher asks before it
  starts: Apply fix, Start without, Don't ask again, or Cancel. `required`
  changes the wording to "Without this fix the game may not start".
- **Applying** means: download the fix's files (each checked against the
  index's size and SHA-256), copy `install` files, write `game_settings` values,
  write `settings` into the game's launcher settings and, if the fix has a
  setup program, run it **before the game** (the game is queued behind it in
  `run-next.txt`). The setup gets the game's executable as its only argument.
- What a game has had is kept in its launcher settings file
  (`<game>.wine-nx.txt` beside the executable, or under
  `program-settings/` for USB games): `game-fix=<id> <version> <exit code>`,
  and `game-fix-skip=<id> <version>` for Don't ask again.
- A **newer `version`** is offered again as an update. A setup that exits
  non-zero is recorded as "A step failed" and offered again.
- A game started from a **HOME menu shortcut** bypasses the launcher. If it has
  a `required` fix it hasn't had, Autorun opens the launcher with a message
  instead of starting it.
- Logs: `sdmc:/switch/wine/logs/autorun_runtime.log`, lines starting with
  `[FIXES]`, `[FIX REGISTRY]`, or the setup's own prefix.

Autorun's side lives in the Autorun repository:
`horizon-wine/source/game_fixes.c` (index, matching, applying),
`horizon-wine/source/launcher_fixes.c` (the question, downloads),
`horizon-wine/source/game_settings.c` (the settings engine profiles use), and
`horizon-wine/tests/check-game-fixes.sh` (the host tests).

## Layout

```
fixes/<id>/fix.json        one fix (the folder name is its id)
fixes/<id>/*               its setup source and files
profiles/<id>.json         one settings profile
common/registry_setup.c    the generic setup used by every fix with "registry"
include/fix_game.h         command-line helpers for setup programs
tools/build-fixes.py       builds fixes/ and profiles/ into switch/ and FIXES.md
tools/describe-exe.py      prints what an executable can be matched by
tools/fixes_list.py        renders FIXES.md
tests/check_index.py       CI: the index matches the files, FIXES.md is current
switch/wine/game-fixes/    the built output, laid out as on the SD card
```

## fix.json

The folder name is the fix's id: lowercase letters, digits and dashes, at
most 31 characters. Unknown fields are refused by the build, and an Autorun
build that doesn't know a field **leaves the whole fix out** rather than apply
part of it, so new fields are safe for old builds.

| Field | Required | Type and limits |
|---|---|---|
| `title` | yes | string, under 96 bytes. The game's name as the launcher shows it |
| `version` | yes | integer from 1. Raise it whenever what the fix puts on a card changes |
| `required` | no | `true` when the game may not start without the fix |
| `summary` | yes | string, under 640 bytes. Shown in the question: say what it does, plainly |
| `match` | yes | how the game is recognised, below |
| `run` | no | a setup program written in C, below. Not together with `registry` |
| `data` | no | files from the fix's folder, put beside the setup on the card |
| `install` | no | up to 8 files put in place on the card |
| `settings` | no | up to 16 launcher settings for the game |
| `registry` | no | up to 64 registry edits. Not together with `run` |
| `game_settings` | no | values for the game's own INI or XML file |

A fix must do something: a setup, a file, a setting or `game_settings`. A fix
can have at most 16 files in all.

### match

Every kind given must hold. A fix must name the executable, by `exe` or
`version`, or it would match every program in a folder.

| Key | Meaning |
|---|---|
| `exe` | up to 8 executable names, ignoring case; any of them |
| `version` | up to 4 version-resource strings, `{"ProductName": "...", "OriginalFilename": "..."}`. Keys and values ignore case; a value ending in `*` matches any rest (`"FileVersion": "1.26*"`). Still matches when the file is renamed |
| `timestamp` | up to 8 PE link times (decimal); any of them. Pins builds |
| `size` | up to 8 file sizes in bytes; any of them. Pins builds |
| `files` | up to 8 paths relative to the executable's folder that must exist, files or folders; `..` goes up (`"../TSData"`) |

When more than one fix matches, the one asking more wins: `exe` scores 1,
each file 1, each version string 2, `timestamp` 4, `size` 4. So a fix for one
patch level beats a fix for every build of the same game.

Run `python3 tools/describe-exe.py GAME.EXE` to get the name, size, link time
and version strings, and a `match` to start from.

### registry

Values an installer would have written. The build writes them to
`registry.txt` and makes `common/registry_setup.c` the fix's setup
(`autorun-registry.exe`), which applies them inside Wine with the Win32
registry calls before the game starts.

```json
"registry": [
  { "key": "HKCU\\Software\\Vendor\\Game\\Video", "name": "Width", "dword": 1280 },
  { "key": "HKLM\\Software\\Vendor\\Game", "name": "InstallPath", "string": "{game}\\" },
  { "key": "HKCU\\Software\\Vendor\\Game", "name": "SeenIntro", "delete": true },
  { "key": "HKLM\\Software\\Vendor\\Game64", "name": "Path", "string": "{game}", "view": 64 }
]
```

- `key` starts `HKCU\` or `HKLM\`. `name` may be `""` for the key's default value.
- Exactly one of `string` (under 1000 characters, no tabs or newlines),
  `dword` (0 to 4294967295) or `delete: true`. Deleting a value that isn't
  there counts as done.
- `view`: `32` (the default) or `64`, the side of a 64-bit registry the game
  reads. `HKLM\Software` differs between the two; a 32-bit game reads the
  32-bit side.
- `{game}` in a string is the game's folder as Windows sees it, such as
  `C:\WarCraft III`; at the root of a drive `{game}\` stays `C:\`.

### install

```json
"install": [
  { "file": "HALO.keys.txt", "to": "{game}/{stem}.keys.txt", "keep": true },
  { "file": "Prefs.ini", "to": "{drive_c}/users/steamuser/Documents/My Games/Game/Prefs.ini", "keep": true }
]
```

- `file` is a file in the fix's folder (letters, digits, `.`, `_`, `-`, `+`).
- `to` starts with `{game}/` (the executable's folder on the card) or
  `{drive_c}/` (`sdmc:/switch/wine/drive_c`), and may use `{stem}` (the
  executable's name without `.exe`). No `..`, under 256 bytes. Folders are made.
- `keep: true` leaves a file that is already there alone: use it for anything
  the player may have changed.
- The Windows user is `steamuser`: `C:\users\steamuser\Documents`,
  `AppData\Local`, `AppData\Roaming`, `Saved Games` and so on.

### settings

The game's own launcher settings, written into its `<game>.wine-nx.txt`
exactly as the launcher writes them.

| Key | Values |
|---|---|
| `d3d` | `wine` (Wine's Direct3D), `dxvk+vkd3d` (adds VKD3D for Direct3D 12); absent is DXVK |
| `dxvk-source` | `sarek`, `gplasync`; absent is the official DXVK |
| `dxvk-version`, `vkd3d-version` | a release version |
| `dxvk-hud` | `fps`, `api,fps,frametimes`, ... |
| `cpu` | `box64` (absent is FEX) |
| `sync` | `horizon` (Horizon synchronization) |
| `four-cores` | `0` to keep graphics workers off core 3 |
| `windows` | `framebuffer` or `compositor` |
| `frame-limit` | `30`, `40`, `45`, `60`, `75`, `90`, `120` |
| `vsync` | `0` to turn it off |
| `upscaling` | `fsr`, `integer` |
| `lsfg` | `1` for frame generation (the player needs Lossless.dll) |
| `lazy-file-views` | `1` for Fast file loading: large read-only file views read on demand |

Keys are lowercase letters, digits and dashes; values under 64 characters.
The launcher's setting names change with Autorun: check
`horizon-wine/source/launcher_settings.h` before using a key not listed here.

### game_settings

Values in the game's own settings file, written by the launcher with Autorun's
settings engine every time the fix is applied, so a newer version of the fix
reaches a file an older one set.

```json
"game_settings": {
  "path": "{drive_c}/users/steamuser/Documents/My Games/Game/Game.ini",
  "format": "ini",
  "initial_text": "[Display]\r\niAdapter=0\r\n",
  "rows": [
    { "section": "Display", "key": "iSize W", "initial": "1280" },
    { "section": "Display", "key": "iSize H", "initial": "720" }
  ]
}
```

- `path` as `install`'s `to`. `format` is `ini` (the default) or `xml`.
- `initial_text` is the file's content when it doesn't exist yet (under 4000 bytes).
- 1 to 32 `rows`, each with `section`, `key` and `initial` (under 64 characters each).
- UTF-16 files are refused by the engine. The engine also adds an `[Autorun]`
  section with `SettingsApplied=1` to the file.
- **A game with a settings profile keeps it:** a fix's
  `game_settings` is skipped for that game, so one file never has two sources.
  For a game that needs a settings *screen*, write a profile instead.

### run: a setup program

For what data can't say: finding files, editing a file's contents, choices
that depend on what's on the card. See `fixes/gh3/gh3_setup.c` and
`fixes/sims2/sims2_setup.c`.

```json
"run": { "source": "game_setup.c", "exe": "game-setup.exe", "libs": ["-ladvapi32"] },
"data": ["dxvk.conf"]
```

- C, built by `tools/build-fixes.py` with Autorun's llvm-mingw as an **i386
  program without a C runtime** (`-nostdlib`, entry `start`). Provide `memset`
  and `memcpy`; keep big buffers `static` (there is no stack probe); use Win32
  only from `kernel32`, `ntdll` and whatever `libs` names (`-ladvapi32`
  registry, `-lshell32`, `-lole32`).
- The game's executable is the only argument: `fix_game_folder()` and
  `fix_game_executable()` in `include/fix_game.h`. Without one (run by hand),
  fall back to the program's own folder.
- `data` files sit beside the program on the card: find them with
  `GetModuleFileNameW`.
- Report every step with `NtDisplayString`, in one line, plain ASCII, with your
  own prefix (`[GAME SETUP] set Width: ok`); it lands in `autorun_runtime.log`.
- Exit 0 when every step worked. Anything else shows as "A step failed" and the
  fix is offered again.
- **Running twice must be harmless**: it runs again on every update and every
  re-apply. Keep a player's own files (check before overwriting), and back up
  a file you edit once (`Name.original`).
- `run` and `registry` don't mix: a fix with its own setup writes its keys itself.

## Settings profiles: profiles/<id>.json

A game's settings screen in the launcher (presets, choices, help), the values
written to its settings file before it starts, and the arguments it starts
with. Unlike a fix, a profile is **not asked about**. Autorun has no profiles
of its own: every game's comes from here, through the card's index, so a
broken profile breaks that game for every player. Test it.

```json
{
  "version": 1,
  "match": { "exe": ["Game.exe"] },
  "machine": "x86",
  "path": "{drive_c}/users/steamuser/Documents/My Games/Game/Game.ini",
  "format": "ini",
  "initial_text": "[Display]\r\n",
  "presets": ["Low", "Medium", "High", "Ultra"],
  "arguments": "-nolauncher",
  "rows": [
    { "section": "Display", "key": "iSize W", "key2": "iSize H", "label": "Resolution",
      "type": "resolution", "initial": "1280x720",
      "choices": [ { "label": "1280 x 720", "value": "1280x720" } ],
      "help": "The game's resolution." },
    { "section": "Display", "key": "bDrawShadows", "label": "Shadows", "type": "integer",
      "presets": ["0", "1", "1", "1"],
      "choices": [ { "label": "Disabled", "value": "0" }, { "label": "Enabled", "value": "1" } ] }
  ]
}
```

- `machine`: `x86` or `x64`, the executable's. `path` must be under `{drive_c}/`.
- `presets`: up to 4 names; each row's `presets` gives that row's value for
  each (`null` leaves it alone). The first preset is applied once to a new file.
- Row `type`: `text`, `integer`, `number`, `resolution` (needs `key2`, value
  `WIDTHxHEIGHT`) or `d3d_api` (`11` or `12`, which also picks DXVK or VKD3D).
- `choices`: up to 256, `{ "label", "value" }`; a `null` value is "game default".
- `section` is required for INI and absent for XML.
- `pending_resolution`: two keys set to 0 when the resolution changes (XML games).
- `arguments`: one string appended to the game's command line when it starts.
- `add_arguments`: up to 16 `{ "unless": "-key=", "add": "-key=value" }`, each
  added unless the command line already has an argument beginning with
  `unless` (ignoring case and quotes), all of them or none when they don't fit.
  Use it for arguments a player may want to override.
- **A profile of arguments alone** has no `path` and no `rows`: it adds
  arguments and shows no settings screen, as `sottr` and the Kingdom Hearts
  profiles do. A profile with a `path` needs `rows`, and the other way round.
- `update`: the name of a compiled hook in Autorun's `game_settings.c`
  (`game_settings_update_hook`); today only `ff7remake`. A profile naming a
  hook the build lacks is left out.
- Up to 62 rows; labels under 96 characters, help under 256.

Autorun's host tests run its settings engine, and the Kingdom Hearts and Tomb
Raider arguments, against this checkout's profiles
(`horizon-wine/tests/check-game-fixes.sh`): change a profile those tests
cover, and run them.

## Recipes

| Problem | Fix |
|---|---|
| The game says it isn't installed, or asks for its install path | `registry`, with the key its installer writes (check the installer, or the game's imports and strings) |
| The game starts its own launcher and closes | a settings file the launcher would have written (`install` or `game_settings`), or a profile's `arguments` such as `-nolauncher` |
| Wrong or unsupported resolution at start | `game_settings` or a `registry` value for 1280x720 |
| Wine should use a native DLL | `registry`: `HKCU\Software\Wine\AppDefaults\<game>.exe\DllOverrides`, name the DLL, string `native,builtin` |
| Wine should offer only the screen's mode | `registry`: `HKCU\Software\Wine\AppDefaults\<game>.exe\X11 Driver`, `EmulateModelist` = `Y` (as `war3`) |
| DXVK needs an option | `install` a `dxvk.conf` to `{game}/dxvk.conf` with `keep: true` |
| Controls for a controller | `install` `{game}/{stem}.keys.txt` with `keep: true` (format: Autorun's `config/keys.txt`) |
| Arguments the game always needs | a profile's `add_arguments` (each added unless the player gave one), or `arguments` |
| Box64 options | `install` `{game}/{stem}.box64.txt` with `keep: true` |
| Different renderer or translator | `settings`: `d3d`, `cpu`, `dxvk-source` |
| Slow loading from huge data files | `settings`: `"lazy-file-views": "1"` |

## What a fix cannot do

- **Patch the game's code.** Autorun's in-memory patches (`*_startup.h` in
  Autorun's `horizon-wine/source`, such as the ones skipping GTA IV's or
  Fallout's launcher) are compiled into the runtime and reviewed with it.
  Propose one to Autorun instead.
- **Set environment variables** or Wine's own runtime switches, other than
  through `settings`. Left 4 Dead's Steam variables are compiled in Autorun
  for that reason.
- **Run code outside Wine**, or on the card before the launcher.
- **Change Autorun's behaviour for every game.** A fix applies to the games
  it matches.
- **Ship what isn't yours to ship** (see the rule at the top).

## Workflow

1. Recognise the game: `python3 tools/describe-exe.py GAME.EXE`.
2. Write `fixes/<id>/fix.json` (or `profiles/<id>.json`), as data where you can.
3. Build from inside an Autorun checkout, whose toolchain builds setups:
   `python3 tools/build-fixes.py` (or `--autorun PATH`). It validates every
   field, compiles setups, writes `registry.txt`, the index and `FIXES.md`.
4. Check: `python3 tests/check_index.py` (what CI runs). In Autorun,
   `horizon-wine/tests/check-game-fixes.sh` runs the host tests against this
   checkout.
5. Test a setup or registry edits under Wine on a computer, before a Switch:
   `WINEPREFIX=/tmp/pfx wine switch/wine/game-fixes/<id>/autorun-registry.exe 'C:\Game\game.exe'`,
   then `wine reg query ...`. Then on a Switch, with the game.
6. Commit `fixes/` or `profiles/`, `switch/` and `FIXES.md` **together**, and
   open a pull request. Pushing to `main` publishes to every card.

## Versions, serials, compatibility

- Raise a fix's or profile's `version` whenever what it puts on a card changes.
  The build refuses otherwise: a card that applied the earlier version would
  never hear of the change. Text-only changes (`title`, `summary`) don't need
  a new version.
- Never edit `serial` by hand: the build raises it when anything published changes.
- Removing a fix: delete its folder and rebuild. Cards that applied it keep
  what it did.
- New fields need an Autorun that understands them. Old builds leave such a
  fix out instead of applying part of it, so add a field to Autorun first and
  use it here once that build is out.

## Pitfalls

- Commit with the project's identity. Check `git config user.name` and
  `git config user.email` in this checkout before your first commit; a new
  clone takes your global identity, which is public once pushed.
- Don't edit files under `switch/` or `FIXES.md` by hand: the build writes them,
  and CI fails when they disagree with the index.
- JSON strings need `\\` for a registry key's backslashes.
- `HKLM\Software` from a 32-bit game is the 32-bit view (`view` 32, the
  default); a 64-bit game needs `view` 64.
- INI files from Windows games are usually CRLF: write `initial_text` with `\r\n`.
- A setup runs with no C runtime: no `printf`, `malloc` or `strlen` unless you
  write them.
