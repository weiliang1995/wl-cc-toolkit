"""PermissionRequest hook: replace the terminal y/n prompt with a native panel.

Output schema (note that `behaviour` is the British spelling):
  {"hookSpecificOutput": {"hookEventName": "PermissionRequest",
                          "decision": {"behaviour": "allow"|"deny", ...}}}
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ccdialogs import hookio, labels, ui


def _body(event):
    tool = event.get("tool_name", "?")
    raw = event.get("tool_input", {})
    # Lead with the bash command itself: what is being approved should be
    # readable at a glance, not buried in a JSON dump.
    if tool == "Bash" and isinstance(raw, dict) and raw.get("command"):
        body = raw["command"]
        desc = raw.get("description")
        if desc:
            body = "%s\n\n%s" % (body, desc)
        return "Bash\n\n%s" % body
    return "%s\n\n%s" % (
        tool, json.dumps(raw, indent=2, ensure_ascii=False))


def handle(event):
    suggestions = event.get("permission_suggestions") or []
    body = _body(event)
    lb = labels.of(body)

    choice = ui.ask_permission(
        lb["permission_title"], body, bool(suggestions))

    if choice == "allow":
        decision = {"behaviour": "allow"}
    elif choice == "always":
        # Passed straight through -- this script neither parses nor builds
        # permission rules.
        decision = {"behaviour": "allow", "updatedPermissions": suggestions}
    elif choice == "deny":
        decision = {"behaviour": "deny",
                    "message": "User denied via native dialog"}
    else:
        return None  # cancelled -> no decision -> fall back to the terminal

    return {"hookSpecificOutput": {
        "hookEventName": "PermissionRequest", "decision": decision}}


if __name__ == "__main__":
    hookio.run(handle)
