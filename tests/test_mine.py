from datetime import datetime, timezone

import pytest

from core import mine
from core.bank import Question

QUESTION = Question(
    id="kv",
    topic="Инференс",
    question="Зачем нужен KV-cache?",
    key_points=["пункт банка A", "пункт банка B"],
    reference="Эталон.",
    track="LLM",
)
NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)


def test_load_missing_file_is_empty(tmp_path):
    assert mine.load(tmp_path / "nope.json") == {}


def test_load_broken_file_is_empty(tmp_path):
    path = tmp_path / "my.json"
    path.write_text("{not json", encoding="utf-8")
    assert mine.load(path) == {}


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "sub" / "my.json"
    entries = mine.upsert({}, "kv", ["раз", "два"], now=NOW)
    mine.save(entries, path)
    assert mine.load(path) == entries


def test_upsert_stamps_and_does_not_mutate_input():
    original = {}
    entries = mine.upsert(original, "kv", ["раз"], note="из моего проекта", now=NOW)
    assert original == {}
    assert entries["kv"]["points"] == ["раз"]
    assert entries["kv"]["note"] == "из моего проекта"
    assert entries["kv"]["updated"] == "2026-07-29T12:00:00+00:00"


def test_upsert_rejects_empty_points():
    with pytest.raises(ValueError):
        mine.upsert({}, "kv", [])


def test_remove():
    entries = mine.upsert({}, "kv", ["раз"], now=NOW)
    assert mine.remove(entries, "kv") == {}
    assert mine.remove(entries, "nope") == entries


@pytest.mark.parametrize(
    "text, expected",
    [
        ("раз\nдва", ["раз", "два"]),
        ("- раз\n* два\n• три", ["раз", "два", "три"]),
        ("1. раз\n2) два", ["раз", "два"]),
        ("  раз  \n\n\n  два", ["раз", "два"]),
        ("", []),
        ("   \n  ", []),
    ],
)
def test_parse_points(text, expected):
    assert mine.parse_points(text) == expected


def test_apply_to_swaps_key_points_and_keeps_the_rest():
    entries = mine.upsert({}, "kv", ["мой пункт"], now=NOW)
    question, is_mine = mine.apply_to(QUESTION, entries)
    assert is_mine is True
    assert question.key_points == ["мой пункт"]
    assert question.question == QUESTION.question
    assert question.reference == QUESTION.reference  # банковский эталон остаётся для показа


def test_apply_to_without_personal_answer_returns_question_untouched():
    question, is_mine = mine.apply_to(QUESTION, {})
    assert is_mine is False
    assert question is QUESTION


def test_apply_to_ignores_empty_or_blank_points():
    assert mine.apply_to(QUESTION, {"kv": {"points": []}})[1] is False
    assert mine.apply_to(QUESTION, {"kv": {"points": ["  "]}})[1] is False
