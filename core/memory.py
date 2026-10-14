"""Working, episodic and semantic memory, stored as plain files.

Rule (your brief): read relevant memory before acting, write a concise lesson after
every run. start_run() does the reading and finish_run() refuses to close a run
without a lesson.

- working:  memory/working/current_run.json  (gitignored; may hold real data)
- episodic: memory/episodes/<date>-run-NN.md (committed; neutral wording only)
- semantic: memory/knowledge/*.{md,json} + INDEX.md (committed)
"""
import datetime as _dt
import json
import re
from pathlib import Path

from core.dispatch import Dispatcher
from core.redact import redact

EPISODE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-run-(\d{2,})\.md$")
JSON_BLOCK_RE = re.compile(r"```json\n(.*?)\n```", re.S)
LESSON_MAX = 300


class MissingLesson(Exception):
    """A run cannot be closed without a lesson."""


class Memory:
    def __init__(self, dispatcher: Dispatcher):
        self.d = dispatcher
        self.root = dispatcher.root
        self.working_path = Path("memory/working/current_run.json")
        self.episodes_dir = Path("memory/episodes")
        self.knowledge_dir = Path("memory/knowledge")

    # --- working memory ------------------------------------------------
    def load_working(self) -> dict:
        p = self.root / self.working_path
        if not p.exists():
            return {}
        return json.loads(self.d.read_text(self.working_path, "load working memory"))

    def save_working(self, state: dict, reason: str) -> None:
        self.d.write_text(self.working_path, json.dumps(state, indent=2, default=str), reason)

    # --- semantic memory -----------------------------------------------
    def index(self) -> list:
        """Entries of memory/knowledge/INDEX.md as (file, tags, summary)."""
        p = self.root / self.knowledge_dir / "INDEX.md"
        if not p.exists():
            return []
        entries = []
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^- `([^`]+)` \[([^\]]*)\] (.+)$", line)
            if m:
                tags = [t.strip() for t in m.group(2).split(",") if t.strip()]
                entries.append((m.group(1), tags, m.group(3)))
        return entries

    def read_knowledge(self, name: str, reason: str) -> str:
        return self.d.read_text(self.knowledge_dir / name, reason)

    def write_knowledge(self, name: str, content: str, tags, summary: str, reason: str) -> None:
        self.d.write_text(self.knowledge_dir / name, content, reason)
        self._upsert_index(name, tags, summary, reason)

    def _upsert_index(self, name, tags, summary, reason) -> None:
        entries = [e for e in self.index() if e[0] != name] + [(name, list(tags), summary)]
        lines = ["# Knowledge index", "",
                 "One line per file: `file` [tags] summary. Read this first, then only the files you need.", ""]
        lines += [f"- `{f}` [{', '.join(t)}] {s}" for f, t, s in sorted(entries)]
        self.d.write_text(self.knowledge_dir / "INDEX.md", "\n".join(lines) + "\n", f"index update: {reason}")

    # --- episodic memory -----------------------------------------------
    def episodes(self) -> list:
        p = self.root / self.episodes_dir
        if not p.exists():
            return []
        return sorted(f.name for f in p.iterdir() if EPISODE_RE.match(f.name))

    def read_episode(self, name: str, reason: str) -> dict:
        text = self.d.read_text(self.episodes_dir / name, reason)
        m = JSON_BLOCK_RE.search(text)
        return json.loads(m.group(1)) if m else {}

    def _next_episode_name(self, day: _dt.date) -> str:
        stem = day.isoformat()
        used = [int(m.group(2)) for n in self.episodes() if (m := EPISODE_RE.match(n)) and m.group(1) == stem]
        return f"{stem}-run-{max(used, default=0) + 1:02d}.md"

    # --- the run contract ----------------------------------------------
    def start_run(self, goal: str, tags, recent: int = 3) -> dict:
        """Read relevant memory BEFORE acting; returns what was read."""
        tags = set(tags)
        knowledge = {}
        for name, entry_tags, _summary in self.index():
            if tags & set(entry_tags) or "always" in entry_tags:
                knowledge[name] = self.read_knowledge(name, f"relevant to run goal: {goal}")
        past = [self.read_episode(n, f"recent episode for run goal: {goal}") for n in self.episodes()[-recent:]]
        context = {"goal": goal, "tags": sorted(tags), "started": _dt.datetime.now().isoformat(timespec="seconds"),
                   "knowledge_read": sorted(knowledge), "episodes_read": len(past)}
        self.save_working({"context": context}, f"start run: {goal}")
        return {"context": context, "knowledge": knowledge, "episodes": past}

    def finish_run(self, day: _dt.date, goal: str, actions, outcome: dict, lesson: str,
                   what_went_wrong: str = "", improvement: str = "") -> str:
        """Write the episode and the lesson AFTER every run. Refuses an empty lesson."""
        lesson = redact((lesson or "").strip())
        if not lesson:
            raise MissingLesson("every run must end with a concise lesson")
        if len(lesson) > LESSON_MAX:
            raise MissingLesson(f"lesson is {len(lesson)} chars; keep it under {LESSON_MAX}")
        name = self._next_episode_name(day)
        record = {"episode": name[:-3], "goal": redact(goal), "actions": [redact(a) for a in actions],
                  "outcome": outcome, "what_went_wrong": redact(what_went_wrong),
                  "lesson": lesson, "improvement": redact(improvement)}
        body = [f"# Episode {record['episode']}", "", "```json", json.dumps(record, indent=2), "```", "",
                f"**Goal:** {record['goal']}", "", "**Actions:**"]
        body += [f"- {a}" for a in record["actions"]] or ["- (none)"]
        body += ["", "**Outcome:**", ""]
        body += [f"- {k}: {v}" for k, v in outcome.items()] or ["- (none)"]
        body += ["", f"**What went wrong:** {record['what_went_wrong'] or 'nothing recorded'}",
                 "", f"**Lesson:** {lesson}", "", f"**Proposed improvement:** {record['improvement'] or 'none'}", ""]
        self.d.write_text(self.episodes_dir / name, "\n".join(body), f"episode for run: {goal}")
        self.d.append_text(self.knowledge_dir / "lessons.md", f"- {record['episode']}: {lesson}\n",
                           "distil run lesson into semantic memory")
        if "lessons.md" not in [e[0] for e in self.index()]:
            self._upsert_index("lessons.md", ["always"], "One line per run: the lesson it taught.", "register lessons")
        return name
