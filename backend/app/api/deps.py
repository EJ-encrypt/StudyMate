import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


def _provision(db: Session, user_id: uuid.UUID, claims: dict) -> User:
    """Create the StudyMate profile the first time a Supabase user calls the API.

    The account itself lives in Supabase Auth; this row holds what StudyMate
    adds to it (academic profile, preferences) and is what every other table
    references. Its id is the Supabase user id, so no mapping table is needed.
    """
    metadata = claims.get("user_metadata") or {}
    email = claims.get("email") or metadata.get("email") or f"{user_id}@users.invalid"
    full_name = (metadata.get("full_name") or metadata.get("name") or email.split("@")[0]).strip()

    user = User(id=user_id, email=email, full_name=full_name[:255] or "Student")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Two first requests raced (the app fires several on load); the other
        # one created the row, so use it.
        db.rollback()
        existing = db.get(User, user_id)
        if existing is None:
            raise
        return existing
    db.refresh(user)
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_error

    claims = decode_access_token(credentials.credentials)
    if claims is None:
        raise credentials_error

    try:
        user_id = uuid.UUID(str(claims.get("sub")))
    except ValueError:
        raise credentials_error

    user = db.get(User, user_id)
    if user is None:
        user = _provision(db, user_id, claims)
    return user
