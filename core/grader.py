"""Grading: compare the candidate's answer against the reference, point by point.

The model only assigns per-point statuses. The score is computed in Python —
local models hand out numbers at random.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from core import prompts
from core.bank import Question
from core.llm import GRADER_TEMPERATURE, LLMError, chat

COVERED, PARTIAL, MISSED = "covered", "partial", "missed"
STATUSES = (COVERED, PARTIAL, MISSED)

# Below this similarity a returned point is not considered the same point.
_MATCH_THRESHOLD = 0.45


@dataclass
class PointResult:
    point: str
    status: str = MISSED
    quote: str = ""


@dataclass
class Grade:
    points: list[PointResult] = field(default_factory=list)
    invented: list[str] = field(default_factory=list)
    hedging: bool = False
    score: int = 1

    def count(self, status: str) -> int:
        return sum(1 for point in self.points if point.status == status)


def grade(
    question: Question,
    answer: str,
    *,
    model: str | None = None,
    attempts: int = 2,
) -> Grade:
    """Grade one answer. Raises LLMError if the model never returns usable JSON."""
    if not question.key_points:
        raise ValueError(f"Question '{question.id}' has no key_points to grade against")

    if not answer.strip():
        # Nothing to compare — do not spend a model call on an empty answer.
        points = [PointResult(point=point) for point in question.key_points]
        return Grade(points=points, score=score_points(points))

    messages = [
        {"role": "system", "content": prompts.GRADER_SYSTEM},
        {
            "role": "user",
            "content": prompts.GRADER_USER.format(
                reference=question.reference or "—",
                key_points=prompts.numbered(question.key_points),
                question=question.question,
                answer=answer.strip(),
                n_points=len(question.key_points),
            ),
        },
    ]

    last_error: Exception | None = None
    for _ in range(max(1, attempts)):
        raw = chat(messages, model=model, temperature=GRADER_TEMPERATURE, json_mode=True)
        try:
            payload = parse_json(raw)
        except ValueError as exc:
            last_error = exc
            continue
        return build_grade(question.key_points, payload)

    raise LLMError(f"Grader did not return valid JSON: {last_error}")


def parse_json(raw: str) -> dict:
    """Parse the grader's reply, tolerating markdown fences and stray prose."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("empty reply")

    fenced = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("no JSON object in reply") from None
        try:
            payload = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed JSON: {exc}") from None

    if not isinstance(payload, dict):
        raise ValueError("JSON is not an object")
    return payload


def build_grade(key_points: list[str], payload: dict) -> Grade:
    """Map the model's reply onto our own key points and score it ourselves."""
    points = align_points(key_points, payload.get("points"))
    return Grade(
        points=points,
        invented=[str(item).strip() for item in _as_list(payload.get("invented")) if str(item).strip()],
        hedging=bool(payload.get("hedging")),
        score=score_points(points),
    )


def align_points(key_points: list[str], raw_points) -> list[PointResult]:
    """Match returned points back to ours — the model rewords and reorders them."""
    returned = [item for item in _as_list(raw_points) if isinstance(item, dict)]
    results = [PointResult(point=point) for point in key_points]
    used: set[int] = set()

    for index, result in enumerate(results):
        match = _best_match(result.point, returned, used)
        if match is None and index < len(returned) and index not in used:
            match = index  # fall back to position when wording drifted too far
        if match is None:
            continue
        used.add(match)
        item = returned[match]
        result.status = _status(item.get("status"))
        result.quote = str(item.get("quote") or "").strip()

    return results


def _best_match(point: str, returned: list[dict], used: set[int]) -> int | None:
    best_index, best_ratio = None, 0.0
    for index, item in enumerate(returned):
        if index in used:
            continue
        ratio = _similarity(point, str(item.get("point") or ""))
        if ratio > best_ratio:
            best_index, best_ratio = index, ratio
    return best_index if best_ratio >= _MATCH_THRESHOLD else None


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalize(left), _normalize(right)).ratio()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _status(value) -> str:
    status = str(value or "").strip().lower()
    return status if status in STATUSES else MISSED


def _as_list(value) -> list:
    if isinstance(value, list):
        return value
    if value in (None, "", {}):
        return []
    return [value]


def score_points(points: list[PointResult]) -> int:
    """covered = 1, partial = 0.5, missed = 0 → share of the bank, mapped to 1-10."""
    if not points:
        return 1
    weights = {COVERED: 1.0, PARTIAL: 0.5, MISSED: 0.0}
    share = sum(weights[point.status] for point in points) / len(points)
    return max(1, min(10, round(share * 10)))
