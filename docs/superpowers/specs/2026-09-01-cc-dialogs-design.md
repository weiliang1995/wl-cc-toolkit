# cc-dialogs 设计文档

日期：2026-09-01
状态：已通过设计评审，待写实现计划

## 1. 背景与目标

Claude Code 在终端 TUI 里打断用户的时刻（权限确认、选项询问）容易被忽略 —— 用户切到别的窗口干活时，终端里的提示不会主动引起注意，导致 Claude 长时间空等。

cc-dialogs 把这些时刻替换成 macOS / Windows 的**原生对话框**，让打断真正可见。

已有一份**同事开发的 macOS 实现**（纯 hooks + 三个 Python 脚本 + osascript），本项目在其机制基础上重写为跨平台版本，并新增焦点感知的通知策略。

## 2. 范围

四个场景，分两类：

| 类别 | 场景 | 是否阻塞 | 参考实现 |
|---|---|---|---|
| 决策 | 工具权限确认（Bash/Write/Edit 的 y/n） | 是 | 有 |
| 决策 | AskUserQuestion 选项询问 | 是 | 有 |
| 通知 | Claude 停下等待用户 | 否 | 有（策略需改进） |
| 通知 | 任务完成 | 否 | 与上一条合并 —— 均由 `Stop` 触发 |

**明确不做**：主输入框（用户打字的地方）没有任何拦截点，确定不可行。

## 3. Hook 机制与协议

> 本节的 schema 细节来自对已有 macOS 实现的调研，**是本项目的地基**。官方文档对这两处的输出 schema 描述不完整，以下内容以实测为准。

### 3.1 权限确认 — `PermissionRequest`

输出顶层结构恒定：

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": { }
  }
}
```

`decision` 字段：

- `behaviour`: `"allow"` | `"deny"` —— **英式拼写，不是 `behavior`**
- `message`: string，拒绝理由
- `updatedPermissions`: array，仅"总是允许"时使用

三种形态：

```json
// 允许
{"hookSpecificOutput":{"hookEventName":"PermissionRequest",
  "decision":{"behaviour":"allow"}}}

// 拒绝
{"hookSpecificOutput":{"hookEventName":"PermissionRequest",
  "decision":{"behaviour":"deny","message":"User denied via dialog"}}}

// 总是允许
{"hookSpecificOutput":{"hookEventName":"PermissionRequest",
  "decision":{"behaviour":"allow",
    "updatedPermissions":[{"type":"addRules","rules":[{}]}]}}}
```

**`updatedPermissions` 是原样透传**：CC 通过输入的 `permission_suggestions` 字段给出建议规则，脚本不解析、不构造，只在用户点"总是允许"时把它回填。CC 会将其写入 project localSettings。这意味着脚本无需理解权限规则语法。

正常退出且 stdout 是合法 JSON 时，终端的 y/n 提示被完全跳过。

### 3.2 选项询问 — `PreToolUse` + matcher `AskUserQuestion`

**不走 deny + reason，走 allow + 改写输入。** 把用户的选择预填进 `tool_input.answers` 后放行；工具照常执行，但因为答案已备齐，CC 跳过 TUI 直接返回结果。

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": {
      "questions": [ ],
      "answers": { "<question 文本原文>": "<label>" }
    }
  }
}
```

- `answers` 的 **key 是 `question["question"]` 的原文**，value 是选中项的 `label`
- **value 恒为 string**，不是数组
- 多选时用 `", "` 拼接成一个字符串，形如 `"Option A, Option C"`

macOS 侧实现要点（Windows 需等价行为）：
- `choose from list` 加 `multiple selections allowed` 控制多选
- 返回的多选结果以换行分隔，`out.split("\n")` 后单选取 `[0]`，多选 `", ".join(...)`

### 3.3 通知 — `UserPromptSubmit` + `Stop`

无返回值，纯副作用。详见第 6 节。

### 3.4 hooks.json

已有 macOS 版本（本项目需改造为跨平台）：

```json
{
  "PreToolUse": [{
    "matcher": "AskUserQuestion",
    "hooks": [{"type":"command",
      "command":"/usr/bin/python3 ${CLAUDE_PLUGIN_ROOT}/hooks/ask_user_question_dialog.py",
      "timeout": 600}]
  }],
  "PermissionRequest": [{
    "matcher": "",
    "hooks": [{"type":"command",
      "command":"/usr/bin/python3 ${CLAUDE_PLUGIN_ROOT}/hooks/permission_request_dialog.py",
      "timeout": 600}]
  }],
  "Stop": [{
    "matcher": "",
    "hooks": [{"type":"command",
      "command":"/usr/bin/python3 ${CLAUDE_PLUGIN_ROOT}/hooks/idle_notification.py",
      "timeout": 600}]
  }]
}
```

关键点：

- **`timeout: 600`** —— `PreToolUse` 默认只有 30 秒，对"等用户点对话框"远远不够，必须显式调大
- `${CLAUDE_PLUGIN_ROOT}` 指向插件根目录
- 非工具事件的 `matcher` 为空字符串

## 4. 目录结构

```
packages/cc-dialogs/
├── .claude-plugin/plugin.json
├── hooks/
│   ├── hooks.json
│   ├── permission_dialog.py      # 入口：PermissionRequest
│   ├── question_dialog.py        # 入口：PreToolUse/AskUserQuestion
│   ├── focus_baseline.py         # 入口：UserPromptSubmit
│   ├── idle_notify.py            # 入口：Stop
│   └── ccdialogs/                # 共享库
│       ├── __init__.py
│       ├── hookio.py             # stdin/stdout JSON 协议 + 统一降级出口
│       ├── config.py             # 配置读取 + 总开关
│       ├── state.py              # session 状态读写与清理
│       ├── focus.py              # 焦点比对逻辑（平台无关，可单测）
│       └── ui/
│           ├── __init__.py       # 抽象 API + 平台分发
│           ├── macos.py          # osascript 后端
│           └── windows.py        # PowerShell 后端
├── README.md
└── CHANGELOG.md
```

入口脚本保持极薄（读入参 → 调库 → 写结果），逻辑集中在 `ccdialogs/`。加平台只动 `ui/`，改策略只动 `focus.py`。

## 5. 平台抽象层

`ui/__init__.py` 暴露四个原语，两个后端各自实现：

| 原语 | macOS | Windows |
|---|---|---|
| `ask_permission(title, body, buttons)` | `display dialog` | WinForms 自定义三按钮窗体 |
| `ask_choice(title, prompt, options, multi)` | `choose from list` | WinForms `CheckedListBox` |
| `notify(title, body)` | `display notification` | `NotifyIcon.ShowBalloonTip` |
| `frontmost() -> (app, title)` | System Events | P/Invoke `GetForegroundWindow` + `GetWindowText` |

**Windows 统一用 WinForms**（`System.Windows.Forms`，PowerShell 5.1 自带，零依赖）。

不用 `Out-GridView` 的理由：虽然语义最接近 `choose from list`，但它是带筛选框的数据表格，用于选择两三个选项观感突兀，且 PowerShell 7 与 Server Core 上默认不存在。

**已知坑**：Windows 的 `NotifyIcon` 气泡依赖进程存活，`ShowBalloonTip` 后需短暂 sleep 再退出，否则气泡不显示。

## 6. 焦点检测

### 6.1 已有实现的做法与问题

同事版本：AppleScript 问 System Events 拿最前台进程名 + 前台窗口标题 → 白名单匹配 app（编辑器 vscode/cursor、终端 iTerm2/Terminal/warp）→ 命中后检查**窗口标题是否包含项目名**，包含则认为用户正在看，不通知。

之所以用标题匹配而非 PID 比对：**VS Code / Cursor 的多个窗口共用同一个 PID**，PID 比对必然误判。

两个问题：

1. **标题里不含项目名的窗口一律判为失焦** → 误发通知
2. 方向错误：拿不准时倾向于打扰用户

### 6.2 本项目的方案：自校准基准

核心观察：**用户按回车提交 prompt 的那一刻，其窗口必然是前台的。**

```
UserPromptSubmit ──> frontmost() ──> 存 {app, title, ts}
                                     到 <state_dir>/<session_id>.json

Stop ──> 读基准 ──> frontmost() ──> 比对 ──> 一致：不通知
                                         └─ 不一致：notify()
```

优点：不需要项目名匹配，不需要 app 白名单（任何终端/编辑器自动适配），每轮自动刷新基准。

### 6.3 比对规则

位于 `focus.py`，平台无关，**必须有单元测试**：

1. `app` 不同 → 失焦
2. `title` 完全相同 → 焦点在
3. 否则按分隔符（`—` `–` `-` `|`）切段后比较：
   - 段数 ≥ 3：**丢弃第一段**（通常是易变的文件名），其余段全等 → 焦点在
   - 段数 ≤ 2：要求全等，否则失焦

第 3 条容忍 VS Code 切换文件：`a.ts — proj — Visual Studio Code` 与
`b.ts — proj — Visual Studio Code` 丢弃首段后同为 `proj | Visual Studio Code`，
判为同一窗口。

**为什么不用"最长公共后缀 + 字符数阈值"**：两个开着**不同项目**的 VS Code 窗口
同样共享 ` — Visual Studio Code`（21 字符）这段后缀。阈值定低会把不同项目误判为
同一窗口，定高则短项目名（如 `app`）无法匹配 —— 不存在安全的阈值。按段比较则
天然区分：`proj` 与 `proj2` 是不同的段。

**为什么段数 ≤ 2 时要求全等**：终端标题常形如 `proj — zsh`，丢弃首段只剩 `zsh`，
会匹配上任意一个 zsh 窗口。

**无基准时**（例如插件在本轮中途安装）判为焦点在，不通知。宁可漏发，不可误扰。

### 6.4 状态存储

- Windows：`%LOCALAPPDATA%\cc-dialogs\`
- macOS：`~/.cache/cc-dialogs/`
- 文件名 `<session_id>.json`，内容 `{app, title, ts}`
- `SessionEnd` 时删除；每次写入顺带清理超过 7 天的残留（防 session 异常终止泄漏）

## 7. 降级铁律

> **任何异常都以 exit 0 + 空 stdout 收场。**

CC 对"hook 无输出"的解释是"不做决定，走正常流程"。因此脚本崩溃 = 自动回退终端 TUI，而非卡死或报错。这是已有实现最值得继承的设计。

覆盖范围：弹窗超时、用户取消、无图形界面、osascript/PowerShell 缺失、JSON 解析失败、任何未捕获异常。全部走 `hookio.py` 里的同一个出口。

两道前置闸门（避免每次白跑子进程）：

- **总开关**：环境变量 `CC_DIALOGS=off` 一票否决，供批处理场景使用
- **无 GUI 提前退出**：
  - macOS：检测 `SSH_TTY` / `SSH_CONNECTION`，命中即退出
  - **Windows：不做预检**，直接尝试弹窗，失败落入静默退出

**为什么 Windows 不预检**：判据应是「有没有桌面可画」，而非「本地还是远程」。
RDP 会话拥有完整桌面，对话框与通知均正常工作（画面传到远端而已），
因此**不能**用 `SESSIONNAME != Console` 排除 RDP —— 那会把一个能用的场景关掉。
真正无桌面的是 SSH 连入 Windows，而这种情况 WinForms 会直接抛异常，
由降级铁律兜住即可。为省一次子进程而引入误判不划算。

所有 hook 的 `timeout` 统一 600 秒。

## 8. 长内容处理

权限确认可能涉及很长的 Bash 命令或大段 diff。

- **Windows**：可滚动的只读多行 `TextBox`，不截断
- **macOS**：`display dialog` 有实际长度限制，超过 2000 字符截断并标注 `…（还有 N 字符，完整内容见终端）`

终端里 CC 本身会打印完整内容，对话框只需支撑判断，无需完整呈现。

## 9. 插件与市场清单

### 9.1 plugin.json

```json
{
  "name": "cc-dialogs",
  "version": "0.1.0",
  "description": "把 Claude Code 的终端交互替换为 macOS / Windows 原生对话框"
}
```

### 9.2 marketplace.json

建这个包**同时解锁仓库根部的 `.claude-plugin/marketplace.json`** —— `/plugin-dev` 与 `/publish` 两个命令均依赖它，目前为空。

文件已存在于仓库根部：

```json
{
  "name": "wl-cc-toolkit",
  "owner": {"name": "weiliang1995"},
  "plugins": [
    {"name": "", "source": "", "description": ""}
  ]
}
```

`owner` 是**对象**，不是字符串。

实现时需填入 cc-dialogs 条目：

```json
{
  "name": "cc-dialogs",
  "source": "./packages/cc-dialogs",
  "description": "把 Claude Code 的终端交互替换为 macOS / Windows 原生对话框"
}
```

`source` 字段被 `/plugin-dev` 用来解析本地路径（见 `.claude/commands/plugin-dev.md`
第 1 步），需保持 `./packages/<name>` 形式。

**marketplace 名（`wl-cc-toolkit`）与仓库名（`cc-toolkit`）不同**，这是允许的，
但 `plugin-dev.md` 中的 `CACHE` 与 `MARKETPLACE` 常量必须跟随 **marketplace 名**。
该文件已于 2026-09-01 同步修正为 `wl-cc-toolkit`。

## 10. 未决项

### 10.1 hooks.json 中的 Python 调用方式（**实现前必须 spike**）

问题：`/usr/bin/python3` 在 Windows 不存在；`py -3` 在 macOS 不存在；hooks.json 是静态 JSON 无条件语法；本机 `PATHEXT` 不含 `.PY`，故无法直接执行 `.py` 文件。

本机环境已确认：Python 3.11，`py -3` → `C:\Windows\py.exe`，`python` 可用但经由 WindowsApps 别名（较脆弱）。

**候选方案**：`py -3 "…" || python3 "…"`

`||` 在 cmd 与 sh 中均成立。Windows 上 `py` 命中；macOS 上 `py` 不存在（exit 9009/127）自动落到 `python3`。

**前提**：脚本必须严格 exit 0 —— 恰与第 7 节的降级铁律自洽。否则脚本的正常非零退出会触发第二次执行。

**依赖**：CC 是否通过 shell 执行 hook 命令。需实测。

**保底方案**：分发 `hooks.macos.json` / `hooks.windows.json` 两份，安装时择一。确定可行，代价是多一个安装步骤。

### 10.2 ~~marketplace.json 的确切 schema~~（已解决）

已于 2026-09-01 确认，见 9.2。

## 11. 测试策略

- **`focus.py` 的比对规则**：纯函数，必须有单元测试。必须覆盖的情形：
  同一 VS Code 窗口切换文件（应判焦点在）、**两个不同项目的 VS Code 窗口**
  （应判失焦 —— 这是字符阈值方案会失手的用例）、终端标题两段式、
  无基准、app 变化、标题含不同分隔符风格
- **`hookio.py` 的降级出口**：注入各类异常，断言恒为 exit 0 + 空 stdout
- **UI 后端**：无法自动化，靠手动验收清单（三按钮各点一次、多选、取消、超时）
- **协议正确性**：构造样例 stdin JSON，断言 stdout 与第 3 节的 schema 逐字段吻合（尤其 `behaviour` 拼写与 `answers` 的 string 类型）

## 12. 实施顺序建议

1. spike：验证 10.1 的 Python 调用方案
2. **marketplace.json + plugin.json，打通 `/plugin-dev` 本地联调** —— 必须前置：后续每一步都要在真实 CC 会话里验证，没有它就只能靠单测盲写
3. `hookio.py` + 降级铁律 + 单测
4. `permission_dialog.py` + Windows 后端（日常撞击频次最高，价值密度最大）
5. `question_dialog.py` + Windows 后端
6. `focus.py` + `state.py` + 单测
7. `focus_baseline.py` + `idle_notify.py` + 两侧 `frontmost()` / `notify()`
8. macOS 后端补齐
