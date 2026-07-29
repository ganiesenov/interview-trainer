"""Question bank loading.

The knowledge lives here, not in the model: every question carries the key
points and a reference answer the candidate is compared against.

Two on-disk shapes are supported, because the same bank feeds two tools:

    JSON (banks/bank_full.json, also eaten by tools/gen_bank.py and the cards):
        {"id", "track", "topic", "q", "points": [...], "ref"}

    YAML (hand-written banks):
        {"id", "track", "topic", "question", "key_points": [...], "reference"}

Field names from either shape are accepted in either file format.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Question:
    id: str
    topic: str
    question: str
    key_points: list[str] = field(default_factory=list)
    reference: str = ""
    track: str = ""


class BankError(ValueError):
    """The bank file is missing or malformed."""


def load_bank(path: str | Path) -> list[Question]:
    path = Path(path)
    if not path.exists():
        raise BankError(f"Bank not found: {path}")

    text = path.read_text(encoding="utf-8")
    try:
        raw = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise BankError(f"{path}: cannot parse: {exc}") from None

    raw = raw or []
    if not isinstance(raw, list):
        raise BankError(f"{path}: expected a list of questions at the top level")

    questions = [_to_question(item, index, path) for index, item in enumerate(raw, start=1)]
    if not questions:
        raise BankError(f"{path}: bank is empty")

    duplicates = _duplicate_ids(questions)
    if duplicates:
        raise BankError(f"{path}: duplicate ids: {', '.join(sorted(duplicates))}")

    return questions


def _to_question(item, index: int, path: Path) -> Question:
    if not isinstance(item, dict):
        raise BankError(f"{path}: entry #{index} is not a mapping")

    question_text = _first(item, "question", "q")
    if not item.get("id") or not question_text:
        missing = [
            name
            for name, value in (("id", item.get("id")), ("question/q", question_text))
            if not value
        ]
        raise BankError(f"{path}: entry #{index} is missing {', '.join(missing)}")

    key_points = _first(item, "key_points", "points") or []
    if not isinstance(key_points, list):
        raise BankError(f"{path}: {item['id']}: key_points/points must be a list")

    return Question(
        id=str(item["id"]),
        topic=str(item.get("topic", "")),
        question=str(question_text).strip(),
        key_points=[str(point).strip() for point in key_points if str(point).strip()],
        reference=str(_first(item, "reference", "ref") or "").strip(),
        track=str(item.get("track", "")),
    )


def _first(item: dict, *names: str):
    for name in names:
        if item.get(name):
            return item[name]
    return None


def _duplicate_ids(questions: list[Question]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for question in questions:
        if question.id in seen:
            duplicates.add(question.id)
        seen.add(question.id)
    return duplicates


def filter_questions(
    questions: list[Question],
    *,
    track: str | None = None,
    topic: str | None = None,
) -> list[Question]:
    """Filter by track/topic. Matching is case-insensitive and prefix-friendly."""
    pool = questions
    if track:
        pool = [q for q in pool if _matches(q.track, track)]
        if not pool:
            raise BankError(f"No questions in track '{track}'")
    if topic:
        pool = [q for q in pool if _matches(q.topic, topic)]
        if not pool:
            raise BankError(f"No questions with topic '{topic}'")
    return pool


def _matches(value: str, wanted: str) -> bool:
    value, wanted = value.strip().lower(), wanted.strip().lower()
    return value == wanted or value.startswith(wanted)


def pick(
    questions: list[Question],
    *,
    question_id: str | None = None,
    track: str | None = None,
    topic: str | None = None,
    exclude: set[str] | None = None,
    rng: random.Random | None = None,
) -> Question:
    """Pick one question: by id, or at random within an optional track/topic."""
    if question_id:
        for question in questions:
            if question.id == question_id:
                return question
        raise BankError(f"Question with id '{question_id}' not found")

    pool = filter_questions(questions, track=track, topic=topic)
    fresh = [q for q in pool if q.id not in (exclude or set())]
    # Once the pool is exhausted, start over rather than refusing to ask.
    return (rng or random).choice(fresh or pool)


def coverage(questions: list[Question]) -> dict[str, dict[str, int]]:
    """track -> topic -> count, for `run.py --stats`."""
    stats: dict[str, dict[str, int]] = {}
    for question in questions:
        track = stats.setdefault(question.track or "—", {})
        topic = question.topic or "—"
        track[topic] = track.get(topic, 0) + 1
    return stats
