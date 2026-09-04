# Changelog

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
