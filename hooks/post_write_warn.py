#!/usr/bin/env python3
"""lhg-amazon-listing 硬门②（警告级，不拦截）：写 Listing 文档时做轻量提醒。

触发：PostToolUse / Write|Edit。只检查 .md/.txt 文档：
  - 文档含"标题"章节但标题超过 200 字符 → 提醒精简
  - 文档像 Listing（有标题章节）却没有五点描述章节 → 提醒补全

只做提醒，永远 exit 0、不拦截写入；内部出错 fail-open。
逃生方式：LHG_AMZ_HOOKS_OFF=1（环境变量）可关闭本提醒；
或 /plugin disable lhg-amazon-listing 停用整个插件。
零第三方依赖。
"""

import json
import os
import re
import sys

DOC_EXTS = {".md", ".txt", ".markdown"}


def main() -> int:
    if os.environ.get("LHG_AMZ_HOOKS_OFF") == "1":
        return 0

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "") or ""
    if not file_path:
        return 0

    _, ext = os.path.splitext(file_path)
    if ext.lower() not in DOC_EXTS:
        return 0  # 非文档：快速放行

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return 0

    if "标题" not in text:
        return 0  # 不像 Listing 文档：放行

    warns = []
    m = re.search(r"#{1,3}\s*标题\s*\n+(.{4,})", text)
    if m:
        title = m.group(1).strip().lstrip("-*0123456789. ").strip().split("\n")[0]
        if len(title) > 200:
            warns.append("标题 %d 个字符，超过 200 上限，建议精简。" % len(title))
    if "五点描述" not in text and "Bullet" not in text:
        warns.append("缺少五点描述章节，Bullet Points 是转化主战场，建议补足 5 条。")

    if not warns:
        return 0

    msg = (
        "Listing 文档提醒（lhg-amazon-listing）：%s\n%s\n"
        "完整检查请跑 /lhg-amazon-listing:audit；关闭本提醒：export LHG_AMZ_HOOKS_OFF=1。"
    ) % (file_path, "\n".join("  - " + w for w in warns))
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
