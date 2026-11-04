import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.assessment import AssessmentItemRead
from app.schemas.review import CourseDueRead, DueCards, ReviewCreate, ReviewRead
from app.services import review

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


@router.get("/due", response_model=DueCards)
def due_cards(
    course_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DueCards:
    """Cards due for another look, answers included, as for any flashcard set."""
    items = review.due_items(db, current_user.id, course_id)
    return DueCards(items=[AssessmentItemRead.model_validate(item, from_attributes=True) for item in items])


@router.get("/due/courses", response_model=list[CourseDueRead])
def due_per_course(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[CourseDueRead]:
    return [CourseDueRead(**entry.__dict__) for entry in review.due_by_course(db, current_user.id)]


@router.post("/{item_id}/review", response_model=ReviewRead)
def review_card(
    item_id: uuid.UUID,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewRead:
    if review.own_flashcard(db, current_user.id, item_id) is None:
        raise HTTPException(status_code=404, detail="Card not found")
    row = review.record(db, current_user.id, item_id, payload.remembered)
    db.commit()
    return ReviewRead(item_id=item_id, box=row.box, due_at=row.due_at)
