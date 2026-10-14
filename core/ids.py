"""Code-owned identifiers, hashes and timestamps.

No model ever writes these fields [A p.4, p.8 "Where to start" #1].
"""
import datetime as _dt
import hashlib
import re
from zoneinfo import ZoneInfo

AREAS = ("CON", "CAR", "PER", "MUS", "POD", "ALL")  # [B p.8]
PREFIXES = ("T", "IN", "R", "CAL")                  # tasks, inbox events, registry, calendar [B p.5, p.16]
LOCAL_TZ = ZoneInfo("America/Los_Angeles")          # model.md G9, marked uncertain

_ID_RE = re.compile(r"^(T|IN|R|CAL)-(\d{8})-(CON|CAR|PER|MUS|POD|ALL)-(\d{2,})$")


def email_intent_hash(thread_id: str, last_msg_id: str, intent_idx: int) -> str:
    """sha256(thread_id|last_msg_id|intent_idx) [A p.4]."""
    if not thread_id or not last_msg_id or intent_idx < 0:
        raise ValueError("thread_id, last_msg_id and a non-negative intent_idx are required")
    return hashlib.sha256(f"{thread_id}|{last_msg_id}|{intent_idx}".encode()).hexdigest()


def normalize_summary(summary: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", re.sub(r"\s+", " ", summary.lower())).strip()


def task_intent_hash(area: str, summary: str) -> str:
    """SHA256(area || normalized summary) [B p.9], used to dedupe tasks."""
    if area not in AREAS:
        raise ValueError(f"unknown area {area!r}")
    return hashlib.sha256(f"{area}|{normalize_summary(summary)}".encode()).hexdigest()


def timestamp_from_internal_date(internal_date_ms) -> str:
    """Gmail internalDate (epoch ms) -> ISO 8601 in local time [A p.4]."""
    ms = int(internal_date_ms)
    return _dt.datetime.fromtimestamp(ms / 1000, tz=LOCAL_TZ).isoformat(timespec="seconds")


def next_id(prefix: str, area: str, day: _dt.date, existing_ids) -> str:
    """Collision-proof ID [B p.3, p.5]: PREFIX-YYYYMMDD-AREA-NN.

    NN is computed by code from the IDs that already exist, never chosen by a model.
    """
    if prefix not in PREFIXES:
        raise ValueError(f"unknown prefix {prefix!r}")
    if area not in AREAS:
        raise ValueError(f"unknown area {area!r}")
    stem = f"{prefix}-{day:%Y%m%d}-{area}-"
    used = [int(m.group(4)) for i in existing_ids if (m := _ID_RE.match(i)) and i.startswith(stem)]
    return f"{stem}{max(used, default=0) + 1:02d}"


def is_valid_id(value: str) -> bool:
    return bool(_ID_RE.match(value or ""))
