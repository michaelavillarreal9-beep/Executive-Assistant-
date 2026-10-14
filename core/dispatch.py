"""The single entry point for every action a script takes.

- Every action is logged with its reason to logs/actions.log (guardrail: audit trail).
- File access is confined to the repo; deletes need a named human approval.
- Nothing here can reach the network.
- After 3 failed attempts on the same step, it stops and asks (guardrail).

Tool calls made by Claude itself (Gmail, Calendar, Drive) are governed separately by
.claude/settings.json and .claude/hooks/ (architecture.md section 8).
"""
import datetime as _dt
import json
from pathlib import Path

MAX_FAILURES = 3


class ApprovalRequired(Exception):
    """The action needs a human approval that was not given."""


class OutsideRepo(Exception):
    """The action tried to touch a path outside the repository."""


class CheckIn(Exception):
    """A step failed MAX_FAILURES times; stop and ask the human."""


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _clean(text: str) -> str:
    return " ".join(str(text).replace("|", "/").split())


class Dispatcher:
    def __init__(self, root, phase: str = "RUN"):
        self.root = Path(root).resolve()
        self.phase = phase
        self.log_path = self.root / "logs" / "actions.log"
        self.failures_path = self.root / "memory" / "working" / "failures.json"

    # --- logging -------------------------------------------------------
    def log(self, action: str, reason: str, outcome: str = "ok") -> None:
        if not reason or not reason.strip():
            raise ValueError("every action needs a reason")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        line = f"{_now()} | {self.phase} | {_clean(action)} | {_clean(reason)} | {_clean(outcome)}\n"
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(line)

    # --- path boundary -------------------------------------------------
    def _inside(self, path) -> Path:
        p = (self.root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        if p != self.root and self.root not in p.parents:
            raise OutsideRepo(f"{path} is outside the repository")
        return p

    def rel(self, path) -> str:
        return str(self._inside(path).relative_to(self.root))

    # --- file actions --------------------------------------------------
    def read_text(self, path, reason: str) -> str:
        p = self._inside(path)
        text = p.read_text(encoding="utf-8")
        self.log(f"read {self.rel(p)}", reason)
        return text

    def write_text(self, path, content: str, reason: str) -> Path:
        p = self._inside(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        verb = "overwrite" if p.exists() else "create"
        p.write_text(content, encoding="utf-8")
        self.log(f"{verb} {self.rel(p)}", reason)
        return p

    def append_text(self, path, content: str, reason: str) -> Path:
        p = self._inside(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(content)
        self.log(f"append {self.rel(p)}", reason)
        return p

    def delete(self, path, reason: str, approved_by: str = None) -> None:
        """Deleting needs a named human approval (guardrail)."""
        p = self._inside(path)
        if not approved_by:
            self.log(f"delete {self.rel(p)}", reason, "BLOCKED: approval required")
            raise ApprovalRequired(f"deleting {self.rel(p)} needs your approval")
        p.unlink()
        self.log(f"delete {self.rel(p)}", reason, f"approved by {approved_by}")

    # --- steps with the 3-failure rule ---------------------------------
    def _failures(self) -> dict:
        try:
            return json.loads(self.failures_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_failures(self, data: dict) -> None:
        self.failures_path.parent.mkdir(parents=True, exist_ok=True)
        self.failures_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def step(self, name: str, reason: str, fn, *args, **kwargs):
        """Run one step. Failures persist across runs; the 4th attempt is refused."""
        failures = self._failures()
        count = failures.get(name, 0)
        if count >= MAX_FAILURES:
            self.log(f"step {name}", reason, f"BLOCKED: {count} failures, check in with the human")
            raise CheckIn(f"step {name!r} failed {count} times; asking before trying again")
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            failures[name] = count + 1
            self._save_failures(failures)
            self.log(f"step {name}", reason, f"FAILED ({count + 1}/{MAX_FAILURES}): {type(exc).__name__}: {exc}")
            raise
        if name in failures:
            del failures[name]
            self._save_failures(failures)
        self.log(f"step {name}", reason)
        return result

    def reset_step(self, name: str, approved_by: str) -> None:
        """After a human check-in, clear a step's failure count."""
        failures = self._failures()
        failures.pop(name, None)
        self._save_failures(failures)
        self.log(f"reset step {name}", "human check-in", f"approved by {approved_by}")
