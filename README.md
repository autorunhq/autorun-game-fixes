# autorun-game-fixes

Per-game fixes for [Autorun](https://github.com/autorunhq/autorun), the Windows
compatibility layer for the Nintendo Switch. Some games need more than Autorun
gives every program before they start or play well on the Switch: registry keys
their installer would have written, a settings file their own launcher would
have made, controls that suit them. Those fixes live here.

Autorun recognises a game in its library from its executable and the files
around it. When a fix exists for that game, the launcher asks before the game
starts, and says when the game may not start without the fix. If the player
accepts, Autorun downloads the fix, checks it, applies it and then starts the
game. When a fix gets a new version, the launcher asks again.

Every Autorun build ships a copy of the index. Even a console that is offline
when a game starts can say that the game has a fix, and that it needs a network
to download it.

**Without a network:** download this repository (Code, Download ZIP) and copy
its `switch` folder to the root of the SD card, merging folders.

## Which games

**[FIXES.md](FIXES.md)** lists every fix and settings profile published here,
with what each does and how its game is recognised. The build writes it from
the index, so it's always current.

## Settings profiles

`profiles/<id>.json` is everything Autorun does for a game without asking,
and the only place it's defined:

- the game's **settings screen** in Autorun, for its own INI or XML file, with
  presets, choices and help text, and the values written before it starts;
- the **arguments** it is started with, each added unless the player already
  gave one like it (Kingdom Hearts' Epic arguments, Shadow of the Tomb
  Raider's `-nolauncher`).

Autorun has no profiles of its own any more: every one is here, and a change
published here reaches every card without an Autorun update. What can't be
data (patches to a game's code as it loads, environment variables) stays
compiled in Autorun.

## Layout

```
fixes/<id>/fix.json        what the fix is for and what it does
fixes/<id>/*.c             a setup program's source, when it has one
fixes/<id>/*               the files it puts on the card
include/fix_game.h         how a setup program reads the game it is run for
common/registry_setup.c    the setup a fix with "registry" gets: applies registry.txt
tools/build-fixes.py       builds fixes/ into switch/
tools/describe-exe.py      what an executable can be matched by
tools/fixes_list.py        writes FIXES.md from the index
FIXES.md                   every fix and profile, for people (written by the build)
AGENTS.md                  everything a fix can do, for agents and contributors
profiles/<id>.json         a game's settings profile
switch/wine/game-fixes/    what a card holds: index.json, and <id>/ for each fix
```

The `switch/` tree has the same layout as the SD card. Autorun reads
`switch/wine/game-fixes/index.json` from the `main` branch and downloads each
fix's files from beside it.

## Adding a fix

1. Run `tools/describe-exe.py` on the game's executable. It prints the
   exe's size, link time and version strings (`ProductName`,
   `OriginalFilename`…) as a `match` to start from.
2. Make `fixes/<id>/fix.json`. The format is described at the top of
   `tools/build-fixes.py`. A game can be matched by several things, and every
   one that is given must hold:
   - `exe`: the executable's file name.
   - `version`: its version strings, which still match when the file is
     renamed. A `*` at the end of a value matches any rest.
   - `timestamp` or `size`: one exact build of the game.
   - `files`: files that must sit beside it.

   When several fixes match, the one that asks more of the game wins. That lets
   a fix for one patch level sit beside a fix for every build.
3. Say what the fix changes, as data where you can:
   - `registry`: values an installer would have written, for example
     `{"key": "HKCU\\Software\\Blizzard Entertainment\\Warcraft III\\Video", "name": "reswidth", "dword": 1280}`.
     The build turns the list into `registry.txt`, with a small generic setup
     program (`common/registry_setup.c`) that applies it inside Wine. `war3`
     is done this way.
   - `game_settings`: values in the game's own INI or XML settings file. The
     launcher writes them with Autorun's game settings engine. A game that
     has a settings profile keeps its profile instead.
   - `install`, to put a file somewhere, and `settings`, for the game's
     launcher settings.

   For anything else, write a setup program in C, as `gh3_setup.c` does. It is built without a C runtime. It
   gets the game's executable as its one argument (`fix_game_folder()` in
   `include/fix_game.h`). It reports each step with `NtDisplayString`, which
   ends up in `autorun_runtime.log`, and exits with 0 when every step worked.
   Running it twice must be harmless.
4. Run `tools/build-fixes.py` from inside an Autorun checkout; its llvm-mingw
   builds the setup programs. Then commit `fixes/` and `switch/` together.
   Pushing to `main` publishes the fix.

Raise a fix's `version` whenever what it puts on a card changes. The build
refuses otherwise, because a card that already applied the earlier version
would never be offered the change.

`tests/check_index.py` checks that the index matches the published files. It
runs on every push.
