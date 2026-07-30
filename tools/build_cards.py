#!/usr/bin/env python3
"""Вшивает банк вопросов, уроки теории и полные разборы в страницу карточек.

    python tools/build_cards.py

Страница карточек самодостаточна: вопросы, теория и разборы лежат прямо в HTML,
чтобы она открывалась с телефона без сервера. Источники правды —
banks/bank_full.json, banks/lessons.json и docs/answers/*.md; после их изменения
запускай этот скрипт, иначе страница разъедется с источниками (это ловит
tests/test_cards_sync.py).
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "banks" / "bank_full.json"
LESSONS = ROOT / "banks" / "lessons.json"
ANSWERS = ROOT / "docs" / "answers"
CARDS = ROOT / "cards" / "interview_cards.html"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_deep() -> dict[str, str]:
    """Per-card breakdowns from docs/answers/*.md, keyed by card id."""
    deep: dict[str, str] = {}
    section = re.compile(r"^### `(\w+)`[^\n]*\n(.*?)(?=^### |^## |\Z)", re.M | re.S)
    for path in sorted(ANSWERS.glob("*.md")):
        for card_id, body in section.findall(path.read_text(encoding="utf-8")):
            body = re.sub(r"\n-{3,}\s*$", "", body.strip()).strip()
            if card_id in deep:
                sys.exit(f"разбор для карточки {card_id} встречается дважды (в т.ч. {path.name})")
            deep[card_id] = body
    return deep


def replace_block(html: str, name: str, value, indent: int) -> str:
    block = f"const {name} = " + json.dumps(value, ensure_ascii=False, indent=indent) + ";"
    html, n = re.subn(rf"const {name} = \[.*?\];", lambda _: block, html, flags=re.S)
    if n != 1:
        sys.exit(f"в HTML не найден ровно один блок const {name} (найдено {n})")
    return html


def replace_line_block(html: str, name: str, value) -> str:
    """Replace a single-line `const NAME = {...};` declaration (compact JSON)."""
    block = f"const {name} = " + json.dumps(value, ensure_ascii=False) + ";"
    html, n = re.subn(rf"const {name} = \{{.*\}};", lambda _: block, html)
    if n != 1:
        sys.exit(f"в HTML не найдена ровно одна строка const {name} (найдено {n})")
    return html


def main() -> None:
    bank = load(BANK)
    lessons = load(LESSONS)
    deep = load_deep()

    known = {card["id"] for card in bank}
    dangling = {
        lesson["id"]: [i for i in lesson["cards"] if i not in known]
        for lesson in lessons
    }
    dangling = {k: v for k, v in dangling.items() if v}
    if dangling:
        sys.exit(f"уроки ссылаются на несуществующие карточки: {dangling}")

    unknown_deep = sorted(set(deep) - known)
    if unknown_deep:
        sys.exit(f"в docs/answers есть разборы несуществующих карточек: {unknown_deep}")

    html = CARDS.read_text(encoding="utf-8")
    html = replace_block(html, "CARDS", bank, 0)
    html = replace_block(html, "LESSONS", lessons, 1)
    html = replace_line_block(html, "DEEP", deep)
    CARDS.write_text(html, encoding="utf-8")

    missing_meta = [l["id"] for l in lessons if not (l.get("tldr") and l.get("sources") and l.get("minutes"))]
    if missing_meta:
        sys.exit(f"у уроков нет tldr/sources/minutes: {missing_meta}")

    covered = {i for lesson in lessons for i in lesson["cards"]}
    print(
        f"вшито: {len(bank)} карточек, {len(lessons)} урок(ов), {len(deep)} разбор(ов); "
        f"теорией покрыто {len(covered)} карточек из {len(bank)}"
    )


if __name__ == "__main__":
    main()
