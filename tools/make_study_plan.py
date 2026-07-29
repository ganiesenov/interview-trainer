"""Собирает docs/study-plan.md из банка.

    python tools/make_study_plan.py

Правишь состав дней здесь, а не в markdown: скрипт проверяет, что все id есть
в banks/bank_full.json, и подставляет актуальные тексты вопросов.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = json.loads((ROOT / "banks" / "bank_full.json").read_text(encoding="utf-8"))
BY_ID = {c["id"]: c for c in BANK}

PLAN = [
 ("Неделя 1 — LLM: как это работает и как это обслуживается", [
  ("День 1", "Внимание и блок трансформера",
   ["attn", "mha", "gqa", "ffn", "norm", "dl_positional", "encdec"],
   "Attention Is All You Need; d2l.ai, глава про внимание",
   "Вывести scaled dot-product на бумаге и объяснить деление на корень из d_k"),
  ("День 2", "Инференс: как генерируется токен",
   ["kv", "prefill", "batching", "llm_throughput", "spec", "sampling", "llm_repetition"],
   "Документация vLLM (continuous batching, PagedAttention); блог о speculative decoding",
   "Посчитать размер KV-cache для 7B при контексте 8k и батче 16"),
  ("День 3", "Память, стоимость, размер модели",
   ["quant", "llm_kvquant", "tokcost", "llm_p99", "llm_tp", "llm_sizechoice", "struct"],
   "QLoRA (NF4); документация GPTQ/AWQ; llama.cpp про GGUF",
   "Прикинуть, сколько GPU нужно на 200 rps при 2k контекста и 200 токенов ответа"),
  ("День 4", "Длинный контекст и позиции",
   ["len", "contextrot", "llm_ctxstage", "rope", "llm_prefixcache", "llm_memory", "llm_vocab"],
   "RoFormer (RoPE); Position Interpolation, YaRN; Lost in the Middle",
   "Объяснить, почему модель на 4k ломается на 32k и что делает интерполяция позиций"),
  ("День 5", "Повтор недели без новых карточек",
   [],
   "—",
   "Прогнать через run.py 8 случайных вопросов из пройденного, вслух и на диктофон"),
 ]),
 ("Неделя 2 — RAG, эмбеддинги, оценка", [
  ("День 1", "Поиск: основа RAG",
   ["chunk", "hybrid", "rerank", "index", "qrw", "nl_bm25"],
   "BM25 (Robertson & Zaragoza); документация FAISS и HNSW",
   "Нарисовать полный путь запроса от текста до ответа с этапами и задержками"),
  ("День 2", "RAG в проде",
   ["ground", "llm_ragdiag", "llm_ragk", "llm_ragfresh", "llm_multihop", "llm_ragtables"],
   "Оригинальная статья RAG (Lewis et al.); материалы по RAGAS",
   "Придумать, как отделить ошибку поиска от ошибки генерации на своих данных"),
  ("День 3", "Эмбеддинги",
   ["emb", "pool", "matry", "embtrain", "llm_embchoice", "llm_embreindex"],
   "Sentence-BERT; Matryoshka Representation Learning; карточки моделей bge/e5",
   "Объяснить, зачем нужны hard negatives и почему важен размер батча"),
  ("День 4", "Оценка генерации",
   ["evalgen", "halluc", "llm_judgebias", "eval_ab", "contam", "llm_offon", "ppl"],
   "Judging LLM-as-a-Judge (MT-Bench); материалы по контаминации бенчмарков",
   "Составить план офлайн-набора для своей задачи: что в него войдёт и почему"),
  ("День 5", "Повтор + первый мок",
   [],
   "—",
   "Взять 3 вопроса из недели 1 и 3 из недели 2, отвечать без подглядывания"),
 ]),
 ("Неделя 3 — Дообучение, алайнмент, фундамент DL", [
  ("День 1", "PEFT",
   ["lora", "qlora", "peftcompare", "llm_multilora", "lossmask", "packing"],
   "LoRA; QLoRA; документация PEFT от HuggingFace",
   "Объяснить, что именно обучается в LoRA и почему B инициализируется нулями"),
  ("День 2", "Данные для дообучения",
   ["sftdata", "forget", "llm_sftsize", "distill", "llm_synthdata", "llm_ragvsft"],
   "LIMA (качество против объёма); Self-Instruct",
   "Сформулировать критерий, когда задача решается RAG, а когда дообучением"),
  ("День 3", "Алайнмент и рассуждения",
   ["dpo", "rewardhack", "llm_prefpairs", "llm_rlvr", "llm_reasoning", "cot", "selfcons"],
   "InstructGPT (RLHF); DPO; Chain-of-Thought; Self-Consistency",
   "Вывести, из чего складывается лосс DPO и что делает beta"),
  ("День 4", "Фундамент DL",
   ["dl_backprop", "dl_vanish", "dl_optimizers", "dl_weightdecay", "dl_normwhy",
    "dl_losschoice", "dl_softmaxnum"],
   "Decoupled Weight Decay (AdamW); How Does Batch Normalization Help Optimization; d2l.ai",
   "Объяснить, почему кросс-энтропия принимает логиты, а не вероятности"),
  ("День 5", "Практика обучения",
   ["dl_debug", "dl_lrfind", "dl_gradclip", "dl_gradaccum", "dl_paramcount",
    "dl_activation_ckpt", "dl_seed"],
   "Karpathy, A Recipe for Training Neural Networks",
   "Посчитать память под обучение 7B в bf16 с Adam и с checkpointing"),
 ]),
 ("Неделя 4 — Прод, статистика, системный дизайн, HR", [
  ("День 1", "MLOps: наблюдаемость",
   ["psi", "repro", "op_fs", "op_monitor", "op_registry", "op_shadowdata", "op_incident"],
   "Chip Huyen, Designing Machine Learning Systems, главы про мониторинг и дрейф",
   "Описать, что мониторить в своём последнем проекте и с какими порогами"),
  ("День 2", "MLOps: выкатка и эксплуатация",
   ["op_canary", "op_shadow", "op_rollback", "op_slo", "op_cost", "op_thresholds",
    "op_modelinput_log"],
   "Та же книга, главы про деплой; Google SRE Book (алерты и SLO)",
   "Написать план отката для модели, которая уже работает у тебя в проде"),
  ("День 3", "Статистика и A/B",
   ["st_pval", "st_power", "st_mde", "st_peek", "st_mult", "st_cuped", "st_ratio", "st_srm"],
   "Kohavi, Tang, Xu — Trustworthy Online Controlled Experiments (главы 1-5, 17-22)",
   "Посчитать размер выборки для прироста конверсии на 1% при базе 5%"),
  ("День 4", "Системный дизайн",
   ["sd_rag200", "sd_domain", "agent", "latency", "tooluse", "sd_support",
    "llm_agentfail", "llm_toolschema"],
   "Alex Xu, Machine Learning System Design Interview; посты о проде LLM-агентов",
   "Спроектировать RAG на 200 rps вслух за 20 минут, с бюджетом задержки по этапам"),
  ("День 5", "HR и питч проекта",
   ["tellme", "whyleave", "hr_salary", "hr_expectations", "hr_notech", "hr_failure",
    "hr_questions", "hr_pitch_project"],
   "—",
   "Записать на диктофон рассказ о себе за 2 минуты и про проект за 3 минуты"),
 ]),
]

BACKGROUND = {
 "Классический ML — по диагонали": ["ml_biasvar", "gbdt", "ml_rfgb", "calib", "ml_rocpr",
                                    "leak", "groupkf", "imbal", "ml_thresh", "ml_erroranalysis"],
 "Computer Vision — если спросят": ["cv_conv", "cv_normchoice", "cv_det", "cv_map",
                                    "cv_seg", "cv_transfer", "cv_vit"],
 "NLP-классика — если спросят": ["tok", "nl_tokcomp", "ner", "nl_tfidf", "nl_annotate",
                                 "nl_longdoc"],
}

missing = []
for _, days in PLAN:
    for _, _, ids, _, _ in days:
        missing += [i for i in ids if i not in BY_ID]
for ids in BACKGROUND.values():
    missing += [i for i in ids if i not in BY_ID]
if missing:
    raise SystemExit("нет в банке: " + ", ".join(sorted(set(missing))))

core_ids = {i for _, days in PLAN for _, _, ids, _, _ in days for i in ids}
bg_ids = {i for ids in BACKGROUND.values() for i in ids}

def cards(n: int) -> str:
    tail = n % 100
    if 11 <= tail <= 14:
        return f"{n} карточек"
    last = n % 10
    if last == 1:
        return f"{n} карточка"
    if 2 <= last <= 4:
        return f"{n} карточки"
    return f"{n} карточек"


out = [
 "# План подготовки",
 "",
 f"Ядро — {cards(len(core_ids))} из {len(BANK)} под роль LLM / NLP / AI Engineer,",
 f"плюс {cards(len(bg_ids))} фоном — на случай вопросов из смежных областей.",
 "Остальное в банке — справочник, а не программа.",
 "",
 "## Как работать",
 "",
 "1. **Сначала произнеси вслух, потом открывай эталон.** Прочитать разбор и подумать",
 "   «ну да, я это знал» — самый надёжный способ обмануть себя. Не смог сказать связно",
 "   за 60 секунд — значит не знаешь.",
 "2. **Механику выводи, а не заучивай.** Всё, что помечено как «вывести на бумаге»,",
 "   должно получаться с нуля. Выведенное не забывается, заученное рассыпается на",
 "   первом уточняющем вопросе.",
 "3. **Пиши свой эталон.** После разбора `run.py` предлагает записать свою формулировку",
 "   пунктов (`--mine <id>`). Дальше сверка идёт с твоей версией, а не с моей. Момент,",
 "   когда ты формулируешь ответ сам, и есть момент запоминания.",
 "4. **Суждения привязывай к своим проектам.** На вопросах вида «когда RAG, а когда",
 "   дообучение» правильный ответ звучит как «в моём проекте было так, я выбрал это,",
 "   потому что…». Поэтому `profile/projects.md` важнее половины теории.",
 "5. **Сомневаешься в карточке — иди в первоисточник.** Банк написан языковой моделью",
 "   и не верифицирован; в каждом дне указано, где смотреть правду.",
 "",
 "## Ритм дня — примерно час",
 "",
 "| Блок | Время | Что делать |",
 "|---|---|---|",
 "| Повторение | 15 мин | Карточки с телефона по вчерашним и позавчерашним темам |",
 "| Тренажёр | 20 мин | 3 вопроса дня через `run.py` вслух, с диктофоном |",
 "| Глубина | 15 мин | Первоисточник дня + вывод на бумаге |",
 "| Проект | 10 мин | Один блок в `profile/projects.md` |",
 "",
 "Пятый день каждой недели — без новых карточек: только повторение и мок.",
 "",
]

for week, days in PLAN:
    out += [f"## {week}", ""]
    for day, theme, ids, source, task in days:
        out += [f"### {day} — {theme}", ""]
        if ids:
            out.append("| id | Вопрос |")
            out.append("|---|---|")
            for i in ids:
                out.append(f"| `{i}` | {BY_ID[i]['q']} |")
            out.append("")
        out += [f"**Первоисточник:** {source}", "", f"**Сделать руками:** {task}", ""]
        if ids:
            out += ["```bash", "python run.py --id " + ids[0], "```", ""]

out += ["## Фон — читать, но не зубрить", ""]
for title, ids in BACKGROUND.items():
    out += [f"### {title}", ""]
    out += ["| id | Вопрос |", "|---|---|"]
    for i in ids:
        out.append(f"| `{i}` | {BY_ID[i]['q']} |")
    out.append("")

out += [
 "## Как понять, что готов",
 "",
 "Не по баллу тренажёра, а по трём признакам:",
 "",
 "1. По любой карточке ядра ты говоришь 60 секунд связно, без пауз и без «ну как бы».",
 "2. На вопрос «почему именно так» у тебя есть причина, а не ссылка на то, что так принято.",
 "3. По каждому проекту из `profile/projects.md` ты называешь цифру: что было, что стало,",
 "   как мерил. Именно здесь разваливается большинство кандидатов.",
 "",
 "Если по трети карточек ядра ты не согласен с моей формулировкой пунктов — это нормально",
 "и даже полезно: перепиши их через `--mine`, банк станет твоим.",
 "",
]

(ROOT / "docs" / "study-plan.md").write_text("\n".join(out), encoding="utf-8")
print(f"docs/study-plan.md: ядро {len(core_ids)}, фон {len(bg_ids)}, всего строк {len(out)}")
