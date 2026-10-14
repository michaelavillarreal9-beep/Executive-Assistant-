import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GUARD = REPO / ".claude" / "hooks" / "guard.py"
LOGGER = REPO / ".claude" / "hooks" / "log_tool.py"

sys.path.insert(0, str(GUARD.parent))
import guard  # noqa: E402


def run_hook(script, event, root):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
    return subprocess.run([sys.executable, str(script)], input=json.dumps(event), text=True,
                          capture_output=True, env=env)


class TestGuard(unittest.TestCase):
    WRITES = ["mcp__Gmail__send_message", "mcp__Gmail__reply", "mcp__Gmail__forward", "mcp__Gmail__create_draft",
              "mcp__Gmail__trash_thread", "mcp__Gmail__label_message", "mcp__Gmail__update_message_labels",
              "mcp__plugin_small-business_gmail__create_draft", "mcp__Google_Calendar__create_event",
              "mcp__Google_Calendar__respond_to_event", "mcp__Google_Drive__share_file",
              "mcp__plugin_small-business_google-drive__create_file", "mcp__Gmail__some_future_write_tool"]
    READS = ["mcp__Gmail__search_threads", "mcp__Gmail__get_thread", "mcp__Gmail__get_message",
             "mcp__Gmail__list_labels", "mcp__Google_Calendar__list_events", "mcp__Google_Drive__read_file_content",
             "mcp__Google_Drive__download_file_content", "mcp__Google_Calendar__suggest_time"]
    OTHER = ["Bash", "Read", "mcp__Claude_Docs__update", "mcp__Todoist__find-tasks"]

    def test_writes_blocked_reads_allowed(self):
        for name in self.WRITES:
            with self.subTest(name=name):
                self.assertIsNotNone(guard.decide(name))
        for name in self.READS + self.OTHER:
            with self.subTest(name=name):
                self.assertIsNone(guard.decide(name))

    def test_exit_code_2_blocks_and_is_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_hook(GUARD, {"tool_name": "mcp__Gmail__send_message", "tool_input": {}}, tmp)
            self.assertEqual(r.returncode, 2)
            self.assertIn("read-only", r.stderr)
            self.assertIn("BLOCKED", (Path(tmp) / "logs" / "actions.log").read_text())
            r = run_hook(GUARD, {"tool_name": "mcp__Gmail__search_threads", "tool_input": {}}, tmp)
            self.assertEqual(r.returncode, 0)

    def test_settings_deny_list_covers_the_send_path(self):
        settings = json.loads((REPO / ".claude" / "settings.json").read_text())
        deny = set(settings["permissions"]["deny"])
        for name in ["mcp__Gmail__send_message", "mcp__Gmail__reply", "mcp__Gmail__forward",
                     "mcp__Gmail__create_draft", "mcp__Gmail__trash_message"]:
            self.assertIn(name, deny)
        self.assertFalse(any(d.endswith(("search_threads", "get_thread", "get_message")) for d in deny))


class TestToolLogger(unittest.TestCase):
    def test_logs_name_and_redacted_inputs_never_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            event = {"tool_name": "mcp__Gmail__search_threads",
                     "tool_input": {"query": "from:a.person@example.com newer_than:1d", "body": "secret text"},
                     "tool_response": {"content": "PRIVATE EMAIL BODY account 99887766"}}
            r = run_hook(LOGGER, event, tmp)
            self.assertEqual(r.returncode, 0)
            line = (Path(tmp) / "logs" / "tool-calls.log").read_text()
            self.assertIn("mcp__Gmail__search_threads", line)
            self.assertIn("[someone]@example.com", line)
            self.assertIn("body=<13 chars>", line)
            self.assertNotIn("PRIVATE", line)
            self.assertNotIn("secret", line)


if __name__ == "__main__":
    unittest.main()
