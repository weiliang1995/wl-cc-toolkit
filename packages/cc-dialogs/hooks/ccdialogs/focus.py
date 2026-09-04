"""Decide whether the user is still looking at this Claude session's window.

Strategy: record the frontmost window at UserPromptSubmit as the baseline --
the moment the user hits enter their window is necessarily in front -- then
compare it against the frontmost window at Stop.

Not "longest common suffix + character threshold": two VS Code windows open
on different projects also share " - Visual Studio Code" (21 characters), so
there is no safe threshold. Splitting on separators distinguishes them
naturally: proj and other are different segments.

"Window" here means the active view, not the OS window. VS Code puts the
focused view's name in the title's first segment -- a file name, or the name
of whichever Claude session owns the focused panel -- so comparing every
segment also catches the two cases that live inside one OS window: you
clicked into a file, or you moved to another Claude session's panel.
"""

import re

from . import state, ui

_SEP_RE = re.compile(r"\s*[—–|]\s*|\s+-\s+")


def segments(title):
    """Split on the usual title separators, dropping blanks and empties."""
    return [s for s in (p.strip() for p in _SEP_RE.split(title or "")) if s]


def same_window(baseline, current):
    """True means the user is still on the baseline window (stay quiet).

    With no baseline or no current window info, return True -- better to miss
    a notification than to interrupt for nothing.
    """
    if not baseline or not current:
        return True

    if baseline.get("app") != current.get("app"):
        return False

    bt = baseline.get("title", "") or ""
    ct = current.get("title", "") or ""

    # Every segment counts, the first one included. In VS Code that first
    # segment is the active view -- a file name, or the name of whichever
    # Claude session owns the focused panel -- so dropping it would make
    # "I clicked into a file" and "I moved to another Claude panel" both read
    # as still watching, which is precisely when the dialogs are wanted.
    #
    # Comparing segment lists rather than the raw strings keeps the check
    # immune to how the separator happens to be rendered.
    return segments(bt) == segments(ct)


def user_is_watching(session_id):
    """True when the session's own window is still frontmost.

    Gates the dialogs: a panel stealing focus from the window you are already
    typing in is pure noise, so when you are looking at the session we make no
    decision and Claude Code draws its own terminal prompt instead.

    The unsure cases here go the opposite way from `same_window`: no baseline
    or unreadable focus means show the panel. Popping a panel you did not need
    is a far smaller cost than silently losing the plugin's whole point.
    """
    if not session_id:
        return False
    baseline = state.load(session_id)
    current = ui.frontmost()
    if not baseline or not current:
        return False
    return same_window(baseline, current)
