import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.schedule import PushSubscription
from app.models.user import User
from app.schemas.schedule import NotificationConfig, PushSubscriptionCreate, PushSubscriptionDelete
from app.services.notifications import Notification, notify
from app.services.reminders import send_due
from app.workers.jobs import run_pending

router = APIRouter(prefix="/notifications", tags=["notifications"])
jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])
cron_router = APIRouter(prefix="/cron", tags=["cron"])


@router.get("/config", response_model=NotificationConfig)
def notification_config() -> NotificationConfig:
    """What the browser needs to subscribe, and which channels are switched on."""
    return NotificationConfig(
        vapid_public_key=settings.vapid_public_key,
        push_available=settings.push_enabled,
        email_available=settings.email_enabled,
    )


@router.post("/subscriptions", status_code=status.HTTP_204_NO_CONTENT)
def subscribe(
    payload: PushSubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == payload.endpoint).first()
    if existing is None:
        db.add(PushSubscription(student_id=current_user.id, **payload.model_dump()))
    else:
        # The same browser, perhaps now signed in as someone else.
        existing.student_id = current_user.id
        existing.p256dh = payload.p256dh
        existing.auth = payload.auth
    db.commit()


@router.post("/subscriptions/remove", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe(
    payload: PushSubscriptionDelete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    db.query(PushSubscription).filter(
        PushSubscription.endpoint == payload.endpoint,
        PushSubscription.student_id == current_user.id,
    ).delete()
    db.commit()


@router.post("/test")
def send_test(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int | bool]:
    """Let a student check reminders reach them before relying on them."""
    return notify(
        db,
        current_user,
        Notification(
            title="Reminders are working",
            body="This is how StudyMate will remind you about lectures.",
            path="/schedule",
            tag="studymate-test",
        ),
    )


@jobs_router.post("/run")
def run_my_jobs(current_user: User = Depends(get_current_user)) -> dict[str, int]:
    """Process this student's queued uploads and generations now.

    Called by the browser right after it queues work, so material is read in
    seconds rather than waiting for the next scheduler sweep. Only the
    caller's own jobs run, so one student cannot spend another's time budget.
    """
    return {"ran": run_pending(student_id=current_user.id)}


def _require_cron_secret(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {settings.cron_secret}"
    if not settings.cron_secret or not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid cron secret")


@cron_router.post("/tick", dependencies=[Depends(_require_cron_secret)])
@cron_router.get("/tick", dependencies=[Depends(_require_cron_secret)])
def tick(db: Session = Depends(get_db)) -> dict[str, int]:
    """Called every minute by the scheduler (Supabase pg_cron).

    Reminders first, because they are time-critical and cheap; then a short
    sweep of any jobs nobody else picked up.
    """
    reminders = send_due(db)
    jobs = run_pending(budget_seconds=45)
    return {"reminders": reminders, "jobs": jobs}
