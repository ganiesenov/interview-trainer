#!/usr/bin/env python3
"""Импорт реальных вопросов с собеседований и сопоставление с банком.

    python tools/import_real.py --normalize          # data/real/extracted.jsonl -> normalized.jsonl
    python tools/import_real.py --match              # топ-5 кандидатов из банка (bge-m3)
    python tools/import_real.py --resolve            # вердикты судьи + overrides -> resolved.jsonl

Двухэтапный матчинг: эмбеддинги дают кандидатов, решает судья (субагенты
по tools/judge_prompt.md, вердикты в data/real/judged.jsonl). Ручные правки —
data/real/overrides.json: {"rid": "card_id" | null}, применяются поверх судьи.

Источник — выгрузка Threads (data/real/source.jsonl), посты о собесах уже
разбиты на атомарные вопросы в data/real/extracted.jsonl. Всё в data/real/
git-ignored: тексты чужие, в банк и в коммиты не попадают ни вопросы как есть,
ни ответы автора.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_bank import embed, load_bank  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / "data" / "real"
EXTRACTED = REAL / "extracted.jsonl"
NORMALIZED = REAL / "normalized.jsonl"
CANDIDATES = REAL / "candidates.jsonl"
JUDGED = REAL / "judged.jsonl"
OVERRIDES = REAL / "overrides.json"
RESOLVED = REAL / "resolved.jsonl"
TOP_K = 5
FLOOR = 0.60
UNMATCHED_TRACKS = {"Кодинг-секция"}  # algorithms: the bank barely covers them
DUP_THRESHOLD = 0.9
POST_URL = "https://www.threads.com/@mentor_dse/post/{code}"
UNNAMED = "Без названия"

TRACKS = {
    "LLM", "NLP", "Классический ML", "Статистика", "Основы DL", "Computer Vision",
    "MLOps", "Системный дизайн", "HR-скрининг", "Кодинг-секция",
}

# Raw company spelling -> canonical name. Anything not listed is kept as is.
COMPANY_ALIASES = {
    "T‑Bank": "Т-Банк", "T-Bank": "Т-Банк", "Тинькофф": "Т-Банк",
    "Yandex": "Яндекс", "Яндекс Маркет": "Яндекс", "Яндекс Музыка": "Яндекс",
    "Сбер / GigaChat": "Сбер", "Sber": "Сбер",
    "Dodo": "Додо",
    "CIAN": "Циан",
    "Tochka": "Точка",
    "Waymo (Alphabet; бывший проект Google)": "Waymo",
    "Самокат / ecom.tech": "Самокат",
    "Wisebits / xHamster": "Wisebits",
}

# Descriptions instead of a name: they must not count as separate companies.
UNNAMED_COMPANIES = {
    "техническое ML-собеседование", "запись технического собеседования", "HFT role",
    "Финтех-компания", "Speech AI-компания", "Стартап с AI-агентами",
    "Стартап с AI-продуктами", "Промышленный SaaS-проект", "Новая enterprise AI-команда",
    "B2B-маркетплейс закупок", "Соцсеть для геймеров", "Adult-платформа",
    "iGaming-компания",
}


def normalize_company(raw: str | None) -> str:
    name = (raw or "").strip()
    for prefix in ("статья ", "доклад "):
        if name.startswith(prefix):
            name = name[len(prefix):]
    if not name or name in UNNAMED_COMPANIES:
        return UNNAMED
    return COMPANY_ALIASES.get(name, name)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def normalize() -> None:
    source = read_jsonl(REAL / "source.jsonl")
    rows = []
    for i, item in enumerate(read_jsonl(EXTRACTED)):
        if not item["question"]:
            continue
        if item["track"] not in TRACKS:
            sys.exit(f"строка {i}: неизвестный трек {item['track']!r}")
        post = source[item["src"]]
        rows.append({
            "rid": f"r{len(rows):03d}",
            "src": item["src"],
            "kind": item["kind"],
            "company": normalize_company(post["company"]),
            "company_raw": post["company"],
            "stage": item.get("stage", ""),
            "track": item["track"],
            "topic": item.get("topic", ""),
            "question": item["question"],
            "hint": item.get("hint", ""),
            "urls": [POST_URL.format(code=post["code"])],
        })
    total = len(rows)
    rows = merge_retellings(rows)
    for i, r in enumerate(rows):
        r["rid"] = f"r{i:03d}"
    write_jsonl(NORMALIZED, rows)
    print(f"{total} вопросов из {len(source)} постов, после склейки пересказов {len(rows)}"
          f" -> {NORMALIZED.relative_to(ROOT)}")


def merge_retellings(rows: list[dict], threshold: float = DUP_THRESHOLD) -> list[dict]:
    """One interview process is often retold in several posts: merge the repeats.

    Only within one company, so the same question from two companies stays two
    data points for "how many companies ask this".
    """
    E = embed([r["question"] for r in rows])
    kept: list[int] = []
    for i, r in enumerate(rows):
        same = [j for j in kept if rows[j]["company"] == r["company"] and r["company"] != UNNAMED]
        if same:
            sims = E[i] @ E[same].T
            j = same[int(np.argmax(sims))]
            if sims.max() >= threshold:
                rows[j]["urls"] += [u for u in r["urls"] if u not in rows[j]["urls"]]
                continue
        kept.append(i)
    return [rows[i] for i in kept]


def match(floor: float) -> None:
    real = [r for r in read_jsonl(NORMALIZED) if r["track"] not in UNMATCHED_TRACKS]
    bank = load_bank()
    print(f"эмбеддинги: {len(bank)} карточек банка, {len(real)} реальных вопросов...")
    sims = embed([r["question"] for r in real]) @ embed([c["q"] for c in bank]).T

    rows = []
    for r, row in zip(real, sims):
        top = [j for j in np.argsort(-row)[:TOP_K] if row[j] >= floor]
        rows.append({
            "rid": r["rid"], "track": r["track"], "question": r["question"],
            "candidates": [
                {"id": bank[j]["id"], "sim": round(float(row[j]), 4),
                 "q": bank[j]["q"], "points": bank[j]["points"]}
                for j in top
            ],
        })
    write_jsonl(CANDIDATES, rows)
    empty = sum(not r["candidates"] for r in rows)
    print(f"{len(rows)} вопросов, без кандидатов выше {floor}: {empty} -> {CANDIDATES.relative_to(ROOT)}")


def resolve() -> None:
    """Judge verdicts + manual overrides -> one verdict per matched question."""
    judged = {j["rid"]: j for j in read_jsonl(JUDGED)}
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8")) if OVERRIDES.exists() else {}
    known = {c["id"] for c in load_bank()}
    rows, missing = [], []
    for r in read_jsonl(NORMALIZED):
        if r["track"] in UNMATCHED_TRACKS:
            continue
        verdict = judged.get(r["rid"])
        if verdict is None:
            missing.append(r["rid"])
            continue
        card, kind = verdict["card_id"], verdict["match"]
        if r["rid"] in overrides:
            card = overrides[r["rid"]]
            kind = "exact" if card else "none"
        if card and card not in known:
            sys.exit(f"{r['rid']}: карточки {card} нет в банке")
        rows.append({**r, "card_id": card, "match": kind, "why": verdict.get("why", ""),
                     "override": r["rid"] in overrides})
    if missing:
        sys.exit(f"нет вердикта судьи для {len(missing)} вопросов: {', '.join(missing[:10])}...")
    write_jsonl(RESOLVED, rows)

    print(f"{'трек':<18}{'exact':>7}{'partial':>9}{'none':>6}")
    for track in sorted({r["track"] for r in rows}, key=lambda t: -sum(r["track"] == t for r in rows)):
        sub = [r for r in rows if r["track"] == track]
        n = {k: sum(r["match"] == k for r in sub) for k in ("exact", "partial", "none")}
        print(f"{track:<18}{n['exact']:>7}{n['partial']:>9}{n['none']:>6}")
    print(f"overrides применено: {sum(r['override'] for r in rows)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--normalize", action="store_true")
    ap.add_argument("--match", action="store_true")
    ap.add_argument("--floor", type=float, default=FLOOR, help="нижняя отсечка косинуса")
    ap.add_argument("--resolve", action="store_true")
    a = ap.parse_args()
    if not (a.normalize or a.match or a.resolve):
        ap.error("нужен --normalize, --match или --resolve")
    if a.normalize:
        normalize()
    if a.match:
        match(a.floor)
    if a.resolve:
        resolve()


if __name__ == "__main__":
    main()
