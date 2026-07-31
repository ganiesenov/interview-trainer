"""The Код-тренажёр bank: every reference solution must actually pass its own check.

banks/code_tasks.json is inlined into the cards page by tools/build_cards.py;
these tests catch (a) the page drifting from the bank, (b) a solution or check
silently broken by an edit — solutions are executed for real.
"""

import json
import re
from pathlib import Path

import pytest

BANK = Path("banks/code_tasks.json")
CARDS = Path("cards/interview_cards.html")

REQUIRED = ("id", "title", "track", "level", "minutes",
            "statement", "hints", "solution", "check", "notes")
LEVELS = {"разминка", "основная", "со звёздочкой"}

# tasks building on the attention task get its solution pre-loaded
NEEDS_ATTENTION = {"ct_mha", "ct_kvcache"}


def tasks():
    return json.loads(BANK.read_text(encoding="utf-8"))


def test_tasks_are_well_formed():
    seen = set()
    for t in tasks():
        for field in REQUIRED:
            assert t.get(field), f"{t.get('id')}: missing {field}"
        assert t["id"] not in seen, f"duplicate task id {t['id']}"
        seen.add(t["id"])
        assert t["level"] in LEVELS, f"{t['id']}: unknown level {t['level']}"
        assert 1 <= len(t["hints"]) <= 3, f"{t['id']}: hints should be 1-3"
        assert t["minutes"] >= 5, f"{t['id']}: implausible minutes"
        assert "**Что проверяют.**" in t["notes"], t["id"]


def test_cards_html_matches_the_code_tasks():
    html = CARDS.read_text(encoding="utf-8")
    match = re.search(r"const CODETASKS = (\[.*?\]);", html, re.DOTALL)
    assert match, "const CODETASKS block not found — run tools/build_cards.py"
    assert json.loads(match.group(1)) == tasks(), \
        "CODETASKS drifted from banks/code_tasks.json — run tools/build_cards.py"


@pytest.mark.parametrize("task", tasks(), ids=lambda t: t["id"])
def test_reference_solution_passes_its_check(task):
    if "numpy" in task["solution"] or "numpy" in task["check"]:
        pytest.importorskip("numpy")
    ns = {}
    if task["id"] in NEEDS_ATTENTION:
        attention = next(t for t in tasks() if t["id"] == "ct_attention")
        exec(attention["solution"], ns)  # noqa: S102 — our own bank
    exec(task["solution"], ns)  # noqa: S102
    exec(task["check"], ns)  # noqa: S102
