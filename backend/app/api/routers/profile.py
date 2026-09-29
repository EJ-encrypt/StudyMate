from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.gamification import ProgressSummary
from app.services.gamification import summary

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/progress", response_model=ProgressSummary)
def my_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgressSummary:
    db.commit()
    return ProgressSummary(**summary(db, current_user.id))
