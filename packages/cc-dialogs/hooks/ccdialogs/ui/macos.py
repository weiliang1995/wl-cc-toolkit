"""macOS 后端：全部通过 osascript 调用系统原生 UI。"""

import subprocess

_TRUNCATE = 2000  # display dialog 有实际长度限制


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


def _clip(text):
    text = text or ""
    if len(text) <= _TRUNCATE:
        return text
    return text[:_TRUNCATE] + "\n…（还有 %d 字符，完整内容见终端）" % (
        len(text) - _TRUNCATE)


def ask_permission(title, body, allow_always):
    buttons = ['"拒绝"', '"总是允许"', '"允许"'] if allow_always else ['"拒绝"', '"允许"']
    script = (
        'display dialog "%s" with title "%s" buttons {%s} default button "允许"'
        % (_q(_clip(body)), _q(title), ", ".join(buttons))
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
