import random

import pytest

from core.bank import BankError, coverage, filter_questions, load_bank, pick

BANK = "banks/bank_full.json"


def write(tmp_path, text, name="bank.yaml"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_shipped_bank_loads_and_is_gradeable():
    questions = load_bank(BANK)
    assert len(questions) >= 100
    for question in questions:
        assert question.key_points, f"{question.id} has no key_points"
        assert question.reference, f"{question.id} has no reference"
        assert question.track, f"{question.id} has no track"


def test_json_and_yaml_field_names_are_interchangeable(tmp_path):
    json_bank = write(
        tmp_path,
        '[{"id": "a", "track": "LLM", "topic": "Инференс", "q": "Вопрос?",'
        ' "points": ["раз", "два"], "ref": "Эталон."}]',
        name="bank.json",
    )
    yaml_bank = write(
        tmp_path,
        "- id: a\n"
        "  track: LLM\n"
        "  topic: Инференс\n"
        "  question: Вопрос?\n"
        "  key_points:\n    - раз\n    - два\n"
        "  reference: Эталон.\n",
    )
    assert load_bank(json_bank) == load_bank(yaml_bank)


def test_missing_file():
    with pytest.raises(BankError):
        load_bank("banks/nope.yaml")


def test_unparsable_file_is_reported_as_bank_error(tmp_path):
    with pytest.raises(BankError, match="cannot parse"):
        load_bank(write(tmp_path, "{not json", name="bank.json"))


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


def test_filter_by_track_and_topic():
    questions = load_bank(BANK)
    llm = filter_questions(questions, track="LLM")
    assert llm and all(question.track == "LLM" for question in llm)

    inference = filter_questions(questions, track="LLM", topic="Инференс")
    assert inference and all(question.topic == "Инференс" for question in inference)
    assert len(inference) < len(llm)

    # Case-insensitive and prefix-friendly, so `--track llm` works.
    assert filter_questions(questions, track="llm") == llm

    with pytest.raises(BankError, match="track"):
        filter_questions(questions, track="Астрология")
    with pytest.raises(BankError, match="topic"):
        filter_questions(questions, track="LLM", topic="Астрология")


def test_pick_by_id():
    questions = load_bank(BANK)
    assert pick(questions, question_id="kv").id == "kv"
    with pytest.raises(BankError):
        pick(questions, question_id="nope")


def test_pick_avoids_already_asked_until_the_pool_is_exhausted():
    questions = load_bank(BANK)
    pool = filter_questions(questions, track="HR-скрининг")
    rng = random.Random(0)

    asked = set()
    for _ in range(len(pool)):
        question = pick(questions, track="HR-скрининг", exclude=asked, rng=rng)
        assert question.id not in asked
        asked.add(question.id)

    # Pool exhausted — it wraps around instead of raising.
    assert pick(questions, track="HR-скрининг", exclude=asked, rng=rng).id in asked


def test_coverage_counts_by_track_and_topic():
    questions = load_bank(BANK)
    stats = coverage(questions)
    assert sum(sum(topics.values()) for topics in stats.values()) == len(questions)
    assert stats["LLM"]["Инференс"] >= 5
