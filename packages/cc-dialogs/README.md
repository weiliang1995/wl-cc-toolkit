# cc-dialogs

把 Claude Code 的终端交互替换为 macOS / Windows 原生对话框。

## 场景

| Hook | 脚本 | 作用 |
|---|---|---|
| `PermissionRequest` | `permission_dialog.py` | 权限确认 → 原生三按钮对话框（允许 / 总是允许 / 拒绝） |
| `PreToolUse` (AskUserQuestion) | `question_dialog.py` | 选项询问 → 原生列表，支持多选 |
| `UserPromptSubmit` | `focus_baseline.py` | 记录焦点基准（纯副作用，不弹窗） |
| `Stop` | `idle_notify.py` | 你切走窗口了才发系统通知 |

## 要求

- Python 3.8+
- macOS 或 Windows 10+
- 不需要安装任何第三方包

## 开关

设 `CC_DIALOGS=off` 可临时全部禁用（跑批处理时用）。

## 降级

任何异常都会静默回退到 Claude Code 原本的终端提示，绝不卡住会话。
覆盖：弹窗取消、超时、无图形界面、PowerShell/osascript 缺失、脚本崩溃。

## 焦点判定

通知只在你**切走窗口**时才发，判据是自校准的：

1. `UserPromptSubmit` 时记录当前前台窗口 —— 你按回车那一刻窗口必然是前台的
2. `Stop` 时再取一次，与基准比对
3. 相同则认为你还在看，不打扰

比对按标题分隔符（`—` `–` `|` ` - `）切段：三段以上丢弃首段（通常是文件名）比较其余，
两段及以下要求全等。因此 VS Code 里切换文件不算切走窗口，切到另一个项目的窗口则算。

不用「最长公共后缀 + 字符阈值」：两个开着不同项目的 VS Code 窗口同样共享
` - Visual Studio Code`，不存在安全的阈值。

## 自检

```
py -3 selftest.py          # 焦点比对逻辑，两秒
py -3 selftest.py --ui     # 额外弹出真实对话框
```

## 已知限制

- **RDP 断开后**弹窗发给已断开的桌面，你看不到，Claude 会等到 600 秒超时后回退终端
- **SSH 连入**无桌面，全部功能静默禁用，行为与未安装一致
- 终端里 `cd` 若导致窗口标题变化，可能被判为切走窗口而多发一条通知
- `.ps1` 必须保持 CRLF 换行 —— PowerShell 5.1 的 here-string 在 LF 下解析失败
  （已由仓库根部 `.gitattributes` 锁定）
