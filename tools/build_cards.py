#!/usr/bin/env python3
"""Вшивает банк вопросов, уроки теории и полные разборы в страницу карточек.

    python tools/build_cards.py

Страница карточек самодостаточна: вопросы, теория и разборы лежат прямо в HTML,
чтобы она открывалась с телефона без сервера. Источники правды —
banks/bank_full.json, banks/real.json, banks/lessons.json и docs/answers/*.md; после их изменения
запускай этот скрипт, иначе страница разъедется с источниками (это ловит
tests/test_cards_sync.py).
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "banks" / "bank_full.json"
REAL = ROOT / "banks" / "real.json"
LESSONS = ROOT / "banks" / "lessons.json"
FIGURES = ROOT / "banks" / "figures.json"
CODE_TASKS = ROOT / "banks" / "code_tasks.json"
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
    # anchor on "\n];": card text may contain "];", a JSON string never holds a raw newline
    html, n = re.subn(rf"const {name} = \[(?:.*?\n)?\];", lambda _: block, html, flags=re.S)
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

    real = load(REAL) if REAL.exists() else []
    known = {card["id"] for card in bank}
    # a lesson may test bank cards and real-interview cards alike
    testable = known | {card["id"] for card in real}
    dangling = {
        lesson["id"]: [i for i in lesson["cards"] if i not in testable]
        for lesson in lessons
    }
    dangling = {k: v for k, v in dangling.items() if v}
    if dangling:
        sys.exit(f"уроки ссылаются на несуществующие карточки: {dangling}")

    real_errors = []
    for card in real:
        if card["id"] in known:
            real_errors.append(f"{card['id']}: id занят в банке")
        if card.get("see") and card["see"] not in known:
            real_errors.append(f"{card['id']}: see -> {card['see']} нет в банке")
        if not card.get("asked"):
            real_errors.append(f"{card['id']}: нет asked")
    if len({card["id"] for card in real}) != len(real):
        real_errors.append("дубли id в banks/real.json")
    if real_errors:
        sys.exit("ошибки в banks/real.json:\n" + "\n".join(real_errors))

    unknown_deep = sorted(set(deep) - known - {card["id"] for card in real})
    if unknown_deep:
        sys.exit(f"в docs/answers есть разборы несуществующих карточек: {unknown_deep}")

    figures = load(FIGURES) if FIGURES.exists() else {}
    used_figs = {
        m for lesson in lessons for m in re.findall(r"\{\{fig:(\w+)\}\}", lesson["body"])
    }
    missing_figs = sorted(used_figs - set(figures))
    if missing_figs:
        sys.exit(f"уроки ссылаются на несуществующие схемы: {missing_figs}")

    tasks = load(CODE_TASKS) if CODE_TASKS.exists() else []
    seen_tasks = set()
    for task in tasks:
        for field in ("id", "title", "track", "level", "minutes",
                      "statement", "hints", "solution", "check", "notes"):
            if not task.get(field):
                sys.exit(f"задача {task.get('id')}: нет поля {field}")
        if task["id"] in seen_tasks:
            sys.exit(f"дубль задачи {task['id']}")
        seen_tasks.add(task["id"])

    html = CARDS.read_text(encoding="utf-8")
    html = replace_block(html, "CARDS", bank, 0)
    html = replace_block(html, "REAL", real, 0)
    html = replace_block(html, "LESSONS", lessons, 1)
    html = replace_block(html, "CODETASKS", tasks, 1)
    html = replace_line_block(html, "DEEP", deep)
    html = replace_line_block(html, "FIGS", figures)
    CARDS.write_text(html, encoding="utf-8")

    missing_meta = [l["id"] for l in lessons if not (l.get("tldr") and l.get("sources") and l.get("minutes"))]
    if missing_meta:
        sys.exit(f"у уроков нет tldr/sources/minutes: {missing_meta}")

    covered = {i for lesson in lessons for i in lesson["cards"]} & known
    print(
        f"вшито: {len(bank)} карточек, {len(real)} с реальных собесов, {len(lessons)} урок(ов), {len(deep)} разбор(ов), "
        f"{len(tasks)} код-задач(и); теорией покрыто {len(covered)} карточек из {len(bank)}"
    )


if __name__ == "__main__":
    main()
