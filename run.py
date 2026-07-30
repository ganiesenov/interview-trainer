#!/usr/bin/env python3
"""CLI entry point.

v0: quiz — one question, one open answer, one breakdown.
v1: mock (--mock) — the same engine spends follow-ups on uncovered points,
    and every session lands in SQLite (history, weak spots, review queue).
"""

from __future__ import annotations

import argparse
import json
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from core import mine, prompts, store
from core.bank import BankError, Question, coverage, filter_questions, load_bank, pick
from core.grader import COVERED, MISSED, PARTIAL, Grade, gaps, grade
from core.interviewer import Interviewer, load_profile
from core.llm import DEFAULT_MODEL, LLMError

console = Console()

STATUS_STYLE = {COVERED: "bold green", PARTIAL: "bold yellow", MISSED: "bold red"}
STATUS_LABEL = {COVERED: "covered", PARTIAL: "partial", MISSED: "missed"}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        questions = load_bank(args.bank)
    except BankError as exc:
        console.print(f"[bold red]Ошибка банка:[/] {exc}")
        return 2

    if args.stats:
        show_stats(questions)
        return 0

    if args.list:
        try:
            list_questions(filter_questions(questions, track=args.track, topic=args.topic))
        except BankError as exc:
            console.print(f"[bold red]Ошибка банка:[/] {exc}")
            return 2
        return 0

    if args.list_mine:
        list_mine(questions)
        return 0

    if args.mine:
        return edit_mine(questions, args.mine)

    if args.history or args.weak:
        conn = store.connect(args.db)
        if args.history:
            show_history(conn)
        if args.weak:
            show_weak(conn, {q.id: q for q in questions})
        return 0

    review_ids: list[str] = []
    if args.review:
        conn = store.connect(args.db)
        review_ids = [item.question_id for item in store.due_items(conn)]
        review_ids = [i for i in review_ids if any(q.id == i for q in questions)]
        if not review_ids:
            console.print("[dim]Очередь повторения пуста — все вопросы ещё «свежие».[/]")
            return 0
        console.print(f"[dim]В очереди повторения: {len(review_ids)} вопрос(ов).[/]")

    max_followups = args.followups if args.followups is not None else (3 if args.mock else 0)
    profile = load_profile() if (args.profile or max_followups) else ""
    asked: set[str] = set()

    while True:
        try:
            if review_ids:
                question = pick(questions, question_id=review_ids[0])
                review_ids.pop(0)
            else:
                question = pick(
                    questions,
                    question_id=args.id,
                    track=args.track,
                    topic=args.topic,
                    exclude=asked,
                )
        except BankError as exc:
            console.print(f"[bold red]Ошибка банка:[/] {exc}")
            return 2
        asked.add(question.id)

        try:
            run_session(
                question,
                model=args.model,
                role=args.role,
                profile=profile,
                use_mine=not args.bank_ref,
                ask_mine=args.ask_mine,
                max_followups=max_followups,
                db_path=None if args.no_save else args.db,
            )
        except LLMError as exc:
            console.print(f"\n[bold red]Модель недоступна:[/] {exc}")
            return 1
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Прервано.[/]")
            return 130

        if review_ids:
            if not ask_yes_no("Следующий из очереди?"):
                return 0
            continue
        if args.id or not ask_yes_no("Ещё вопрос?"):
            return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interview Trainer — v0, режим квиза")
    parser.add_argument("--bank", default="banks/bank_full.json", help="файл банка вопросов")
    parser.add_argument("--track", help="ограничить выборку направлением (LLM, Статистика, …)")
    parser.add_argument("--topic", help="ограничить выборку темой")
    parser.add_argument("--id", help="задать конкретный вопрос по id")
    parser.add_argument("--model", default=None, help=f"модель Ollama (по умолчанию {DEFAULT_MODEL})")
    parser.add_argument("--role", default=prompts.DEFAULT_ROLE, help="позиция, на которую идёт интервью")
    parser.add_argument(
        "--profile",
        action="store_true",
        help="подмешать profile/ в контекст интервьюера (нужно для follow-up, v0 их не задаёт)",
    )
    parser.add_argument("--list", action="store_true", help="показать содержимое банка и выйти")
    parser.add_argument("--stats", action="store_true", help="покрытие банка по направлениям и темам")
    parser.add_argument("--mine", metavar="ID", help="записать или переписать свой эталон для вопроса")
    parser.add_argument("--list-mine", action="store_true", help="показать вопросы со своим эталоном")
    parser.add_argument(
        "--ask-mine",
        action="store_true",
        help="предлагать записать свой эталон после каждого разбора (по умолчанию не спрашивает)",
    )
    parser.add_argument(
        "--bank-ref",
        action="store_true",
        help="сверять с эталоном банка, даже если есть свой",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="мок-интервью: до 3 уточняющих по нераскрытым пунктам, потом вердикт",
    )
    parser.add_argument(
        "--followups",
        type=int,
        default=None,
        metavar="N",
        help="переопределить число уточняющих (0 = квиз, 3 = как --mock)",
    )
    parser.add_argument("--history", action="store_true", help="последние сессии из журнала")
    parser.add_argument("--weak", action="store_true", help="слабые темы и вопросы по журналу")
    parser.add_argument(
        "--review",
        action="store_true",
        help="гонять вопросы из очереди повторения (плохие — чаще)",
    )
    parser.add_argument("--no-save", action="store_true", help="не записывать сессию в журнал")
    parser.add_argument("--db", default=str(store.DEFAULT_PATH), help="файл журнала SQLite")
    return parser.parse_args(argv)


def list_questions(questions: list[Question]) -> None:
    table = Table(title=f"Банк: {len(questions)} вопрос(ов)", header_style="bold")
    table.add_column("id", style="cyan", no_wrap=True)
    table.add_column("track", style="green", no_wrap=True)
    table.add_column("topic", style="magenta", no_wrap=True)
    table.add_column("question")
    table.add_column("points", justify="right", style="dim")
    for question in questions:
        table.add_row(
            question.id,
            question.track,
            question.topic,
            question.question,
            str(len(question.key_points)),
        )
    console.print(table)


def show_stats(questions: list[Question]) -> None:
    stats = coverage(questions)
    table = Table(title=f"Покрытие банка: {len(questions)} вопрос(ов)", header_style="bold")
    table.add_column("track", style="green", no_wrap=True)
    table.add_column("topic", style="magenta")
    table.add_column("n", justify="right")
    for track in sorted(stats, key=lambda name: -sum(stats[name].values())):
        topics = sorted(stats[track].items(), key=lambda item: -item[1])
        total = sum(stats[track].values())
        table.add_row(f"[bold]{track}[/]", "[dim]всего[/]", f"[bold]{total}[/]")
        for topic, count in topics:
            table.add_row("", topic, str(count))
    console.print(table)


def run_session(
    question: Question,
    *,
    model: str | None,
    role: str,
    profile: str,
    use_mine: bool = True,
    ask_mine: bool = False,
    max_followups: int = 0,
    db_path: str | None = None,
) -> None:
    """One question end to end: answer → (follow-ups while points stay uncovered) → verdict."""
    entries = mine.load() if use_mine else {}
    graded_against, is_mine = mine.apply_to(question, entries)

    interviewer = Interviewer(
        question=question,
        role=role,
        profile=profile,
        max_followups=max_followups,
        model=model,
    )

    console.print()
    console.print(
        Panel(
            Text(interviewer.ask(), style="bold"),
            title=(
                f"[cyan]{question.id}[/] · [green]{question.track or '—'}[/]"
                f" / [magenta]{question.topic or '—'}[/]"
            ),
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print("[dim]Отвечай своими словами. Пустая строка — закончить ответ.[/]\n")

    answer = read_answer()
    interviewer.record_answer(answer)
    answers = [answer]

    with console.status("[dim]Сверяю с эталоном…[/]", spinner="dots"):
        result = grade(graded_against, answer, model=model)
    first = result

    # The mock loop: while the budget lasts and points stay uncovered, dig deeper.
    while interviewer.followups_left and gaps(result):
        console.print(
            f"[dim]{result.count(COVERED)}/{len(result.points)} пунктов закрыто —"
            f" интервьюер не отстаёт ({interviewer.followups_left} уточн. осталось).[/]"
        )
        with console.status("[dim]Интервьюер думает…[/]", spinner="dots"):
            followup_text = interviewer.followup(gaps(result))
        if not followup_text:
            break
        console.print()
        console.print(
            Panel(Text(followup_text, style="bold"), title="[yellow]Уточняющий[/]", border_style="yellow", padding=(1, 2))
        )
        console.print("[dim]Пустая строка — закончить ответ (или сразу Enter, чтобы пасовать).[/]\n")
        followup_answer = read_answer(allow_empty=True)
        interviewer.record_answer(followup_answer or "не знаю")
        if followup_answer:
            answers.append(followup_answer)
            with console.status("[dim]Сверяю с эталоном…[/]", spinner="dots"):
                result = grade(graded_against, "\n\n".join(answers), model=model)
        # An empty answer keeps the previous grade; the budget is spent either way.

    render_grade(question, result, is_mine=is_mine, first=first if max_followups else None)

    if db_path is not None:
        conn = store.connect(db_path)
        store.save(
            conn,
            question=question,
            mode="mock" if max_followups else "quiz",
            first=first,
            final=result,
            followups=interviewer.max_followups - interviewer.followups_left,
            model=model,
        )
        conn.close()

    if ask_mine:
        maybe_save_mine(question, already=is_mine)


def read_answer(allow_empty: bool = False) -> str:
    lines: list[str] = []
    while True:
        try:
            line = input("> " if not lines else "  ")
        except EOFError:
            break
        if not line.strip():
            if lines or allow_empty:
                break
            continue
        lines.append(line)
    return "\n".join(lines)


def render_grade(
    question: Question,
    result: Grade,
    *,
    is_mine: bool = False,
    first: Grade | None = None,
) -> None:
    console.print()
    console.print(Rule("Разбор", style="dim"))
    if is_mine:
        console.print("[dim]Сверка с твоим эталоном (банковский — ниже).[/]")

    table = Table(show_lines=True, header_style="bold", expand=True)
    table.add_column("Пункт твоего эталона" if is_mine else "Пункт эталона", ratio=3)
    table.add_column("Статус", no_wrap=True)
    table.add_column("Из твоего ответа", ratio=2, style="dim")
    for point in result.points:
        table.add_row(
            point.point,
            Text(STATUS_LABEL[point.status], style=STATUS_STYLE[point.status]),
            point.quote or "—",
        )
    console.print(table)

    summary = (
        f"[bold green]{result.count(COVERED)} covered[/] · "
        f"[bold yellow]{result.count(PARTIAL)} partial[/] · "
        f"[bold red]{result.count(MISSED)} missed[/]"
    )
    console.print(f"\n{summary}   Оценка: [bold]{result.score}/10[/]")

    if first is not None and first.score != result.score:
        rescued = sum(
            1
            for before, after in zip(first.points, result.points)
            if before.status != COVERED and after.status == COVERED
        )
        console.print(
            f"[dim]Первый ответ: {first.score}/10 → после уточняющих: {result.score}/10"
            f" (вытащил на уточняющих: {rescued} пункт(а)).[/]"
        )

    if result.invented:
        console.print("\n[bold red]Противоречит эталону:[/]")
        for item in result.invented:
            console.print(f"  • {item}")

    if not result.hedging and result.count(MISSED):
        console.print("\n[yellow]Не признал, что чего-то не знает — выдумывал вместо «не знаю».[/]")

    if question.reference:
        console.print()
        console.print(
            Panel(
                Markdown(question.reference),
                title="Эталон",
                border_style="green",
                padding=(1, 2),
            )
        )
    console.print()


def maybe_save_mine(question: Question, *, already: bool) -> None:
    """Offer to record your own wording of the key points. Opt-in via --ask-mine."""
    if not sys.stdin.isatty():
        return
    prompt = "Переписать свой эталон?" if already else "Записать свой эталон для этого вопроса?"
    if not ask_yes_no(prompt, default_yes=False):
        return
    write_mine(question)


def write_mine(question: Question) -> bool:
    """Read personal key points from stdin and store them. True if saved."""
    entries = mine.load()
    existing = mine.points_for(entries, question.id)
    if existing:
        console.print("\n[dim]Текущая версия:[/]")
        for point in existing:
            console.print(f"  • {point}")

    console.print(
        "\n[dim]Пиши пункты своими словами, по одному в строке. "
        "Пустая строка — закончить, ввод без единого пункта — отмена.[/]"
    )
    points = mine.parse_points(read_answer())
    if not points:
        console.print("[dim]Не сохранено.[/]")
        return False

    mine.save(mine.upsert(entries, question.id, points))
    console.print(f"[green]Сохранено:[/] {len(points)} пункт(ов) в {mine.DEFAULT_PATH}")
    return True


def edit_mine(questions: list[Question], question_id: str) -> int:
    try:
        question = pick(questions, question_id=question_id)
    except BankError as exc:
        console.print(f"[bold red]Ошибка банка:[/] {exc}")
        return 2

    console.print()
    console.print(Panel(Text(question.question, style="bold"), title=f"[cyan]{question.id}[/]"))
    console.print("\n[dim]Пункты банка (для ориентира):[/]")
    for point in question.key_points:
        console.print(f"  • {point}")

    try:
        return 0 if write_mine(question) else 0
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Прервано.[/]")
        return 130


def list_mine(questions: list[Question]) -> None:
    entries = mine.load()
    if not entries:
        console.print(
            "[dim]Своих эталонов пока нет. Запиши первый: python run.py --mine <id>[/]"
        )
        return

    by_id = {question.id: question for question in questions}
    table = Table(
        title=f"Свои эталоны: {len(entries)} из {len(questions)}",
        header_style="bold",
    )
    table.add_column("id", style="cyan", no_wrap=True)
    table.add_column("track", style="green", no_wrap=True)
    table.add_column("question")
    table.add_column("пунктов", justify="right", style="dim")
    table.add_column("обновлён", style="dim", no_wrap=True)
    for question_id, entry in sorted(entries.items()):
        question = by_id.get(question_id)
        table.add_row(
            question_id,
            question.track if question else "[red]нет в банке[/]",
            question.question if question else "—",
            str(len(entry.get("points") or [])),
            (entry.get("updated") or "")[:10],
        )
    console.print(table)


def show_history(conn) -> None:
    rows = store.history(conn)
    if not rows:
        console.print("[dim]Журнал пуст — пройди первый вопрос.[/]")
        return
    table = Table(title=f"Последние сессии ({len(rows)})", header_style="bold")
    table.add_column("когда", style="dim", no_wrap=True)
    table.add_column("id", style="cyan", no_wrap=True)
    table.add_column("track", style="green", no_wrap=True)
    table.add_column("режим", no_wrap=True)
    table.add_column("оценка", justify="right")
    table.add_column("уточн.", justify="right", style="dim")
    for row in rows:
        score = (
            f"{row['score_first']}→{row['score_final']}"
            if row["mode"] == "mock" and row["score_first"] != row["score_final"]
            else str(row["score_final"])
        )
        table.add_row(
            row["ts"][:16].replace("T", " "),
            row["question_id"],
            row["track"] or "—",
            row["mode"],
            score,
            str(row["followups"]),
        )
    console.print(table)


def show_weak(conn, by_id: dict[str, Question]) -> None:
    topics = store.weak_topics(conn)
    if not topics:
        console.print("[dim]Журнал пуст — слабые места появятся после первых сессий.[/]")
        return

    table = Table(title="Слабые темы (средняя оценка, хуже — выше)", header_style="bold")
    table.add_column("track", style="green", no_wrap=True)
    table.add_column("topic", style="magenta")
    table.add_column("попыток", justify="right")
    table.add_column("средняя", justify="right")
    for row in topics:
        style = "bold red" if row["avg_score"] < 5 else ("yellow" if row["avg_score"] < 8 else "dim")
        table.add_row(
            row["track"] or "—",
            row["topic"] or "—",
            str(row["attempts"]),
            Text(str(row["avg_score"]), style=style),
        )
    console.print(table)

    questions = store.weak_questions(conn)
    if questions:
        table = Table(title="Вопросы на повторение (последняя попытка < 8)", header_style="bold")
        table.add_column("id", style="cyan", no_wrap=True)
        table.add_column("вопрос")
        table.add_column("оценка", justify="right")
        table.add_column("нераскрытые пункты", style="dim")
        for row in questions:
            question = by_id.get(row["question_id"])
            missed = ", ".join(json.loads(row["missed_points"])[:2])
            table.add_row(
                row["question_id"],
                question.question if question else "—",
                str(row["score_final"]),
                missed + ("…" if len(json.loads(row["missed_points"])) > 2 else ""),
            )
        console.print(table)
        console.print("[dim]Прогнать очередь: python run.py --review[/]")


def ask_yes_no(prompt: str, *, default_yes: bool = True) -> bool:
    try:
        answer = input(f"{prompt} {'[Y/n]' if default_yes else '[y/N]'} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print()
        return False
    if not answer:
        return default_yes
    return answer in ("y", "yes", "д", "да")


if __name__ == "__main__":
    sys.exit(main())
