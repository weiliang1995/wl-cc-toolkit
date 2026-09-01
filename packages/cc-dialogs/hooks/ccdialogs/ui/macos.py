"""macOS 后端：全部通过 osascript 调用系统原生 UI。"""

import subprocess

from .. import labels

_TRUNCATE = 2000  # display dialog has a practical length limit


def _osa(script):
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, encoding="utf-8")
    except Exception:
        return None
    if proc.returncode != 0:
        # 用户取消时 osascript 以非零码退出 —— 视为取消，不是错误
        return None
    return (proc.stdout or "").strip()


def _q(s):
    """转义进 AppleScript 字符串字面量。"""
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')


def _clip(text, lb):
    text = text or ""
    if len(text) <= _TRUNCATE:
        return text
    return text[:_TRUNCATE] + lb["truncated"].format(n=len(text) - _TRUNCATE)


def ask_permission(title, body, allow_always):
    lb = labels.of(title, body)
    # Order matters: AppleScript returns the button's own text, and "always"
    # must be tested before "allow" when one label contains the other.
    order = ["deny", "always", "allow"] if allow_always else ["deny", "allow"]
    buttons = ", ".join('"%s"' % _q(lb[k]) for k in order)
    script = (
        'display dialog "%s" with title "%s" buttons {%s} default button "%s"'
        % (_q(_clip(body, lb)), _q(title), buttons, _q(lb["allow"]))
    )
    out = _osa(script)
    if out is None:
        return "cancel"
    for key in ("always", "deny", "allow"):
        if key in order and lb[key] in out:
            return key
    return "cancel"


def ask_choice(title, prompt, options, multi):
    items = ", ".join('"%s"' % _q(o) for o in options)
    script = (
        'set r to choose from list {%s} with title "%s" with prompt "%s"%s\n'
        'if r is false then return ""\n'
        "set AppleScript's text item delimiters to linefeed\n"
        'return r as text'
        % (items, _q(title), _q(prompt),
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
