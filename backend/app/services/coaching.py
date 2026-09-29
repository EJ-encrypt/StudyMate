"""Per-concept mastery, weak-topic detection and revision recommendations.

Mastery is an exponential moving average of correctness rather than a plain
percentage, so a student who has since learned a topic is not held back by
early wrong answers, while a single lucky guess cannot mark a topic mastered
either. Recommendations are computed from that record rather than asked of a
model: the ranking is deterministic, instant, free, and explainable to the
student, which matters more here than prose.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.assessment import AssessmentItem
from app.models.document import CourseConcept
from app.models.mastery import ConceptMastery

# Weight given to the newest answer. 0.4 moves noticeably on each answer while
# still taking roughly three consistent answers to cross a band boundary.
LEARNING_RATE = 0.4

# Below this a concept counts as weak; at or above it counts as strong. A
# concept never answered has no score and is reported separately, because
# "not practised" is different from "practised badly".
WEAK_THRESHOLD = 0.5
STRONG_THRESHOLD = 0.8

# One answer is not evidence of mastery, however it went.
CONFIDENT_ATTEMPTS = 3


@dataclass
class ConceptProgress:
    concept_id: uuid.UUID
    name: str
    summary: str
    score: float | None
    attempts: int
    correct: int
    last_seen_at: datetime | None

    @property
    def status(self) -> str:
        if self.attempts == 0:
            return "unpractised"
        if self.score is not None and self.score < WEAK_THRESHOLD:
            return "weak"
        if self.attempts < CONFIDENT_ATTEMPTS:
            return "developing"
        if self.score is not None and self.score >= STRONG_THRESHOLD:
            return "strong"
        return "developing"


def record_answers(
    db: Session,
    student_id: uuid.UUID,
    course_id: uuid.UUID,
    graded: list[tuple[AssessmentItem, bool]],
) -> None:
    """Fold a submitted attempt's results into per-concept mastery.

    Items that could not be tied to a concept are skipped rather than
    guessed at: a wrong attribution would push the wrong topic's score.
    """
    for item, was_correct in graded:
        if item.course_concept_id is None:
            continue

        mastery = (
            db.query(ConceptMastery)
            .filter(
                ConceptMastery.student_id == student_id,
                ConceptMastery.course_concept_id == item.course_concept_id,
            )
            .first()
        )
        if mastery is None:
            mastery = ConceptMastery(
                student_id=student_id,
                course_id=course_id,
                course_concept_id=item.course_concept_id,
                # Seed with the first result rather than averaging against a
                # zero that was never observed.
                score=1.0 if was_correct else 0.0,
                attempts=1,
                correct=1 if was_correct else 0,
                last_seen_at=datetime.now(timezone.utc),
            )
            db.add(mastery)
            continue

        observation = 1.0 if was_correct else 0.0
        mastery.score = (1 - LEARNING_RATE) * mastery.score + LEARNING_RATE * observation
        mastery.attempts += 1
        mastery.correct += 1 if was_correct else 0
        mastery.last_seen_at = datetime.now(timezone.utc)


def course_progress(
    db: Session, student_id: uuid.UUID, course_id: uuid.UUID
) -> list[ConceptProgress]:
    """Every concept in the course with whatever is known about it so far."""
    rows = (
        db.query(CourseConcept, ConceptMastery)
        .outerjoin(
            ConceptMastery,
            (ConceptMastery.course_concept_id == CourseConcept.id)
            & (ConceptMastery.student_id == student_id),
        )
        .filter(CourseConcept.student_id == student_id, CourseConcept.course_id == course_id)
        .order_by(CourseConcept.created_at)
        .all()
    )

    return [
        ConceptProgress(
            concept_id=concept.id,
            name=concept.name,
            summary=concept.summary,
            score=mastery.score if mastery else None,
            attempts=mastery.attempts if mastery else 0,
            correct=mastery.correct if mastery else 0,
            last_seen_at=mastery.last_seen_at if mastery else None,
        )
        for concept, mastery in rows
    ]


def recommend(progress: list[ConceptProgress], limit: int = 5) -> list[ConceptProgress]:
    """Which concepts to revise next.

    Weak concepts come first, worst score first, because that is where
    practice pays most. Unpractised concepts follow, since an unknown is
    worth more attention than something already answered well. Concepts
    that are merely developing come last, and strong ones are not
    recommended at all.
    """

    def rank(item: ConceptProgress) -> tuple[int, float]:
        if item.status == "weak":
            return (0, item.score if item.score is not None else 0.0)
        if item.status == "unpractised":
            return (1, 0.0)
        if item.status == "developing":
            return (2, item.score if item.score is not None else 0.0)
        return (3, item.score if item.score is not None else 1.0)

    ranked = sorted((p for p in progress if p.status != "strong"), key=rank)
    return ranked[:limit]
