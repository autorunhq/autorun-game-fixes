<p align="center">
  <img src="documentation/logo-image.png" alt="Autorun logo" width="220">
</p>

<h1 align="center">Autorun Game Fixes</h1>

<p align="center">
  What each game needs to run well on the Switch, for <a href="https://github.com/autorunhq/autorun">Autorun</a>.<br>
  <sub>Published here, on every console without waiting for an Autorun release.</sub>
</p>

Some Windows games need more than Autorun gives every program before they start
or play well on the Switch: registry keys their installer would have written, a
settings file their own launcher would have made, arguments, controls that suit
a controller. This repository holds those, one game at a time, and Autorun
downloads them by itself.

- **Game fixes** are offered before a game starts. Autorun recognises the game
  by its executable, its version information and the files around it, says what
  the fix does and whether the game may not start without it, and applies it if
  the player says so. A new version is offered again.
- **Settings profiles** are applied without asking: a game's settings screen in
  Autorun, the values written to its own settings file, and the arguments it is
  started with.
- **No release needed.** A fix or profile pushed to `main` reaches every console
  running a current Autorun the next time its launcher opens. Only something
  Autorun doesn't know how to do yet needs a new Autorun.
- **Offline too.** Every Autorun build carries the list it was made with, so an
  offline console still knows a game has a fix and that it needs the internet
  once to download it.
- **No game files.** A fix only sets up the copy of the game the player
  already owns.

## Not a piracy or circumvention tool

A fix sets up a legitimate copy the player owns so that it runs on the Switch.
It never contains a game's files, and it never removes or gets around copy
protection, DRM or license checks.

Some fixes and profiles exist only because of how Autorun works. Autorun runs
Wine as **a single process** on the Switch, one Windows program at a time,
because Horizon gives a homebrew app no way to start a second program next to
itself. A PC game that starts through a launcher (one that detects hardware
and writes a settings file, or a store's front end that starts the game and
waits) would close on the Switch, because the launcher's second program can't
start. So a fix does the launcher's part instead: it writes the settings file
the launcher would have written, or passes the arguments it would have passed.
Autorun's runtime also skips, in memory, the one call a game makes to hand
itself back to its launcher. Nothing else changes.

A launcher that has to **keep running beside the game** (a store's client such
as Steam, the EA app or Ubisoft Connect, which the game keeps asking whether
you own it) is another matter: Autorun can't leave a second process running,
and no fix fakes the store's answer. For such a game a fix sets up everything
else the original copy needs, such as the registry keys its installer writes,
its settings and its paths on the card. Getting it to start without its client
is the player's own decision and responsibility, only for a copy they bought;
this repository doesn't include, link to or support a tool for it.

> **No support for pirated, cracked or modified games.** Fixes are made and
> tested for legitimate, unmodified copies. Pull requests that target a pirated
> release, ship a crack, a no-CD patch or a modified executable, or work around
> a game's protection are closed, and so are issues about such copies.

> **No support for third-party bundles.** Downloads that ship a game already
> packed with Autorun as its environment aren't made by this project, and we
> don't support or endorse them. Fixes are written for a game the player copied
> to the card from their own copy, with Autorun from its
> [releases](https://github.com/autorunhq/autorun/releases), not for a bundle's
> layout, and issues about bundles are closed.

**Without a network:** download this repository (Code › Download ZIP) and copy
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
documentation/             the README's images
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
