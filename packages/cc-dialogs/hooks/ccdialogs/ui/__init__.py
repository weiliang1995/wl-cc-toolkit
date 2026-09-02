"""The four UI primitives, and dispatch to the platform backend.

Every platform difference is confined to this package; callers only ever use
these four functions.
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
    """Return 'allow' / 'always' / 'deny' / 'cancel'."""
    return backend().ask_permission(title, body, allow_always)


def ask_choice(title, prompt, options, multi):
    """Return the chosen labels; [] when cancelled."""
    return backend().ask_choice(title, prompt, options, multi)


def notify(title, body):
    backend().notify(title, body)


def frontmost():
    """Return {'app': str, 'title': str}, or None when unavailable."""
    return backend().frontmost()
