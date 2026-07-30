"""The interviewer: asks the question and holds the follow-up counter.

Quiz and mock interview are the same engine — the only difference is
`max_followups` (0 for quiz, 3 for mock). v0 always passes 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from core import prompts
from core.bank import Question
from core.llm import QUESTION_TEMPERATURE, chat


@dataclass
class Interviewer:
    question: Question
    role: str = prompts.DEFAULT_ROLE
    profile: str = ""
    max_followups: int = 0
    model: str | None = None
    transcript: list[tuple[str, str]] = field(default_factory=list)
    _asked_followups: int = 0

    def ask(self) -> str:
        """The opening question — taken verbatim from the bank, never generated."""
        self.transcript.append(("interviewer", self.question.question))
        return self.question.question

    def record_answer(self, answer: str) -> None:
        self.transcript.append(("candidate", answer.strip()))

    @property
    def followups_left(self) -> int:
        return max(0, self.max_followups - self._asked_followups)

    def followup(self, gaps: list[str] | None = None) -> str | None:
        """Next probing question aimed at uncovered points, or None once the budget is spent."""
        if self.followups_left == 0:
            return None

        messages = [
            {
                "role": "system",
                "content": prompts.INTERVIEWER_SYSTEM.format(
                    role=self.role,
                    profile=self.profile or "—",
                    max_followups=self.max_followups,
                ),
            },
            {
                "role": "user",
                "content": prompts.FOLLOWUP_USER.format(
                    topic=self.question.topic or "—",
                    question=self.question.question,
                    key_points=prompts.numbered(self.question.key_points),
                    gaps=prompts.numbered(gaps or []),
                    transcript=prompts.render_transcript(self.transcript),
                ),
            },
        ]
        text = chat(
            messages,
            model=self.model,
            temperature=QUESTION_TEMPERATURE,
            num_predict=200,
        ).strip()
        if not text:
            return None

        self._asked_followups += 1
        self.transcript.append(("interviewer", text))
        return text


def load_profile(directory: str | Path = "profile") -> str:
    """Concatenate the candidate's profile files; missing files are fine."""
    directory = Path(directory)
    chunks = []
    for name in ("resume.md", "projects.md"):
        path = directory / name
        if path.exists():
            text = path.read_text(encoding="utf-8").strip()
            if text:
                chunks.append(text)
    return "\n\n---\n\n".join(chunks)
