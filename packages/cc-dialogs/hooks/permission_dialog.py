"""PermissionRequest hook：把终端的 y/n 提示换成原生对话框。

输出 schema（注意 behaviour 是英式拼写）：
  {"hookSpecificOutput": {"hookEventName": "PermissionRequest",
                          "decision": {"behaviour": "allow"|"deny", ...}}}
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ccdialogs import hookio, ui


def _body(event):
    tool = event.get("tool_name", "?")
    raw = event.get("tool_input", {})
    # Bash 的命令单独拎出来放最前面，一眼能看清要批准什么
    if tool == "Bash" and isinstance(raw, dict) and raw.get("command"):
        head = raw["command"]
        desc = raw.get("description")
        body = head if not desc else "%s\n\n（%s）" % (head, desc)
        return "工具：Bash\n\n%s" % body
    return "工具：%s\n\n%s" % (
        tool, json.dumps(raw, indent=2, ensure_ascii=False))


def handle(event):
    suggestions = event.get("permission_suggestions") or []
    choice = ui.ask_permission(
        "Claude Code 请求权限", _body(event), bool(suggestions))

    if choice == "allow":
        decision = {"behaviour": "allow"}
    elif choice == "always":
        # updatedPermissions 原样透传 —— 脚本不解析也不构造权限规则
        decision = {"behaviour": "allow", "updatedPermissions": suggestions}
    elif choice == "deny":
        decision = {"behaviour": "deny",
                    "message": "User denied via native dialog"}
    else:
        return None  # 取消 → 不做决定 → 回退终端 TUI

    return {"hookSpecificOutput": {
        "hookEventName": "PermissionRequest", "decision": decision}}


if __name__ == "__main__":
    hookio.run(handle)
