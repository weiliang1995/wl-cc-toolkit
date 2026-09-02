"""Per-session state store: keeps the focus baseline for the Stop comparison."""

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
    """session_id ends up in a path, so sanitize it against traversal."""
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


_LOG_MAX_BYTES = 200 * 1024


def note(line):
    """Append one diagnostic line. Silent on failure, self-truncating.

    The focus verdict is the one thing here that cannot be reproduced after
    the fact -- the window titles it compared are gone the moment they
    change -- so every Stop records what it saw and what it decided.
    """
    try:
        d = state_dir()
        d.mkdir(parents=True, exist_ok=True)
        p = d / "focus.log"
        if p.exists() and p.stat().st_size > _LOG_MAX_BYTES:
            p.unlink()
        with p.open("a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), line))
    except Exception:
        pass


def prune(max_age_days=7):
    """Delete stale state files so abnormally ended sessions do not leak.

    Failures are silent.
    """
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
