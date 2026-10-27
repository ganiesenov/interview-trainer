#!/usr/bin/env python3
"""Импорт реальных вопросов с собеседований и сопоставление с банком.

    python tools/import_real.py --normalize          # data/real/extracted.jsonl -> normalized.jsonl
    python tools/import_real.py --match              # топ-5 кандидатов из банка (bge-m3)
    python tools/import_real.py --resolve            # вердикты судьи + overrides -> resolved.jsonl
    python tools/import_real.py --apply              # поле asked на exact-карточках банка
    python tools/import_real.py --build-real         # deck/verified/asked в banks/real.json

Двухэтапный матчинг: эмбеддинги дают кандидатов, решает судья (субагенты
по tools/judge_prompt.md, вердикты в data/real/judged.jsonl). Ручные правки —
data/real/overrides.json применяются поверх судьи: {"rid": "card_id"} — exact,
{"rid": null} — none, {"rid": {"match": "partial"}} — partial (карточка судьи).

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
from gen_bank import embed, load_bank, save_bank  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / "data" / "real"
EXTRACTED = REAL / "extracted.jsonl"
NORMALIZED = REAL / "normalized.jsonl"
CANDIDATES = REAL / "candidates.jsonl"
JUDGED = REAL / "judged.jsonl"
OVERRIDES = REAL / "overrides.json"
RESOLVED = REAL / "resolved.jsonl"
REAL_MAP = REAL / "real_map.json"
REAL_DECK = ROOT / "banks" / "real.json"
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
            card, kind = parse_override(overrides[r["rid"]], card)
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


def parse_override(value, judge_card: str | None) -> tuple[str | None, str]:
    """null -> none; "card_id" -> exact; {"match": ..., "card_id"?: ...} -> as given."""
    if value is None:
        return None, "none"
    if isinstance(value, str):
        return value, "exact"
    kind = value["match"]
    card = value.get("card_id", judge_card) if kind != "none" else None
    return card, kind


def apply_asked() -> None:
    """Put "asked": [{"company", "url"}] on bank cards that a real question matched exactly.

    Case write-ups are articles, not interviews, so they never count as "asked".
    Rerunnable: stale "asked" fields are dropped first.
    """
    asked: dict[str, dict[str, str]] = {}
    for r in read_jsonl(RESOLVED):
        if r["match"] == "exact" and r["kind"] != "case":
            asked.setdefault(r["card_id"], {}).setdefault(r["company"], r["urls"][0])
    bank = load_bank()
    for card in bank:
        card.pop("asked", None)
        if card["id"] in asked:
            card["asked"] = [{"company": c, "url": u} for c, u in sorted(asked[card["id"]].items())]
    save_bank(bank)
    named = sum(any(a["company"] != UNNAMED for a in c.get("asked", [])) for c in bank)
    print(f"asked проставлен на {len(asked)} карточек, из них с названной компанией {named}")


def build_real() -> None:
    """Fill deck/verified/asked on banks/real.json from data/real/real_map.json.

    Card text is hand-written in banks/real.json; which real questions a card
    answers lives in the git-ignored map, so only company and post link reach the repo.
    """
    cards = json.loads(REAL_DECK.read_text(encoding="utf-8"))
    mapping = json.loads(REAL_MAP.read_text(encoding="utf-8"))
    by_rid = {r["rid"]: r for r in read_jsonl(RESOLVED)}
    bank_ids = {c["id"] for c in load_bank()}

    errors = []
    for card in cards:
        cid = card["id"]
        if cid in bank_ids:
            errors.append(f"{cid}: id занят в банке")
        if card.get("see") and card["see"] not in bank_ids:
            errors.append(f"{cid}: see -> {card['see']} нет в банке")
        rids = mapping.get(cid)
        if not rids:
            errors.append(f"{cid}: нет в {REAL_MAP.name}")
            continue
        asked: dict[str, str] = {}
        for rid in rids:
            r = by_rid[rid]
            if r["match"] == "exact":
                errors.append(f"{cid}: {rid} уже закрыт карточкой {r['card_id']}")
            asked.setdefault(r["company"], r["urls"][0])
        card["deck"] = "real"
        card["verified"] = card.get("verified", False)
        card["asked"] = [{"company": c, "url": u} for c, u in sorted(asked.items())]
    if errors:
        sys.exit("\n".join(errors))
    REAL_DECK.write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(cards)} карточек в {REAL_DECK.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--normalize", action="store_true")
    ap.add_argument("--match", action="store_true")
    ap.add_argument("--floor", type=float, default=FLOOR, help="нижняя отсечка косинуса")
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--build-real", action="store_true")
    a = ap.parse_args()
    if not (a.normalize or a.match or a.resolve or a.apply or a.build_real):
        ap.error("нужен --normalize, --match, --resolve, --apply или --build-real")
    if a.normalize:
        normalize()
    if a.match:
        match(a.floor)
    if a.resolve:
        resolve()
    if a.apply:
        apply_asked()
    if a.build_real:
        build_real()


if __name__ == "__main__":
    main()
