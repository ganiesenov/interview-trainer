#!/usr/bin/env python3
"""Вшивает банк вопросов и уроки теории в страницу карточек.

    python tools/build_cards.py

Страница карточек самодостаточна: и вопросы, и теория лежат прямо в HTML, чтобы
она открывалась с телефона без сервера. Источники правды — banks/bank_full.json и
banks/lessons.json; после их изменения запускай этот скрипт, иначе страница
разъедется с банком (это ловит tests/test_cards_sync.py).
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "banks" / "bank_full.json"
LESSONS = ROOT / "banks" / "lessons.json"
CARDS = ROOT / "cards" / "interview_cards.html"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def replace_block(html: str, name: str, value, indent: int) -> str:
    block = f"const {name} = " + json.dumps(value, ensure_ascii=False, indent=indent) + ";"
    html, n = re.subn(rf"const {name} = \[.*?\];", lambda _: block, html, flags=re.S)
    if n != 1:
        sys.exit(f"в HTML не найден ровно один блок const {name} (найдено {n})")
    return html


def main() -> None:
    bank = load(BANK)
    lessons = load(LESSONS)

    known = {card["id"] for card in bank}
    dangling = {
        lesson["id"]: [i for i in lesson["cards"] if i not in known]
        for lesson in lessons
    }
    dangling = {k: v for k, v in dangling.items() if v}
    if dangling:
        sys.exit(f"уроки ссылаются на несуществующие карточки: {dangling}")

    html = CARDS.read_text(encoding="utf-8")
    html = replace_block(html, "CARDS", bank, 0)
    html = replace_block(html, "LESSONS", lessons, 1)
    CARDS.write_text(html, encoding="utf-8")

    missing_meta = [l["id"] for l in lessons if not (l.get("tldr") and l.get("sources") and l.get("minutes"))]
    if missing_meta:
        sys.exit(f"у уроков нет tldr/sources/minutes: {missing_meta}")

    covered = {i for lesson in lessons for i in lesson["cards"]}
    print(
        f"вшито: {len(bank)} карточек, {len(lessons)} урок(ов); "
        f"теорией покрыто {len(covered)} карточек из {len(bank)}"
    )


if __name__ == "__main__":
    main()
