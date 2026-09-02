"""UserPromptSubmit hook: record the focus baseline.

The moment the user hits enter to submit a prompt, their window is
necessarily in front. That is the anchor for the whole focus check -- no
allowlist and no project-name matching needed.

This hook produces no output; it is pure side effect.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ccdialogs import hookio, state, ui


def handle(event):
    session_id = event.get("session_id")
    if not session_id:
        return None
    win = ui.frontmost()
    if win:
        state.save(session_id, win)
    state.prune()
    return None


if __name__ == "__main__":
    hookio.run(handle)
