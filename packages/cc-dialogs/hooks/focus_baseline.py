"""UserPromptSubmit hook：记录焦点基准。

用户按下回车提交 prompt 的那一刻，其窗口必然是前台的 —— 这是整个焦点
判定的锚点，无需白名单也无需项目名匹配。

本 hook 不产生任何输出，纯副作用。
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
