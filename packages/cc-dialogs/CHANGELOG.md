# Changelog

## 1.1.0 - 2026-09-05

### Changed

- The focus check now counts the window title's first segment instead of
  dropping it. VS Code puts the focused view's name there — a file name in the
  editor, the owning session's name in a Claude Code panel — so clicking into a
  file, or moving to another Claude panel in the same window, now counts as
  "not watching" and gets a dialog. Previously both read as "still watching".
- Titles are compared as segment lists rather than raw strings, so the check no
  longer depends on how the separator is rendered.

### Fixed

- Two panels open at once no longer fight over the foreground. Each one used to
  re-assert `HWND_TOPMOST` on a 700ms timer, and since Windows fronts whichever
  topmost window was raised last, two sessions' panels took turns covering each
  other for as long as both were up. The timer is gone; panels still set
  `TopMost` once. The cost is that a toast appearing later can now cover a
  panel, which the timer had been added to prevent.

### Notes

- Claude Code sometimes renames a session mid-turn, which now reads as a view
  change and can produce one dialog you did not need. Deliberate trade: a panel
  you did not need costs less than silently losing the plugin's whole point.
- Known limitation: the baseline is sampled a few hundred milliseconds after
  you press Enter, so submitting a prompt and immediately switching to another
  tab records that other tab as the baseline. The session then reads as "away"
  when you come back to it, and can notify you while you are sitting in front
  of it. Counting the first segment makes this visible where the previous rule
  hid it.

## 1.0.1 - 2026-09-05

### Fixed

- `hooks/hooks.json` listed its four events at the top level, where Claude Code
  expects them nested under a `hooks` key. A marketplace install therefore
  registered zero hooks and no dialog ever appeared. Installs that predated the
  1.0.0 release only kept working because the same hooks were also wired by hand
  in `~/.claude/settings.json`.

### Changed

- `CHANGELOG.md` rewritten in English, and the 0.1.0 feature list folded into
  the 1.0.0 release notes

## 1.0.0 - 2026-09-02

First marketplace release. Replaces Claude Code's terminal prompts with native
dialogs, and stays quiet while you are still looking at the session window.

### Added

- `PermissionRequest` → native three-button permission dialog; "always allow"
  passes `permission_suggestions` through
- `PreToolUse` / `AskUserQuestion` → native option list; answers come back as
  `allow` + `updatedInput`, multi-select supported
- `UserPromptSubmit` + `Stop` → self-calibrating focus check; a system
  notification fires only once you have switched away from the session window
- Windows backend (PowerShell + WinForms) and macOS backend (osascript)
- Corner-panel styling, overridable via `%LOCALAPPDATA%\cc-dialogs\style.json`
  (see `STYLE.md`)
- Button labels picked automatically from the language of the content
- `CC_DIALOGS=off` kill switch
- `selftest.py` for the focus comparison

### Fixed

- Auto-close timer left the buttons dead
- Garbled Chinese text on Windows
- A UTF-8 BOM on stdin is now tolerated

### Notes

- The macOS backend is **still unverified on real hardware**; Windows is the
  tested path

## 0.1.0 - 2026-09-01

Initial internal version, wired by hand in `~/.claude/settings.json` rather than
installed as a plugin. Its feature set is folded into 1.0.0 above.
