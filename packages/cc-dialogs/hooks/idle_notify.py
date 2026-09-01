"""Stop hook：Claude 停下等待时，若用户已切走窗口则发系统通知。

Stop 每轮对话结束都会触发，因此必须有判据，否则每答一句都弹通知。
判据是与 UserPromptSubmit 记录的基准比对。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ccdialogs import focus, hookio, state, ui


def should_notify(session_id, current):
    """仅当用户确实切走了窗口才通知。拿不准一律不通知。"""
    baseline = state.load(session_id)
    if not baseline or not current:
        return False
    return not focus.same_window(baseline, current)


def handle(event):
    session_id = event.get("session_id")
    if not session_id:
        return None
    if should_notify(session_id, ui.frontmost()):
        ui.notify("Claude Code", "已完成，等待你的下一步")
    return None


if __name__ == "__main__":
    hookio.run(handle)
