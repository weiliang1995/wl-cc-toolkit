"""PreToolUse / AskUserQuestion hook：把终端选项框换成原生列表。

机制：不 deny，而是 allow + updatedInput —— 把用户的选择预填进
tool_input.answers 后放行。工具照常执行，但因答案已备齐，CC 跳过 TUI
直接返回结果。

answers 的 key 是 question["question"] 的原文；value 恒为 string，
多选用 ", " 拼接。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ccdialogs import hookio, ui


def build_answers(questions, picks):
    """把 {题号: [label, ...]} 转成 {question 原文: "A, B"}。空选跳过。"""
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

    picks = {}
    for i, q in enumerate(questions):
        labels = [o.get("label", "") for o in (q.get("options") or [])]
        if not labels:
            return None
        chosen = ui.ask_choice(
            q.get("header") or "Claude Code",
            q.get("question", ""),
            labels,
            bool(q.get("multiSelect")),
        )
        if not chosen:
            return None  # 任一题取消 → 整体回退终端 TUI
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
