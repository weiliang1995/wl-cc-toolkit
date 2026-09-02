"""Windows backend: write the params to a temp JSON file, run a ps1 against
it, and read JSON back off stdout.

PowerShell strings are never assembled in Python -- several layers of quoting
are easy to get wrong and painful to debug.
"""

import json
import os
import pathlib
import subprocess
import tempfile

from .. import labels

_PS_DIR = pathlib.Path(__file__).parent / "win"

# A panel waits for a click, so it gets no timeout. Probes must be fast --
# they run on every turn.
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
    # ConvertTo-Json collapses a one-element array into a scalar
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
