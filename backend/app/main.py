from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import assessments, auth, coach, courses, documents, profile
from app.core.config import settings

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
