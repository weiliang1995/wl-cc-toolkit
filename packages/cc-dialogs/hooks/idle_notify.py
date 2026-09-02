"""Stop hook: notify only if the user has looked away.

Stop fires at the end of every turn, so an unconditional notification would
fire on every single reply. The test is a comparison against the baseline
recorded at UserPromptSubmit.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ccdialogs import focus, hookio, labels, state, ui


def should_notify(session_id, current):
    """Only when the user genuinely switched away. When unsure, stay quiet."""
    baseline = state.load(session_id)
    if not baseline or not current:
        state.note("quiet: baseline=%r current=%r" % (baseline, current))
        return False
    verdict = not focus.same_window(baseline, current)
    # The titles this compared are gone the moment a window changes, so a
    # misfire is unreproducible unless it was written down as it happened.
    state.note("notify=%s baseline=%r current=%r" % (verdict, baseline, current))
    return verdict


def handle(event):
    session_id = event.get("session_id")
    if not session_id:
        return None
    if should_notify(session_id, ui.frontmost()):
        lb = labels.of(event.get("last_assistant_message"))
        ui.notify(labels.APP_NAME, lb["idle_body"])
    return None


if __name__ == "__main__":
    hookio.run(handle)
