"""SQLite memory: sessions, weak spots and the repetition queue (v1).

One row per finished quiz or mock session. Pure logic (intervals, aggregation)
is separated from I/O so it can be unit-tested without a database.
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from core.bank import Question
from core.grader import COVERED, MISSED, PARTIAL, Grade

DEFAULT_PATH = Path("data/sessions.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id            INTEGER PRIMARY KEY,
    ts            TEXT NOT NULL,
    question_id   TEXT NOT NULL,
    track         TEXT,
    topic         TEXT,
    mode          TEXT NOT NULL,
    model         TEXT,
    score_first   INTEGER NOT NULL,
    score_final   INTEGER NOT NULL,
    covered       INTEGER NOT NULL,
    partial       INTEGER NOT NULL,
    missed        INTEGER NOT NULL,
    missed_points TEXT NOT NULL,
    followups     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_sessions_question ON sessions (question_id, ts);
"""

# Review intervals by final score: fail — tomorrow, shaky — in 3 days, solid — in a week.
_INTERVALS = ((8, 7), (5, 3), (0, 1))


def connect(path: str | Path = DEFAULT_PATH) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def save(
    conn: sqlite3.Connection,
    *,
    question: Question,
    mode: str,
    first: Grade,
    final: Grade,
    followups: int,
    model: str | None = None,
    ts: str | None = None,
) -> None:
    missed_points = [p.point for p in final.points if p.status != COVERED]
    conn.execute(
        "INSERT INTO sessions (ts, question_id, track, topic, mode, model, score_first,"
        " score_final, covered, partial, missed, missed_points, followups)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ts or dt.datetime.now().isoformat(timespec="seconds"),
            question.id,
            question.track,
            question.topic,
            mode,
            model,
            first.score,
            final.score,
            final.count(COVERED),
            final.count(PARTIAL),
            final.count(MISSED),
            json.dumps(missed_points, ensure_ascii=False),
            followups,
        ),
    )
    conn.commit()


def history(conn: sqlite3.Connection, limit: int = 20) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM sessions ORDER BY ts DESC, id DESC LIMIT ?", (limit,)
    ).fetchall()


def weak_topics(conn: sqlite3.Connection, limit: int = 15) -> list[sqlite3.Row]:
    """Topics ranked by average final score, worst first."""
    return conn.execute(
        "SELECT track, topic, COUNT(*) AS attempts, ROUND(AVG(score_final), 1) AS avg_score,"
        " MAX(ts) AS last_ts FROM sessions GROUP BY track, topic"
        " ORDER BY avg_score ASC, attempts DESC LIMIT ?",
        (limit,),
    ).fetchall()


def weak_questions(conn: sqlite3.Connection, limit: int = 15) -> list[sqlite3.Row]:
    """Questions whose latest attempt scored worst."""
    return conn.execute(
        "SELECT question_id, track, topic, score_final, missed_points, ts FROM sessions"
        " WHERE id IN (SELECT MAX(id) FROM sessions GROUP BY question_id)"
        " AND score_final < 8 ORDER BY score_final ASC, ts ASC LIMIT ?",
        (limit,),
    ).fetchall()


def review_interval_days(score: int) -> int:
    for threshold, days in _INTERVALS:
        if score >= threshold:
            return days
    return 1


@dataclass
class DueItem:
    question_id: str
    score: int
    last_ts: str
    due: str  # ISO date when the question is due again


def due_items(
    conn: sqlite3.Connection, now: dt.datetime | None = None
) -> list[DueItem]:
    """The repetition queue: latest attempt per question, overdue first."""
    now = now or dt.datetime.now()
    rows = conn.execute(
        "SELECT question_id, score_final, ts FROM sessions"
        " WHERE id IN (SELECT MAX(id) FROM sessions GROUP BY question_id)"
    ).fetchall()
    items = []
    for row in rows:
        last = dt.datetime.fromisoformat(row["ts"])
        due = last + dt.timedelta(days=review_interval_days(row["score_final"]))
        if due <= now:
            items.append(
                DueItem(
                    question_id=row["question_id"],
                    score=row["score_final"],
                    last_ts=row["ts"],
                    due=due.date().isoformat(),
                )
            )
    items.sort(key=lambda item: (item.due, item.score))
    return items
