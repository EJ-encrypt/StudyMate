import uuid
from datetime import datetime, timezone

import pytest

from app.services.coaching import (
    CONFIDENT_ATTEMPTS,
    LEARNING_RATE,
    ConceptProgress,
    recommend,
)


def _progress(name: str, score: float | None, attempts: int) -> ConceptProgress:
    return ConceptProgress(
        concept_id=uuid.uuid4(),
        name=name,
        summary="",
        score=score,
        attempts=attempts,
        correct=0,
        last_seen_at=datetime.now(timezone.utc) if attempts else None,
    )


def test_unanswered_concept_is_unpractised_not_weak() -> None:
    assert _progress("Deadlock", None, 0).status == "unpractised"


def test_low_score_is_weak() -> None:
    assert _progress("Deadlock", 0.2, 4).status == "weak"


def test_one_correct_answer_is_not_yet_mastery() -> None:
    """A single lucky answer should not mark a topic strong."""
    assert _progress("Deadlock", 1.0, 1).status == "developing"


def test_consistently_correct_becomes_strong() -> None:
    assert _progress("Deadlock", 0.95, CONFIDENT_ATTEMPTS).status == "strong"


def test_recommendations_put_weak_topics_first_then_unpractised() -> None:
    progress = [
        _progress("Strong", 0.95, 5),
        _progress("Unpractised", None, 0),
        _progress("Weakest", 0.1, 4),
        _progress("Developing", 0.7, 2),
        _progress("Weak", 0.35, 4),
    ]

    names = [p.name for p in recommend(progress)]

    assert names[:2] == ["Weakest", "Weak"], "worst scores first"
    assert names[2] == "Unpractised", "an unknown outranks something already answered well"
    assert "Strong" not in names, "mastered topics are not recommended"


def test_recommendations_are_capped() -> None:
    progress = [_progress(f"C{i}", 0.1, 3) for i in range(20)]
    assert len(recommend(progress, limit=5)) == 5


@pytest.mark.parametrize(
    ("start", "was_correct", "expected"),
    [
        (0.0, True, LEARNING_RATE),
        (1.0, False, 1 - LEARNING_RATE),
    ],
)
def test_moving_average_moves_towards_the_new_result(
    start: float, was_correct: bool, expected: float
) -> None:
    observation = 1.0 if was_correct else 0.0
    updated = (1 - LEARNING_RATE) * start + LEARNING_RATE * observation
    assert updated == pytest.approx(expected)


def test_repeated_correct_answers_recover_from_a_bad_start() -> None:
    """A student who learns the topic should climb out of 'weak'."""
    score = 0.0
    for _ in range(4):
        score = (1 - LEARNING_RATE) * score + LEARNING_RATE * 1.0
    assert score > 0.5, "four correct answers should clear the weak threshold"
