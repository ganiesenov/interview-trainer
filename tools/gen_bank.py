#!/usr/bin/env python3
"""
Доращивание банка вопросов локальной моделью + дедупликация по смыслу.

    ollama pull qwen2.5:32b-instruct-q4_K_M
    ollama pull bge-m3
    pip install ollama numpy

    python tools/gen_bank.py --track "Статистика" --topic "A/B-тесты" --n 15
    python tools/gen_bank.py --track "Computer Vision" --auto   # по всем темам направления
    python tools/gen_bank.py --stats                            # покрытие банка
    python tools/gen_bank.py --dedup-only                       # чистка существующего банка
    python tools/gen_bank.py --inject cards/interview_cards.html  # вшить банк в карточки

Банк — banks/bank_full.json, тот же файл читает run.py.

Смысл дедупликации: генератор неизбежно выдаёт "зачем нужен KV-cache" и
"почему decode упирается в память" как два разных вопроса. Порог 0.86 по
косинусу отсекает такие пары. Ожидай, что после чистки останется 30-50%
сгенерированного — это норма, а не поломка.
"""

import argparse, json, re, sys
from pathlib import Path

import numpy as np
import ollama

BANK = Path(__file__).resolve().parents[1] / "banks" / "bank_full.json"
GEN_MODEL = "qwen2.5:32b-instruct-q4_K_M"
EMB_MODEL = "bge-m3"
SIM_THRESHOLD = 0.86

PROMPT = """Ты составляешь банк вопросов для технического собеседования на позицию \
ML / Data Science инженера. Уровень — senior, 5+ лет опыта.

Направление: {track}
Тема: {topic}
Сгенерируй {n} вопросов.

Требования к каждому вопросу:
- Проверяет понимание механики, а не знание термина. Плохо: "что такое LoRA".
  Хорошо: "что именно обучается в LoRA и за что отвечают r и alpha".
- key_points: ровно 5 пунктов, каждый — конкретное утверждение, которое сильный
  кандидат обязан произнести. Не темы для рассуждения, а проверяемые факты.
- Хотя бы один пункт про подвох, компромисс или цену решения.
- ref: связный эталонный ответ на 4-5 предложений, без списков и маркдауна.
- Всё на русском. Английские термины оставляй как есть (attention, KV-cache).

Уже есть такие вопросы по этой теме — НЕ повторяй и не перефразируй их:
{existing}

Верни СТРОГО JSON-массив, без markdown-обёртки и без комментариев:
[{{"id":"короткий_слаг","track":"{track}","topic":"{topic}","q":"...","points":["...","...","...","...","..."],"ref":"..."}}]
"""


def load_bank() -> list[dict]:
    return json.loads(BANK.read_text(encoding="utf-8")) if BANK.exists() else []


def save_bank(cards: list[dict]) -> None:
    BANK.write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")


def embed(texts: list[str]) -> np.ndarray:
    vecs = [ollama.embeddings(model=EMB_MODEL, prompt=t)["embedding"] for t in texts]
    m = np.array(vecs, dtype=np.float32)
    return m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)


def generate(track: str, topic: str, n: int, bank: list[dict]) -> list[dict]:
    existing = "\n".join(f"- {c['q']}" for c in bank if c["topic"] == topic) or "(пока нет)"
    raw = ollama.chat(
        model=GEN_MODEL,
        messages=[{"role": "user", "content": PROMPT.format(track=track, topic=topic, n=n, existing=existing)}],
        format="json",
        options={"temperature": 0.8, "num_ctx": 8192},
    )["message"]["content"]

    try:
        data = json.loads(re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M))
    except json.JSONDecodeError:
        print("модель вернула невалидный JSON — прогони ещё раз", file=sys.stderr)
        return []
    if isinstance(data, dict):                      # иногда заворачивает в {"questions": [...]}
        data = next((v for v in data.values() if isinstance(v, list)), [])

    ok = []
    for c in data:
        if not all(k in c for k in ("id", "q", "points", "ref")):
            continue
        if len(c["points"]) < 4:                    # халтура — выбрасываем
            continue
        c["track"], c["topic"] = track, topic
        ok.append(c)
    print(f"  сгенерировано {len(data)}, прошло формальную проверку {len(ok)}")
    return ok


def dedup(cards: list[dict], threshold: float = SIM_THRESHOLD) -> list[dict]:
    if len(cards) < 2:
        return cards
    print(f"дедупликация {len(cards)} вопросов...")
    E = embed([c["q"] for c in cards])
    keep, dropped = [], []
    kept_idx: list[int] = []
    for i, c in enumerate(cards):
        if kept_idx:
            sims = E[i] @ E[kept_idx].T
            j = int(np.argmax(sims))
            if sims[j] >= threshold:
                dropped.append((c["q"], cards[kept_idx[j]]["q"], float(sims[j])))
                continue
        keep.append(c)
        kept_idx.append(i)

    if dropped:
        print(f"\nвыброшено {len(dropped)} дублей:")
        for new, old, s in dropped[:20]:
            print(f"  {s:.3f}  {new[:60]}\n         ~ {old[:60]}")
    print(f"\nосталось {len(keep)}")
    return keep


def inject(html_path: Path, cards: list[dict]) -> None:
    html = html_path.read_text(encoding="utf-8")
    block = "const CARDS = " + json.dumps(cards, ensure_ascii=False, indent=0) + ";"
    html, n = re.subn(r"const CARDS = \[.*?\];", lambda _: block, html, flags=re.S)
    if not n:
        sys.exit("в HTML не найден блок const CARDS")
    html_path.write_text(html, encoding="utf-8")
    print(f"вшито {len(cards)} вопросов в {html_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track")
    ap.add_argument("--topic")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--auto", action="store_true", help="пройтись по всем темам направления")
    ap.add_argument("--stats", action="store_true", help="показать покрытие банка")
    ap.add_argument("--dedup-only", action="store_true")
    ap.add_argument("--inject", type=Path)
    ap.add_argument("--threshold", type=float, default=SIM_THRESHOLD)
    a = ap.parse_args()

    bank = load_bank()
    print(f"в банке {len(bank)} вопросов")

    if a.inject:
        inject(a.inject, bank)
        return

    if a.stats:
        tracks: dict[str, dict[str, int]] = {}
        for c in bank:
            tracks.setdefault(c["track"], {}).setdefault(c["topic"], 0)
            tracks[c["track"]][c["topic"]] += 1
        for tr in sorted(tracks, key=lambda t: -sum(tracks[t].values())):
            print(f"\n{tr}  ({sum(tracks[tr].values())})")
            for tp, n in sorted(tracks[tr].items(), key=lambda x: -x[1]):
                print(f"   {n:3}  {tp}")
        return

    if a.dedup_only:
        save_bank(dedup(bank, a.threshold))
        return

    if not a.track:
        ap.error("нужен --track либо --dedup-only, --stats, --inject")

    if a.auto:
        topics = sorted({c["topic"] for c in bank if c["track"] == a.track})
        if not topics:
            ap.error(f"в банке нет направления {a.track}")
    else:
        if not a.topic:
            ap.error("нужен --topic либо --auto")
        topics = [a.topic]

    fresh = []
    for tp in topics:
        print(f"\n[{a.track} / {tp}]")
        fresh += generate(a.track, tp, a.n, bank)
    if not fresh:
        return
    merged = dedup(bank + fresh, a.threshold)
    added = len(merged) - len(bank)
    save_bank(merged)
    print(f"\nитого добавлено {added} из {len(fresh)} сгенерированных")
    if added < len(fresh) * 0.4:
        print("больше половины оказалось дублями — тема близка к исчерпанию, бери следующую")


if __name__ == "__main__":
    main()
