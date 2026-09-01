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
