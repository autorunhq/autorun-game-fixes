/* The game a fix is run for.
 *
 * Autorun's launcher starts a fix's setup program with the game's executable
 * as its one argument -- "C:\WarCraft III\war3.exe", quoted as a Windows
 * command line quotes a path -- and the setup works on that game wherever the
 * card keeps it. Run by hand, with no argument, a setup falls back to its own
 * folder, which is where the earlier releases told players to put it.
 *
 * Built without a C runtime, as the setups are: GetCommandLineW is all there
 * is to read. */
#ifndef AUTORUN_FIX_GAME_H
#define AUTORUN_FIX_GAME_H

#include <windows.h>

/* The executable named on the command line, without quotes; FALSE when there
 * is none. Only the first argument after the program's own name is read. */
static inline BOOL fix_game_executable( WCHAR *out, unsigned int max )
{
    const WCHAR *p = GetCommandLineW();
    unsigned int n = 0;
    WCHAR close;

    if (!p || !max) return FALSE;
    /* The program's own name: quoted, or up to the first space. */
    if (*p == '"') { p++; while (*p && *p != '"') p++; if (*p) p++; }
    else while (*p && *p != ' ' && *p != '\t') p++;
    while (*p == ' ' || *p == '\t') p++;
    if (!*p) return FALSE;
    close = *p == '"' ? '"' : ' ';
    if (close == '"') p++;
    while (*p && *p != close && (close == '"' || *p != '\t'))
    {
        if (n + 1 >= max) return FALSE;
        out[n++] = *p++;
    }
    out[n] = 0;
    return n > 3;
}

/* The folder an executable is in, without its name or the trailing slash --
 * except at the root of a drive, where the slash is part of the name. */
static inline BOOL fix_folder_of( const WCHAR *path, WCHAR *out, unsigned int max )
{
    unsigned int n = 0;

    while (path[n] && n + 1 < max) { out[n] = path[n]; n++; }
    out[n] = 0;
    while (n && out[n - 1] != '\\') n--;
    if (!n) return FALSE;
    out[n > 3 ? n - 1 : n] = 0;
    return TRUE;
}

/* The game's folder, from the command line; FALSE when the setup was run by
 * hand and the caller should look where it is itself. */
static inline BOOL fix_game_folder( WCHAR *out, unsigned int max )
{
    WCHAR exe[MAX_PATH];

    return fix_game_executable( exe, MAX_PATH ) && fix_folder_of( exe, out, max );
}

#endif
