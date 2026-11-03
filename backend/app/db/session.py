import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

# On Vercel each function instance may be frozen or discarded between
# requests, so pooled connections go stale and many instances would exhaust
# Postgres. Connections go through Supabase's pooler instead (port 6543), and
# SQLAlchemy keeps none of its own.
_serverless = bool(os.environ.get("VERCEL"))

engine = (
    create_engine(settings.database_url, poolclass=NullPool)
    if _serverless
    else create_engine(settings.database_url, pool_pre_ping=True)
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
