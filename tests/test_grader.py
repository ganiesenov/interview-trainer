from core.grader import COVERED, MISSED, PARTIAL, PointResult, align_points, build_grade, parse_json, score_points

import pytest

POINTS = ["K и V прошлых токенов не меняются", "память растёт линейно по длине"]


def test_parse_json_plain():
    assert parse_json('{"hedging": true}') == {"hedging": True}


def test_parse_json_strips_markdown_fence():
    raw = 'Вот результат:\n```json\n{"points": []}\n```'
    assert parse_json(raw) == {"points": []}


def test_parse_json_recovers_from_trailing_prose():
    raw = '{"points": [], "hedging": false}\nНадеюсь, это помогло.'
    assert parse_json(raw) == {"points": [], "hedging": False}


@pytest.mark.parametrize("raw", ["", "   ", "no json here", "{broken"])
def test_parse_json_rejects_garbage(raw):
    with pytest.raises(ValueError):
        parse_json(raw)


def test_align_points_matches_reworded_and_reordered_points():
    returned = [
        {"point": "память линейно растёт по длине", "status": "partial", "quote": "память"},
        {"point": "K и V прошлых токенов не пересчитываются", "status": "covered", "quote": "не меняются"},
    ]
    aligned = align_points(POINTS, returned)
    assert [point.status for point in aligned] == [COVERED, PARTIAL]
    assert aligned[0].quote == "не меняются"


def test_align_points_defaults_missing_and_unknown_statuses_to_missed():
    aligned = align_points(POINTS, [{"point": POINTS[0], "status": "отлично"}])
    assert [point.status for point in aligned] == [MISSED, MISSED]


def test_align_points_never_reuses_one_returned_point_twice():
    returned = [{"point": POINTS[0], "status": "covered", "quote": "q"}]
    aligned = align_points(POINTS, returned)
    assert aligned[0].status == COVERED
    assert aligned[1].status == MISSED


def test_align_points_survives_a_non_list_payload():
    assert [point.status for point in align_points(POINTS, None)] == [MISSED, MISSED]


@pytest.mark.parametrize(
    "statuses, expected",
    [
        ([COVERED, COVERED], 10),
        ([MISSED, MISSED], 1),  # floor is 1, not 0
        ([COVERED, MISSED], 5),
        ([PARTIAL, PARTIAL], 5),
        ([COVERED, PARTIAL, MISSED, MISSED], 4),
    ],
)
def test_score_is_computed_from_statuses(statuses, expected):
    points = [PointResult(point=str(i), status=status) for i, status in enumerate(statuses)]
    assert score_points(points) == expected


def test_build_grade_ignores_the_score_the_model_returned():
    payload = {
        "points": [{"point": POINTS[0], "status": "covered"}, {"point": POINTS[1], "status": "covered"}],
        "invented": ["  ", "кэш ускоряет обучение"],
        "hedging": "yes",
        "score": 2,
    }
    result = build_grade(POINTS, payload)
    assert result.score == 10
    assert result.invented == ["кэш ускоряет обучение"]
    assert result.hedging is True
