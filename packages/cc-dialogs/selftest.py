"""cc-dialogs 自检：验证焦点比对逻辑与 UI 原语。

    py -3 packages/cc-dialogs/selftest.py          # 只跑纯逻辑，两秒
    py -3 packages/cc-dialogs/selftest.py --ui     # 额外弹出真实对话框

焦点比对是唯一「错了也看不见」的部分 —— 判错时你只会觉得通知有点怪，
不会知道是哪条规则出的问题。所以它值得留个自检。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "hooks"))

from ccdialogs import focus

VSCODE, TERM = "Code", "WindowsTerminal"
_fails = []


def check(label, got, want):
    if got == want:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s  (got %r, want %r)" % (label, got, want))
        _fails.append(label)


def w(app, title):
    return {"app": app, "title": title}


def test_segments():
    print("segments:")
    check("破折号切段",
          focus.segments("a.ts — proj — Visual Studio Code"),
          ["a.ts", "proj", "Visual Studio Code"])
    check("竖线切段", focus.segments("a | b | c"), ["a", "b", "c"])
    check("带空格的连字符切段，词内连字符不切",
          focus.segments("my-proj - zsh"), ["my-proj", "zsh"])
    check("单段", focus.segments("bash"), ["bash"])
    check("空段被丢弃", focus.segments("a ——  — b"), ["a", "b"])


def test_same_window():
    print("same_window:")
    check("无基准视为在看（宁可漏发）",
          focus.same_window(None, w(VSCODE, "x")), True)
    check("拿不到当前窗口视为在看",
          focus.same_window(w(VSCODE, "x"), None), True)
    check("完全相同", focus.same_window(w(TERM, "proj"), w(TERM, "proj")), True)
    check("app 不同即失焦",
          focus.same_window(w(VSCODE, "p"), w("chrome", "p")), False)
    check("VS Code 切文件仍是同一窗口",
          focus.same_window(
              w(VSCODE, "a.ts — proj — Visual Studio Code"),
              w(VSCODE, "b.ts — proj — Visual Studio Code")), True)
    # 这是「最长公共后缀 + 字符阈值」方案会失手的用例：
    # 两者共享 " — Visual Studio Code"（21 字符），但项目不同
    check("不同项目的两个 VS Code 窗口不算同一窗口",
          focus.same_window(
              w(VSCODE, "a.ts — proj — Visual Studio Code"),
              w(VSCODE, "a.ts — other — Visual Studio Code")), False)
    check("两段式终端标题要求全等",
          focus.same_window(w(TERM, "proj — zsh"),
                            w(TERM, "other — zsh")), False)
    check("两段式终端标题相同",
          focus.same_window(w(TERM, "proj — zsh"),
                            w(TERM, "proj — zsh")), True)
    check("混用分隔符风格",
          focus.same_window(
              w(VSCODE, "a.ts | proj | Visual Studio Code"),
              w(VSCODE, "b.ts — proj — Visual Studio Code")), True)
    check("缺 title 键不崩",
          focus.same_window({"app": VSCODE}, {"app": VSCODE}), True)


def _run_hook(handler, stdin_text):
    """跑一次 hookio.run，返回 (exit_code, stdout)。"""
    import io
    from ccdialogs import hookio
    real_in, real_out = sys.stdin, sys.stdout
    sys.stdin, sys.stdout = io.StringIO(stdin_text), io.StringIO()
    try:
        hookio.run(handler)
    except SystemExit as e:
        return e.code, sys.stdout.getvalue()
    finally:
        captured = sys.stdout
        sys.stdin, sys.stdout = real_in, real_out
    return None, captured.getvalue()


def test_hookio():
    print("hookio（降级铁律）:")
    check("正常返回值写成 JSON",
          _run_hook(lambda e: {"ok": e["v"]}, '{"v":1}'), (0, '{"ok": 1}'))
    # PowerShell 管道会在前面塞 BOM，json.loads 会噎住
    check("容忍 stdin 前面的 UTF-8 BOM",
          _run_hook(lambda e: {"ok": 1}, '﻿{"v":1}\n'), (0, '{"ok": 1}'))
    check("handler 抛异常也 exit 0 且无输出",
          _run_hook(lambda e: 1 / 0, "{}"), (0, ""))
    check("畸形 JSON 也 exit 0 且无输出",
          _run_hook(lambda e: {"x": 1}, "not json"), (0, ""))
    check("空 stdin 也 exit 0 且无输出",
          _run_hook(lambda e: {"x": 1}, ""), (0, ""))
    check("返回 None 时不输出",
          _run_hook(lambda e: None, "{}"), (0, ""))

    os.environ["CC_DIALOGS"] = "off"
    try:
        check("总开关关闭时 handler 不执行",
              _run_hook(lambda e: 1 / 0, "{}"), (0, ""))
    finally:
        os.environ.pop("CC_DIALOGS", None)


def test_ui():
    from ccdialogs import ui
    print("ui（需要人工确认）:")
    print("  前台窗口 -> %r" % (ui.frontmost(),))
    print("  弹权限对话框…")
    print("  你点了 -> %r" % ui.ask_permission(
        "cc-dialogs 自检", "这是一条测试内容。\n随便点一个按钮。", True))
    print("  弹单选框…")
    print("  你选了 -> %r" % ui.ask_choice(
        "自检", "随便选一个", ["选项 A", "选项 B", "选项 C"], False))
    print("  弹多选框…")
    print("  你选了 -> %r" % ui.ask_choice(
        "自检", "可以多选", ["选项 A", "选项 B", "选项 C"], True))
    print("  发通知…")
    ui.notify("cc-dialogs", "自检通知，右下角应该看得到")


if __name__ == "__main__":
    test_segments()
    test_same_window()
    test_hookio()
    if "--ui" in sys.argv:
        test_ui()
    print()
    if _fails:
        print("%d 项失败：%s" % (len(_fails), ", ".join(_fails)))
        sys.exit(1)
    print("全部通过")
