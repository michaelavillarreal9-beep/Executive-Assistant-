#!/usr/bin/env python3
"""PostToolUse logger: one plain-text line per tool call in logs/tool-calls.log.

Logs the tool name and a short, redacted view of its inputs. Never logs tool
results, so no email contents reach the log [A p.3].
"""
import datetime as _dt
import json
import os
import sys

CODE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or CODE_ROOT  # where logs go
sys.path.insert(0, CODE_ROOT)  # where core/ lives

# Inputs safe to show (truncated and redacted). Anything else is logged by size only.
SHOWN = {"query", "q", "file_path", "path", "pattern", "glob", "description", "url", "command",
         "thread_id", "threadId", "message_id", "messageId", "id", "max_results", "maxResults",
         "limit", "action", "skill", "subagent_type", "timeMin", "timeMax", "calendarId"}
MAX_VALUE = 160


def summarize(tool_input) -> str:
    try:
        from core.redact import redact
    except Exception:
        def redact(t):
            return t
    if not isinstance(tool_input, dict):
        return f"<{len(str(tool_input))} chars>"
    parts = []
    for key in sorted(tool_input):
        value = tool_input[key]
        if key in SHOWN and isinstance(value, (str, int, float, bool)):
            text = " ".join(redact(str(value)).split()).replace("|", "/")
            if len(text) > MAX_VALUE:
                text = text[: MAX_VALUE - 1] + "…"
            parts.append(f"{key}={text}")
        else:
            parts.append(f"{key}=<{len(json.dumps(value, default=str))} chars>")
    return "; ".join(parts)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{stamp} | {event.get('tool_name', '?')} | {summarize(event.get('tool_input'))}\n"
    path = os.path.join(ROOT, "logs", "tool-calls.log")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
