# Game fixes and settings profiles

<!-- Written by tools/build-fixes.py from switch/wine/game-fixes/index.json. Do not edit. -->

What [Autorun](https://github.com/autorunhq/autorun) offers for each game, as published (index serial 4). See the [README](README.md) for how it works and how to add one.

## Fixes (4)

Offered before the game starts. **Required** means the game may not start without its fix.

| Game | Fix | Version | Required | What it does | Recognised by |
|---|---|---|---|---|---|
| Guitar Hero III | [`gh3`](https://github.com/autorunhq/autorun-game-fixes/tree/main/fixes/gh3) | 1 | Yes | Writes the registry key Aspyr's installer writes, without which the game stops at startup; sets its screen to 1280x720 with the crowd and the other CPU-heavy details off; and writes a dxvk.conf that keeps textures out of file mappings. For another language, put en, fr, it, de, es or ko in language.txt in the game's folder. | `GH3.exe`; with `AWL.dll` beside it |
| Halo: Combat Evolved | [`halo`](https://github.com/autorunhq/autorun-game-fixes/tree/main/fixes/halo) | 1 | No | Controls for Halo: the left stick walks with w, a, s and d and the d-pad works the menus with the arrows; X chooses, Y jumps, L is the action key, R reloads, ZL crouches and ZR shows the scores. Kept if the game already has its own controls file. | `halo.exe`; with `Controls` beside it |
| The Sims 2 Ultimate Collection | [`sims2`](https://github.com/autorunhq/autorun-game-fixes/tree/main/fixes/sims2) | 1 | Yes | Writes what the release's "Instalar Registros" batch file writes, with the card's paths: where each pack is, the language, and the keys the retail executables read. Copies a dxvk.conf that holds the game to 512 MB of video memory, and sets Graphics Rules.sgr for the 1280x720 screen. For another language, put its number in language.txt beside the packs. | `Sims2EP9.exe`; with `../TSData` beside it |
| WarCraft III | [`war3`](https://github.com/autorunhq/autorun-game-fixes/tree/main/fixes/war3) | 2 | Yes | Sets the game's video to the Switch's 1280x720 screen, so the pointer and the touchscreen line up; draws with the game's own OpenGL renderer, which takes half the CPU its Direct3D does; and offers only the 1280x720 mode, so the movies fill the width. Start the game through a 36-bit or 39-bit forwarder. | `war3.exe`, `Frozen Throne.exe`; with `Game.dll` beside it |

## Settings profiles (6)

A game's settings screen in Autorun, written to the game's own settings file before it starts. A game Autorun has a profile built in for uses its built-in one.

| Game | Profile | Version | Machine | Settings file | Settings |
|---|---|---|---|---|---|
| Fallout3.exe | [`fallout3`](https://github.com/autorunhq/autorun-game-fixes/tree/main/profiles/fallout3.json) | 1 | x86 | `FalloutPrefs.ini` | 44 |
| Fallout4.exe | [`fallout4`](https://github.com/autorunhq/autorun-game-fixes/tree/main/profiles/fallout4.json) | 1 | x64 | `Fallout4Prefs.ini` | 49 |
| FalloutNV.exe | [`falloutnv`](https://github.com/autorunhq/autorun-game-fixes/tree/main/profiles/falloutnv.json) | 1 | x86 | `FalloutPrefs.ini` | 44 |
| ff7remake_.exe | [`ff7remake`](https://github.com/autorunhq/autorun-game-fixes/tree/main/profiles/ff7remake.json) | 1 | x64 | `Engine.ini` | 14 |
| MOHA.exe | [`moha`](https://github.com/autorunhq/autorun-game-fixes/tree/main/profiles/moha.json) | 1 | x86 | `MOHAAutorun.ini` | 40 |
| Spider-Man Web of Shadows.exe | [`spider-man-web-of-shadows`](https://github.com/autorunhq/autorun-game-fixes/tree/main/profiles/spider-man-web-of-shadows.json) | 1 | x86 | `Config.xml` | 26 |
