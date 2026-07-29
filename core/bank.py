"""Question bank loading.

The knowledge lives here, not in the model: every question carries the key
points and a reference answer the candidate is compared against.
"""

from __future__ import annotations

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


class BankError(ValueError):
    """The bank file is missing or malformed."""


def load_bank(path: str | Path) -> list[Question]:
    path = Path(path)
    if not path.exists():
        raise BankError(f"Bank not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(raw, list):
        raise BankError(f"{path}: expected a list of questions at the top level")

    questions = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise BankError(f"{path}: entry #{index} is not a mapping")
        missing = [key for key in ("id", "question") if not item.get(key)]
        if missing:
            raise BankError(f"{path}: entry #{index} is missing {', '.join(missing)}")

        key_points = item.get("key_points") or []
        if not isinstance(key_points, list):
            raise BankError(f"{path}: {item['id']}: key_points must be a list")

        questions.append(
            Question(
                id=str(item["id"]),
                topic=str(item.get("topic", "")),
                question=str(item["question"]).strip(),
                key_points=[str(point).strip() for point in key_points if str(point).strip()],
                reference=str(item.get("reference", "")).strip(),
            )
        )

    if not questions:
        raise BankError(f"{path}: bank is empty")

    duplicates = _duplicate_ids(questions)
    if duplicates:
        raise BankError(f"{path}: duplicate ids: {', '.join(sorted(duplicates))}")

    return questions


def _duplicate_ids(questions: list[Question]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for question in questions:
        if question.id in seen:
            duplicates.add(question.id)
        seen.add(question.id)
    return duplicates


def pick(
    questions: list[Question],
    *,
    question_id: str | None = None,
    topic: str | None = None,
    exclude: set[str] | None = None,
    rng: random.Random | None = None,
) -> Question:
    """Pick one question: by id, or at random within an optional topic."""
    if question_id:
        for question in questions:
            if question.id == question_id:
                return question
        raise BankError(f"Question with id '{question_id}' not found")

    pool = [q for q in questions if not topic or q.topic == topic]
    if not pool:
        raise BankError(f"No questions with topic '{topic}'")

    fresh = [q for q in pool if q.id not in (exclude or set())]
    # Once the bank is exhausted, start over rather than refusing to ask.
    return (rng or random).choice(fresh or pool)
