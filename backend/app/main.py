from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routers import assessments, auth, coach, courses, documents, profile
from app.core.config import DEFAULT_JWT_SECRET, settings

if settings.is_production and settings.jwt_secret == DEFAULT_JWT_SECRET:
    # Anyone who knows the placeholder could mint tokens for any account, so
    # this refuses to start rather than warning into a log nobody reads.
    raise RuntimeError(
        "JWT_SECRET is still the example value. Set a real secret before "
        "running with ENVIRONMENT=production, e.g. "
        "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Serving the built frontend from the API makes the whole app one origin, so
# it works behind a single URL (a tunnel, or any single host) with no CORS and
# no separate frontend deployment. Absent in development, where Vite serves it.
_FRONTEND_DIR = Path(settings.frontend_dist)

if _FRONTEND_DIR.is_dir():
    app.mount(
        "/assets", StaticFiles(directory=_FRONTEND_DIR / "assets"), name="assets"
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str) -> FileResponse:
        """Hand every unmatched path to the single-page app.

        Registered last, so real API routes above still win. A client-side
        route such as /materials must return index.html rather than a 404,
        or refreshing the page in the browser breaks.
        """
        candidate = _FRONTEND_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIR / "index.html")
