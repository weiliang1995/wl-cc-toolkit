"""The stdin/stdout protocol for hook entry points, and the fallback rule.

The rule: any failure ends in exit 0 with empty stdout. Claude Code reads "no
output" as "the hook made no decision" and falls back to the terminal TUI --
so a crashing script can never wedge the session.
"""

import json
import os
import sys


def disabled():
    """Master switch: CC_DIALOGS=off disables every dialog."""
    return os.environ.get("CC_DIALOGS", "").strip().lower() == "off"


def run(handler):
    """Read stdin JSON, pass it to handler, write the result as stdout JSON.

    Never raises.
    """
    result = None
    try:
        if not disabled():
            # Read bytes, not text: Claude Code always sends UTF-8, but
            # sys.stdin decodes with the locale codec (cp936 on a Chinese
            # Windows), which silently mangles every non-ASCII character --
            # and a mangled question text no longer matches the key Claude
            # Code looks the answer up under. Some callers (PowerShell
            # pipelines, for one) also prepend a UTF-8 BOM, which makes
            # json.loads fail outright.
            raw = sys.stdin.buffer.read().decode("utf-8").lstrip("﻿").strip()
            result = handler(json.loads(raw)) if raw else None
    except BaseException:
        result = None

    if result is not None:
        try:
            sys.stdout.write(json.dumps(result))
        except BaseException:
            pass

    sys.exit(0)
