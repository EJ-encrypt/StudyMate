import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.course import Course
from app.models.user import User
from app.schemas.coach import CoachSummary, ConceptProgressRead
from app.services.coaching import course_progress, recommend

router = APIRouter(prefix="/coach", tags=["coach"])


def _as_read(progress) -> ConceptProgressRead:
    return ConceptProgressRead(
        concept_id=progress.concept_id,
        name=progress.name,
        summary=progress.summary,
        score=progress.score,
        attempts=progress.attempts,
        correct=progress.correct,
        status=progress.status,
        last_seen_at=progress.last_seen_at,
    )


@router.get("/{course_id}", response_model=CoachSummary)
def coach_summary(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CoachSummary:
    """Where the student stands in one course, and what to revise next."""
    course = db.get(Course, course_id)
    if course is None or course.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Course not found")

    progress = course_progress(db, current_user.id, course_id)
    by_status = {status: 0 for status in ("strong", "developing", "weak", "unpractised")}
    for item in progress:
        by_status[item.status] += 1

    practised = [p for p in progress if p.attempts > 0]
    overall = (
        sum(p.score for p in practised if p.score is not None) / len(practised)
        if practised
        else None
    )

    return CoachSummary(
        course_id=course_id,
        concept_count=len(progress),
        overall_mastery=overall,
        strong=by_status["strong"],
        developing=by_status["developing"],
        weak=by_status["weak"],
        unpractised=by_status["unpractised"],
        recommendations=[_as_read(p) for p in recommend(progress)],
        concepts=[_as_read(p) for p in progress],
    )
