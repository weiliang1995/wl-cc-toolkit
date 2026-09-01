"""Windows 后端：把参数写成 JSON 临时文件，交给 ps1 执行，从 stdout 读回 JSON。

不在 Python 里拼 PowerShell 字符串 —— 多层转义极易出错且难以调试。
"""

import json
import os
import pathlib
import subprocess
import tempfile

from .. import labels

_PS_DIR = pathlib.Path(__file__).parent / "win"

# 弹窗要等用户点击，不设超时；探测类调用必须快，避免拖慢每一轮对话。
_DIALOG_TIMEOUT = None
_PROBE_TIMEOUT = 10


def run_ps(script_name, params, timeout=_PROBE_TIMEOUT):
    script = _PS_DIR / script_name
    fd, tmp = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(params, f)
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-STA",
             "-ExecutionPolicy", "Bypass", "-File", str(script),
             "-ParamsPath", tmp],
            capture_output=True, text=True, encoding="utf-8",
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        out = (proc.stdout or "").strip()
        return json.loads(out) if out else {}
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def ask_permission(title, body, allow_always):
    lb = labels.of(title, body)
    r = run_ps("permission.ps1",
               {"appName": labels.APP_NAME,
                "title": title, "body": body,
                "allowAlways": bool(allow_always),
                "labels": {k: lb[k] for k in ("allow", "always", "deny")}},
               timeout=_DIALOG_TIMEOUT)
    return r.get("result", "cancel")


def ask_choice(title, prompt, options, multi):
    lb = labels.of(prompt, *options)
    r = run_ps("choice.ps1",
               {"appName": labels.APP_NAME,
                "title": title, "prompt": prompt,
                "options": list(options), "multi": bool(multi),
                "labels": {k: lb[k] for k in ("ok", "cancel")}},
               timeout=_DIALOG_TIMEOUT)
    picked = r.get("picked") or []
    # ConvertTo-Json 会把单元素数组退化成标量
    if isinstance(picked, str):
        picked = [picked]
    return [str(x) for x in picked]


def frontmost():
    r = run_ps("frontmost.ps1", {})
    if not r or not r.get("app"):
        return None
    return {"app": r.get("app", ""), "title": r.get("title", "")}


def notify(title, body):
    run_ps("notify.ps1", {"title": title, "body": body})
