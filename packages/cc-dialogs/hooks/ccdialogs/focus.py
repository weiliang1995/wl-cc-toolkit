"""判断「用户是否仍在看这个 Claude 会话所在的窗口」。

策略：在 UserPromptSubmit 时刻记录前台窗口作为基准 —— 用户按下回车那一刻，
其窗口必然是前台的 —— 然后在 Stop 时刻与当前前台窗口比对。

不用「最长公共后缀 + 字符阈值」：两个开着不同项目的 VS Code 窗口同样共享
" — Visual Studio Code"（21 字符）这段后缀，不存在安全的阈值。按分隔符切段
比较则天然区分：proj 与 other 是不同的段。
"""

import re

_SEP_RE = re.compile(r"\s*[—–|]\s*|\s+-\s+")


def segments(title):
    """按常见标题分隔符切段，去掉空白与空段。"""
    return [s for s in (p.strip() for p in _SEP_RE.split(title or "")) if s]


def same_window(baseline, current):
    """True 表示用户仍在看基准窗口（此时不该发通知）。

    缺基准或缺当前窗口信息时返回 True —— 宁可漏发，不可误扰。
    """
    if not baseline or not current:
        return True

    if baseline.get("app") != current.get("app"):
        return False

    bt = baseline.get("title", "") or ""
    ct = current.get("title", "") or ""
    if bt == ct:
        return True

    bs, cs = segments(bt), segments(ct)
    # 三段以上时丢弃首段（通常是易变的文件名），比较其余段。
    # 两段及以下要求全等：终端标题形如 "proj — zsh"，丢弃首段只剩 "zsh"，
    # 会匹配上任意一个同 shell 的窗口。
    if len(bs) >= 3 and len(cs) >= 3:
        return bs[1:] == cs[1:]
    return False
