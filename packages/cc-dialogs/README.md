# cc-dialogs

Replaces Claude Code's terminal prompts with native macOS / Windows panels.

## What it covers

| Hook | Script | Effect |
|---|---|---|
| `PermissionRequest` | `permission_dialog.py` | Permission prompt becomes a native panel (Allow / Always allow / Deny) |
| `PreToolUse` (AskUserQuestion) | `question_dialog.py` | Question becomes a native list, multi-select supported |
| `UserPromptSubmit` | `focus_baseline.py` | Records the focus baseline (side effect only, no UI) |
| `Stop` | `idle_notify.py` | Sends a system notification, but only if you looked away |

Panels appear in the bottom-right corner rather than centred, so they read as
notifications you can act on rather than modal interruptions.

## Requirements

- Python 3.8+
- macOS, or Windows 10+
- No third-party packages

## Language

Button labels follow the language of the content being shown: a Chinese
question gets Chinese buttons, an English one gets English. The content
itself comes from Claude, so it is already in whatever language you are
working in. Set `CC_DIALOGS_LANG=en` or `=zh` to force one.

## Switch

Set `CC_DIALOGS=off` to disable everything (useful for batch runs).

## Fallback

Any failure exits silently and Claude Code falls back to its own terminal
prompt. This covers cancellation, timeouts, headless sessions, a missing
PowerShell or osascript, and any unhandled exception. The session never
hangs because of this plugin.

## How the focus check works

Notifications fire only when you have actually switched away:

1. At `UserPromptSubmit`, record the foreground window -- the moment you press
   Enter, your window is by definition in front
2. At `Stop`, read it again and compare
3. If they match, you are still watching, so stay quiet

The comparison splits titles on the usual separators (`—` `–` `|` ` - `) and
every segment must match. Comparing segment lists rather than raw strings
keeps the check immune to how the separator is rendered.

The first segment matters most: VS Code puts the focused view's name there,
which is a file name when you are in the editor and the session's own name
when you are in a Claude Code panel. So the check also distinguishes the two
cases that live inside a single OS window -- you clicked into a file, or you
moved to another Claude session's panel -- and treats both as "you are not
watching this session".

A longest-common-suffix threshold does not work here: two VS Code windows on
*different* projects still share ` - Visual Studio Code`, so no threshold is
safe.

The cost of counting the first segment is that Claude Code sometimes renames
a session mid-turn, which reads as a view change and can produce one dialog
you did not need. That trade is deliberate: a panel you did not need costs
far less than silently losing the plugin's whole point.

## Self-check

```
py -3 selftest.py          # focus and fallback logic, two seconds
py -3 selftest.py --ui     # also pops the real panels
```

## Encoding rules for contributors

Two Windows-specific traps, both already hit once:

- **`.ps1` files must stay pure ASCII.** Windows PowerShell 5.1 parses
  BOM-less `.ps1` files using the system ANSI code page, so any non-ASCII
  literal is mangled. All display text is passed in through the JSON params
  file, which is read with an explicit `-Encoding UTF8`.
- **`.ps1` files must stay CRLF.** PowerShell 5.1 fails to parse here-strings
  (`@'...'@`) with LF endings and treats the embedded C# as PowerShell.
  Enforced by `.gitattributes` at the repository root.

## Known limitations

- **After an RDP disconnect** the panel is drawn on the disconnected desktop
  where you cannot see it; Claude waits out the 600s timeout and then falls
  back to the terminal
- **Over SSH** there is no desktop, so everything silently disables and
  behaves as though the plugin were not installed
- A terminal `cd` that changes the window title may read as looking away and
  produce one extra notification
