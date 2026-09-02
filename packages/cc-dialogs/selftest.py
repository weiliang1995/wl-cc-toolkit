"""cc-dialogs self-check: exercises the focus comparison and the UI primitives.

    py -3 packages/cc-dialogs/selftest.py          # pure logic only, two seconds
    py -3 packages/cc-dialogs/selftest.py --ui     # also pops the real dialogs

The focus comparison is the one part whose mistakes are invisible -- when it
misjudges you only notice that notifications feel a bit off, never which rule
went wrong. That is what earns it a self-check.
"""

import json
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
    check("splits on em dashes",
          focus.segments("a.ts — proj — Visual Studio Code"),
          ["a.ts", "proj", "Visual Studio Code"])
    check("splits on pipes", focus.segments("a | b | c"), ["a", "b", "c"])
    check("splits on spaced hyphens, not intra-word ones",
          focus.segments("my-proj - zsh"), ["my-proj", "zsh"])
    check("single segment", focus.segments("bash"), ["bash"])
    check("empty segments dropped", focus.segments("a ——  — b"), ["a", "b"])


def test_same_window():
    print("same_window:")
    check("no baseline counts as still watching (prefer missing a notify)",
          focus.same_window(None, w(VSCODE, "x")), True)
    check("no current window counts as still watching",
          focus.same_window(w(VSCODE, "x"), None), True)
    check("identical", focus.same_window(w(TERM, "proj"), w(TERM, "proj")), True)
    check("a different app means focus was lost",
          focus.same_window(w(VSCODE, "p"), w("chrome", "p")), False)
    check("switching files in VS Code is still the same window",
          focus.same_window(
              w(VSCODE, "a.ts — proj — Visual Studio Code"),
              w(VSCODE, "b.ts — proj — Visual Studio Code")), True)
    # The case a "longest common suffix + character threshold" scheme gets
    # wrong: both share " — Visual Studio Code" (21 chars) but the projects
    # differ.
    check("two VS Code windows on different projects are different windows",
          focus.same_window(
              w(VSCODE, "a.ts — proj — Visual Studio Code"),
              w(VSCODE, "a.ts — other — Visual Studio Code")), False)
    check("two-segment terminal titles must match exactly",
          focus.same_window(w(TERM, "proj — zsh"),
                            w(TERM, "other — zsh")), False)
    check("identical two-segment terminal titles",
          focus.same_window(w(TERM, "proj — zsh"),
                            w(TERM, "proj — zsh")), True)
    check("mixed separator styles",
          focus.same_window(
              w(VSCODE, "a.ts | proj | Visual Studio Code"),
              w(VSCODE, "b.ts — proj — Visual Studio Code")), True)
    check("a missing title key does not crash",
          focus.same_window({"app": VSCODE}, {"app": VSCODE}), True)


class _FakeStdin(object):
    """A stdin stand-in that, like the real one, carries a byte `.buffer`.

    hookio reads the bytes rather than the decoded text, so a StringIO here
    would let a locale-decoding bug pass the suite unnoticed.
    """

    def __init__(self, data):
        import io
        self.buffer = io.BytesIO(data)


def _run_hook(handler, stdin_bytes):
    """Run hookio.run once and return (exit_code, stdout)."""
    import io
    from ccdialogs import hookio
    if not isinstance(stdin_bytes, bytes):
        stdin_bytes = stdin_bytes.encode("utf-8")
    real_in, real_out = sys.stdin, sys.stdout
    sys.stdin, sys.stdout = _FakeStdin(stdin_bytes), io.StringIO()
    try:
        hookio.run(handler)
    except SystemExit as e:
        return e.code, sys.stdout.getvalue()
    finally:
        captured = sys.stdout
        sys.stdin, sys.stdout = real_in, real_out
    return None, captured.getvalue()


def test_hookio():
    print("hookio (the fallback rule):")
    check("a normal return value is written as JSON",
          _run_hook(lambda e: {"ok": e["v"]}, '{"v":1}'), (0, '{"ok": 1}'))
    # PowerShell pipelines prepend a BOM, which json.loads chokes on
    check("tolerates a leading UTF-8 BOM on stdin",
          _run_hook(lambda e: {"ok": 1}, '﻿{"v":1}\n'), (0, '{"ok": 1}'))
    # The regression that broke AskUserQuestion: stdin decoded with the
    # locale codec (cp936 on a Chinese Windows) mangles every non-ASCII
    # character, and a mangled question text no longer matches the key
    # Claude Code looks the answer up under, so the terminal picker just
    # sits there. Round-tripping the exact string is the whole test.
    check("Chinese survives stdin verbatim",
          _run_hook(lambda e: {"q": e["v"]},
                    u'{"v":"选项栏同步"}'.encode("utf-8")),
          (0, json.dumps({"q": u"选项栏同步"})))
    check("a raising handler still exits 0 with no output",
          _run_hook(lambda e: 1 / 0, "{}"), (0, ""))
    check("malformed JSON still exits 0 with no output",
          _run_hook(lambda e: {"x": 1}, "not json"), (0, ""))
    check("empty stdin still exits 0 with no output",
          _run_hook(lambda e: {"x": 1}, ""), (0, ""))
    check("no output when the handler returns None",
          _run_hook(lambda e: None, "{}"), (0, ""))

    os.environ["CC_DIALOGS"] = "off"
    try:
        check("the handler does not run when the master switch is off",
              _run_hook(lambda e: 1 / 0, "{}"), (0, ""))
    finally:
        os.environ.pop("CC_DIALOGS", None)


_SAMPLE_CMD = (
    "Bash\n\n"
    "for f in src/**/*.py; do\n"
    '  black --line-length 100 "$f"\n'
    "  ruff check --fix \"$f\"\n"
    "done\n\n"
    "Format and lint every Python file under src/"
)


def test_ui():
    """Preview the real panels. Use this to iterate on style.json."""
    from ccdialogs import ui
    print("ui (needs your eyes):")
    print("  frontmost -> %r" % (ui.frontmost(),))

    print("  permission panel, English...")
    print("    clicked -> %r" % ui.ask_permission(
        "Permission needed", _SAMPLE_CMD, True))

    print("  permission panel, Chinese...")
    print("    clicked -> %r" % ui.ask_permission(
        "请求权限", "Bash\n\nrm -rf build/\n\n清理构建产物", True))

    print("  single select...")
    print("    picked -> %r" % ui.ask_choice(
        "Self-check", "Pick one option to check the layout",
        ["Alpha — the first", "Beta — the second", "Gamma — the third"], False))

    print("  multi select...")
    print("    picked -> %r" % ui.ask_choice(
        "自检", "这是一道中文多选题，看看有没有乱码",
        ["选项甲", "选项乙", "选项丙"], True))

    print("  notification...")
    ui.notify("cc-dialogs", "Self-check notification")


if __name__ == "__main__":
    test_segments()
    test_same_window()
    test_hookio()
    if "--ui" in sys.argv:
        test_ui()
    print()
    if _fails:
        print("%d failed: %s" % (len(_fails), ", ".join(_fails)))
        sys.exit(1)
    print("all passed")
