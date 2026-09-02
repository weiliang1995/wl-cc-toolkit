# cc-dialogs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Claude Code 的终端权限确认与选项询问替换为 macOS / Windows 原生对话框，并在用户视线离开会话窗口时发系统通知。

**Architecture:** 纯 Claude Code hooks，无常驻进程。四个入口脚本挂在四个 hook 事件上，逻辑集中在 `ccdialogs/` 共享库；平台差异隔离在 `ui/` 后端，macOS 走 `osascript`，Windows 走 PowerShell + WinForms。任何异常一律静默退出，由 CC 自动回退终端 TUI。

**Tech Stack:** Python 3（仅标准库）、PowerShell 5.1 + System.Windows.Forms（Windows 内置）、osascript / AppleScript（macOS 内置）、unittest（标准库）。

**Spec:** `docs/superpowers/specs/2026-09-01-cc-dialogs-design.md`

## Global Constraints

以下为项目级约束，**每个任务都隐含包含**：

- **零外部依赖**：Python 仅用标准库；测试用 `unittest` 而非 pytest；不得 `pip install` 任何东西
- **降级铁律**：所有入口脚本任何异常都以 **exit 0 + 空 stdout** 收场。CC 将「无输出」解释为「不做决定」，从而回退终端 TUI
- **`decision.behaviour` 是英式拼写** —— 不是 `behavior`
- **`updatedInput.answers` 的 value 恒为 string** —— 多选用 `", "` 拼接，不是数组
- **`answers` 的 key 是 `question["question"]` 的原文**，逐字节相同
- **`updatedPermissions` 原样透传**：来自输入的 `permission_suggestions`，不解析不构造
- **所有 hook 的 `timeout` 必须显式设为 `600`** —— `PreToolUse` 默认仅 30 秒
- **总开关**：环境变量 `CC_DIALOGS=off` 时所有脚本立即静默退出
- **Windows 不做无 GUI 预检** —— RDP 有完整桌面，弹窗正常工作；真正无桌面的 SSH 由 try/catch 兜住
- 包根目录：`packages/cc-dialogs/`

---

## File Structure

| 文件 | 职责 |
|---|---|
| `.claude-plugin/plugin.json` | 插件清单 |
| `hooks/hooks.json` | 四个 hook 的注册 |
| `hooks/permission_dialog.py` | 入口：`PermissionRequest` |
| `hooks/question_dialog.py` | 入口：`PreToolUse` / `AskUserQuestion` |
| `hooks/focus_baseline.py` | 入口：`UserPromptSubmit`，记录焦点基准 |
| `hooks/idle_notify.py` | 入口：`Stop`，比对基准决定是否通知 |
| `hooks/ccdialogs/hookio.py` | stdin/stdout 协议 + 降级铁律 + 总开关 |
| `hooks/ccdialogs/focus.py` | 窗口标题比对（纯函数，平台无关） |
| `hooks/ccdialogs/state.py` | session 状态读写与过期清理 |
| `hooks/ccdialogs/ui/__init__.py` | 四个 UI 原语的抽象与平台分发 |
| `hooks/ccdialogs/ui/windows.py` | Windows 后端（调用 ps1） |
| `hooks/ccdialogs/ui/macos.py` | macOS 后端（调用 osascript） |
| `hooks/ccdialogs/ui/win/*.ps1` | 四个 PowerShell 脚本 |
| `tests/*.py` | unittest 测试 |

**为什么 ps1 单独成文件**：避免在 Python 里拼 PowerShell 字符串导致的多层转义地狱。参数以 JSON 临时文件传入，结果以 JSON 从 stdout 传出。

---

### Task 1: Spike — 确定 hooks.json 的 Python 调用方式

本任务产出的是**一个答案**，不是保留的代码。它决定 Task 2 的 hooks.json 形态。

**Files:**
- Create: `packages/cc-dialogs/hooks/_spike_echo.py`（临时，任务末尾删除）
- Create: `packages/cc-dialogs/hooks/hooks.json`（仅含 spike 用的一条）

**Interfaces:**
- Consumes: 无
- Produces: 一个结论 —— hooks.json 中 Python 调用命令的最终写法，写入 Task 2

**背景**：`/usr/bin/python3` 在 Windows 不存在；`py -3` 在 macOS 不存在；hooks.json 是静态 JSON 无条件语法；本机 `PATHEXT` 不含 `.PY` 故无法直接执行 `.py`。候选方案 `py -3 "…" || python3 "…"` 依赖 CC 通过 shell 执行 hook 命令，需实测。

- [ ] **Step 1: 写探针脚本**

`packages/cc-dialogs/hooks/_spike_echo.py`：

```python
import json, os, sys, pathlib

log = pathlib.Path(os.environ.get("TEMP") or "/tmp") / "cc_dialogs_spike.log"
with log.open("a", encoding="utf-8") as f:
    f.write(json.dumps({
        "argv": sys.argv,
        "executable": sys.executable,
        "version": sys.version,
    }) + "\n")
sys.exit(0)
```

- [ ] **Step 2: 写 spike 用 hooks.json**

`packages/cc-dialogs/hooks/hooks.json`：

```json
{
  "UserPromptSubmit": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "py -3 \"${CLAUDE_PLUGIN_ROOT}/hooks/_spike_echo.py\" || python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/_spike_echo.py\"",
          "timeout": 600
        }
      ]
    }
  ]
}
```

- [ ] **Step 3: 让插件被 CC 加载**

本仓库根部 `.claude-plugin/marketplace.json` 的 `plugins` 数组填入：

```json
{
  "name": "cc-dialogs",
  "source": "./packages/cc-dialogs",
  "description": "Native OS dialogs for Claude Code prompts"
}
```

创建 `packages/cc-dialogs/.claude-plugin/plugin.json`：

```json
{
  "name": "cc-dialogs",
  "version": "0.0.1",
  "description": "Native OS dialogs for Claude Code prompts"
}
```

然后运行 `/plugin-dev cc-dialogs local`，**开一个新的 CC 会话**（hook 在会话启动时加载）。

- [ ] **Step 4: 触发并读取结果**

在新会话里随便输入一句话（触发 `UserPromptSubmit`），然后检查日志：

Run（Windows）：`type %TEMP%\cc_dialogs_spike.log`

Expected（方案可行）：文件存在，且含一行 JSON，`executable` 指向真实 Python 路径。

Expected（方案不可行）：文件不存在，或 CC 报 hook 执行错误。

- [ ] **Step 5: 记录结论**

在本计划文件 Task 2 的 Step 2 处，把最终确定的 `command` 字段值写死。

- **若 `||` 方案可行**：沿用该写法。
- **若不可行**（CC 未经 shell 直接 CreateProcess）：改用保底方案 —— 分发 `hooks.macos.json` 与 `hooks.windows.json` 两份，并在 `packages/cc-dialogs/README.md` 写明安装时需将对应平台的文件复制为 `hooks.json`。Task 2 的 Step 2 相应改为创建两份文件。

- [ ] **Step 6: 清理探针**

```bash
git rm -f packages/cc-dialogs/hooks/_spike_echo.py
```

删除 `%TEMP%\cc_dialogs_spike.log`。**不要提交探针脚本。**

- [ ] **Step 7: Commit**

```bash
git add packages/cc-dialogs/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore(cc-dialogs): 插件清单与市场条目"
```

---

### Task 2: 插件骨架与本地开发闭环

**目标**：让 `/plugin-dev` 能加载本插件，且一个真实 hook 能跑通并产生可见效果。后续每个任务都依赖这个闭环来验证。

**Files:**
- Create: `packages/cc-dialogs/hooks/hooks.json`
- Create: `packages/cc-dialogs/hooks/ccdialogs/__init__.py`
- Create: `packages/cc-dialogs/README.md`
- Create: `packages/cc-dialogs/CHANGELOG.md`

**Interfaces:**
- Consumes: Task 1 的结论（`command` 字段的最终写法）
- Produces: 一个可被 CC 加载的插件；后续任务往 `hooks.json` 增补事件

- [ ] **Step 1: 写完整的 hooks.json**

把 `<PYCMD>` 替换为 Task 1 Step 5 确定的写法（默认 `py -3 "…" || python3 "…"`）：

```json
{
  "PermissionRequest": [
    {"matcher": "", "hooks": [{"type": "command",
      "command": "<PYCMD:permission_dialog.py>", "timeout": 600}]}
  ],
  "PreToolUse": [
    {"matcher": "AskUserQuestion", "hooks": [{"type": "command",
      "command": "<PYCMD:question_dialog.py>", "timeout": 600}]}
  ],
  "UserPromptSubmit": [
    {"matcher": "", "hooks": [{"type": "command",
      "command": "<PYCMD:focus_baseline.py>", "timeout": 600}]}
  ],
  "Stop": [
    {"matcher": "", "hooks": [{"type": "command",
      "command": "<PYCMD:idle_notify.py>", "timeout": 600}]}
  ]
}
```

**四处 `timeout` 都必须是 600。**

- [ ] **Step 2: 建包目录**

`packages/cc-dialogs/hooks/ccdialogs/__init__.py`：空文件。

- [ ] **Step 3: 写四个入口的占位实现**

四个文件内容相同（仅文件名不同），先让它们什么都不做地正常退出：

`packages/cc-dialogs/hooks/permission_dialog.py`（`question_dialog.py`、`focus_baseline.py`、`idle_notify.py` 同样）：

```python
import sys

if __name__ == "__main__":
    sys.exit(0)
```

- [ ] **Step 4: 验证插件加载且不破坏会话**

运行 `/plugin-dev cc-dialogs local`，开新会话，正常对话几轮。

Expected：会话完全正常，权限提示仍走终端 TUI（因为脚本还没做任何事），无报错。

这一步确认了 hooks.json 语法正确且四个事件都能触发脚本。

- [ ] **Step 5: 写 README 骨架**

`packages/cc-dialogs/README.md`：

```markdown
# cc-dialogs

把 Claude Code 的终端交互替换为 macOS / Windows 原生对话框。

## 场景

- 工具权限确认 → 原生三按钮对话框（允许 / 总是允许 / 拒绝）
- AskUserQuestion → 原生选项列表（支持多选）
- Claude 停下等待时 → 若你已切走窗口，发系统通知

## 要求

- Python 3.8+
- macOS 或 Windows 10+
- 无需安装任何第三方包

## 开关

设 `CC_DIALOGS=off` 可临时全部禁用（批处理场景）。

## 降级

任何异常都会静默回退到 Claude Code 原本的终端提示，不会卡住会话。
```

`packages/cc-dialogs/CHANGELOG.md`：

```markdown
# Changelog
```

- [ ] **Step 6: Commit**

```bash
git add packages/cc-dialogs/
git commit -m "feat(cc-dialogs): 插件骨架与四个 hook 入口占位"
```

---

### Task 3: hookio — 协议与降级铁律

**Files:**
- Create: `packages/cc-dialogs/hooks/ccdialogs/hookio.py`
- Test: `packages/cc-dialogs/tests/test_hookio.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `run(handler: Callable[[dict], dict | None]) -> NoReturn` —— 入口包装器，读 stdin JSON 传给 handler，把 handler 返回的 dict 写为 stdout JSON；任何异常静默吞掉。**永远 exit 0。**
  - `disabled() -> bool` —— `CC_DIALOGS` 环境变量为 `off`（不分大小写）时为 True

- [ ] **Step 1: 写失败的测试**

`packages/cc-dialogs/tests/test_hookio.py`：

```python
import io
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))

from ccdialogs import hookio


def run_with(handler, stdin_text, env=None):
    """跑一次 run()，返回 (exit_code, stdout_text)。"""
    out = io.StringIO()
    with mock.patch.object(sys, "stdin", io.StringIO(stdin_text)), \
         mock.patch.object(sys, "stdout", out), \
         mock.patch.dict(os.environ, env or {}, clear=False):
        try:
            hookio.run(handler)
        except SystemExit as e:
            return e.code, out.getvalue()
    raise AssertionError("run() 必须调用 sys.exit")


class TestRun(unittest.TestCase):
    def test_emits_handler_result_as_json(self):
        code, out = run_with(lambda e: {"ok": e["v"]}, '{"v": 1}')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"ok": 1})

    def test_handler_returning_none_emits_nothing(self):
        code, out = run_with(lambda e: None, "{}")
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_handler_exception_exits_zero_with_empty_stdout(self):
        def boom(event):
            raise RuntimeError("kaboom")
        code, out = run_with(boom, "{}")
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_malformed_stdin_exits_zero_with_empty_stdout(self):
        code, out = run_with(lambda e: {"never": True}, "not json at all")
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_kill_switch_skips_handler(self):
        def boom(event):
            raise AssertionError("handler 不该被调用")
        code, out = run_with(boom, "{}", env={"CC_DIALOGS": "off"})
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_kill_switch_is_case_insensitive(self):
        code, out = run_with(lambda e: {"x": 1}, "{}", env={"CC_DIALOGS": "OFF"})
        self.assertEqual(out, "")

    def test_unset_kill_switch_runs_handler(self):
        code, out = run_with(lambda e: {"x": 1}, "{}", env={"CC_DIALOGS": ""})
        self.assertEqual(json.loads(out), {"x": 1})


class TestDisabled(unittest.TestCase):
    def test_off_is_disabled(self):
        with mock.patch.dict(os.environ, {"CC_DIALOGS": "off"}):
            self.assertTrue(hookio.disabled())

    def test_anything_else_is_enabled(self):
        for v in ("", "on", "1", "true"):
            with mock.patch.dict(os.environ, {"CC_DIALOGS": v}):
                self.assertFalse(hookio.disabled())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `py -3 -m unittest discover -s packages/cc-dialogs/tests -v`

Expected: FAIL —— `ModuleNotFoundError: No module named 'ccdialogs.hookio'`

- [ ] **Step 3: 写最小实现**

`packages/cc-dialogs/hooks/ccdialogs/hookio.py`：

```python
"""Hook 入口的 stdin/stdout 协议与降级铁律。

铁律：任何异常都以 exit 0 + 空 stdout 收场。Claude Code 把「无输出」
解释为「hook 不做决定」，于是自动回退到终端 TUI —— 脚本崩溃永远不会
卡住用户的会话。
"""

import json
import os
import sys


def disabled():
    """总开关：CC_DIALOGS=off 时禁用全部对话框。"""
    return os.environ.get("CC_DIALOGS", "").strip().lower() == "off"


def run(handler):
    """读 stdin JSON 交给 handler，把返回值写为 stdout JSON。永不抛出。"""
    result = None
    try:
        if not disabled():
            result = handler(json.loads(sys.stdin.read()))
    except BaseException:
        result = None

    if result is not None:
        try:
            sys.stdout.write(json.dumps(result))
        except BaseException:
            pass

    sys.exit(0)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `py -3 -m unittest discover -s packages/cc-dialogs/tests -v`

Expected: PASS，9 个测试全绿

- [ ] **Step 5: Commit**

```bash
git add packages/cc-dialogs/hooks/ccdialogs/hookio.py packages/cc-dialogs/tests/test_hookio.py
git commit -m "feat(cc-dialogs): hookio 协议与降级铁律"
```

---

### Task 4: focus — 窗口标题比对

纯函数，无平台依赖，是整个通知策略的核心判据。

**Files:**
- Create: `packages/cc-dialogs/hooks/ccdialogs/focus.py`
- Test: `packages/cc-dialogs/tests/test_focus.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `segments(title: str) -> list[str]` —— 按 `—` `–` `|` ` - ` 切段并去空白
  - `same_window(baseline: dict | None, current: dict | None) -> bool` —— 两者形如 `{"app": str, "title": str}`；返回 True 表示「用户仍在看这个窗口」

- [ ] **Step 1: 写失败的测试**

`packages/cc-dialogs/tests/test_focus.py`：

```python
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))

from ccdialogs import focus

VSCODE = "Code"
TERM = "WindowsTerminal"


def w(app, title):
    return {"app": app, "title": title}


class TestSegments(unittest.TestCase):
    def test_em_dash(self):
        self.assertEqual(
            focus.segments("a.ts — proj — Visual Studio Code"),
            ["a.ts", "proj", "Visual Studio Code"],
        )

    def test_pipe(self):
        self.assertEqual(focus.segments("a | b | c"), ["a", "b", "c"])

    def test_spaced_hyphen_splits_but_hyphenated_word_does_not(self):
        self.assertEqual(focus.segments("my-proj - zsh"), ["my-proj", "zsh"])

    def test_single_segment(self):
        self.assertEqual(focus.segments("bash"), ["bash"])

    def test_empty_segments_dropped(self):
        self.assertEqual(focus.segments("a ——  — b"), ["a", "b"])


class TestSameWindow(unittest.TestCase):
    def test_no_baseline_assumes_focused(self):
        # 插件中途安装时没有基准 —— 宁可漏发通知，不可误扰
        self.assertTrue(focus.same_window(None, w(VSCODE, "x")))

    def test_no_current_assumes_focused(self):
        self.assertTrue(focus.same_window(w(VSCODE, "x"), None))

    def test_identical_is_same(self):
        self.assertTrue(focus.same_window(w(TERM, "proj"), w(TERM, "proj")))

    def test_different_app_is_not_same(self):
        self.assertFalse(focus.same_window(w(VSCODE, "p"), w("chrome", "p")))

    def test_vscode_switching_files_is_same_window(self):
        self.assertTrue(focus.same_window(
            w(VSCODE, "a.ts — proj — Visual Studio Code"),
            w(VSCODE, "b.ts — proj — Visual Studio Code"),
        ))

    def test_vscode_different_projects_is_not_same_window(self):
        # 这是「最长公共后缀 + 字符阈值」方案会失手的用例：
        # 两者共享 " — Visual Studio Code"（21 字符），但项目不同
        self.assertFalse(focus.same_window(
            w(VSCODE, "a.ts — proj — Visual Studio Code"),
            w(VSCODE, "a.ts — other — Visual Studio Code"),
        ))

    def test_two_segment_terminal_requires_exact_match(self):
        # 只有两段时丢弃首段会只剩 "zsh"，那会匹配上任意 zsh 窗口
        self.assertFalse(focus.same_window(
            w(TERM, "proj — zsh"), w(TERM, "other — zsh")))

    def test_two_segment_terminal_same_title(self):
        self.assertTrue(focus.same_window(
            w(TERM, "proj — zsh"), w(TERM, "proj — zsh")))

    def test_mixed_separator_styles(self):
        self.assertTrue(focus.same_window(
            w(VSCODE, "a.ts | proj | Visual Studio Code"),
            w(VSCODE, "b.ts — proj — Visual Studio Code"),
        ))

    def test_missing_title_keys_do_not_crash(self):
        self.assertFalse(focus.same_window({"app": VSCODE}, {"app": "chrome"}))
        self.assertTrue(focus.same_window({"app": VSCODE}, {"app": VSCODE}))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `py -3 -m unittest discover -s packages/cc-dialogs/tests -v`

Expected: FAIL —— `ModuleNotFoundError: No module named 'ccdialogs.focus'`

- [ ] **Step 3: 写最小实现**

`packages/cc-dialogs/hooks/ccdialogs/focus.py`：

```python
"""判断「用户是否仍在看这个 Claude 会话所在的窗口」。

策略：在 UserPromptSubmit 时刻记录前台窗口作为基准 —— 用户按下回车那一刻，
其窗口必然是前台的 —— 然后在 Stop 时刻与当前前台窗口比对。

不用「最长公共后缀 + 字符阈值」：两个开着不同项目的 VS Code 窗口同样共享
" — Visual Studio Code"（21 字符）这段后缀，不存在安全的阈值。按分隔符切段
比较则天然区分：proj 与 other 是不同的段。
"""

import re

_SEP_RE = re.compile(r"\s*[—–|]\s*|\s+-\s+")


def segments(title):
    """按常见标题分隔符切段，去掉空白与空段。"""
    return [s for s in (p.strip() for p in _SEP_RE.split(title or "")) if s]


def same_window(baseline, current):
    """True 表示用户仍在看基准窗口（此时不该发通知）。

    缺基准或缺当前窗口信息时返回 True —— 宁可漏发，不可误扰。
    """
    if not baseline or not current:
        return True

    if baseline.get("app") != current.get("app"):
        return False

    bt = baseline.get("title", "") or ""
    ct = current.get("title", "") or ""
    if bt == ct:
        return True

    bs, cs = segments(bt), segments(ct)
    # 三段以上时丢弃首段（通常是易变的文件名），比较其余段。
    # 两段及以下要求全等：终端标题形如 "proj — zsh"，丢弃首段只剩 "zsh"，
    # 会匹配上任意一个同 shell 的窗口。
    if len(bs) >= 3 and len(cs) >= 3:
        return bs[1:] == cs[1:]
    return False
```

- [ ] **Step 4: 运行测试确认通过**

Run: `py -3 -m unittest discover -s packages/cc-dialogs/tests -v`

Expected: PASS，全部测试绿

- [ ] **Step 5: Commit**

```bash
git add packages/cc-dialogs/hooks/ccdialogs/focus.py packages/cc-dialogs/tests/test_focus.py
git commit -m "feat(cc-dialogs): 窗口标题比对逻辑"
```

---

### Task 5: state — session 状态存储

**Files:**
- Create: `packages/cc-dialogs/hooks/ccdialogs/state.py`
- Test: `packages/cc-dialogs/tests/test_state.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `state_dir() -> pathlib.Path` —— Windows `%LOCALAPPDATA%\cc-dialogs`，其他 `~/.cache/cc-dialogs`
  - `save(session_id: str, data: dict) -> None`
  - `load(session_id: str) -> dict | None` —— 不存在或损坏时返回 None
  - `clear(session_id: str) -> None`
  - `prune(max_age_days: int = 7) -> None` —— 删除过期文件，失败静默

- [ ] **Step 1: 写失败的测试**

`packages/cc-dialogs/tests/test_state.py`：

```python
import os
import sys
import time
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))

from ccdialogs import state


class StateTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(
            state, "state_dir", lambda: __import__("pathlib").Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)


class TestRoundTrip(StateTestCase):
    def test_save_then_load(self):
        state.save("s1", {"app": "Code", "title": "x"})
        self.assertEqual(state.load("s1"), {"app": "Code", "title": "x"})

    def test_load_missing_returns_none(self):
        self.assertIsNone(state.load("nope"))

    def test_load_corrupt_returns_none(self):
        p = state.state_dir() / "bad.json"
        p.write_text("{ not json", encoding="utf-8")
        self.assertIsNone(state.load("bad"))

    def test_clear_removes_file(self):
        state.save("s1", {"a": 1})
        state.clear("s1")
        self.assertIsNone(state.load("s1"))

    def test_clear_missing_does_not_raise(self):
        state.clear("never-existed")

    def test_session_id_with_path_separators_is_sanitised(self):
        # session_id 直接拼进路径会造成目录穿越
        state.save("../../evil", {"a": 1})
        self.assertEqual(state.load("../../evil"), {"a": 1})
        children = list(state.state_dir().iterdir())
        self.assertEqual(len(children), 1)
        self.assertNotIn("..", children[0].name)


class TestPrune(StateTestCase):
    def test_prune_removes_old_files(self):
        state.save("old", {"a": 1})
        p = state.state_dir() / (state._safe_name("old") + ".json")
        old = time.time() - 8 * 86400
        os.utime(p, (old, old))
        state.prune(max_age_days=7)
        self.assertIsNone(state.load("old"))

    def test_prune_keeps_fresh_files(self):
        state.save("fresh", {"a": 1})
        state.prune(max_age_days=7)
        self.assertEqual(state.load("fresh"), {"a": 1})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `py -3 -m unittest discover -s packages/cc-dialogs/tests -v`

Expected: FAIL —— `ModuleNotFoundError: No module named 'ccdialogs.state'`

- [ ] **Step 3: 写最小实现**

`packages/cc-dialogs/hooks/ccdialogs/state.py`：

```python
"""Per-session 状态存储：保存焦点基准，供 Stop 时刻比对。"""

import json
import os
import pathlib
import re
import sys
import time

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def state_dir():
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return pathlib.Path(base) / "cc-dialogs"


def _safe_name(session_id):
    """session_id 会被拼进路径，必须消毒以防目录穿越。"""
    return _UNSAFE.sub("_", str(session_id))[:128] or "unnamed"


def _path(session_id):
    return state_dir() / (_safe_name(session_id) + ".json")


def save(session_id, data):
    d = state_dir()
    d.mkdir(parents=True, exist_ok=True)
    _path(session_id).write_text(json.dumps(data), encoding="utf-8")


def load(session_id):
    try:
        return json.loads(_path(session_id).read_text(encoding="utf-8"))
    except Exception:
        return None


def clear(session_id):
    try:
        _path(session_id).unlink()
    except Exception:
        pass


def prune(max_age_days=7):
    """删除过期状态文件，防止会话异常终止时泄漏。失败静默。"""
    cutoff = time.time() - max_age_days * 86400
    try:
        for p in state_dir().glob("*.json"):
            try:
                if p.stat().st_mtime < cutoff:
                    p.unlink()
            except Exception:
                pass
    except Exception:
        pass
```

- [ ] **Step 4: 运行测试确认通过**

Run: `py -3 -m unittest discover -s packages/cc-dialogs/tests -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/cc-dialogs/hooks/ccdialogs/state.py packages/cc-dialogs/tests/test_state.py
git commit -m "feat(cc-dialogs): session 状态存储"
```

---

### Task 6: UI 抽象层与 Windows 权限对话框

第一个端到端可见成果：权限确认弹出原生窗口。

**Files:**
- Create: `packages/cc-dialogs/hooks/ccdialogs/ui/__init__.py`
- Create: `packages/cc-dialogs/hooks/ccdialogs/ui/windows.py`
- Create: `packages/cc-dialogs/hooks/ccdialogs/ui/win/permission.ps1`
- Modify: `packages/cc-dialogs/hooks/permission_dialog.py`
- Test: `packages/cc-dialogs/tests/test_ui_dispatch.py`

**Interfaces:**
- Consumes: `hookio.run`
- Produces:
  - `ui.ask_permission(title: str, body: str, allow_always: bool) -> str` —— 返回 `"allow"` / `"always"` / `"deny"` / `"cancel"`
  - `ui.backend()` —— 按 `sys.platform` 返回后端模块，不支持的平台抛 `RuntimeError`
  - `windows.run_ps(script_name: str, params: dict) -> dict` —— 通用 ps1 调用器

- [ ] **Step 1: 写失败的测试（仅测平台分发，不测真实弹窗）**

`packages/cc-dialogs/tests/test_ui_dispatch.py`：

```python
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))

from ccdialogs import ui


class TestBackend(unittest.TestCase):
    def test_win32_selects_windows_backend(self):
        with mock.patch.object(sys, "platform", "win32"):
            self.assertEqual(ui.backend().__name__.split(".")[-1], "windows")

    def test_darwin_selects_macos_backend(self):
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertEqual(ui.backend().__name__.split(".")[-1], "macos")

    def test_unsupported_platform_raises(self):
        with mock.patch.object(sys, "platform", "linux"):
            with self.assertRaises(RuntimeError):
                ui.backend()


class TestAskPermissionDelegates(unittest.TestCase):
    def test_delegates_to_backend(self):
        fake = mock.Mock()
        fake.ask_permission.return_value = "allow"
        with mock.patch.object(ui, "backend", lambda: fake):
            self.assertEqual(ui.ask_permission("t", "b", True), "allow")
        fake.ask_permission.assert_called_once_with("t", "b", True)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `py -3 -m unittest discover -s packages/cc-dialogs/tests -v`

Expected: FAIL —— `ModuleNotFoundError: No module named 'ccdialogs.ui'`

- [ ] **Step 3: 写抽象层**

`packages/cc-dialogs/hooks/ccdialogs/ui/__init__.py`：

```python
"""四个 UI 原语的抽象与平台分发。

平台差异全部隔离在本包内；上层只调用这四个函数。
"""

import importlib
import sys

_BACKENDS = {"win32": "windows", "darwin": "macos"}


def backend():
    name = _BACKENDS.get(sys.platform)
    if not name:
        raise RuntimeError("cc-dialogs: unsupported platform %r" % sys.platform)
    return importlib.import_module("ccdialogs.ui." + name)


def ask_permission(title, body, allow_always):
    """返回 'allow' / 'always' / 'deny' / 'cancel'。"""
    return backend().ask_permission(title, body, allow_always)


def ask_choice(title, prompt, options, multi):
    """返回选中的 label 列表；取消时返回 []。"""
    return backend().ask_choice(title, prompt, options, multi)


def notify(title, body):
    backend().notify(title, body)


def frontmost():
    """返回 {'app': str, 'title': str}；取不到时返回 None。"""
    return backend().frontmost()
```

- [ ] **Step 4: 写 Windows 后端的 ps1 调用器与权限对话框**

`packages/cc-dialogs/hooks/ccdialogs/ui/windows.py`：

```python
"""Windows 后端：把参数写成 JSON 临时文件，交给 ps1 执行，从 stdout 读回 JSON。

不在 Python 里拼 PowerShell 字符串 —— 多层转义极易出错且难以调试。
"""

import json
import os
import pathlib
import subprocess
import tempfile

_PS_DIR = pathlib.Path(__file__).parent / "win"


def run_ps(script_name, params):
    script = _PS_DIR / script_name
    fd, tmp = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(params, f)
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-STA",
             "-ExecutionPolicy", "Bypass", "-File", str(script), "-ParamsPath", tmp],
            capture_output=True, text=True, encoding="utf-8",
        )
        out = (proc.stdout or "").strip()
        return json.loads(out) if out else {}
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def ask_permission(title, body, allow_always):
    r = run_ps("permission.ps1", {
        "title": title, "body": body, "allowAlways": bool(allow_always)})
    return r.get("result", "cancel")
```

- [ ] **Step 5: 写权限对话框的 ps1**

`packages/cc-dialogs/hooks/ccdialogs/ui/win/permission.ps1`：

```powershell
param([Parameter(Mandatory=$true)][string]$ParamsPath)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$p = Get-Content -LiteralPath $ParamsPath -Raw -Encoding UTF8 | ConvertFrom-Json

$form                   = New-Object System.Windows.Forms.Form
$form.Text              = $p.title
$form.Size              = New-Object System.Drawing.Size(620, 380)
$form.StartPosition     = 'CenterScreen'
$form.TopMost           = $true
$form.FormBorderStyle   = 'FixedDialog'
$form.MaximizeBox       = $false
$form.MinimizeBox       = $false

# 只读多行滚动框：长 Bash 命令与大段 diff 无需截断
$box            = New-Object System.Windows.Forms.TextBox
$box.Multiline  = $true
$box.ReadOnly   = $true
$box.ScrollBars = 'Vertical'
$box.WordWrap   = $true
$box.Font       = New-Object System.Drawing.Font('Consolas', 9)
$box.Text       = $p.body
$box.Location   = New-Object System.Drawing.Point(12, 12)
$box.Size       = New-Object System.Drawing.Size(580, 270)
$box.Anchor     = 'Top,Left,Right,Bottom'
$form.Controls.Add($box)

$script:result = 'cancel'

function New-ActionButton($text, $value, $x) {
  $b          = New-Object System.Windows.Forms.Button
  $b.Text     = $text
  $b.Size     = New-Object System.Drawing.Size(120, 30)
  $b.Location = New-Object System.Drawing.Point($x, 296)
  $b.Anchor   = 'Bottom,Right'
  $b.Add_Click({ $script:result = $value; $form.Close() }.GetNewClosure())
  return $b
}

$deny  = New-ActionButton '拒绝'     'deny'   344
$allow = New-ActionButton '允许'     'allow'  472
$form.Controls.Add($deny)
$form.Controls.Add($allow)

if ($p.allowAlways) {
  $always = New-ActionButton '总是允许' 'always' 216
  $form.Controls.Add($always)
}

$form.AcceptButton = $allow
$form.CancelButton = $deny
$form.Add_Shown({ $form.Activate(); $allow.Focus() })
[void]$form.ShowDialog()

@{ result = $script:result } | ConvertTo-Json -Compress
```

- [ ] **Step 6: 接上入口脚本**

`packages/cc-dialogs/hooks/permission_dialog.py`：

```python
"""PermissionRequest hook：把终端的 y/n 提示换成原生对话框。

输出 schema（注意 behaviour 是英式拼写）：
  {"hookSpecificOutput": {"hookEventName": "PermissionRequest",
                          "decision": {"behaviour": "allow"|"deny", ...}}}
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ccdialogs import hookio, ui


def _body(event):
    tool = event.get("tool_name", "?")
    payload = json.dumps(event.get("tool_input", {}), indent=2, ensure_ascii=False)
    return "工具：%s\n\n%s" % (tool, payload)


def handle(event):
    suggestions = event.get("permission_suggestions") or []
    choice = ui.ask_permission(
        "Claude Code 请求权限", _body(event), bool(suggestions))

    if choice == "allow":
        decision = {"behaviour": "allow"}
    elif choice == "always":
        # updatedPermissions 原样透传 —— 脚本不解析也不构造权限规则
        decision = {"behaviour": "allow", "updatedPermissions": suggestions}
    elif choice == "deny":
        decision = {"behaviour": "deny", "message": "User denied via native dialog"}
    else:
        return None  # 取消 → 不做决定 → 回退终端 TUI

    return {"hookSpecificOutput": {
        "hookEventName": "PermissionRequest", "decision": decision}}


if __name__ == "__main__":
    hookio.run(handle)
```

四个入口脚本的 `hookio.run` 都必须放在 `if __name__ == "__main__"` 内 —— 否则测试
import 该模块时会立即读 stdin 并退出，测试进程直接挂死。

- [ ] **Step 7: 运行单测确认通过**

Run: `py -3 -m unittest discover -s packages/cc-dialogs/tests -v`

Expected: PASS

- [ ] **Step 8: 真机验收**

开新 CC 会话，让它跑一条需要授权的命令。逐项确认：

- [ ] 弹出原生窗口，标题「Claude Code 请求权限」，正文含工具名与参数
- [ ] 点「允许」→ 命令执行，终端未出现 y/n 提示
- [ ] 点「拒绝」→ 命令被阻止，Claude 收到拒绝理由
- [ ] 点「总是允许」→ 命令执行，且规则写入项目 localSettings（检查 `.claude/settings.local.json`）
- [ ] 直接关窗口 → 回退到终端 y/n 提示，会话不卡
- [ ] 设 `CC_DIALOGS=off` 后开新会话 → 完全走终端，不弹窗
- [ ] 给一条超长命令（如粘贴 200 行脚本）→ 正文可滚动，窗口不变形

- [ ] **Step 9: Commit**

```bash
git add packages/cc-dialogs/hooks/ccdialogs/ui/ packages/cc-dialogs/hooks/permission_dialog.py packages/cc-dialogs/tests/test_ui_dispatch.py
git commit -m "feat(cc-dialogs): Windows 原生权限对话框"
```

---

### Task 7: Windows 选项对话框

**Files:**
- Create: `packages/cc-dialogs/hooks/ccdialogs/ui/win/choice.ps1`
- Modify: `packages/cc-dialogs/hooks/ccdialogs/ui/windows.py`
- Modify: `packages/cc-dialogs/hooks/question_dialog.py`
- Test: `packages/cc-dialogs/tests/test_question_payload.py`

**Interfaces:**
- Consumes: `ui.ask_choice`、`hookio.run`
- Produces:
  - `question_dialog.build_answers(questions: list[dict], picks: dict[int, list[str]]) -> dict[str, str]`
    —— 纯函数，供测试；把每题选中的 label 列表转成 `{question 原文: "A, B"}`

- [ ] **Step 1: 写失败的测试**

`packages/cc-dialogs/tests/test_question_payload.py`：

```python
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))

import question_dialog as qd

QUESTIONS = [
    {"question": "选哪个框架？", "options": [{"label": "React"}, {"label": "Vue"}]},
    {"question": "要哪些特性？", "options": [{"label": "A"}, {"label": "B"}]},
]


class TestBuildAnswers(unittest.TestCase):
    def test_key_is_verbatim_question_text(self):
        out = qd.build_answers(QUESTIONS, {0: ["React"]})
        self.assertIn("选哪个框架？", out)

    def test_single_choice_value_is_plain_string(self):
        out = qd.build_answers(QUESTIONS, {0: ["React"]})
        self.assertEqual(out["选哪个框架？"], "React")
        self.assertIsInstance(out["选哪个框架？"], str)

    def test_multi_choice_joined_with_comma_space(self):
        # value 恒为 string，绝不是数组
        out = qd.build_answers(QUESTIONS, {1: ["A", "B"]})
        self.assertEqual(out["要哪些特性？"], "A, B")

    def test_unanswered_question_omitted(self):
        out = qd.build_answers(QUESTIONS, {0: ["Vue"]})
        self.assertNotIn("要哪些特性？", out)

    def test_empty_pick_omitted(self):
        out = qd.build_answers(QUESTIONS, {0: []})
        self.assertEqual(out, {})

    def test_all_questions_answered(self):
        out = qd.build_answers(QUESTIONS, {0: ["Vue"], 1: ["B"]})
        self.assertEqual(out, {"选哪个框架？": "Vue", "要哪些特性？": "B"})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `py -3 -m unittest discover -s packages/cc-dialogs/tests -v`

Expected: FAIL —— `AttributeError: module 'question_dialog' has no attribute 'build_answers'`

- [ ] **Step 3: 写选项对话框的 ps1**

`packages/cc-dialogs/hooks/ccdialogs/ui/win/choice.ps1`：

```powershell
param([Parameter(Mandatory=$true)][string]$ParamsPath)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$p = Get-Content -LiteralPath $ParamsPath -Raw -Encoding UTF8 | ConvertFrom-Json

$form                 = New-Object System.Windows.Forms.Form
$form.Text            = $p.title
$form.Size            = New-Object System.Drawing.Size(560, 420)
$form.StartPosition   = 'CenterScreen'
$form.TopMost         = $true
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox     = $false
$form.MinimizeBox     = $false

$label          = New-Object System.Windows.Forms.Label
$label.Text     = $p.prompt
$label.Location = New-Object System.Drawing.Point(12, 12)
$label.Size     = New-Object System.Drawing.Size(520, 40)
$form.Controls.Add($label)

# 多选用 CheckedListBox，单选用 ListBox —— 语义直观，无需额外说明文字
if ($p.multi) {
  $list = New-Object System.Windows.Forms.CheckedListBox
  $list.CheckOnClick = $true
} else {
  $list = New-Object System.Windows.Forms.ListBox
}
$list.Location = New-Object System.Drawing.Point(12, 58)
$list.Size     = New-Object System.Drawing.Size(520, 260)
$list.Font     = New-Object System.Drawing.Font('Segoe UI', 10)
foreach ($o in $p.options) { [void]$list.Items.Add($o) }
if (-not $p.multi -and $list.Items.Count -gt 0) { $list.SelectedIndex = 0 }
$form.Controls.Add($list)

$script:picked = @()

$ok          = New-Object System.Windows.Forms.Button
$ok.Text     = '确定'
$ok.Size     = New-Object System.Drawing.Size(110, 30)
$ok.Location = New-Object System.Drawing.Point(412, 332)
$ok.Add_Click({
  if ($p.multi) { $script:picked = @($list.CheckedItems) }
  elseif ($null -ne $list.SelectedItem) { $script:picked = @($list.SelectedItem) }
  $form.Close()
})
$form.Controls.Add($ok)

$cancel          = New-Object System.Windows.Forms.Button
$cancel.Text     = '取消'
$cancel.Size     = New-Object System.Drawing.Size(110, 30)
$cancel.Location = New-Object System.Drawing.Point(292, 332)
$cancel.Add_Click({ $script:picked = @(); $form.Close() })
$form.Controls.Add($cancel)

$form.AcceptButton = $ok
$form.CancelButton = $cancel
$form.Add_Shown({ $form.Activate(); $list.Focus() })
[void]$form.ShowDialog()

@{ picked = @($script:picked) } | ConvertTo-Json -Compress -Depth 3
```

- [ ] **Step 4: 在 Windows 后端加 ask_choice**

追加到 `packages/cc-dialogs/hooks/ccdialogs/ui/windows.py`：

```python
def ask_choice(title, prompt, options, multi):
    r = run_ps("choice.ps1", {
        "title": title, "prompt": prompt,
        "options": list(options), "multi": bool(multi)})
    picked = r.get("picked") or []
    # ConvertTo-Json 对单元素数组会退化成标量
    if isinstance(picked, str):
        picked = [picked]
    return [str(x) for x in picked]
```

- [ ] **Step 5: 写入口脚本**

`packages/cc-dialogs/hooks/question_dialog.py`：

```python
"""PreToolUse / AskUserQuestion hook：把终端选项框换成原生列表。

机制：不 deny，而是 allow + updatedInput —— 把用户的选择预填进
tool_input.answers 后放行。工具照常执行，但因答案已备齐，CC 跳过 TUI
直接返回结果。

answers 的 key 是 question["question"] 的原文；value 恒为 string，
多选用 ", " 拼接。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ccdialogs import hookio, ui


def build_answers(questions, picks):
    """把 {题号: [label, ...]} 转成 {question 原文: "A, B"}。空选跳过。"""
    answers = {}
    for i, q in enumerate(questions):
        chosen = picks.get(i) or []
        if chosen:
            answers[q["question"]] = ", ".join(chosen)
    return answers


def handle(event):
    tool_input = event.get("tool_input") or {}
    questions = tool_input.get("questions") or []
    if not questions:
        return None

    picks = {}
    for i, q in enumerate(questions):
        labels = [o.get("label", "") for o in (q.get("options") or [])]
        if not labels:
            return None
        chosen = ui.ask_choice(
            q.get("header") or "Claude Code",
            q.get("question", ""),
            labels,
            bool(q.get("multiSelect")),
        )
        if not chosen:
            return None  # 任一题取消 → 整体回退终端 TUI
        picks[i] = chosen

    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "updatedInput": {
            "questions": questions,
            "answers": build_answers(questions, picks),
        },
    }}


if __name__ == "__main__":
    hookio.run(handle)
```

注意：`hookio.run` 放在 `if __name__ == "__main__"` 内，否则测试 import 时会读 stdin 并退出。

- [ ] **Step 6: 运行测试确认通过**

Run: `py -3 -m unittest discover -s packages/cc-dialogs/tests -v`

Expected: PASS

- [ ] **Step 7: 真机验收**

让 Claude 用 AskUserQuestion 问你问题（例如「问我三个关于配色的选择题，其中一个多选」）：

- [ ] 单选题弹出 ListBox，默认选中第一项
- [ ] 多选题弹出带勾选框的 CheckedListBox
- [ ] 多题时依次弹出，全部答完后 Claude 直接收到答案，终端无选项框
- [ ] 多选选两项 → Claude 收到的答案形如 `"A, C"`
- [ ] 中途取消任一题 → 回退到终端选项框，会话不卡

- [ ] **Step 8: Commit**

```bash
git add packages/cc-dialogs/hooks/ccdialogs/ui/win/choice.ps1 packages/cc-dialogs/hooks/ccdialogs/ui/windows.py packages/cc-dialogs/hooks/question_dialog.py packages/cc-dialogs/tests/test_question_payload.py
git commit -m "feat(cc-dialogs): Windows 原生选项对话框"
```

---

### Task 8: Windows 前台窗口探测与通知

**Files:**
- Create: `packages/cc-dialogs/hooks/ccdialogs/ui/win/frontmost.ps1`
- Create: `packages/cc-dialogs/hooks/ccdialogs/ui/win/notify.ps1`
- Modify: `packages/cc-dialogs/hooks/ccdialogs/ui/windows.py`

**Interfaces:**
- Consumes: `windows.run_ps`
- Produces: `windows.frontmost() -> dict | None`、`windows.notify(title, body) -> None`

- [ ] **Step 1: 写 frontmost.ps1**

`packages/cc-dialogs/hooks/ccdialogs/ui/win/frontmost.ps1`：

```powershell
param([string]$ParamsPath)

$ErrorActionPreference = 'Stop'

# 取的是 HWND 而非 PID：VS Code / Cursor 的多个窗口共用同一个进程，
# PID 比对必然误判；GetForegroundWindow 拿到的是具体那一个窗口。
Add-Type @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public class CcFg {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)]
  public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")]
  public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
}
'@

$h = [CcFg]::GetForegroundWindow()
if ($h -eq [IntPtr]::Zero) { '{}'; exit 0 }

$len = [CcFg]::GetWindowTextLength($h)
$sb  = New-Object System.Text.StringBuilder ($len + 1)
[void][CcFg]::GetWindowText($h, $sb, $sb.Capacity)

$pid = 0
[void][CcFg]::GetWindowThreadProcessId($h, [ref]$pid)
$app = try { (Get-Process -Id $pid -ErrorAction Stop).ProcessName } catch { '' }

@{ app = $app; title = $sb.ToString() } | ConvertTo-Json -Compress
```

- [ ] **Step 2: 写 notify.ps1**

`packages/cc-dialogs/hooks/ccdialogs/ui/win/notify.ps1`：

```powershell
param([Parameter(Mandatory=$true)][string]$ParamsPath)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms

$p = Get-Content -LiteralPath $ParamsPath -Raw -Encoding UTF8 | ConvertFrom-Json

$icon                 = New-Object System.Windows.Forms.NotifyIcon
$icon.Icon            = [System.Drawing.SystemIcons]::Information
$icon.Visible         = $true
$icon.BalloonTipTitle = $p.title
$icon.BalloonTipText  = $p.body
$icon.ShowBalloonTip(5000)

# NotifyIcon 的气泡依赖进程存活：立即退出气泡就不显示。
Start-Sleep -Milliseconds 1200
$icon.Visible = $false
$icon.Dispose()

'{}'
```

- [ ] **Step 3: 在 Windows 后端接上**

追加到 `packages/cc-dialogs/hooks/ccdialogs/ui/windows.py`：

```python
def frontmost():
    r = run_ps("frontmost.ps1", {})
    if not r or not r.get("app"):
        return None
    return {"app": r.get("app", ""), "title": r.get("title", "")}


def notify(title, body):
    run_ps("notify.ps1", {"title": title, "body": body})
```

- [ ] **Step 4: 手工验证两个原语**

Run:

```bash
cd packages/cc-dialogs/hooks
py -3 -c "import sys; sys.path.insert(0,'.'); from ccdialogs.ui import windows as w; print(w.frontmost())"
```

Expected：打印当前前台窗口，如 `{'app': 'WindowsTerminal', 'title': '...'}`。切到 VS Code 再跑一次，`app` 应变为 `Code`。

Run:

```bash
py -3 -c "import sys; sys.path.insert(0,'.'); from ccdialogs.ui import windows as w; w.notify('cc-dialogs', '测试通知')"
```

Expected：右下角出现系统通知气泡。

- [ ] **Step 5: Commit**

```bash
git add packages/cc-dialogs/hooks/ccdialogs/ui/win/frontmost.ps1 packages/cc-dialogs/hooks/ccdialogs/ui/win/notify.ps1 packages/cc-dialogs/hooks/ccdialogs/ui/windows.py
git commit -m "feat(cc-dialogs): Windows 前台窗口探测与系统通知"
```

---

### Task 9: 焦点基准记录与空闲通知

**Files:**
- Modify: `packages/cc-dialogs/hooks/focus_baseline.py`
- Modify: `packages/cc-dialogs/hooks/idle_notify.py`
- Test: `packages/cc-dialogs/tests/test_idle_notify.py`

**Interfaces:**
- Consumes: `focus.same_window`、`state.save/load/prune`、`ui.frontmost/notify`
- Produces: `idle_notify.should_notify(session_id: str, current: dict | None) -> bool`

- [ ] **Step 1: 写失败的测试**

`packages/cc-dialogs/tests/test_idle_notify.py`：

```python
import os
import sys
import tempfile
import pathlib
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))

from ccdialogs import state
import idle_notify


class TestShouldNotify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        p = mock.patch.object(state, "state_dir",
                              lambda: pathlib.Path(self.tmp.name))
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_no_baseline_does_not_notify(self):
        self.assertFalse(idle_notify.should_notify("s", {"app": "Code", "title": "x"}))

    def test_same_window_does_not_notify(self):
        state.save("s", {"app": "Code", "title": "a.ts — p — Visual Studio Code"})
        self.assertFalse(idle_notify.should_notify(
            "s", {"app": "Code", "title": "b.ts — p — Visual Studio Code"}))

    def test_switched_away_notifies(self):
        state.save("s", {"app": "WindowsTerminal", "title": "proj"})
        self.assertTrue(idle_notify.should_notify("s", {"app": "chrome", "title": "x"}))

    def test_unknown_current_window_does_not_notify(self):
        state.save("s", {"app": "WindowsTerminal", "title": "proj"})
        self.assertFalse(idle_notify.should_notify("s", None))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `py -3 -m unittest discover -s packages/cc-dialogs/tests -v`

Expected: FAIL —— `AttributeError: module 'idle_notify' has no attribute 'should_notify'`

- [ ] **Step 3: 写基准记录脚本**

`packages/cc-dialogs/hooks/focus_baseline.py`：

```python
"""UserPromptSubmit hook：记录焦点基准。

用户按下回车提交 prompt 的那一刻，其窗口必然是前台的 —— 这是整个
焦点判定的锚点，无需白名单也无需项目名匹配。

本 hook 不产生任何输出，纯副作用。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ccdialogs import hookio, state, ui


def handle(event):
    session_id = event.get("session_id")
    if not session_id:
        return None
    win = ui.frontmost()
    if win:
        state.save(session_id, win)
    state.prune()
    return None


if __name__ == "__main__":
    hookio.run(handle)
```

- [ ] **Step 4: 写空闲通知脚本**

`packages/cc-dialogs/hooks/idle_notify.py`：

```python
"""Stop hook：Claude 停下等待时，若用户已切走窗口则发系统通知。

Stop 每轮对话结束都会触发，因此必须有判据，否则每答一句都弹通知。
判据是与 UserPromptSubmit 记录的基准比对。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ccdialogs import focus, hookio, state, ui


def should_notify(session_id, current):
    """仅当用户确实切走了窗口才通知。拿不准一律不通知。"""
    baseline = state.load(session_id)
    if not baseline:
        return False
    if not current:
        return False
    return not focus.same_window(baseline, current)


def handle(event):
    session_id = event.get("session_id")
    if not session_id:
        return None
    if should_notify(session_id, ui.frontmost()):
        ui.notify("Claude Code", "任务已完成，等待你的下一步")
    return None


if __name__ == "__main__":
    hookio.run(handle)
```

注意 `should_notify` 与 `focus.same_window` 的空值语义相反：`same_window` 缺基准时返回 True（视为在看），`should_notify` 因而返回 False（不通知）。两处都是「宁可漏发，不可误扰」。

- [ ] **Step 5: 运行测试确认通过**

Run: `py -3 -m unittest discover -s packages/cc-dialogs/tests -v`

Expected: PASS

- [ ] **Step 6: 真机验收**

- [ ] 停在终端窗口不动，让 Claude 答一句 → **不弹通知**
- [ ] 提交 prompt 后立刻切到浏览器，等 Claude 答完 → **弹出通知**
- [ ] VS Code 里提交 prompt，然后在同一窗口切换文件 → **不弹通知**
- [ ] 开两个不同项目的 VS Code 窗口，在 A 提交后切到 B → **弹出通知**
- [ ] 连续对话十轮不切窗口 → 一条通知都没有
- [ ] 检查 `%LOCALAPPDATA%\cc-dialogs\` 有对应 session 的 json 文件

- [ ] **Step 7: Commit**

```bash
git add packages/cc-dialogs/hooks/focus_baseline.py packages/cc-dialogs/hooks/idle_notify.py packages/cc-dialogs/tests/test_idle_notify.py
git commit -m "feat(cc-dialogs): 焦点基准记录与空闲通知"
```

---

### Task 10: macOS 后端

**Files:**
- Create: `packages/cc-dialogs/hooks/ccdialogs/ui/macos.py`

**Interfaces:**
- Consumes: `ui.backend()` 的分发约定
- Produces: 与 `windows.py` 完全相同的四个函数签名

**前置**：本任务需在 macOS 上执行验收。若暂无 macOS 设备，可先跳过并在 CHANGELOG 标注「macOS 后端未验证」。

- [ ] **Step 1: 写 macOS 后端**

`packages/cc-dialogs/hooks/ccdialogs/ui/macos.py`：

```python
"""macOS 后端：全部通过 osascript 调用系统原生 UI。"""

import subprocess

_TRUNCATE = 2000  # display dialog 有实际长度限制


def _osa(script):
    proc = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        # 用户取消时 osascript 以非零码退出 —— 视为取消，不是错误
        return None
    return (proc.stdout or "").strip()


def _q(s):
    """转义进 AppleScript 字符串字面量。"""
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')


def _clip(text):
    text = text or ""
    if len(text) <= _TRUNCATE:
        return text
    return text[:_TRUNCATE] + "\n…（还有 %d 字符，完整内容见终端）" % (
        len(text) - _TRUNCATE)


def ask_permission(title, body, allow_always):
    buttons = ['"拒绝"', '"总是允许"', '"允许"'] if allow_always else ['"拒绝"', '"允许"']
    script = (
        'display dialog "%s" with title "%s" buttons {%s} '
        'default button "允许"' % (_q(_clip(body)), _q(title), ", ".join(buttons))
    )
    out = _osa(script)
    if out is None:
        return "cancel"
    if "总是允许" in out:
        return "always"
    if "允许" in out:
        return "allow"
    if "拒绝" in out:
        return "deny"
    return "cancel"


def ask_choice(title, prompt, options, multi):
    items = ", ".join('"%s"' % _q(o) for o in options)
    script = (
        'set r to choose from list {%s} with title "%s" with prompt "%s"%s\n'
        'if r is false then return ""\n'
        'set AppleScript\'s text item delimiters to linefeed\n'
        'return r as text' % (
            items, _q(title), _q(prompt),
            " with multiple selections allowed" if multi else "")
    )
    out = _osa(script)
    if not out:
        return []
    return [line for line in out.split("\n") if line]


def notify(title, body):
    _osa('display notification "%s" with title "%s"' % (_q(body), _q(title)))


def frontmost():
    script = (
        'tell application "System Events"\n'
        '  set p to first application process whose frontmost is true\n'
        '  set n to name of p\n'
        '  try\n'
        '    set t to name of front window of p\n'
        '  on error\n'
        '    set t to ""\n'
        '  end try\n'
        'end tell\n'
        'return n & "\\n" & t'
    )
    out = _osa(script)
    if not out:
        return None
    parts = out.split("\n", 1)
    return {"app": parts[0], "title": parts[1] if len(parts) > 1 else ""}
```

- [ ] **Step 2: 运行单测确认未回归**

Run: `py -3 -m unittest discover -s packages/cc-dialogs/tests -v`

Expected: PASS（平台分发测试会覆盖 `darwin` → `macos` 的导入）

- [ ] **Step 3: macOS 真机验收**

在 macOS 上跑一遍 Task 6 Step 8、Task 7 Step 7、Task 9 Step 6 的全部验收项。额外确认：

- [ ] 超长命令被截断且末尾有「还有 N 字符」提示，对话框不撑爆
- [ ] `choose from list` 取消（点 Cancel）→ 回退终端
- [ ] 通知出现在通知中心，不抢焦点

- [ ] **Step 4: Commit**

```bash
git add packages/cc-dialogs/hooks/ccdialogs/ui/macos.py
git commit -m "feat(cc-dialogs): macOS 后端"
```

---

### Task 11: 收尾与发布

**Files:**
- Modify: `packages/cc-dialogs/README.md`
- Modify: `CATALOG.md`
- Modify: `packages/cc-dialogs/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: 前十个任务的全部成果
- Produces: 可发布的 0.1.0

- [ ] **Step 1: 补全 README**

在 `packages/cc-dialogs/README.md` 追加：

```markdown
## 工作原理

| Hook | 脚本 | 作用 |
|---|---|---|
| `PermissionRequest` | `permission_dialog.py` | 三按钮权限对话框 |
| `PreToolUse` (AskUserQuestion) | `question_dialog.py` | 选项列表，`allow` + `updatedInput` 回填答案 |
| `UserPromptSubmit` | `focus_baseline.py` | 记录焦点基准 |
| `Stop` | `idle_notify.py` | 比对基准，切走了才通知 |

## 已知限制

- RDP 断开后弹窗发给已断开的桌面，你看不到，Claude 会等到 600 秒超时后回退终端
- SSH 连入无桌面，全部功能静默禁用，行为与未安装一致
- 终端里 `cd` 到子目录若导致窗口标题变化，可能被判为切走窗口而多发一条通知
```

- [ ] **Step 2: 更新 CATALOG**

Run: `/update-catalog`

确认 `CATALOG.md` 的 Packages 表格出现 cc-dialogs 一行。

- [ ] **Step 3: 全量测试**

Run: `py -3 -m unittest discover -s packages/cc-dialogs/tests -v`

Expected: 全绿

- [ ] **Step 4: 切回远程模式验证发布形态**

Run: `/plugin-dev cc-dialogs remote`

确认插件仍能从缓存加载（而非依赖本地软链）。

- [ ] **Step 5: 发布**

Run: `/publish cc-dialogs minor`

版本从 `0.0.1` 升至 `0.1.0`，生成 CHANGELOG，打 tag 推送。

---

## Self-Review

**Spec 覆盖检查**：

| Spec 章节 | 对应任务 |
|---|---|
| 3.1 PermissionRequest schema | Task 6 |
| 3.2 updatedInput / answers | Task 7 |
| 3.4 hooks.json 与 timeout 600 | Task 2 |
| 4 目录结构 | Task 2–8 |
| 5 平台抽象层四原语 | Task 6（ask_permission）、7（ask_choice）、8（frontmost/notify）、10（macOS 全部） |
| 6.2 自校准基准 | Task 9 |
| 6.3 比对规则 | Task 4 |
| 6.4 状态存储 | Task 5 |
| 7 降级铁律与总开关 | Task 3 |
| 8 长内容处理 | Task 6（Windows 滚动框）、10（macOS 截断） |
| 9 plugin.json / marketplace.json | Task 1 |
| 10.1 Python 调用 spike | Task 1 |
| 11 测试策略 | Task 3、4、5、7、9 |

无遗漏。

**类型一致性**：`ask_permission` 返回四态字符串，`windows.py` 与 `macos.py` 一致；`ask_choice` 两端均返回 `list[str]`；`frontmost()` 两端均返回 `{"app", "title"}` 或 `None`；`same_window` 与 `should_notify` 的空值语义在 Task 9 Step 4 处显式说明。

**未覆盖的 spec 项**：`SessionEnd` 时清理状态文件未单独建任务 —— 由 `state.prune()` 在每次 `UserPromptSubmit` 时兜底（Task 9 Step 3），无需额外 hook。
