import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routers import (
    assessments,
    auth,
    coach,
    courses,
    documents,
    games,
    notifications,
    profile,
    review,
    schedule,
    social,
)
from app.core.config import settings
from app.db.session import get_db

if settings.is_production:
    # Refuse to start half-configured rather than failing on the first
    # student's request: without these, sign-in, uploads or the scheduler
    # silently do not work.
    missing = [
        name
        for name, value in (
            ("SUPABASE_URL", settings.supabase_url),
            ("SUPABASE_SERVICE_ROLE_KEY", settings.supabase_service_role_key),
            ("CRON_SECRET", settings.cron_secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required settings for production: {', '.join(missing)}")

# Warnings from the workers (a model falling back, a failed knowledge-base
# sync) are the main evidence when something goes wrong in production, and
# Vercel only shows what reaches stderr.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

if settings.sentry_dsn:
    # Crashes students hit are reported with their stack trace, so they can be
    # fixed before anyone has to describe them. Errors only, no performance
    # tracing, and no personal data: Sentry sees the account id, never the
    # email address or what was uploaded.
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        send_default_pii=False,
        traces_sample_rate=0.0,
    )

app = FastAPI(title="StudyMate AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(documents.router)
app.include_router(assessments.router)
app.include_router(coach.router)
app.include_router(profile.router)
app.include_router(schedule.router)
app.include_router(notifications.router)
app.include_router(notifications.jobs_router)
app.include_router(notifications.cron_router)
app.include_router(games.router)
app.include_router(social.router)
app.include_router(review.router)
app.include_router(documents.storage_router)


@app.get("/health")
def health(deep: bool = False, db: Session = Depends(get_db)) -> dict[str, str]:
    """Is the API up; with ?deep=1, can it also reach the database.

    The deep check is what the daily keep-alive (.github/workflows) calls:
    Supabase pauses a free project after a week without activity, which
    would take the app down until someone restores it by hand.
    """
    if not deep:
        # A session only connects when first used, so this costs nothing.
        return {"status": "ok"}
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
