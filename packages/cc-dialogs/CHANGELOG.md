# Changelog

## 1.0.0 - 2026-09-02

### Added

- 角落面板样式，可通过 `%LOCALAPPDATA%\cc-dialogs\style.json` 覆写（见 `STYLE.md`）
- 按内容语言自动选择按钮标签

### Fixed

- 自动关闭定时器会让按钮失效
- Windows 下中文乱码
- 容忍 stdin 的 UTF-8 BOM

### 备注

- macOS 后端**仍未在真机验证**；Windows 为已验证路径

## 0.1.0 - 2026-09-01

### Added

- `PermissionRequest` → 原生三按钮权限对话框，「总是允许」透传 `permission_suggestions`
- `PreToolUse` / `AskUserQuestion` → 原生选项列表，`allow` + `updatedInput` 回填答案，支持多选
- `UserPromptSubmit` + `Stop` → 自校准焦点判定，仅在切走窗口时发系统通知
- Windows 后端（PowerShell + WinForms）与 macOS 后端（osascript）
- `CC_DIALOGS=off` 总开关
- `selftest.py` 焦点比对自检

### 备注

- macOS 后端**尚未在真机验证**
