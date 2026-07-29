# Interview Trainer

Локальный тренажёр собеседований на позиции **LLM / NLP / DL / AI Engineer**.

Главная функция — интервьюер, который задаёт вопрос и **не отстаёт**, пока не станет
ясно, понимаешь ты решение или пересказываешь туториал. Весь инференс локальный
(Ollama), знание живёт в банке вопросов, а не в модели: она только сверяет текст
кандидата с эталоном.

Полное ТЗ — [`docs/spec.md`](docs/spec.md).

## Статус

Каркас. Кода пока нет — следующий шаг **v0 (режим квиза)**, см. «Фазы» в ТЗ.

## Стек

| Слой | Решение |
|---|---|
| Модель | `qwen2.5:32b-instruct-q4_K_M` через Ollama |
| Валидный JSON | `format="json"` в Ollama |
| Температура | 0.15 оценщик / 0.7 генерация вопросов |
| v0 | Python CLI (`rich`) |
| v1 | FastAPI + SQLite, одна HTML-страница + htmx |
| v2 | faster-whisper large-v3 + Silero TTS |

## Структура

```
interview_trainer/
├── CLAUDE.md              # контекст проекта для Claude Code
├── docs/spec.md           # ТЗ
├── profile/
│   ├── resume.md          # резюме в свободной форме
│   └── projects.md        # проекты: контекст, решения, цифры, что сломалось
├── core/
│   ├── interviewer.py     # ведёт диалог, держит счётчик follow-up
│   ├── grader.py          # выдаёт оценку строго в JSON
│   ├── prompts.py         # все шаблоны промптов
│   └── store.py           # SQLite: сессии, слабые места
├── banks/
│   ├── theory.yaml        # вопросы по матчасти
│   └── sysdesign.yaml     # кейсы system design
├── run.py                 # точка входа CLI
└── data/sessions.db
```

## Режимы

Квиз и мок-интервью — один движок, разница только в `max_followups`:

```
quiz  = вопрос → ответ → оценка                    (max_followups = 0)
mock  = вопрос → ответ → уточняющий ×N → вердикт   (max_followups = 3)
```

Ответ всегда открытый — никаких вариантов на выбор.

Рубрики: `project` (главная), `theory`, `sysdesign`, `coding`, `hr`, `pitch`.

## Запуск (после v0)

```bash
ollama pull qwen2.5:32b-instruct-q4_K_M
pip install -r requirements.txt
python run.py --mode quiz
```

## Личные данные

`profile/resume.md` и `profile/projects.md` лежат в репозитории как **шаблоны**.
Репозиторий публичный — если заполняешь их реальными деталями работы, либо чисти
чувствительное, либо добавь `profile/` в `.gitignore`.
