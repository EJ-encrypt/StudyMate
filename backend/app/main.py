import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import (
    assessments,
    auth,
    coach,
    courses,
    documents,
    games,
    notifications,
    profile,
    schedule,
    social,
)
from app.core.config import settings

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
app.include_router(documents.storage_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
