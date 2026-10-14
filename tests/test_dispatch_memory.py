import datetime as dt
import tempfile
import unittest
from pathlib import Path

from core.dispatch import ApprovalRequired, CheckIn, Dispatcher, OutsideRepo
from core.memory import Memory, MissingLesson


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.d = Dispatcher(self.root, phase="TEST")

    def tearDown(self):
        self.tmp.cleanup()

    def log_lines(self):
        return (self.root / "logs" / "actions.log").read_text().splitlines()


class TestDispatch(Base):
    def test_every_action_is_logged_with_reason(self):
        self.d.write_text("notes/a.txt", "hi", "test write")
        self.d.read_text("notes/a.txt", "test read")
        lines = self.log_lines()
        self.assertEqual(len(lines), 2)
        self.assertIn("| TEST | create notes/a.txt | test write | ok", lines[0])
        self.assertIn("read notes/a.txt | test read", lines[1])

    def test_reason_is_required(self):
        with self.assertRaises(ValueError):
            self.d.write_text("a.txt", "x", "  ")

    def test_cannot_touch_outside_repo(self):
        for path in ["../escape.txt", "/etc/passwd", "a/../../b.txt"]:
            with self.subTest(path=path), self.assertRaises(OutsideRepo):
                self.d.write_text(path, "x", "should fail")

    def test_delete_needs_named_approval(self):
        self.d.write_text("a.txt", "x", "setup")
        with self.assertRaises(ApprovalRequired):
            self.d.delete("a.txt", "cleanup")
        self.assertTrue((self.root / "a.txt").exists())
        self.assertIn("BLOCKED", self.log_lines()[-1])
        self.d.delete("a.txt", "cleanup", approved_by="Michael")
        self.assertFalse((self.root / "a.txt").exists())

    def test_three_failures_then_check_in(self):
        def boom():
            raise RuntimeError("nope")
        for _ in range(3):
            with self.assertRaises(RuntimeError):
                self.d.step("parse", "try parse", boom)
        # 4th attempt is refused even though it would succeed, and even from a new process
        fresh = Dispatcher(self.root, phase="TEST")
        with self.assertRaises(CheckIn):
            fresh.step("parse", "try parse", lambda: 1)
        fresh.reset_step("parse", approved_by="Michael")
        self.assertEqual(fresh.step("parse", "try parse", lambda: 1), 1)

    def test_success_clears_failure_count(self):
        def boom():
            raise RuntimeError("nope")
        for _ in range(2):
            with self.assertRaises(RuntimeError):
                self.d.step("s", "r", boom)
        self.d.step("s", "r", lambda: None)
        for _ in range(3):
            with self.assertRaises(RuntimeError):
                self.d.step("s", "r", boom)


class TestMemory(Base):
    def setUp(self):
        super().setUp()
        self.m = Memory(self.d)

    def test_run_must_end_with_a_lesson(self):
        self.m.start_run("triage", ["email"])
        with self.assertRaises(MissingLesson):
            self.m.finish_run(dt.date(2026, 10, 14), "triage", [], {}, lesson="  ")
        self.assertEqual(self.m.episodes(), [])

    def test_episode_written_and_lesson_distilled(self):
        name = self.m.finish_run(dt.date(2026, 10, 14), "triage", ["read 5 threads"], {"items": 5},
                                 lesson="Receipts are FYI_LOG, not noise.")
        self.assertEqual(name, "2026-10-14-run-01.md")
        rec = self.m.read_episode(name, "test")
        self.assertEqual(rec["outcome"], {"items": 5})
        self.assertIn("Receipts are FYI_LOG", (self.root / "memory/knowledge/lessons.md").read_text())
        self.assertIn("lessons.md", [e[0] for e in self.m.index()])
        second = self.m.finish_run(dt.date(2026, 10, 14), "triage", [], {}, lesson="Second.")
        self.assertEqual(second, "2026-10-14-run-02.md")

    def test_episode_text_is_redacted(self):
        name = self.m.finish_run(dt.date(2026, 10, 14), "pay $2,450 to acct 99887766", [], {},
                                 lesson="Mail from bob@example.com matters.")
        text = (self.root / "memory/episodes" / name).read_text()
        self.assertNotIn("2,450", text)
        self.assertNotIn("99887766", text)
        self.assertNotIn("bob@", text)

    def test_start_run_reads_relevant_memory_first(self):
        self.m.write_knowledge("contacts.json", "{}", ["email", "triage"], "Sender domain to area.", "seed")
        self.m.write_knowledge("music.md", "x", ["music"], "Unrelated.", "seed")
        self.m.finish_run(dt.date(2026, 10, 13), "triage", [], {}, lesson="L1.")
        ctx = self.m.start_run("triage", ["email"])
        self.assertIn("contacts.json", ctx["knowledge"])
        self.assertIn("lessons.md", ctx["knowledge"])      # tagged "always"
        self.assertNotIn("music.md", ctx["knowledge"])
        self.assertEqual(len(ctx["episodes"]), 1)
        self.assertEqual(self.m.load_working()["context"]["goal"], "triage")
        reads = [l for l in self.log_lines() if "| read " in l]
        self.assertTrue(any("contacts.json" in l for l in reads))


if __name__ == "__main__":
    unittest.main()
