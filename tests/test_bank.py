import random

import pytest

from core.bank import BankError, load_bank, pick

BANK = "banks/theory.yaml"


def write(tmp_path, text):
    path = tmp_path / "bank.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_shipped_bank_loads_and_is_gradeable():
    questions = load_bank(BANK)
    assert len(questions) == 5
    for question in questions:
        assert question.key_points, f"{question.id} has no key_points"
        assert question.reference, f"{question.id} has no reference"


def test_missing_file():
    with pytest.raises(BankError):
        load_bank("banks/nope.yaml")


def test_entry_without_question_is_rejected(tmp_path):
    with pytest.raises(BankError, match="question"):
        load_bank(write(tmp_path, "- id: a\n  topic: t\n"))


def test_duplicate_ids_are_rejected(tmp_path):
    text = "- id: a\n  question: q1\n- id: a\n  question: q2\n"
    with pytest.raises(BankError, match="duplicate"):
        load_bank(write(tmp_path, text))


def test_empty_bank_is_rejected(tmp_path):
    with pytest.raises(BankError):
        load_bank(write(tmp_path, "[]\n"))


def test_pick_by_id_and_topic():
    questions = load_bank(BANK)
    assert pick(questions, question_id="kv_cache_01").id == "kv_cache_01"
    assert pick(questions, topic="architecture").topic == "architecture"
    with pytest.raises(BankError):
        pick(questions, question_id="nope")
    with pytest.raises(BankError):
        pick(questions, topic="nope")


def test_pick_avoids_already_asked_until_the_bank_is_exhausted():
    questions = load_bank(BANK)
    ids = {question.id for question in questions}
    rng = random.Random(0)

    asked = set()
    for _ in range(len(questions)):
        question = pick(questions, exclude=asked, rng=rng)
        assert question.id not in asked
        asked.add(question.id)

    # Bank exhausted — it wraps around instead of raising.
    assert pick(questions, exclude=asked, rng=rng).id in ids
