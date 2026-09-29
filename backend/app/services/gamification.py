"""XP, streaks and badges.

Deliberately deterministic and cheap: this runs inside the attempt-submission
request, so it must not add a model call or a slow query to something the
student is waiting on.
"""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.assessment import Assessment, AssessmentKind, Attempt
from app.models.document import CourseConcept, LectureDocument
from app.models.gamification import EarnedBadge, StudentProgress
from app.models.mastery import ConceptMastery
from app.services.coaching import STRONG_THRESHOLD, CONFIDENT_ATTEMPTS

XP_PER_CORRECT_ANSWER = 10
XP_PER_ATTEMPT = 5
XP_PER_DOCUMENT = 15


@dataclass(frozen=True)
class Badge:
    code: str
    name: str
    description: str


BADGES: tuple[Badge, ...] = (
    Badge("first_upload", "Getting Started", "Upload your first piece of lecture material."),
    Badge("first_quiz", "First Attempt", "Complete your first quiz."),
    Badge("perfect_score", "Flawless", "Score full marks on a quiz."),
    Badge("streak_3", "Three in a Row", "Study on three consecutive days."),
    Badge("streak_7", "Week Strong", "Study on seven consecutive days."),
    Badge("concept_mastered", "Concept Mastered", "Reach a strong rating on any concept."),
    Badge("ten_concepts", "Building a Library", "Collect ten concepts in one course."),
    Badge("exam_ready", "Exam Ready", "Complete a full exam paper."),
)

BADGES_BY_CODE = {badge.code: badge for badge in BADGES}


def _progress_for(db: Session, student_id: uuid.UUID) -> StudentProgress:
    progress = db.get(StudentProgress, student_id)
    if progress is None:
        progress = StudentProgress(student_id=student_id)
        db.add(progress)
        db.flush()
    return progress


def _award(db: Session, student_id: uuid.UUID, code: str, earned: list[Badge]) -> None:
    already = (
        db.query(EarnedBadge)
        .filter(EarnedBadge.student_id == student_id, EarnedBadge.code == code)
        .first()
    )
    if already is not None:
        return
    db.add(EarnedBadge(student_id=student_id, code=code))
    # Sessions run with autoflush off, so without this the badge stays pending
    # and the check above misses it next time, violating the unique constraint.
    db.flush()
    earned.append(BADGES_BY_CODE[code])


def _touch_streak(progress: StudentProgress, today: date) -> None:
    if progress.last_active_on == today:
        return
    if progress.last_active_on == today - timedelta(days=1):
        progress.current_streak += 1
    else:
        progress.current_streak = 1
    progress.last_active_on = today
    progress.longest_streak = max(progress.longest_streak, progress.current_streak)


def record_document_processed(db: Session, student_id: uuid.UUID) -> None:
    progress = _progress_for(db, student_id)
    progress.xp += XP_PER_DOCUMENT
    earned: list[Badge] = []
    _award(db, student_id, "first_upload", earned)


def record_attempt(
    db: Session,
    student_id: uuid.UUID,
    assessment: Assessment,
    correct_count: int,
    total_count: int,
    today: date | None = None,
) -> list[Badge]:
    """Update XP and streak for a submitted attempt, returning any new badges."""
    progress = _progress_for(db, student_id)
    progress.xp += XP_PER_ATTEMPT + correct_count * XP_PER_CORRECT_ANSWER
    _touch_streak(progress, today or date.today())

    earned: list[Badge] = []
    _award(db, student_id, "first_quiz", earned)

    if total_count > 0 and correct_count == total_count:
        _award(db, student_id, "perfect_score", earned)

    if assessment.kind is AssessmentKind.EXAM:
        _award(db, student_id, "exam_ready", earned)

    if progress.current_streak >= 3:
        _award(db, student_id, "streak_3", earned)
    if progress.current_streak >= 7:
        _award(db, student_id, "streak_7", earned)

    mastered = (
        db.query(ConceptMastery)
        .filter(
            ConceptMastery.student_id == student_id,
            ConceptMastery.score >= STRONG_THRESHOLD,
            ConceptMastery.attempts >= CONFIDENT_ATTEMPTS,
        )
        .first()
    )
    if mastered is not None:
        _award(db, student_id, "concept_mastered", earned)

    library = (
        db.query(CourseConcept.course_id, CourseConcept.id)
        .filter(CourseConcept.student_id == student_id)
        .all()
    )
    per_course: dict[uuid.UUID, int] = {}
    for course_id, _ in library:
        per_course[course_id] = per_course.get(course_id, 0) + 1
    if any(count >= 10 for count in per_course.values()):
        _award(db, student_id, "ten_concepts", earned)

    return earned


def summary(db: Session, student_id: uuid.UUID) -> dict:
    progress = _progress_for(db, student_id)
    earned = {
        badge.code: badge.earned_at
        for badge in db.query(EarnedBadge).filter(EarnedBadge.student_id == student_id).all()
    }
    documents = (
        db.query(LectureDocument).filter(LectureDocument.student_id == student_id).count()
    )
    attempts = db.query(Attempt).filter(Attempt.student_id == student_id).count()

    return {
        "xp": progress.xp,
        "current_streak": progress.current_streak,
        "longest_streak": progress.longest_streak,
        "last_active_on": progress.last_active_on,
        "documents": documents,
        "attempts": attempts,
        "badges": [
            {
                "code": badge.code,
                "name": badge.name,
                "description": badge.description,
                "earned_at": earned.get(badge.code),
            }
            for badge in BADGES
        ],
    }
