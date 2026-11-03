from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import OnboardingUpdate, PreferencesUpdate, UserRead

# Sign-up, sign-in and password resets happen in the browser against Supabase
# Auth. These endpoints only read and update the StudyMate side of an account.
router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.put("/me/onboarding", response_model=UserRead)
def complete_onboarding(
    payload: OnboardingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    """Record the student's school, programme, level and semester.

    New courses default to the level and semester recorded here, so a student
    adding a course mid-semester does not have to restate it every time.
    """
    current_user.school = payload.school
    current_user.programme = payload.programme
    current_user.level = payload.level
    current_user.semester = payload.semester
    if payload.full_name:
        current_user.full_name = payload.full_name
    if payload.timezone:
        current_user.timezone = payload.timezone
    db.commit()
    db.refresh(current_user)
    return current_user


@router.patch("/me/preferences", response_model=UserRead)
def update_preferences(
    payload: PreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user
