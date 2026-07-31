"""Вторая партия схем: по разделам внутри уроков (учебник, а не обложка)."""
import json
import math
from pathlib import Path

ROOT = Path("/home/user/interview-trainer")
FP = ROOT / "banks" / "figures.json"
figs = json.loads(FP.read_text(encoding="utf-8"))

T = "fill:var(--ink);font-size:13px;font-family:inherit"
M = "fill:var(--muted);font-size:11px;font-family:inherit"
STYLE = ("<style>.t{" + T + "}.m{" + M + "}.b{fill:var(--bg);stroke:var(--line)}"
         ".a{stroke:var(--accent);fill:none;stroke-width:2}.w{stroke:var(--warn);fill:none;stroke-width:2}"
         ".r{stroke:var(--miss);fill:none;stroke-width:2}.g{stroke:var(--ok);fill:none;stroke-width:2}"
         ".ax{stroke:var(--line);stroke-width:1}</style>")

def svg(w, h, label, body):
    return (f"<svg viewBox='0 0 {w} {h}' xmlns='http://www.w3.org/2000/svg' role='img' "
            f"aria-label='{label}'>{STYLE}{body}</svg>")

def path(pts, cls="a", dash=None):
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    dd = f" stroke-dasharray='{dash}'" if dash else ""
    return f"<path class='{cls}' d='{d}'{dd}/>"

def area(pts, y_base, fill):
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + f" L{pts[-1][0]:.1f} {y_base} L{pts[0][0]:.1f} {y_base} Z"
    return f"<path d='{d}' fill='{fill}' stroke='none' opacity='.22'/>"

def txt(x, y, s, cls="m", anchor=""):
    a = f" text-anchor='{anchor}'" if anchor else ""
    return f"<text class='{cls}' x='{x}' y='{y}'{a}>{s}</text>"

def axes(x0, y0, x1, y1):
    return f"<path class='ax' d='M{x0} {y1} L{x0} {y0} M{x0} {y1} L{x1} {y1}'/>"

def scale(pts, x0, x1, y0, y1, ymin=None, ymax=None):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    ymin = min(ys) if ymin is None else ymin
    ymax = max(ys) if ymax is None else ymax
    sx = lambda x: x0 + (x - xs[0]) / (xs[-1] - xs[0] + 1e-12) * (x1 - x0)
    sy = lambda y: y1 - (y - ymin) / (ymax - ymin + 1e-12) * (y1 - y0)
    return [(sx(x), sy(y)) for x, y in pts]

def box(x, y, w, h, label, cls="b", tcls="t"):
    return (f"<rect class='{cls}' x='{x}' y='{y}' width='{w}' height='{h}' rx='8'/>"
            + txt(x + 10, y + h / 2 + 4, label, tcls))

def rectc(x, y, w, h, color, op=".75", rx=6):
    return f"<rect x='{x:.1f}' y='{y:.1f}' width='{w:.1f}' height='{h:.1f}' rx='{rx}' fill='{color}' opacity='{op}'/>"

arr = lambda x1, y1, x2, y2: f"<path class='a' d='M{x1} {y1} L{x2} {y2}'/>"

# ---------- 1. multi-head: d_model -> h голов -> concat ----------
b = txt(8, 20, "d_model = 768", "t") + box(8, 28, 90, 120, "")
for i in range(4):
    y = 34 + i * 29
    b += rectc(110, y, 60, 22, "var(--accent)", op=str(0.35 + 0.15 * i))
    b += box(186, y - 2, 168, 26, f"голова {i+1}: своё внимание")
    b += arr(98, 88, 110, y + 11) + arr(170, y + 11, 186, y + 11) + arr(354, y + 11, 372, 88)
b += box(372, 74, 96, 28, "concat") + arr(468, 88, 486, 88) + box(486, 74, 120, 28, "W_o проекция")
b += txt(110, 172, "d_head = d_model / h = 96 — суммарная стоимость ТА ЖЕ, что у одной большой головы;")
b += txt(110, 189, "но каждая голова смотрит в своё подпространство: синтаксис, кореференция, позиции.")
figs["mha_heads"] = svg(640, 200, "Многоголовое внимание", b)

# ---------- 2. GQA: сколько KV-голов ----------
def heads_row(y, title, q, kv, note):
    s = txt(8, y + 16, title, "t")
    for i in range(q):
        s += rectc(150 + i * 30, y, 24, 22, "var(--accent)", ".8")
    for i in range(kv):
        w = (q * 30 - 6) / kv
        s += rectc(150 + i * (w + 6 * 0 + (q * 30) / kv * 0) + i * 0, y + 28, 24 if kv == q else (q * 30 - 6) / kv, 14, "var(--warn)", ".8") if False else s
    # проще: рисуем kv прямоугольников равной ширины под строкой Q
    total = q * 30 - 6
    for i in range(kv):
        w = total / kv - (4 if kv > 1 else 0)
        s += rectc(150 + i * (total / kv), y + 28, w, 14, "var(--warn)", ".85", rx=4)
    s += txt(150 + q * 30 + 10, y + 16, note)
    return s
b = txt(150, 14, "синее — Q-головы, оранжевое — их K/V", "m")
b += heads_row(24, "MHA: 8 KV", 8, 8, "кэш ×8")
b += heads_row(84, "GQA: 2 группы", 8, 2, "кэш ×2 — качество почти MHA")
b += heads_row(144, "MQA: 1 KV", 8, 1, "кэш ×1 — иногда теряет")
b += txt(8, 208, "KV-кэш пропорционален числу KV-голов: GQA режет память кэша в разы, не трогая число Q-голов.")
figs["gqa_kv"] = svg(640, 218, "MHA, GQA, MQA", b)

# ---------- 3. continuous batching: динамический батч ----------
rows = [(0, 7, "запрос A"), (1.5, 5, "запрос B"), (3, 9, "запрос C"), (5.5, 4, "запрос D")]
b = txt(8, 18, "статический батч: все ждут самого длинного; continuous: место освобождается сразу", "m")
for i, (start, ln, name) in enumerate(rows):
    y = 30 + i * 32
    b += txt(8, y + 16, name)
    b += rectc(90 + start * 52, y, ln * 52, 24, "var(--accent)", str(0.4 + 0.12 * i))
    b += txt(90 + (start + ln) * 52 + 6, y + 16, "✓")
b += f"<line x1='90' y1='28' x2='90' y2='158' stroke='var(--line)'/>"
b += txt(8, 178, "Новый запрос подсаживается в батч на первом же шаге decode, законченный — освобождает слот.")
b += txt(8, 195, "Утилизация GPU растёт в разы; это и есть continuous batching (Orca, vLLM).")
figs["continuous_batching"] = svg(640, 205, "Continuous batching", b)

# ---------- 4. speculative decoding ----------
b = txt(8, 20, "черновик (маленькая модель), k=5 токенов вперёд:", "t")
draft = ["Пар", "иж", " -", " стол", "ица"]
ok = [True, True, True, False, False]
for i, (tk, good) in enumerate(zip(draft, ok)):
    color = "var(--ok)" if good else "var(--miss)"
    b += rectc(8 + i * 76, 30, 70, 26, color, ".35")
    b += txt(16 + i * 76, 47, tk, "t")
b += txt(8, 84, "проверка (большая модель, ОДИН прямой проход по всем пяти):", "t")
b += txt(8, 104, "первые 3 совпали → приняты; 4-й разошёлся → отброшен вместе с хвостом,")
b += txt(8, 121, "большая модель ставит свой токен. Схема принятия сохраняет распределение большой модели.")
b += txt(8, 150, "Выигрыш ×1.5–3: decode упирается в чтение весов, а проверка k токенов стоит как один шаг.")
b += txt(8, 167, "Ускорение тем больше, чем чаще черновик угадывает — модели должны быть согласованы.")
figs["speculative"] = svg(640, 178, "Speculative decoding", b)

# ---------- 5. кванты: память 7B ----------
b = txt(8, 20, "7B параметров — память под веса:", "t")
for i, (name, gb, color) in enumerate([("fp16", 14, "var(--accent)"), ("int8", 7, "var(--warn)"), ("int4", 3.5, "var(--ok)")]):
    y = 34 + i * 40
    b += txt(8, y + 17, name, "t")
    b += rectc(70, y, gb * 36, 26, color, ".8")
    b += txt(80 + gb * 36, y + 17, f"{gb} ГБ")
b += txt(8, 172, "Каждый шаг вдвое дешевле по памяти И быстрее по decode (меньше байт читать),")
b += txt(8, 189, "но качество проверяется на СВОЁМ наборе: деградация неравномерна по задачам.")
figs["quant_bits"] = svg(640, 200, "Квантизация весов", b)

# ---------- 6. attention sink ----------
b = txt(8, 18, "куда смотрит внимание при длинной генерации (строка = текущий шаг):", "m")
import random
for row in range(5):
    y = 28 + row * 24
    n = 16
    for c in range(n):
        first = c < 2
        recent = c > n - 4 - row % 2
        v = 0.85 if first else (0.55 if recent else 0.10 + 0.02 * ((c * 7 + row * 3) % 5))
        b += rectc(30 + c * 36, y, 32, 20, "var(--accent)", f"{v:.2f}", rx=4)
b += txt(30, 158, "первые 1–4 токена стабильно собирают большую долю внимания — softmax обязан деть единицу веса.")
b += txt(30, 175, "Выбросишь их из окна — перплексия взрывается. StreamingLLM: первые токены держим навсегда,")
b += txt(30, 192, "остальное — скользящее окно. Это устойчивость генерации, а не память о середине.")
figs["attention_sink"] = svg(640, 202, "Attention sink", b)

# ---------- 7. чанкинг ----------
b = txt(8, 18, "по N символов:", "t")
b += rectc(130, 6, 190, 22, "var(--miss)", ".3") + rectc(324, 6, 190, 22, "var(--miss)", ".3")
b += txt(136, 21, "…давление должно быть не ме", "m") + txt(330, 21, "нее 10 мм. Клапан типа Б…", "m")
b += txt(8, 52, "разрез посреди мысли: эмбеддинг размыт, антецедент потерян")
b += txt(8, 84, "по структуре:", "t")
b += rectc(130, 72, 240, 22, "var(--ok)", ".3") + rectc(378, 72, 200, 22, "var(--ok)", ".3")
b += txt(136, 87, "§2.1 Требования к давлению (целиком)", "m") + txt(384, 87, "§2.2 Клапаны (целиком)", "m")
b += txt(8, 118, "заголовки/абзацы + оверлап 10–20% + префикс с контекстом документа.")
b += txt(8, 143, "Отдельный приём: искать по мелким кускам, в модель подавать родительский чанк целиком.")
figs["chunking"] = svg(640, 155, "Чанкинг", b)

# ---------- 8. multihop ----------
b = box(8, 24, 190, 34, "«Где родился автор X?»")
b += arr(198, 41, 220, 41) + box(220, 24, 130, 34, "поиск №1") + arr(350, 41, 372, 41)
b += box(372, 24, 130, 34, "«автор — Y»", "b")
b += f"<path class='a' d='M437 58 v20 h-217 v14'/>"
b += box(220, 92, 160, 34, "поиск №2: «Y родился»") + arr(380, 109, 402, 109) + box(402, 92, 110, 34, "ответ")
b += txt(8, 152, "Документ про город рождения Y не похож на исходный вопрос — один поиск его не найдёт")
b += txt(8, 169, "принципиально: для второго прыжка нужен результат первого. Отсюда итеративный поиск (IRCoT),")
b += txt(8, 186, "декомпозиция вопроса или граф сущностей; плата — задержка и стоимость в разы.")
figs["multihop"] = svg(640, 196, "Multi-hop вопросы", b)

# ---------- 9. matryoshka ----------
b = txt(8, 20, "один вектор d=1024, информация упакована по убыванию важности:", "t")
for i, (d, color) in enumerate([(1024, "var(--line)"), (512, "var(--muted)"), (256, "var(--warn)"), (64, "var(--accent)")]):
    w = 24 + d * 0.56
    b += f"<rect x='8' y='34' width='{w:.0f}' height='30' rx='8' fill='none' stroke='{color}' stroke-width='2'/>"
    b += txt(12 + w - 40, 90 + i * 0, "", "m")
b += txt(20, 54, "64", "t") + txt(120, 54, "256", "m") + txt(340, 54, "512", "m") + txt(560, 54, "1024", "m")
b += txt(8, 92, "Каждый префикс — сам по себе рабочий эмбеддинг: лосс на обучении считается по всем усечениям.")
b += txt(8, 112, "Прод: грубый отбор по первым 256 координатам (индекс в 4 раза меньше и быстрее),")
b += txt(8, 129, "переранжирование кандидатов полным вектором. PCA поверх обычной модели теряет больше.")
figs["matryoshka"] = svg(640, 140, "Matryoshka-эмбеддинги", b)

# ---------- 10. маска лосса ----------
tokens = [("[сист.]", 0), ("Ты", 0), ("юрист", 0), ("<user>", 0), ("Что", 0), ("такое", 0), ("оферта?", 0), ("<bot>", 0), ("Оферта", 1), ("—", 1), ("это", 1), ("предложение…", 1)]
b = txt(8, 18, "labels для SFT: серое = −100 (лосс не считается), синее = учимся", "m")
x = 8
for tk, on in tokens:
    w = 14 + len(tk) * 8.2
    color = "var(--accent)" if on else "var(--muted)"
    b += rectc(x, 28, w, 26, color, ".8" if on else ".25")
    b += txt(x + 7, 45, tk, "t" if on else "m")
    x += w + 6
b += txt(8, 84, "Без маски градиент течёт и по промпту: модель учится генерировать вопросы и служебные теги,")
b += txt(8, 101, "а сигнал по ответу разбавлен. Ошибка тихая — лосс падает, качество хуже ожидаемого.")
b += txt(8, 118, "В диалогах маскируются ВСЕ реплики пользователя; нормировка — на число немаскированных токенов.")
figs["loss_mask"] = svg(640, 130, "Маска лосса", b)

# ---------- 11. packing: блочно-диагональная маска ----------
b = txt(8, 18, "attention-маска при packing трёх примеров в одну последовательность:", "m")
sizes = [5, 4, 6]
off = 0
cell = 13
for si, s in enumerate(sizes):
    for i in range(s):
        for j in range(s):
            if j <= i:
                b += rectc(40 + (off + j) * cell, 30 + (off + i) * cell, cell - 2, cell - 2, "var(--accent)", ".6", rx=2)
    off += s
n = sum(sizes)
b += f"<rect x='40' y='30' width='{n*cell}' height='{n*cell}' fill='none' stroke='var(--line)'/>"
b += txt(260, 60, "каждый пример видит только себя", "t")
b += txt(260, 80, "(каузально внутри своего блока)")
b += txt(260, 108, "наивная каузальная маска дала бы")
b += txt(260, 125, "весь нижний треугольник — пример 3")
b += txt(260, 142, "читал бы примеры 1 и 2: протечка")
b += txt(260, 170, "+ position_ids сбрасываются в 0")
b += txt(260, 187, "на каждой границе (иначе RoPE врёт)")
b += txt(40, 30 + n * cell + 16, "packing убирает паддинг (GPU не считает пустоту), но требует ровно этой маски.")
figs["packing_mask"] = svg(640, 30 + 15 * 13 + 30, "Packing", b)

# ---------- 12. забывание и реплей ----------
xs = [i / 50 for i in range(0, 101)]
dom_nr = [(x, 0.35 + 0.6 * (1 - math.exp(-2.2 * x))) for x in xs]
gen_nr = [(x, 0.9 - 0.45 * (1 - math.exp(-1.8 * x))) for x in xs]
gen_re = [(x, 0.9 - 0.08 * (1 - math.exp(-1.8 * x))) for x in xs]
P = lambda pts: scale(pts, 60, 610, 26, 150, 0.3, 1.0)
figs["replay_curve"] = svg(640, 210, "Забывание и реплей",
    axes(60, 26, 610, 150)
    + path(P(dom_nr), "a") + path(P(gen_nr), "r") + path(P(gen_re), "g")
    + txt(560, P(dom_nr)[-1][1] - 8, "домен", "t", "end")
    + txt(560, P(gen_re)[-1][1] - 8, "общие навыки, смесь 1:3–5", "t", "end")
    + txt(560, P(gen_nr)[-1][1] + 16, "общие навыки, без реплея", "t", "end")
    + txt(60, 18, "качество") + txt(560, 166, "шаги дообучения →", "m", "end")
    + txt(60, 186, "Градиенты домена сдвигают веса, отвечавшие за общие способности. Подмешивание общих данных")
    + txt(60, 203, "(реплей) почти убирает падение. Меряется регресс-набором на каждом чекпоинте, не на глаз."))

# ---------- 13. GRPO ----------
b = box(8, 30, 120, 34, "промпт-задача")
for i in range(4):
    y = 8 + i * 42
    b += arr(128, 47, 168, y + 15)
    r = ["0", "1", "1", "0"][i]
    color = "var(--ok)" if r == "1" else "var(--miss)"
    b += box(168, y, 176, 30, f"ответ {i+1} → чекер: {r}")
    b += f"<circle cx='356' cy='{y+15}' r='5' fill='{color}'/>"
b += box(400, 64, 224, 34, "baseline = среднее группы = 0.5")
b += txt(400, 120, "advantage = награда − 0.5,")
b += txt(400, 137, "нормированная на разброс")
b += txt(8, 186, "PPO требовал value-модель размером с политику. GRPO берёт группу ответов на ОДИН промпт")
b += txt(8, 203, "и использует её среднее как baseline — вторая сеть не нужна. Так обучали DeepSeekMath и R1.")
figs["grpo_group"] = svg(640, 212, "GRPO", b)

# ---------- 14. оси нормализации ----------
def grid(x0, hl_rows, hl_cols, title, sub):
    s = txt(x0, 20, title, "t") + txt(x0, 36, sub)
    for i in range(4):
        for j in range(6):
            hl = (i in hl_rows) or (j in hl_cols)
            s += rectc(x0 + j * 26, 46 + i * 26, 22, 22, "var(--accent)" if hl else "var(--line)", ".7" if hl else ".35", rx=4)
    s += txt(x0, 168, "строки = примеры батча") + txt(x0, 184, "столбцы = признаки/каналы")
    return s
figs["norm_axes"] = svg(640, 216, "Оси нормализации",
    grid(20, [], [2], "BatchNorm", "статистика по батчу (столбец)")
    + grid(240, [1], [], "LayerNorm", "по признакам примера (строка)")
    + grid(460, [], [], "", "")
    + txt(460, 20, "GroupNorm", "t") + txt(460, 36, "по группе каналов строки")
    + "".join(rectc(460 + j * 26, 46 + 1 * 26, 22, 22, "var(--accent)", ".7", rx=4) for j in range(3))
    + txt(20, 208, "Правило: нормируй по той оси, где статистика надёжна. Маленький батч → BN шумит (бери LN/GN)."))

# ---------- 15. checkpointing: память O(L) vs O(√L) ----------
xs = list(range(4, 101, 4))
lin = [(x, x) for x in xs]
sq = [(x, 2 * math.sqrt(x)) for x in xs]
P = lambda pts: scale(pts, 60, 610, 26, 140, 0, 100)
figs["ckpt_sqrt"] = svg(640, 205, "Gradient checkpointing",
    axes(60, 26, 610, 140)
    + path(P(lin), "r") + path(P(sq), "g")
    + txt(560, P(lin)[-1][1] - 8, "все активации: O(L)", "t", "end")
    + txt(560, P(sq)[-1][1] - 10, "чекпоинты: O(√L)", "t", "end")
    + txt(60, 18, "память под активации") + txt(560, 156, "глубина L →", "m", "end")
    + txt(60, 180, "Храним только опорные точки, сегменты пересчитываем на обратном проходе:")
    + txt(60, 197, "память ~√L при k=√L точек, цена ≈ +30% времени (ещё один прямой проход)."))

# ---------- 16. PSI: сдвиг распределения по бинам ----------
def npdf(mu, s, x):
    return math.exp(-((x - mu) ** 2) / (2 * s * s)) / (s * math.sqrt(2 * math.pi))
bins = [(-3 + i * 0.6, -3 + (i + 1) * 0.6) for i in range(10)]
h_old = [npdf(-0.3, 1, (a + b_) / 2) for a, b_ in bins]
h_new = [npdf(0.55, 1.15, (a + b_) / 2) for a, b_ in bins]
mx = max(h_old + h_new)
b = txt(8, 18, "распределение признака по бинам: контур — трейн, заливка — прод", "m")
for i, ((a, e), ho, hn) in enumerate(zip(bins, h_old, h_new)):
    x = 40 + i * 56
    hh_o = ho / mx * 100
    hh_n = hn / mx * 100
    b += rectc(x, 140 - hh_n, 40, hh_n, "var(--warn)", ".5", rx=3)
    b += f"<rect x='{x}' y='{140-hh_o:.1f}' width='40' height='{hh_o:.1f}' rx='3' fill='none' stroke='var(--accent)' stroke-width='2'/>"
b += f"<line x1='36' y1='140' x2='604' y2='140' stroke='var(--line)'/>"
b += txt(8, 168, "PSI = Σ (pᵢ−qᵢ)·ln(pᵢ/qᵢ): ~0.1 — следить, ~0.25 — тревога. Считается по важным признакам")
b += txt(8, 185, "и по скору модели; на больших n алертить по величине сдвига, а не по p-value.")
figs["psi_bins"] = svg(640, 195, "PSI", b)

# ---------- 17. MDE: n ~ 1/Δ² ----------
xs = [i / 100 for i in range(8, 101)]
n_curve = [(x, 1 / (x * x)) for x in xs]
P = lambda pts: scale(pts, 60, 610, 26, 140, 0, 160)
figs["mde_curve"] = svg(640, 205, "Цена маленького эффекта",
    axes(60, 26, 610, 140) + path(P(n_curve), "a")
    + txt(60, 18, "нужный размер выборки") + txt(560, 156, "MDE (искомый эффект) →", "m", "end")
    + txt(150, 60, "MDE вдвое меньше → выборка", "t") + txt(150, 78, "вчетверо больше: n ∝ 1/Δ²", "t")
    + txt(60, 180, "Прикидка: n ≈ 16σ²/Δ² на группу (α=0.05, мощность 0.8). Если нужный n недостижим —")
    + txt(60, 197, "тест бессмыслен, и признать это надо ДО запуска: CUPED, прокси-метрика или больший MDE."))

# ---------- 18. CUPED ----------
pts_pre = [(-2.2 + 0.23 * i, 0) for i in range(20)]
raw = [(x, 0.75 * x + ((i * 37) % 11 - 5) * 0.14) for i, (x, _) in enumerate(pts_pre)]
P = lambda pts: scale(pts, 60, 420, 26, 168, -2.4, 2.4)
sp = P(raw)
line = P([(-2.2, 0.75 * -2.2), (2.2, 0.75 * 2.2)])
dots = "".join(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4' fill='var(--accent)'/>" for x, y in sp)
figs["cuped_var"] = svg(640, 215, "CUPED",
    axes(60, 26, 420, 168) + dots + path(line, "g")
    + txt(60, 18, "метрика в тесте") + txt(400, 186, "та же метрика ДО теста →", "m", "end")
    + txt(440, 50, "поведение до теста", "t") + txt(440, 66, "предсказывает метрику (ρ)")
    + txt(440, 94, "вычтем предсказуемую часть:", "t") + txt(440, 110, "Y′ = Y − θ(X − X̄)")
    + txt(440, 138, "var(Y′) = var(Y)·(1−ρ²):") + txt(440, 154, "ρ=0.7 → −49% дисперсии")
    + txt(60, 200, "Остатки (расстояния до линии) — новая метрика: тот же несмещённый эффект, меньше шума, меньше n."))

# ---------- 19. ROC vs PR ----------
def roc_pr_points():
    import math as m
    xs = [i / 200 for i in range(1, 200)]
    roc = []
    pr = []
    pos_rate = 0.02
    for thr_q in xs:
        # скоры: позитивы N(1.2,1), негативы N(-0.6,1); порог по квантилю
        thr = -3 + 6 * (1 - thr_q)
        def cdf(mu, x):
            return 0.5 * (1 + m.erf((x - mu) / m.sqrt(2)))
        tpr = 1 - cdf(1.2, thr)
        fpr = 1 - cdf(-0.6, thr)
        roc.append((fpr, tpr))
        prec = (tpr * pos_rate) / (tpr * pos_rate + fpr * (1 - pos_rate) + 1e-9)
        pr.append((tpr, prec))
    return roc, pr
roc, pr = roc_pr_points()
Pr = lambda pts, x0, x1: scale(sorted(pts), x0, x1, 30, 150, 0, 1)
figs["roc_pr"] = svg(640, 215, "ROC против PR при дисбалансе",
    txt(40, 20, "ROC: почти идеал", "t") + axes(40, 30, 300, 150)
    + path(Pr(roc, 40, 300), "a") + path([(40, 150), (300, 30)], "ax", dash="4 3")
    + txt(40, 168, "FPR делится на океан негативов —") + txt(40, 184, "AUC 0.95 при позитиве 2%")
    + txt(360, 20, "PR: правда глаза колет", "t") + axes(360, 30, 620, 150)
    + path(Pr(pr, 360, 620), "w")
    + txt(360, 168, "точность в топе — десятки процентов:") + txt(360, 184, "тысячи ложных на каждую находку")
    + txt(40, 205, "Один и тот же классификатор, одни скоры. При редком позитиве смотри PR и precision@k."))

# ---------- 20. калибровка ----------
xs = [i / 20 for i in range(21)]
ideal = [(x, x) for x in xs]
over = [(x, x ** 1.9) for x in xs]
P = lambda pts: scale(pts, 60, 320, 26, 168, 0, 1)
figs["calibration"] = svg(640, 215, "Диаграмма надёжности",
    axes(60, 26, 320, 168)
    + path(P(ideal), "ax", dash="4 3") + path(P(over), "r")
    + txt(60, 18, "фактическая доля позитивов") + txt(310, 186, "предсказанная вероятность →", "m", "end")
    + txt(350, 50, "пунктир — идеальная калибровка", "t")
    + txt(350, 74, "красная — переуверенная модель:")
    + txt(350, 90, "говорит 0.9, сбывается 0.8")
    + txt(350, 118, "лечится ПОСЛЕ обучения на валидации:", "t")
    + txt(350, 136, "температура (1 параметр, не меняет argmax),")
    + txt(350, 152, "Platt (2 параметра), изотоника (гибче, но данных больше)")
    + txt(60, 205, "AUC про порядок, калибровка про честность вероятностей — они независимы; после ресемплинга калибруй заново."))

# ---------- 21. two-stage vs one-stage ----------
b = txt(8, 20, "TWO-STAGE (Faster R-CNN):", "t")
b += box(8, 30, 90, 30, "картинка") + arr(98, 45, 116, 45) + box(116, 30, 150, 30, "предложения регионов") + arr(266, 45, 284, 45) + box(284, 30, 180, 30, "классиф. + уточнение рамок")
b += txt(478, 50, "точнее, дороже")
b += txt(8, 92, "ONE-STAGE (YOLO/RetinaNet):", "t")
b += box(8, 102, 90, 30, "картинка") + arr(98, 117, 116, 117) + box(116, 102, 230, 30, "плотное предсказание по сетке") + arr(346, 117, 364, 117) + box(364, 102, 100, 30, "NMS")
b += txt(478, 122, "быстрее; focal loss")
b += txt(8, 160, "Дисбаланс «фон против объектов» у one-stage чудовищный — его давит focal loss.")
b += txt(8, 177, "Поверх обоих — NMS; в плотных сценах он душит соседей (Soft-NMS, DETR решают иначе).")
figs["det_stages"] = svg(640, 188, "Детекция", b)

# ---------- 22. isoFLOP (Chinchilla) ----------
curves = ""
mins = []
for ci, C in enumerate([1.0, 2.2, 4.8]):
    pts = []
    for i in range(60):
        n = 0.08 * (10 ** (i / 30))
        d = C / n
        loss = 1.7 + 0.35 / (n ** 0.5) + 0.42 / (d ** 0.5)
        pts.append((math.log10(n), loss))
    Ppts = scale(pts, 60, 610, 26, 150, 1.9, 3.2)
    curves += path(Ppts, ["a", "w", "g"][ci])
    mn = min(range(len(pts)), key=lambda i: pts[i][1])
    mins.append(Ppts[mn])
    curves += f"<circle cx='{Ppts[mn][0]:.1f}' cy='{Ppts[mn][1]:.1f}' r='5' fill='var(--ink)'/>"
curves += path(mins, "ax", dash="5 4")
figs["isoflop"] = svg(640, 212, "IsoFLOP-кривые Chinchilla",
    axes(60, 26, 610, 150) + curves
    + txt(60, 18, "лосс") + txt(560, 166, "размер модели N (лог) →", "m", "end")
    + txt(80, 60, "каждая кривая — фиксированный компьют C:") + txt(80, 76, "мало параметров → мало ёмкости; много → мало токенов")
    + txt(60, 190, "Минимумы (точки) сдвигаются по закону N* ∝ C^0.5 — так и получено «20 токенов на параметр».")
    + txt(60, 207, "Пунктир через минимумы — compute-optimal граница; прод-модели обучают правее неё."))

# ---------- 23. MoE router ----------
b = ""
for i, tk in enumerate(["Мама", "мыла", "раму"]):
    y = 26 + i * 40
    b += box(8, y, 90, 28, tk) + arr(98, y + 14, 128, y + 14)
b += box(128, 60, 100, 34, "router")
experts = ["E1", "E2", "E3", "E4"]
for i, e in enumerate(experts):
    x = 300 + i * 80
    b += box(x, 46, 64, 62, "")
    b += txt(x + 20, 82, e, "t")
b += arr(228, 66, 300, 66) + arr(228, 80, 380, 80) + arr(228, 90, 460, 96)
b += txt(300, 130, "top-2 на каждый токен: считаются ДВА эксперта из N, но в памяти живут ВСЕ.")
b += txt(300, 147, "Без балансирующего лосса router сваливается в любимчиков.")
b += txt(8, 176, "Выигрыш — FLOPs на токен (скорость/стоимость), не VRAM. На инференсе эксперты шардируются")
b += txt(8, 193, "по картам → all-to-all трафик в каждом MoE-слое; маленький батч размазывается и теряет смысл.")
figs["moe_router"] = svg(640, 203, "Mixture of Experts", b)

# ---------- 24. каналы инъекции ----------
b = box(8, 18, 170, 30, "инструкции разработчика")
b += box(8, 58, 170, 30, "реплика пользователя")
b += box(8, 98, 170, 30, "внешний документ/письмо", "b")
b += f"<rect x='8' y='98' width='170' height='30' rx='8' fill='var(--miss)' opacity='.15'/>"
b += arr(178, 33, 250, 66) + arr(178, 73, 250, 72) + arr(178, 113, 250, 78)
b += box(250, 56, 180, 34, "ОДИН поток токенов") + arr(430, 73, 452, 73) + box(452, 56, 100, 34, "модель")
b += txt(8, 152, "У модели нет аппаратного способа отличить «команду хозяина» от текста, притворяющегося")
b += txt(8, 169, "командой: любые маркеры каналов — тоже токены. Поэтому защита архитектурная: минимальные")
b += txt(8, 186, "права инструментов, подтверждение необратимого, изоляция — а не вежливая просьба в промпте.")
figs["injection_channels"] = svg(640, 196, "Prompt injection", b)

FP.write_text(json.dumps(figs, ensure_ascii=False, indent=1), encoding="utf-8")
print("figures total:", len(figs))
