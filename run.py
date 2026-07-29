#!/usr/bin/env python3
"""CLI entry point. v0: quiz mode — one question, one open answer, one breakdown."""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from core import prompts
from core.bank import BankError, Question, load_bank, pick
from core.grader import COVERED, MISSED, PARTIAL, Grade, grade
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

    if args.list:
        list_questions(questions)
        return 0

    profile = load_profile() if args.profile else ""
    asked: set[str] = set()

    while True:
        try:
            question = pick(questions, question_id=args.id, topic=args.topic, exclude=asked)
        except BankError as exc:
            console.print(f"[bold red]Ошибка банка:[/] {exc}")
            return 2
        asked.add(question.id)

        try:
            run_quiz(question, model=args.model, role=args.role, profile=profile)
        except LLMError as exc:
            console.print(f"\n[bold red]Модель недоступна:[/] {exc}")
            return 1
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Прервано.[/]")
            return 130

        if args.id or not ask_yes_no("Ещё вопрос?"):
            return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interview Trainer — v0, режим квиза")
    parser.add_argument("--bank", default="banks/theory.yaml", help="файл банка вопросов")
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
    return parser.parse_args(argv)


def list_questions(questions: list[Question]) -> None:
    table = Table(title=f"Банк: {len(questions)} вопрос(ов)", header_style="bold")
    table.add_column("id", style="cyan", no_wrap=True)
    table.add_column("topic", style="magenta", no_wrap=True)
    table.add_column("question")
    table.add_column("points", justify="right", style="dim")
    for question in questions:
        table.add_row(question.id, question.topic, question.question, str(len(question.key_points)))
    console.print(table)


def run_quiz(question: Question, *, model: str | None, role: str, profile: str) -> None:
    # max_followups is part of the engine from day one; the quiz just spends none.
    interviewer = Interviewer(
        question=question,
        role=role,
        profile=profile,
        max_followups=0,
        model=model,
    )

    console.print()
    console.print(
        Panel(
            Text(interviewer.ask(), style="bold"),
            title=f"[cyan]{question.id}[/] · [magenta]{question.topic or '—'}[/]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print("[dim]Отвечай своими словами. Пустая строка — закончить ответ.[/]\n")

    answer = read_answer()
    interviewer.record_answer(answer)

    with console.status("[dim]Сверяю с эталоном…[/]", spinner="dots"):
        result = grade(question, answer, model=model)

    render_grade(question, result)


def read_answer() -> str:
    lines: list[str] = []
    while True:
        try:
            line = input("> " if not lines else "  ")
        except EOFError:
            break
        if not line.strip():
            if lines:
                break
            continue
        lines.append(line)
    return "\n".join(lines)


def render_grade(question: Question, result: Grade) -> None:
    console.print()
    console.print(Rule("Разбор", style="dim"))

    table = Table(show_lines=True, header_style="bold", expand=True)
    table.add_column("Пункт эталона", ratio=3)
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


def ask_yes_no(prompt: str) -> bool:
    try:
        answer = input(f"{prompt} [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print()
        return False
    return answer in ("", "y", "yes", "д", "да")


if __name__ == "__main__":
    sys.exit(main())
