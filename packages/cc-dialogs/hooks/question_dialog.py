"""PreToolUse / AskUserQuestion hook: replace the terminal picker.

The trick is not to deny but to allow + updatedInput: the user's choice is
pre-filled into tool_input.answers and the call proceeds. The tool still
runs, but with the answers already supplied Claude Code skips its own TUI
and returns the result directly.

The key of `answers` is the verbatim question["question"] text; the value is
always a string, joined with ", " for multi-select -- never a list.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ccdialogs import focus, hookio, labels, ui


def build_answers(questions, picks):
    """Turn {index: [label, ...]} into {verbatim question: "A, B"}."""
    answers = {}
    for i, q in enumerate(questions):
        chosen = picks.get(i) or []
        if chosen:
            answers[q["question"]] = ", ".join(chosen)
    return answers


def handle(event):
    tool_input = event.get("tool_input") or {}
    questions = tool_input.get("questions") or []
    if not questions:
        return None
    if focus.user_is_watching(event.get("session_id")):
        return None  # you are right here -- the terminal picker is fine

    picks = {}
    for i, q in enumerate(questions):
        option_labels = [o.get("label", "") for o in (q.get("options") or [])]
        if not option_labels:
            return None
        chosen = ui.ask_choice(
            q.get("header") or labels.APP_NAME,
            q.get("question", ""),
            option_labels,
            bool(q.get("multiSelect")),
        )
        if not chosen:
            return None  # any cancel -> fall back to the terminal entirely
        picks[i] = chosen

    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "updatedInput": {
            "questions": questions,
            "answers": build_answers(questions, picks),
        },
    }}


if __name__ == "__main__":
    hookio.run(handle)
