"""The flashcards page carries an inlined copy of the bank and of the lessons.

`python tools/build_cards.py` refreshes both; this test catches the copies
silently drifting from banks/bank_full.json and banks/lessons.json.
"""

import json
import re
from pathlib import Path

import pytest

BANK = Path("banks/bank_full.json")
LESSONS = Path("banks/lessons.json")
CARDS = Path("cards/interview_cards.html")


def inlined(name: str) -> list[dict]:
    html = CARDS.read_text(encoding="utf-8")
    match = re.search(rf"const {name} = (\[.*?\]);", html, re.DOTALL)
    if not match:
        pytest.fail(f"const {name} block not found in cards/interview_cards.html")
    return json.loads(match.group(1))


def test_cards_html_matches_the_bank():
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    cards = inlined("CARDS")
    assert [card["id"] for card in cards] == [card["id"] for card in bank]
    assert [card["q"] for card in cards] == [card["q"] for card in bank]


def test_cards_html_matches_the_lessons():
    assert inlined("LESSONS") == json.loads(LESSONS.read_text(encoding="utf-8"))


def test_lessons_are_well_formed_and_point_at_real_cards():
    lessons = json.loads(LESSONS.read_text(encoding="utf-8"))
    known = {card["id"] for card in json.loads(BANK.read_text(encoding="utf-8"))}

    seen_ids = set()
    for lesson in lessons:
        for field in ("id", "title", "track", "cards", "minutes", "tldr", "body", "sources"):
            assert lesson.get(field), f"{lesson.get('id')}: missing {field}"
        assert lesson["id"] not in seen_ids, f"duplicate lesson id {lesson['id']}"
        seen_ids.add(lesson["id"])

        missing = [card for card in lesson["cards"] if card not in known]
        assert not missing, f"{lesson['id']} points at unknown cards: {missing}"
        assert len(lesson["body"].split()) > 200, f"{lesson['id']}: lesson body is too thin"

        # каждый урок обязан начинаться с TL;DR и заканчиваться источниками
        assert 2 <= len(lesson["tldr"]) <= 4, f"{lesson['id']}: tldr should be 2-4 bullets"
        assert lesson["sources"], f"{lesson['id']}: no sources"
        assert lesson["minutes"] >= 3, f"{lesson['id']}: implausible reading time"
