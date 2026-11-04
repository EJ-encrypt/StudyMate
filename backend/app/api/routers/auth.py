from fastapi import APIRouter, Depends, HTTPException, status
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
    changes = payload.model_dump(exclude_unset=True)
    if "username" in changes:
        changes["username"] = changes["username"] or None
        taken = (
            changes["username"]
            and db.query(User.id)
            .filter(User.username == changes["username"], User.id != current_user.id)
            .first()
        )
        if taken:
            raise HTTPException(status_code=409, detail="That username is taken. Try another.")
    for field, value in changes.items():
        if value is None and field not in ("username",):
            # Explicit nulls for required settings are ignored rather than stored.
            continue
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete the account and everything in it: courses, files, quizzes, progress."""
    from app.services.accounts import delete_account

    delete_account(db, current_user)
