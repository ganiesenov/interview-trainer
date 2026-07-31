# Ландшафт интервью: что спрашивают в Казахстане, СНГ и в мире

Сводка по открытым источникам (июль 2026): как устроены собеседования на
ML/LLM-роли на трёх рынках, какие темы звучат чаще всего, и как это ложится на
карточки тренажёра. Всё переведено/пересказано на русский; ссылки на оригиналы —
в каждом разделе и в конце. Материал — ориентир, не истина: процессы меняются,
сверяйся с первоисточниками.

---

## 1. Мир: FAANG и топ-лаборатории

### Anthropic (research engineer / ML engineer)

По [гайду IGotAnOffer](https://igotanoffer.com/en/advice/anthropic-interview-process),
[разборам Glassdoor](https://www.glassdoor.com/Interview/Anthropic-Research-Engineer-Interview-Questions-EI_IE8109027.0,9_KO10,27.htm)
и [Finalround](https://www.finalroundai.com/blog/anthropic-interview-process) луп выглядит так:

- **Кодинг-скрин** — НЕ литкод: одна большая задача из четырёх усложняющихся
  уровней, ~90 минут. Проверяют скорость written-to-spec кода и рефакторинг под
  добавляющиеся ограничения. Тренируется написанием реальных систем, а не задачек.
- **1–2 глубоких технических раунда** — архитектура моделей, динамика обучения,
  scaling-поведение, методы оценки. Ценят эффективный PyTorch-код, а не теорию
  ради теории. Типовые вопросы: **RAG против дообучения** (наша карточка
  `llm_ragvsft`), **как спроектировать эксперимент по детекции галлюцинаций**
  (`evalgen`, `halluc`, `ground`), смещения LLM-судьи (`llm_judgebias`).
- **Research-презентация или take-home** — рассказ о своей работе. Это ровно
  `hr_pitch_project` + `profile/projects.md`.
- **Values-интервью** — миссия, риски, даунсайды. Готовить: зачем именно
  Anthropic (а не OpenAI/DeepMind), одна история про технически сложную проблему,
  2–3 вопроса про текущие research-направления команды. Прочитать
  [Constitutional AI](https://arxiv.org/abs/2212.08073) обязательно — это их ДНК
  (карточка `llm_constitutional`, урок «Безопасность LLM-продукта»).

### OpenAI (research engineer)

По [гайду CleverPrep](https://www.cleverprep.com/companies/openai/research-engineer):
рекрутёр-скрин → кодинг с ML-уклоном (реализация и отладка важнее алгоритмов) →
дизайн систем с упором на **распределённое обучение и инфраструктуру**
(наши `zero`, `dl_deepspeed`, урок «Обучение в масштабе») → mission-fit.

### Общий рынок LLM-инженеров (2025–2026)

Сводка по [DataInterview](https://www.datainterview.com/blog/llms-and-transformers-interview-questions),
[LetsDataScience](https://letsdatascience.com/blog/50-llm-and-ai-engineer-interview-questions-for-2026),
[разбору 100+ реальных интервью](https://adilshamim8.medium.com/every-ai-engineer-interview-question-you-need-to-know-in-2026-from-100-real-interviews-b5b7ae4b961a)
и репозиториям вопросов
([Devinterview-io](https://github.com/Devinterview-io/llms-interview-questions),
[KalyanKS-NLP](https://github.com/KalyanKS-NLP/LLM-Interview-Questions-and-Answers-Hub),
[amitshekhariitbhu](https://github.com/amitshekhariitbhu/ai-engineering-interview-questions)) —
самые частые темы, все закрыты банком:

| Тема (частота в источниках) | Наши карточки / уроки |
|---|---|
| **KV-cache**: как ускоряет, память при 100k контекста × батч 32, менеджмент | `kv`, `llm_kvquant`, разбор недели 1, схема kv_memory |
| **GQA vs MQA** — сравнение архитектурных выборов | `gqa`, схема gqa_kv |
| **Написать Multi-Head Attention по памяти**; починить баг в позиционном кодировании / KV-кэше | код в уроке «Внимание» + `attn`, `mha`, `rope`; недельный проект nanoGPT |
| **RLHF и DPO у доски** | `dpo`, `rewardhack`, вывод DPO-лосса в уроке «Алайнмент» |
| DPO-альтернативы: **KTO**, IPO, ORPO — «что придёт на смену RLHF» | `llm_prefzoo` (добавлена по итогам этого ресёрча) |
| SFT → RLHF конвейер, зачем какая стадия | `llm_ragvsft`, `sftdata`, урок «Данные для дообучения» |
| Tokenization, BPE | `tok`, `nl_tokcomp`, код BPE в уроке NLP |
| RAG: чанкинг, гибрид, реранкер, оценка | весь блок «RAG и оценка» |
| Квантизация, инференс-оптимизация, speculative decoding | `bf16`, `spec`, `llm_moeserve`, уроки «Память» и «Инференс» |

### ML system design (все крупные компании)

Классика по репо [khangich/machine-learning-interview](https://github.com/khangich/machine-learning-interview)
(реальные вопросы Facebook/Amazon/Apple/Google/MS/Snapchat/LinkedIn) и
[alirezadir/Machine-Learning-Interviews](https://github.com/alirezadir/Machine-Learning-Interviews)
(обновлён под GenAI: internals LLM, post-training, PEFT, inference-оптимизация,
GenAI system design): рекомендации, ранжирование ленты, реклама, поиск. У нас —
трек «Системный дизайн» (30 карточек) + `ml_l2r`, `ml_cf`, `ml_recometrics`.
Оба репо стоит пролистать целиком — это лучшая бесплатная база реальных вопросов.

---

## 2. СНГ: Яндекс, Сбер и рынок

### Яндекс (ML-разработчик)

Первоисточник — [страница о найме ML-специалистов](https://yandex.ru/jobs/pages/mldev-interview)
и [описание базовой технической секции](https://education.yandex.ru/knowledge/sektsiia-na-proverku-bazovikh-tekhnicheskikh-navikov-ml-inzhenerov):

- Трек: рекрутёр → технические секции → финалы; трек индивидуальный.
- **Алгоритмическая секция**: обычно две задачи — массивы, хеш-таблицы, краевые
  случаи, тестирование своего решения. Это НЕ закрывается нашим банком — литкод
  тренируется отдельно (easy/medium, 2–3 в день за месяц до лупа).
- ML-секции — по специализации; глубина по классике + DL.

### Сбер (SberDevices, ML-разработчик)

По [официальной странице](https://sberdevices.ru/career/ML/interview/):
знание языка + 1–3 практические задачи кодом; **метрики, оценка моделей,
разбиение данных, методы оптимизации**; базовые модели — линейная регрессия,
деревья, случайный лес, бустинг; по специализации — NLP/CV: слои, активации,
современные архитектуры, подготовка данных. Всё это — наши блоки «Классический
ML» и «Фундамент DL» один в один.

### Рынок РФ/СНГ в целом

- [ИТМО о classic ML на собеседованиях](https://ai.itmo.ru/blog/classic-ml-sobesedovanie-ml-engineer):
  деревья и ансамбли — обязательный блок (наши `gbdt`, `ml_rfgb`, `ml_gbdt_mech`,
  `ml_boostlibs`).
- [Хабр: топ вопросов с NLP-собеседований](https://habr.com/ru/articles/1044420/) —
  обучение LLM, prompt-engineering, alignment; хорошо бьётся с нашими уроками
  «Алайнмент» и «Оценка генерации».
- [Хабр: вопросы по RL в 2026](https://habr.com/ru/articles/1055446/) — RL для
  LLM, скейлинг RL (ProRL), on-policy distillation; наш `llm_rlvr` + `llm_grpo`
  закрывают базу, статья — для глубины.
- [DeepSchool: Anki-карточки для собеседований](https://anki.deepschool.ru/) —
  русскоязычные карточки, полезное дополнение к нашим.
- [ENIGMA AI: вопросы DS/ML 2026](https://enigmai.ru/tech-questions/ml-ds/) —
  фокус сместился с классического supervised на трансформеры, LLM-инженерию и
  real-time данные — ровно тезис нашего трека.

Итог по СНГ: два отличия от мирового лупа — **обязательная алгоритмическая
секция** (литкод, тренируется отдельно) и больший вес **классики на табличках**
(бустинг, метрики, валидация) — у нас это блок «Смежные треки».

---

## 3. Казахстан

Публично задокументированных разборов интервью мало (Kaspi/Halyk процессы не
публикуют; [отзывы Glassdoor о Kaspi](https://www.glassdoor.com/Reviews/Kaspi-Bank-Reviews-E858534.htm)
— о культуре, не о вопросах). Что известно из практики рынка:

- Банки (Halyk, Kaspi, БЦК, Jusan) собеседуют как «Сбер-лайт»: классический ML
  на табличках (скоринг, отток, антифрод — наши `ml_scorecard`, `ml_velocity`,
  `ml_churndef`), SQL, метрики, валидация по времени, иногда системный дизайн
  фичей. LLM-роли только появляются — спрашивают RAG-стек и промптинг
  поверх классики.
- Продуктовые компании и стартапы ориентируются на московский формат
  (алгоритмы + ML-глубина).
- Специфика, которой нет больше нигде: **казахский язык** — вопросы про
  токенизацию агглютинативных языков, fertility, мультиязычные модели и
  низкоресурсные корпуса. Это наши `nl_tokcomp`, `multiling`, `nl_lang_resources`,
  `llm_contpretrain` — и твой собственный research-материал (корпус, QazaqBERT,
  KazEval) здесь становится главным козырем: в KZ ты один из немногих, кто
  делал это руками.

---

## 4. Что учить: приоритеты по итогам ресёрча

1. **Кодить трансформер руками** — просят везде (Anthropic OA, «MHA по памяти»,
   баг-фиксы). Закрывается недельным проектом №1 (nanoGPT) + сниппетами уроков.
2. **Инференс-арифметика** — KV-cache/память/GQA спрашивают на seniority-уровне.
   Уроки «Инференс» и «Память» + разборы недели 1.
3. **RLHF→DPO→зоопарк** у доски — вывод лосса, KTO/IPO/ORPO на словах.
4. **ML system design** — прогнать кейсы khangich/alirezadir (рекомендации,
   лента, поиск) поверх нашего трека «Системный дизайн».
5. **Литкод для СНГ-лупов** — отдельная дорожка, 2–3 задачи в день за месяц.
6. **Классика для банков KZ/СНГ** — блок «Смежные треки» до автоматизма.
7. **Свой research-питч** — топ-лабы слушают его дольше всего; репетировать по
   `hr_pitch_project` с цифрами KazEval/маммографии.

## Источники

Мир: [IGotAnOffer — Anthropic process](https://igotanoffer.com/en/advice/anthropic-interview-process) ·
[Anthropic questions](https://igotanoffer.com/en/advice/anthropic-interview-questions) ·
[Glassdoor — Anthropic RE](https://www.glassdoor.com/Interview/Anthropic-Research-Engineer-Interview-Questions-EI_IE8109027.0,9_KO10,27.htm) ·
[Finalround — Anthropic](https://www.finalroundai.com/blog/anthropic-interview-process) ·
[CleverPrep — OpenAI RE](https://www.cleverprep.com/companies/openai/research-engineer) ·
[DataInterview — 32 LLM questions](https://www.datainterview.com/blog/llms-and-transformers-interview-questions) ·
[LetsDataScience — 50 questions 2026](https://letsdatascience.com/blog/50-llm-and-ai-engineer-interview-questions-for-2026) ·
[Adil Shamim — 100+ real interviews](https://adilshamim8.medium.com/every-ai-engineer-interview-question-you-need-to-know-in-2026-from-100-real-interviews-b5b7ae4b961a) ·
[MyEngineeringPath — 30 senior questions](https://myengineeringpath.dev/genai-engineer/llm-interview-questions/) ·
[Devinterview-io/llms-interview-questions](https://github.com/Devinterview-io/llms-interview-questions) ·
[KalyanKS-NLP/LLM-Interview-QA-Hub](https://github.com/KalyanKS-NLP/LLM-Interview-Questions-and-Answers-Hub) ·
[amitshekhariitbhu/ai-engineering-interview-questions](https://github.com/amitshekhariitbhu/ai-engineering-interview-questions) ·
[khangich/machine-learning-interview](https://github.com/khangich/machine-learning-interview) ·
[alirezadir/Machine-Learning-Interviews](https://github.com/alirezadir/Machine-Learning-Interviews)

СНГ: [Яндекс — как нанимаем ML](https://yandex.ru/jobs/pages/mldev-interview) ·
[Яндекс — базовая техсекция](https://education.yandex.ru/knowledge/sektsiia-na-proverku-bazovikh-tekhnicheskikh-navikov-ml-inzhenerov) ·
[SberDevices — ML-интервью](https://sberdevices.ru/career/ML/interview/) ·
[ИТМО — classic ML](https://ai.itmo.ru/blog/classic-ml-sobesedovanie-ml-engineer) ·
[Хабр — NLP-вопросы](https://habr.com/ru/articles/1044420/) ·
[Хабр — RL-вопросы 2026](https://habr.com/ru/articles/1055446/) ·
[DeepSchool Anki](https://anki.deepschool.ru/) ·
[ENIGMA AI — DS/ML вопросы](https://enigmai.ru/tech-questions/ml-ds/)

KZ: [Glassdoor — Kaspi reviews](https://www.glassdoor.com/Reviews/Kaspi-Bank-Reviews-E858534.htm) ·
[kazakhstan-it-internships](https://github.com/danabeknar/kazakhstan-it-internships)
