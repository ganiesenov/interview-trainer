"""Четвёртая партия схем: кодинг-секции и ML system design."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FP = ROOT / "banks" / "figures.json"
figs = json.loads(FP.read_text(encoding="utf-8"))

T = "fill:var(--ink);font-size:13px;font-family:inherit"
M = "fill:var(--muted);font-size:11px;font-family:inherit"
STYLE = ("<style>.t{" + T + "}.m{" + M + "}.b{fill:var(--bg);stroke:var(--line)}"
         ".a{stroke:var(--accent);fill:none;stroke-width:2}"
         ".ax{stroke:var(--line);stroke-width:1}</style>")


def svg(w, h, label, body):
    return (f"<svg viewBox='0 0 {w} {h}' xmlns='http://www.w3.org/2000/svg' role='img' "
            f"aria-label='{label}'>{STYLE}{body}</svg>")


def txt(x, y, s, cls="m", anchor=""):
    a = f" text-anchor='{anchor}'" if anchor else ""
    return f"<text class='{cls}' x='{x}' y='{y}'{a}>{s}</text>"


def box(x, y, w, h, label, tcls="t"):
    return (f"<rect class='b' x='{x}' y='{y}' width='{w}' height='{h}' rx='8'/>"
            + txt(x + 10, y + h / 2 + 4, label, tcls))


def rectc(x, y, w, h, color, op=".75", rx=6):
    return f"<rect x='{x:.1f}' y='{y:.1f}' width='{w:.1f}' height='{h:.1f}' rx='{rx}' fill='{color}' opacity='{op}'/>"


arr = lambda x1, y1, x2, y2: f"<path class='a' d='M{x1} {y1} L{x2} {y2}'/>"

# ---------- скользящее окно ----------
vals = [2, 5, 1, 8, 3, 7, 4, 6, 2, 9]
b = txt(8, 18, "максимальная сумма окна k=4: окно ДВИГАЕТСЯ, а не пересчитывается", "m")
for i, v in enumerate(vals):
    x = 30 + i * 56
    inside = 2 <= i <= 5
    b += rectc(x, 28, 48, 34, "var(--accent)" if inside else "var(--line)", ".55" if inside else ".3")
    b += txt(x + 18, 50, str(v), "t")
b += f"<path class='a' d='M{30+2*56} 74 h{4*56-8}' />"
b += txt(30 + 2 * 56, 92, "sum += a[j] − a[i]: O(1) на сдвиг вместо O(k) пересчёта")
b += txt(8, 122, "Тот же приём: «самая длинная подстрока без повторов», «минимальное окно с суммой ≥ S».")
b += txt(8, 139, "Родственник — два указателя на отсортированном массиве (пара с заданной суммой за O(n)).")
figs["sliding_window"] = svg(640, 150, "Скользящее окно", b)

# ---------- скрин по уровням ----------
levels = [("Уровень 1", "базовые операции", "~15 мин"),
          ("Уровень 2", "новые требования", "~20 мин"),
          ("Уровень 3", "рефакторинг под усложнение", "~25 мин"),
          ("Уровень 4", "хвост: успевают не все", "остаток")]
b = ""
for i, (name, sub, tm) in enumerate(levels):
    x = 8 + i * 158
    y = 96 - i * 26
    b += box(x, y, 148, 34, name) + txt(x + 2, y + 52, sub) + txt(x + 2, y + 68, tm)
    if i:
        b += arr(x - 10, y + 44, x + 2, y + 20)
b += txt(8, 178, "Оценка идёт по числу закрытых уровней и чистоте кода. Захардкоженное решение уровня 1")
b += txt(8, 195, "умирает на уровне 3: структура (словари, маленькие функции) важнее скорости печати.")
figs["spec_levels"] = svg(640, 205, "Скрин по уровням", b)

# ---------- воронка рекомендаций ----------
b = txt(8, 16, "двухэтапная воронка — каркас ответа на любой «спроектируй рекомендации/ленту/поиск»:", "m")
stages = [("каталог: 10⁷ айтемов", 560, "var(--line)", ".35"),
          ("кандидаты: ~500 (ANN, эвристики, подписки)", 470, "var(--accent)", ".35"),
          ("ranking: полная модель на богатых фичах", 390, "var(--accent)", ".55"),
          ("re-rank: разнообразие, правила, свежесть", 320, "var(--ok)", ".45")]
y = 28
for name, w, color, op in stages:
    b += rectc(320 - w / 2, y, w, 30, color, op)
    b += txt(330 - w / 2, y + 20, name, "t")
    y += 38
b += txt(8, y + 12, "Отбор дёшев и полнотой (recall), ранжирование дорого и точностью (precision) — как retrieval+rerank в RAG.")
b += txt(8, y + 29, "Петля обратной связи: логи кликов → обучение → показы влияют на будущие клики (position bias,")
b += txt(8, y + 46, "feedback loop) — поэтому офлайн-метрики рекомендаций плохо предсказывают онлайн.")
figs["recsys_funnel"] = svg(640, y + 56, "Воронка рекомендаций", b)

FP.write_text(json.dumps(figs, ensure_ascii=False, indent=1), encoding="utf-8")
print("figures total:", len(figs))
