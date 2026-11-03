"""Vercel entry point for the StudyMate API.

Vercel serves every request under /api/* from this one Python function (see
vercel.json). The FastAPI app itself defines its routes without the prefix,
as it always has, so it is mounted under /api here rather than rewritten.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from fastapi import FastAPI  # noqa: E402

from app.main import app as studymate  # noqa: E402

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", studymate)
