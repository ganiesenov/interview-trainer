"""The flashcards page carries an inlined copy of the bank.

`tools/gen_bank.py --inject cards/interview_cards.html` refreshes it; this test
catches the copy silently drifting from banks/bank_full.json.
"""

import json
import re
from pathlib import Path

import pytest

BANK = Path("banks/bank_full.json")
CARDS = Path("cards/interview_cards.html")


def inlined_cards() -> list[dict]:
    html = CARDS.read_text(encoding="utf-8")
    match = re.search(r"const CARDS = (\[.*?\]);", html, re.DOTALL)
    if not match:
        pytest.fail("const CARDS block not found in cards/interview_cards.html")
    return json.loads(match.group(1))


def test_cards_html_matches_the_bank():
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    cards = inlined_cards()
    assert [card["id"] for card in cards] == [card["id"] for card in bank]
    assert [card["q"] for card in cards] == [card["q"] for card in bank]
