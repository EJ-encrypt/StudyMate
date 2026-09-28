import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.assessment import (
    Assessment,
    AssessmentItem,
    AssessmentStatus,
    Attempt,
    AttemptAnswer,
    ItemKind,
)
from app.models.document import DocumentStatus, LectureDocument
from app.models.user import User
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentDetail,
    AssessmentItemRead,
    AssessmentRead,
    AttemptCreate,
    AttemptResult,
    GradedAnswer,
)
from app.services.grading import is_correct
from app.workers.generation_worker import process_assessment
from app.workers.queue import queue

router = APIRouter(prefix="/assessments", tags=["assessments"])

_KIND_TITLES = {
    "flashcard": "Flashcards",
    "mcq": "Multiple choice",
    "fill_blank": "Fill in the blank",
}


def _own_assessment(db: Session, assessment_id: uuid.UUID, current_user: User) -> Assessment:
    assessment = db.get(Assessment, assessment_id)
    if assessment is None or assessment.student_id != current_user.id:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


@router.post("", response_model=AssessmentRead, status_code=status.HTTP_201_CREATED)
def create_assessment(
    payload: AssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Assessment:
    document = db.get(LectureDocument, payload.document_id)
    if document is None or document.student_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status is not DocumentStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail="This document is still being processed; try again once it has finished.",
        )

    assessment = Assessment(
        student_id=current_user.id,
        course_id=document.course_id,
        document_id=document.id,
        title=f"{_KIND_TITLES[payload.kind.value]} - {document.filename}",
        kind=payload.kind,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    queue.enqueue(process_assessment, str(assessment.id), payload.count)
    return assessment


@router.get("", response_model=list[AssessmentRead])
def list_assessments(
    course_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Assessment]:
    query = db.query(Assessment).filter(Assessment.student_id == current_user.id)
    if course_id is not None:
        query = query.filter(Assessment.course_id == course_id)
    if document_id is not None:
        query = query.filter(Assessment.document_id == document_id)
    return query.order_by(Assessment.created_at.desc()).all()


@router.get("/{assessment_id}", response_model=AssessmentDetail)
def get_assessment(
    assessment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentDetail:
    assessment = _own_assessment(db, assessment_id, current_user)
    reveal = assessment.kind is ItemKind.FLASHCARD

    return AssessmentDetail(
        id=assessment.id,
        course_id=assessment.course_id,
        document_id=assessment.document_id,
        title=assessment.title,
        kind=assessment.kind,
        status=assessment.status,
        error_message=assessment.error_message,
        created_at=assessment.created_at,
        items=[
            AssessmentItemRead(
                id=item.id,
                position=item.position,
                kind=item.kind,
                question=item.question,
                options=item.options,
                answer=item.answer if reveal else None,
                explanation=item.explanation if reveal else None,
            )
            for item in assessment.items
        ],
    )


@router.post("/{assessment_id}/attempts", response_model=AttemptResult, status_code=status.HTTP_201_CREATED)
def submit_attempt(
    assessment_id: uuid.UUID,
    payload: AttemptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttemptResult:
    assessment = _own_assessment(db, assessment_id, current_user)
    if assessment.status is not AssessmentStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="This assessment is not ready yet")

    items = {item.id: item for item in assessment.items}
    unknown = [str(a.item_id) for a in payload.answers if a.item_id not in items]
    if unknown:
        raise HTTPException(
            status_code=400, detail=f"These items do not belong to this assessment: {', '.join(unknown)}"
        )

    graded: list[GradedAnswer] = []
    for submission in payload.answers:
        item: AssessmentItem = items[submission.item_id]
        correct = is_correct(item.kind, item.answer, submission.response)
        graded.append(
            GradedAnswer(
                item_id=item.id,
                response=submission.response,
                is_correct=correct,
                correct_answer=item.answer,
                explanation=item.explanation,
            )
        )

    attempt = Attempt(
        assessment_id=assessment.id,
        student_id=current_user.id,
        correct_count=sum(1 for answer in graded if answer.is_correct),
        total_count=len(graded),
    )
    db.add(attempt)
    db.flush()
    for answer in graded:
        db.add(
            AttemptAnswer(
                attempt_id=attempt.id,
                item_id=answer.item_id,
                response=answer.response,
                is_correct=answer.is_correct,
            )
        )
    db.commit()
    db.refresh(attempt)

    return AttemptResult(
        id=attempt.id,
        assessment_id=assessment.id,
        correct_count=attempt.correct_count,
        total_count=attempt.total_count,
        answers=graded,
    )
