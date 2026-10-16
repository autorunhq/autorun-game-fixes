/* A game fix's registry edits, from registry.txt beside this program.
 *
 * tools/build-fixes.py writes registry.txt from the "registry" list of a
 * fix.json and puts this program beside it as the fix's setup, so a fix that
 * only needs keys an installer would have written needs no program of its own.
 * Autorun's launcher runs it before the game with the game's executable as its
 * argument (include/fix_game.h); {game} in a string value is that executable's
 * folder.
 *
 * registry.txt is UTF-8, one edit to a line, five fields apart by tabs:
 *
 *     view   32 or 64: which side of a 64-bit registry, as a 32-bit or a
 *            64-bit game reads it (HKLM\Software differs between the two)
 *     key    HKCU\... or HKLM\...
 *     name   the value's name; empty for the key's default value
 *     type   sz, dword or delete
 *     value  the string, or the number in decimal; empty for delete
 *
 * Each edit is reported to autorun_runtime.log as a [FIX REGISTRY] line; the
 * exit code is 0 when every one worked. A value to delete that is not there
 * counts as deleted. Running it again is harmless. */
#include <windows.h>
#include <winternl.h>
#include "fix_game.h"

__declspec(dllimport) NTSTATUS NTAPI NtDisplayString( const UNICODE_STRING *str );

/* Built without a C runtime; the compiler still expects these for structures. */
void *memset( void *dst, int c, size_t n )
{
    unsigned char *p = dst;
    while (n--) *p++ = (unsigned char)c;
    return dst;
}

void *memcpy( void *dst, const void *src, size_t n )
{
    unsigned char *d = dst;
    const unsigned char *s = src;
    while (n--) *d++ = *s++;
    return dst;
}

#define TEXT_MAX  65536
#define VALUE_MAX 1024

/* One line: "[FIX REGISTRY] <label> <name>: <result>", with the value in hex. */
static void report( const char *label, const WCHAR *name, const char *result, DWORD value )
{
    static const char hex[] = "0123456789abcdef";
    const char *prefix = "[FIX REGISTRY] ";
    WCHAR buffer[400];
    UNICODE_STRING str;
    unsigned int n = 0, i;

    while (*prefix) buffer[n++] = *prefix++;
    while (*label && n < 100) buffer[n++] = *label++;
    if (name)
    {
        buffer[n++] = ' ';
        while (*name && n < 320) buffer[n++] = *name++;
    }
    buffer[n++] = ':';
    buffer[n++] = ' ';
    while (*result && n < 380) buffer[n++] = *result++;
    buffer[n++] = ' ';
    buffer[n++] = '0';
    buffer[n++] = 'x';
    for (i = 0; i < 8; i++) buffer[n++] = hex[(value >> (28 - i * 4)) & 15];
    str.Buffer = buffer;
    str.Length = (USHORT)(n * sizeof(WCHAR));
    str.MaximumLength = str.Length;
    NtDisplayString( &str );
}

static unsigned int wide_length( const WCHAR *text )
{
    unsigned int n = 0;
    while (text[n]) n++;
    return n;
}

static BOOL starts_with( const WCHAR *text, const char *prefix )
{
    while (*prefix) if (*text++ != (WCHAR)*prefix++) return FALSE;
    return TRUE;
}

/* registry.txt beside this program, as UTF-16. */
static BOOL read_edits( WCHAR *out, unsigned int max )
{
    static char bytes[TEXT_MAX];
    WCHAR path[MAX_PATH];
    unsigned int n = GetModuleFileNameW( NULL, path, MAX_PATH ), i;
    const char *name = "registry.txt";
    DWORD got = 0;
    HANDLE file;
    int chars;

    if (!n || n >= MAX_PATH) return FALSE;
    while (n && path[n - 1] != '\\') n--;
    for (i = 0; name[i] && n + 1 < MAX_PATH; i++) path[n++] = name[i];
    path[n] = 0;
    file = CreateFileW( path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL );
    if (file == INVALID_HANDLE_VALUE) return FALSE;
    if (!ReadFile( file, bytes, sizeof(bytes) - 1, &got, NULL ) || got == sizeof(bytes) - 1)
    {
        CloseHandle( file );
        return FALSE;
    }
    CloseHandle( file );
    chars = got ? MultiByteToWideChar( CP_UTF8, MB_ERR_INVALID_CHARS, bytes, got, out, max - 1 ) : 0;
    if (got && chars <= 0) return FALSE;
    out[chars] = 0;
    return TRUE;
}

/* value with every {game} made the game's folder. */
static BOOL expand( const WCHAR *value, const WCHAR *game, WCHAR *out, unsigned int max )
{
    unsigned int n = 0, i;

    while (*value)
    {
        if (starts_with( value, "{game}" ))
        {
            for (i = 0; game[i]; i++) { if (n + 1 >= max) return FALSE; out[n++] = game[i]; }
            value += 6;
            /* At the root of a drive the folder keeps its slash: C:\ and then
             * "\" would be C:\\. */
            if (n && out[n - 1] == '\\' && *value == '\\') value++;
            continue;
        }
        if (n + 1 >= max) return FALSE;
        out[n++] = *value++;
    }
    out[n] = 0;
    return TRUE;
}

static BOOL apply( WCHAR **fields, const WCHAR *game )
{
    static WCHAR value[VALUE_MAX];
    const WCHAR *view = fields[0], *path = fields[1], *name = fields[2], *type = fields[3];
    REGSAM wow = view[0] == '6' ? KEY_WOW64_64KEY : KEY_WOW64_32KEY;
    HKEY root, key;
    LONG status;
    DWORD number = 0;

    if (starts_with( path, "HKCU\\" )) root = HKEY_CURRENT_USER;
    else if (starts_with( path, "HKLM\\" )) root = HKEY_LOCAL_MACHINE;
    else
    {
        report( "skip", path, "FAILED: neither HKCU nor HKLM, error", 0 );
        return FALSE;
    }
    path += 5;

    if (starts_with( type, "delete" ))
    {
        if (!(status = RegOpenKeyExW( root, path, 0, KEY_SET_VALUE | wow, &key )))
        {
            status = RegDeleteValueW( key, name );
            RegCloseKey( key );
        }
        if (status == ERROR_FILE_NOT_FOUND)
        {
            report( "delete", name, "ok, was not set, error", (DWORD)status );
            return TRUE;
        }
        report( "delete", name, status ? "FAILED, error" : "ok, error", (DWORD)status );
        return !status;
    }

    if (starts_with( type, "dword" ))
    {
        const WCHAR *digit;

        for (digit = fields[4]; *digit >= '0' && *digit <= '9'; digit++) number = number * 10 + (*digit - '0');
        if (*digit || digit == fields[4])
        {
            report( "set", name, "FAILED: not a number, error", 0 );
            return FALSE;
        }
    }
    else if (!starts_with( type, "sz" ) || !expand( fields[4], game, value, VALUE_MAX ))
    {
        report( "set", name, "FAILED: unknown type or value too long, error", 0 );
        return FALSE;
    }

    if ((status = RegCreateKeyExW( root, path, 0, NULL, 0, KEY_SET_VALUE | wow, NULL, &key, NULL )))
    {
        report( "open", path, "FAILED, error", (DWORD)status );
        return FALSE;
    }
    if (type[0] == 'd') status = RegSetValueExW( key, name, 0, REG_DWORD, (const BYTE *)&number, sizeof(number) );
    else status = RegSetValueExW( key, name, 0, REG_SZ, (const BYTE *)value, (wide_length( value ) + 1) * sizeof(WCHAR) );
    RegCloseKey( key );
    report( "set", name, status ? "FAILED, error" : "ok, value", status ? (DWORD)status : number );
    return !status;
}

void __stdcall start(void)
{
    static WCHAR text[TEXT_MAX], game[MAX_PATH];
    WCHAR *line, *fields[5];
    unsigned int edits = 0;
    BOOL ok = TRUE;

    report( "start", NULL, "build", 1 );
    if (!read_edits( text, TEXT_MAX ))
    {
        report( "done", NULL, "FAILED: registry.txt beside this program cannot be read, error", GetLastError() );
        ExitProcess( 1 );
    }
    if (!fix_game_folder( game, MAX_PATH )) game[0] = 0;

    for (line = text; *line; )
    {
        WCHAR *p = line, *next;
        unsigned int count = 0;

        while (*p && *p != '\n') p++;
        next = *p ? p + 1 : p;
        *p = 0;
        if (p > line && p[-1] == '\r') p[-1] = 0;
        if (*line)
        {
            fields[count++] = line;
            for (p = line; *p; p++)
                if (*p == '\t')
                {
                    *p = 0;
                    if (count == 5) break;
                    fields[count++] = p + 1;
                }
            if (count != 5)
            {
                report( "skip", line, "FAILED: not five fields, count", count );
                ok = FALSE;
            }
            else
            {
                ok &= apply( fields, game );
                edits++;
            }
        }
        line = next;
    }
    report( ok ? "done, every edit worked, edits" : "done, an edit FAILED (see above), edits", NULL, "count", edits );
    ExitProcess( !ok );
}
