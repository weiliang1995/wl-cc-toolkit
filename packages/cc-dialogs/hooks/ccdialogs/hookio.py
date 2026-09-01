"""Hook 入口的 stdin/stdout 协议与降级铁律。

铁律：任何异常都以 exit 0 + 空 stdout 收场。Claude Code 把「无输出」解释为
「hook 不做决定」，于是自动回退到终端 TUI —— 脚本崩溃永远不会卡住会话。
"""

import json
import os
import sys


def disabled():
    """总开关：CC_DIALOGS=off 时禁用全部对话框。"""
    return os.environ.get("CC_DIALOGS", "").strip().lower() == "off"


def run(handler):
    """读 stdin JSON 交给 handler，把返回值写为 stdout JSON。永不抛出。"""
    result = None
    try:
        if not disabled():
            # 有些调用方（如 PowerShell 管道）会在前面塞一个 UTF-8 BOM，
            # json.loads 会直接失败。
            raw = sys.stdin.read().lstrip("﻿").strip()
            result = handler(json.loads(raw)) if raw else None
    except BaseException:
        result = None

    if result is not None:
        try:
            sys.stdout.write(json.dumps(result))
        except BaseException:
            pass

    sys.exit(0)
