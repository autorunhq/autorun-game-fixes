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

## Fixes

| Fix | Game | What it does |
|---|---|---|
| `war3` | WarCraft III | 1280x720 video settings, the game's own OpenGL renderer, the movies at full width |
| `sims2` | The Sims 2 Ultimate Collection | The release's registry keys with the card's paths, a DXVK memory limit, Graphics Rules at 1280x720 |
| `gh3` | Guitar Hero III | Aspyr's registry key, 1280x720 with the CPU-heavy details off, DXVK's texture memory |
| `falloutnv` | Fallout: New Vegas | The FalloutPrefs.ini its launcher would write, so the game does not hand itself over to that launcher |
| `halo` | Halo: Combat Evolved | Controls: WASD on the left stick, the arrows on the d-pad |

## Layout

```
fixes/<id>/fix.json        what the fix is for and what it does
fixes/<id>/*.c             a setup program's source, when it has one
fixes/<id>/*               the files it puts on the card
include/fix_game.h         how a setup program reads the game it is run for
tools/build-fixes.py       builds fixes/ into switch/
switch/wine/game-fixes/    what a card holds: index.json, and <id>/ for each fix
```

The `switch/` tree has the same layout as the SD card. Autorun reads
`switch/wine/game-fixes/index.json` from the `main` branch and downloads each
fix's files from beside it.

## Adding a fix

1. Make `fixes/<id>/fix.json`. The format is described at the top of
   `tools/build-fixes.py`. A game is matched by executable name plus files that
   must sit beside it, so a fix is not offered to an unrelated `game.exe`.
2. For anything a file copy or a launcher setting cannot do, write a setup
   program in C, as `war3_setup.c` does. It is built without a C runtime. It
   gets the game's executable as its one argument (`fix_game_folder()` in
   `include/fix_game.h`). It reports each step with `NtDisplayString`, which
   ends up in `autorun_runtime.log`, and exits with 0 when every step worked.
   Running it twice must be harmless.
3. Run `tools/build-fixes.py` from inside an Autorun checkout; its llvm-mingw
   builds the setup programs. Then commit `fixes/` and `switch/` together.
   Pushing to `main` publishes the fix.

Raise a fix's `version` whenever what it puts on a card changes. The build
refuses otherwise, because a card that already applied the earlier version
would never be offered the change.

`tests/check_index.py` checks that the index matches the published files. It
runs on every push.
