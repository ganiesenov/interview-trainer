"""Personal reference answers.

The bank holds one opinion about what a strong answer contains. Your own
wording is better calibrated to how you actually speak and to your projects,
so once you write it down the trainer grades against it instead of the bank.

Stored in data/my_answers.json (git-ignored — it is personal):

    {"kv": {"points": ["..."], "note": "...", "updated": "2026-07-29T12:00:00Z"}}
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from core.bank import Question

DEFAULT_PATH = Path("data/my_answers.json")

_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")


def load(path: str | Path = DEFAULT_PATH) -> dict[str, dict]:
    """Load personal answers. A missing or unreadable file is not an error."""
    path = Path(path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def save(entries: dict[str, dict], path: str | Path = DEFAULT_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")


def parse_points(text: str) -> list[str]:
    """Turn typed lines into a list of points, tolerating bullets and numbering."""
    points = []
    for line in (text or "").splitlines():
        cleaned = _BULLET.sub("", line).strip()
        if cleaned:
            points.append(cleaned)
    return points


def upsert(
    entries: dict[str, dict],
    question_id: str,
    points: list[str],
    *,
    note: str = "",
    now: datetime | None = None,
) -> dict[str, dict]:
    """Return a new mapping with this question's personal answer set."""
    if not points:
        raise ValueError("personal answer needs at least one point")
    stamp = (now or datetime.now(timezone.utc)).replace(microsecond=0).isoformat()
    updated = dict(entries)
    updated[question_id] = {"points": list(points), "note": note, "updated": stamp}
    return updated


def remove(entries: dict[str, dict], question_id: str) -> dict[str, dict]:
    updated = dict(entries)
    updated.pop(question_id, None)
    return updated


def points_for(entries: dict[str, dict], question_id: str) -> list[str]:
    entry = entries.get(question_id) or {}
    points = entry.get("points") or []
    return [str(point).strip() for point in points if str(point).strip()]


def apply_to(question: Question, entries: dict[str, dict]) -> tuple[Question, bool]:
    """Swap in the personal key points if they exist. Returns (question, is_mine)."""
    points = points_for(entries, question.id)
    if not points:
        return question, False
    return replace(question, key_points=points), True
