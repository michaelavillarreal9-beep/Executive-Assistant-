#!/usr/bin/env python3
"""PreToolUse guard: Gmail, Calendar and Drive are READ-ONLY (decision R2).

Allow-list, not block-list: on those servers only tools whose verb is a read verb
pass. Anything else (send, reply, draft, label, trash, create, share...) is refused
with exit code 2, which Claude Code treats as a hard block. The settings.json deny
list is a second, independent layer.
"""
import json
import os
import re
import sys

CODE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or CODE_ROOT  # where logs go
sys.path.insert(0, CODE_ROOT)  # where core/ lives

PROTECTED = re.compile(r"^mcp__.*(gmail|calendar|drive).*__(?P<tool>[a-z_\-]+)$", re.I)
READ_VERBS = ("get_", "list_", "search_", "read_", "download_", "suggest_")


def decide(tool_name: str):
    """Return None to allow, or a reason string to block."""
    m = PROTECTED.match(tool_name or "")
    if not m:
        return None
    if m.group("tool").lower().startswith(READ_VERBS):
        return None
    return f"{tool_name} is blocked: email, calendar and drive are read-only in this repo (decision R2)."


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    reason = decide(event.get("tool_name", ""))
    if reason is None:
        return 0
    try:
        from core.dispatch import Dispatcher
        Dispatcher(ROOT, phase="GUARD").log(f"tool {event.get('tool_name')}", "read-only rule", f"BLOCKED: {reason}")
    except Exception:
        pass  # blocking must not depend on logging
    print(reason, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
