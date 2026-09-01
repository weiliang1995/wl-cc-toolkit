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
