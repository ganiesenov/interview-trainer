"""SQLite session log: save/history, weak spots, repetition queue — no LLM involved."""

from __future__ import annotations

import datetime as dt
import json

import pytest

from core import store
from core.bank import Question
from core.grader import COVERED, MISSED, PARTIAL, Grade, PointResult, gaps, score_points


def q(qid="kv", track="LLM", topic="Инференс"):
    return Question(
        id=qid,
        track=track,
        topic=topic,
        question="?",
        key_points=["a", "b"],
        reference="ref",
    )


def g(statuses):
    points = [PointResult(point=f"p{i}", status=s) for i, s in enumerate(statuses)]
    return Grade(points=points, score=score_points(points))


@pytest.fixture
def conn():
    connection = store.connect(":memory:")
    yield connection
    connection.close()


def test_save_and_history(conn):
    first, final = g([MISSED, MISSED]), g([COVERED, PARTIAL])
    store.save(
        conn,
        question=q(),
        mode="mock",
        first=first,
        final=final,
        followups=2,
        model="m",
        ts="2026-07-30T10:00:00",
    )
    rows = store.history(conn)
    assert len(rows) == 1
    row = rows[0]
    assert row["question_id"] == "kv"
    assert row["mode"] == "mock"
    assert (row["score_first"], row["score_final"]) == (first.score, final.score)
    assert (row["covered"], row["partial"], row["missed"]) == (1, 1, 0)
    assert json.loads(row["missed_points"]) == ["p1"]
    assert row["followups"] == 2


def test_history_newest_first(conn):
    for i, ts in enumerate(["2026-07-01T10:00:00", "2026-07-02T10:00:00"]):
        store.save(
            conn, question=q(f"q{i}"), mode="quiz", first=g([COVERED]), final=g([COVERED]),
            followups=0, ts=ts,
        )
    assert [r["question_id"] for r in store.history(conn)] == ["q1", "q0"]


def test_weak_topics_orders_worst_first(conn):
    store.save(conn, question=q("a", topic="Инференс"), mode="quiz",
               first=g([COVERED, COVERED]), final=g([COVERED, COVERED]), followups=0)
    store.save(conn, question=q("b", topic="RAG"), mode="quiz",
               first=g([MISSED, MISSED]), final=g([MISSED, MISSED]), followups=0)
    rows = store.weak_topics(conn)
    assert rows[0]["topic"] == "RAG"
    assert rows[0]["avg_score"] < rows[1]["avg_score"]


def test_weak_questions_uses_latest_attempt(conn):
    # First attempt bad, second attempt good -> the question is no longer weak.
    store.save(conn, question=q("a"), mode="quiz", first=g([MISSED, MISSED]),
               final=g([MISSED, MISSED]), followups=0, ts="2026-07-01T10:00:00")
    store.save(conn, question=q("a"), mode="quiz", first=g([COVERED, COVERED]),
               final=g([COVERED, COVERED]), followups=0, ts="2026-07-02T10:00:00")
    assert store.weak_questions(conn) == []


def test_review_interval_bands():
    assert store.review_interval_days(10) == 7
    assert store.review_interval_days(8) == 7
    assert store.review_interval_days(7) == 3
    assert store.review_interval_days(5) == 3
    assert store.review_interval_days(4) == 1
    assert store.review_interval_days(1) == 1


def test_due_items_overdue_and_fresh(conn):
    now = dt.datetime(2026, 7, 30, 12, 0)
    # score 2 -> due next day: an attempt 3 days ago is overdue.
    store.save(conn, question=q("old"), mode="quiz", first=g([MISSED, MISSED]),
               final=g([MISSED, MISSED]), followups=0, ts="2026-07-27T12:00:00")
    # score 10 -> due in 7 days: an attempt yesterday is fresh.
    store.save(conn, question=q("fresh"), mode="quiz", first=g([COVERED, COVERED]),
               final=g([COVERED, COVERED]), followups=0, ts="2026-07-29T12:00:00")
    items = store.due_items(conn, now=now)
    assert [item.question_id for item in items] == ["old"]
    assert items[0].due == "2026-07-28"


def test_due_uses_latest_attempt_only(conn):
    now = dt.datetime(2026, 7, 30, 12, 0)
    store.save(conn, question=q("a"), mode="quiz", first=g([MISSED, MISSED]),
               final=g([MISSED, MISSED]), followups=0, ts="2026-07-20T12:00:00")
    store.save(conn, question=q("a"), mode="mock", first=g([COVERED, COVERED]),
               final=g([COVERED, COVERED]), followups=1, ts="2026-07-29T12:00:00")
    assert store.due_items(conn, now=now) == []


def test_gaps_lists_uncovered_points():
    result = g([COVERED, PARTIAL, MISSED])
    assert gaps(result) == ["p1", "p2"]
    assert gaps(g([COVERED])) == []
