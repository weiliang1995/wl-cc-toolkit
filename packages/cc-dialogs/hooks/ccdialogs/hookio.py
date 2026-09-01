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
            result = handler(json.loads(sys.stdin.read()))
    except BaseException:
        result = None

    if result is not None:
        try:
            sys.stdout.write(json.dumps(result))
        except BaseException:
            pass

    sys.exit(0)
