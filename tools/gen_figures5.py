"""Пятая партия схем: A/B-практика и отладка обучения."""
import json
import math
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
    return f"<text class='{cls}' x='{x:.1f}' y='{y:.1f}'{a}>{s}</text>"


def path(pts, cls="a", extra=""):
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    return f"<path class='{cls}' d='{d}' {extra}/>"


def rectc(x, y, w, h, color, op=".75", rx=6):
    return (f"<rect x='{x:.1f}' y='{y:.1f}' width='{w:.1f}' height='{h:.1f}' "
            f"rx='{rx}' fill='{color}' opacity='{op}'/>")


# ---------- подглядывание: p-value как случайное блуждание ----------
# детерминированная симуляция без эффекта: z-статистика по нарастающей выборке.
def lcg(seed):
    s = seed
    while True:
        s = (s * 1103515245 + 12345) % (2 ** 31)
        yield s / (2 ** 31)


def normal_pairs(gen):
    while True:
        u1, u2 = next(gen), next(gen)
        r = math.sqrt(-2 * math.log(max(u1, 1e-12)))
        yield r * math.cos(2 * math.pi * u2)
        yield r * math.sin(2 * math.pi * u2)


g = normal_pairs(lcg(20240731))
cum, n, pvals = 0.0, 0, []
for i in range(400):
    cum += next(g)
    n += 1
    z = abs(cum) / math.sqrt(n)
    p = 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))
    if n >= 10:
        pvals.append(p)

W, H, L, R, TOP, BOT = 640, 210, 46, 616, 26, 168
xs = lambda i: L + (R - L) * i / (len(pvals) - 1)
ys = lambda p: BOT - (BOT - TOP) * p
b = txt(8, 16, "A/A-тест (эффекта НЕТ): p-value по мере набора данных — случайное блуждание", "m")
b += f"<line class='ax' x1='{L}' y1='{BOT}' x2='{R}' y2='{BOT}'/>"
b += f"<line class='ax' x1='{L}' y1='{TOP}' x2='{L}' y2='{BOT}'/>"
y05 = ys(0.05)
b += f"<line x1='{L}' y1='{y05:.1f}' x2='{R}' y2='{y05:.1f}' stroke='var(--miss)' stroke-width='1.5' stroke-dasharray='5 4'/>"
b += txt(L + 6, y05 - 6, "p = 0.05", "m")
crossed = [i for i, p in enumerate(pvals) if p < 0.05]
b += path([(xs(i), ys(p)) for i, p in enumerate(pvals)])
for i in crossed[:1]:
    b += f"<circle cx='{xs(i):.1f}' cy='{ys(pvals[i]):.1f}' r='4' fill='var(--miss)'/>"
    b += txt(xs(i) + 8, ys(pvals[i]) - 8, "остановился бы здесь — ложный «эффект»", "m")
b += txt(L, BOT + 16, "объём выборки →", "m")
b += txt(8, H - 6, "Кривая заходит под 0.05 и выходит обратно. Остановка «когда стало значимо» превращает α=5% в 20–30%.")
figs["ab_peeking"] = svg(W, H, "Подглядывание в A/B", b)

# ---------- design effect ----------
W, H, L, R, TOP, BOT = 640, 200, 60, 610, 30, 150
b = txt(8, 16, "кластерная рандомизация: design effect DE = 1 + (m−1)·ICC (m — размер кластера)", "m")
b += f"<line class='ax' x1='{L}' y1='{BOT}' x2='{R}' y2='{BOT}'/>"
b += f"<line class='ax' x1='{L}' y1='{TOP}' x2='{L}' y2='{BOT}'/>"
iccs = [0.01, 0.05, 0.2]
cols = ["var(--ok)", "var(--accent)", "var(--miss)"]
mmax, demax = 200, 1 + (200 - 1) * 0.2
for icc, col in zip(iccs, cols):
    pts = []
    for k in range(0, 101):
        m = 1 + (mmax - 1) * k / 100
        de = 1 + (m - 1) * icc
        x = L + (R - L) * (m - 1) / (mmax - 1)
        y = BOT - (BOT - TOP) * (de - 1) / (demax - 1)
        pts.append((x, y))
    b += path(pts, "a", f"style='stroke:{col}'")
b += f"<rect x='{L+8}' y='{TOP+2}' width='260' height='52' rx='6' fill='var(--bg)' opacity='.75'/>"
b += f"<line x1='{L+16}' y1='{TOP+12}' x2='{L+34}' y2='{TOP+12}' stroke='var(--miss)' stroke-width='2'/>"
b += txt(L + 40, TOP + 16, "ICC=0.2: DE≈41 — выборка ×41", "m")
b += f"<line x1='{L+16}' y1='{TOP+28}' x2='{L+34}' y2='{TOP+28}' stroke='var(--accent)' stroke-width='2'/>"
b += txt(L + 40, TOP + 32, "ICC=0.05: DE≈11", "m")
b += f"<line x1='{L+16}' y1='{TOP+44}' x2='{L+34}' y2='{TOP+44}' stroke='var(--ok)' stroke-width='2'/>"
b += txt(L + 40, TOP + 48, "ICC=0.01: DE≈3", "m")
b += txt((L + R) / 2, BOT + 16, "размер кластера m →", "m", "middle")
b += txt(8, H - 6, "Мощность задаёт ЧИСЛО КЛАСТЕРОВ: город на миллион пользователей — всё равно одно наблюдение.")
figs["design_effect"] = svg(W, H, "Design effect", b)

# ---------- триггерный анализ: разбавление ----------
b = txt(8, 16, "фичу видят 5% пользователей: тот же эффект, разные знаменатели", "m")
eff_t, share = 10.0, 0.05
eff_all = eff_t * share
bx, bw, base_y = 120, 150, 150
b += rectc(bx, base_y - 120, bw, 120, "var(--accent)", ".6")
b += txt(bx + bw / 2, base_y - 126, "+10% на затронутых", "t", "middle")
b += txt(bx + bw / 2, base_y + 16, "триггерный анализ", "m", "middle")
bx2 = 390
b += rectc(bx2, base_y - 6, bw, 6, "var(--miss)", ".7")
b += txt(bx2 + bw / 2, base_y - 14, "+0.5% на всех — тонет в шуме", "t", "middle")
b += txt(bx2 + bw / 2, base_y + 16, "анализ по всем", "m", "middle")
b += txt(8, 190, "Триггерный анализ режет шум 95% незатронутых, но условие попадания обязано быть одинаковым")
b += txt(8, 207, "в обеих группах. Пересчёт на аудиторию: эффект на затронутых × их долю (10% × 0.05 = 0.5%).")
figs["triggered_dilution"] = svg(640, 216, "Разбавление эффекта", b)

# ---------- отладка обучения: дерево диагнозов ----------
def box(x, y, w, h, lines, tcls="t"):
    r = f"<rect class='b' x='{x}' y='{y}' width='{w}' height='{h}' rx='8'/>"
    for j, s in enumerate(lines):
        r += txt(x + 10, y + 18 + j * 15, s, tcls if j == 0 else "m")
    return r


arr = lambda x1, y1, x2, y2: f"<path class='a' d='M{x1} {y1} L{x2} {y2}'/>"
b = box(230, 8, 180, 30, ["кривые train / val"])
b += arr(320, 38, 110, 62) + arr(320, 38, 320, 62) + arr(320, 38, 530, 62)
b += box(20, 62, 185, 62, ["обе высоки, близки", "недообучение: ёмкость,", "длительность, LR"])
b += box(228, 62, 185, 62, ["train ок, val плохо", "переобучение: данные,", "аугментации, регуляризация"])
b += box(436, 62, 185, 62, ["train не падает вовсе", "баг: сначала переобучи", "10 примеров"])
b += txt(8, 150, "Прежде чем крутить архитектуру: санити-чек «переобучи крошечную подвыборку» отделяет")
b += txt(8, 167, "проблемы оптимизации (не может даже запомнить) от проблем обобщения (запоминает, не переносит).")
figs["train_debug"] = svg(640, 176, "Диагностика обучения", b)

# ---------- GPU-голодание ----------
b = txt(8, 16, "шаг обучения на таймлайне: GPU ждёт данные", "m")
y1, y2 = 34, 74
b += txt(8, y1 + 15, "CPU", "t") + txt(8, y2 + 15, "GPU", "t")
seg = [(50, 120, "load+aug"), (172, 120, "load+aug"), (294, 120, "load+aug")]
for x, w, name in seg:
    b += rectc(x, y1, w, 22, "var(--warn)", ".6") + txt(x + 6, y1 + 15, name, "m")
gsegs = [(50, 46), (172, 46), (294, 46)]
for x, w in gsegs:
    b += rectc(x + 74, y2, w, 22, "var(--accent)", ".7") + txt(x + 76, y2 + 15, "шаг", "m")
    b += rectc(x, y2, 72, 22, "var(--line)", ".25") + txt(x + 6, y2 + 15, "idle", "m")
b += txt(8, 122, "Лечение: больше воркеров, предвыборка, pinned memory, упакованный формат вместо тысяч")
b += txt(8, 139, "мелких файлов, препроцессинг заранее. Диагноз за минуту: эпоха на синтетических тензорах.")
figs["gpu_pipeline"] = svg(640, 148, "GPU-голодание", b)

FP.write_text(json.dumps(figs, ensure_ascii=False, indent=1), encoding="utf-8")
print("figures total:", len(figs))
