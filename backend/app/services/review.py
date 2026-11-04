"""Spaced repetition for flashcards, with Leitner boxes.

After turning a card over the student says whether they remembered it. A
remembered card moves up a box and comes back later each time; a forgotten
one drops to the first box and comes back tomorrow. Cards the student knows
stop taking up revision time, and the ones they keep missing keep coming
back until they stick.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.assessment import Assessment, AssessmentItem, ItemKind
from app.models.course import Course
from app.models.review import FlashcardReview

# Days until a card in each box is due again.
INTERVAL_DAYS = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}
TOP_BOX = max(INTERVAL_DAYS)
DUE_LIMIT = 50


def _now() -> datetime:
    return datetime.now(timezone.utc)


def record(db: Session, student_id: uuid.UUID, item_id: uuid.UUID, remembered: bool) -> FlashcardReview:
    """Move the card to its next box and set when it is due."""
    now = _now()
    review = db.get(FlashcardReview, (student_id, item_id))
    if review is None:
        # A new card the student already knows skips the first box.
        review = FlashcardReview(student_id=student_id, item_id=item_id, box=1, review_count=0)
        db.add(review)
        box = 2 if remembered else 1
    else:
        box = min(review.box + 1, TOP_BOX) if remembered else 1
    review.box = box
    review.due_at = now + timedelta(days=INTERVAL_DAYS[box])
    review.reviewed_at = now
    review.review_count = (review.review_count or 0) + 1
    return review


def own_flashcard(db: Session, student_id: uuid.UUID, item_id: uuid.UUID) -> AssessmentItem | None:
    return (
        db.query(AssessmentItem)
        .join(Assessment, Assessment.id == AssessmentItem.assessment_id)
        .filter(
            AssessmentItem.id == item_id,
            AssessmentItem.kind == ItemKind.FLASHCARD,
            Assessment.student_id == student_id,
        )
        .first()
    )


def due_items(db: Session, student_id: uuid.UUID, course_id: uuid.UUID | None = None) -> list[AssessmentItem]:
    """Cards seen before and due again, the most overdue first."""
    query = (
        db.query(AssessmentItem)
        .join(FlashcardReview, FlashcardReview.item_id == AssessmentItem.id)
        .join(Assessment, Assessment.id == AssessmentItem.assessment_id)
        .filter(FlashcardReview.student_id == student_id, FlashcardReview.due_at <= _now())
    )
    if course_id is not None:
        query = query.filter(Assessment.course_id == course_id)
    return query.order_by(FlashcardReview.due_at).limit(DUE_LIMIT).all()


@dataclass
class CourseDue:
    course_id: uuid.UUID
    code: str
    name: str
    due: int


def due_by_course(db: Session, student_id: uuid.UUID) -> list[CourseDue]:
    rows = (
        db.query(Course.id, Course.code, Course.name, func.count(FlashcardReview.item_id))
        .join(Assessment, Assessment.course_id == Course.id)
        .join(AssessmentItem, AssessmentItem.assessment_id == Assessment.id)
        .join(FlashcardReview, FlashcardReview.item_id == AssessmentItem.id)
        .filter(FlashcardReview.student_id == student_id, FlashcardReview.due_at <= _now())
        .group_by(Course.id, Course.code, Course.name)
        .all()
    )
    return sorted(
        (CourseDue(course_id=row[0], code=row[1], name=row[2], due=int(row[3])) for row in rows),
        key=lambda c: -c.due,
    )


def reviewed_since(db: Session, student_id: uuid.UUID, since: datetime) -> int:
    return (
        db.query(FlashcardReview)
        .filter(FlashcardReview.student_id == student_id, FlashcardReview.reviewed_at >= since)
        .count()
    )
