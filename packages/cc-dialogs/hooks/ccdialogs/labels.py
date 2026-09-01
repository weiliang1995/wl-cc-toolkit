"""Button labels, chosen to match the language of the content being shown.

The question text and command previews come from Claude, so they are already
in whatever language the user is working in. Only our own chrome -- the
buttons -- needs deciding, and the cheapest correct signal is the content
itself. Set CC_DIALOGS_LANG to force one.
"""

import os
import re

APP_NAME = "Claude Code"

_CJK = re.compile(
    "["
    "぀-ヿ"      # kana
    "㐀-䶿"      # CJK ext A
    "一-鿿"      # CJK unified
    "가-힯"      # hangul
    "]"
)

_LABELS = {
    "en": {
        "allow": "Allow",
        "always": "Always allow",
        "deny": "Deny",
        "ok": "OK",
        "cancel": "Cancel",
        "permission_title": "Permission needed",
        "idle_body": "Finished - waiting for you",
        "truncated": "\n... ({n} more characters, full text in the terminal)",
    },
    "zh": {
        "allow": "允许",
        "always": "总是允许",
        "deny": "拒绝",
        "ok": "确定",
        "cancel": "取消",
        "permission_title": "请求权限",
        "idle_body": "已完成，等待你的下一步",
        "truncated": "\n……（还有 {n} 个字符，完整内容见终端）",
    },
}


def detect(*texts):
    """Pick a language from the content. CC_DIALOGS_LANG overrides."""
    forced = os.environ.get("CC_DIALOGS_LANG", "").strip().lower()
    if forced in _LABELS:
        return forced
    for t in texts:
        if t and _CJK.search(str(t)):
            return "zh"
    return "en"


def for_lang(lang):
    return _LABELS.get(lang, _LABELS["en"])


def of(*texts):
    """Shorthand: label table matching the language of these texts."""
    return for_lang(detect(*texts))
