import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401 -- registers all models on Base.metadata
from app.api.deps import get_current_user
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.storage import get_storage
from tests.helpers import TEST_JWT_SECRET

# Tokens are verified exactly as in production, against a test secret, and
# files go to a temporary folder rather than Supabase Storage.
settings.supabase_jwt_secret = TEST_JWT_SECRET
settings.supabase_url = ""
settings.supabase_service_role_key = ""
get_storage.cache_clear()

# Tests run against a dedicated <dbname>_test database: the fixtures below
# truncate between tests and drop every table at the end, which would
# otherwise destroy the schema of the database the app is running on.
_app_url = make_url(settings.database_url)
_test_url = _app_url.set(database=f"{_app_url.database}_test")


def _ensure_test_database() -> None:
    admin_engine = create_engine(_app_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                sa.text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": _test_url.database},
            ).scalar()
            if not exists:
                conn.execute(sa.text(f'CREATE DATABASE "{_test_url.database}"'))
    finally:
        admin_engine.dispose()


# create_engine does not connect, so tests that never touch the database
# (extraction, for one) still run without Postgres available.
engine = create_engine(_test_url)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def _create_schema():
    _ensure_test_database()
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db(_create_schema) -> Session:
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    yield tmp_path / "storage"


@pytest.fixture()
def client(db: Session) -> TestClient:
    def _get_db_override():
        yield db

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
