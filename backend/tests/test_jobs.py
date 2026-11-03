import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.course import Course
from app.models.document import DocumentStatus, LectureDocument
from app.models.job import Job
from app.models.user import User
from app.workers import jobs
from tests.conftest import TestSessionLocal
from tests.helpers import auth_headers


def _student(db: Session, email: str = "jobs@example.com") -> User:
    user = User(id=uuid.uuid4(), email=email, full_name="Job Tester")
    db.add(user)
    db.commit()
    return user


def _run(**kwargs) -> int:
    return jobs.run_pending(session_factory=TestSessionLocal, **kwargs)


def test_runs_queued_jobs_and_marks_them_done(db: Session) -> None:
    student = _student(db)
    jobs.enqueue(db, "fake", {"value": 1}, student.id)
    jobs.enqueue(db, "fake", {"value": 2}, student.id)
    db.commit()

    handler = MagicMock()
    with patch.object(jobs, "_handlers", return_value={"fake": handler}):
        assert _run() == 2

    assert [c.kwargs for c in handler.call_args_list] == [{"value": 1}, {"value": 2}]
    db.expire_all()
    assert {job.status for job in db.query(Job).all()} == {"done"}


def test_only_runs_the_callers_own_jobs(db: Session) -> None:
    mine, theirs = _student(db, "mine@example.com"), _student(db, "theirs@example.com")
    jobs.enqueue(db, "fake", {"who": "mine"}, mine.id)
    jobs.enqueue(db, "fake", {"who": "theirs"}, theirs.id)
    db.commit()

    handler = MagicMock()
    with patch.object(jobs, "_handlers", return_value={"fake": handler}):
        assert _run(student_id=mine.id) == 1
    handler.assert_called_once_with(who="mine")


def test_a_failing_job_is_requeued_then_given_up_on(db: Session) -> None:
    student = _student(db)
    course = Course(name="OS", code="CS305", owner_id=student.id)
    db.add(course)
    db.flush()
    document = LectureDocument(
        student_id=student.id, course_id=course.id, filename="a.pdf", storage_path="a.pdf",
        status=DocumentStatus.PROCESSING,
    )
    db.add(document)
    db.flush()
    jobs.enqueue(db, jobs.PROCESS_DOCUMENT, {"document_id": str(document.id)}, student.id)
    db.commit()

    boom = MagicMock(side_effect=RuntimeError("crashed"))
    with patch.object(jobs, "_handlers", return_value={jobs.PROCESS_DOCUMENT: boom}):
        _run()

    assert boom.call_count == jobs.MAX_ATTEMPTS
    db.expire_all()
    job = db.query(Job).one()
    assert job.status == "failed"
    assert "crashed" in job.last_error
    # The student is told, instead of watching "Reading..." forever.
    refreshed = db.get(LectureDocument, document.id)
    assert refreshed.status is DocumentStatus.FAILED
    assert refreshed.can_retry is True


def test_a_job_whose_runner_died_is_picked_up_after_its_lease(db: Session) -> None:
    student = _student(db)
    job = jobs.enqueue(db, "fake", {}, student.id)
    job.status = "running"
    job.attempts = 1
    job.locked_until = datetime.now(timezone.utc) + timedelta(minutes=5)
    db.commit()

    handler = MagicMock()
    with patch.object(jobs, "_handlers", return_value={"fake": handler}):
        assert _run() == 0, "still leased to a live runner"

        job.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
        assert _run() == 1
    handler.assert_called_once()


def test_run_endpoint_requires_sign_in(client: TestClient) -> None:
    assert client.post("/jobs/run").status_code == 401


def test_run_endpoint_runs_the_students_jobs(client: TestClient) -> None:
    headers = auth_headers("kick@example.com")
    with patch("app.api.routers.notifications.run_pending", return_value=2) as run:
        response = client.post("/jobs/run", headers=headers)
    assert response.json() == {"ran": 2}
    me = client.get("/auth/me", headers=headers).json()
    assert run.call_args.kwargs["student_id"] == uuid.UUID(me["id"])


def test_cron_tick_requires_the_secret(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "cron_secret", "s3cret")
    assert client.post("/cron/tick").status_code == 401
    assert client.post("/cron/tick", headers={"Authorization": "Bearer wrong"}).status_code == 401

    with patch("app.api.routers.notifications.send_due", return_value=1), patch(
        "app.api.routers.notifications.run_pending", return_value=0
    ):
        response = client.post("/cron/tick", headers={"Authorization": "Bearer s3cret"})
    assert response.status_code == 200
    assert response.json() == {"reminders": 1, "jobs": 0}


def test_cron_tick_is_closed_when_no_secret_is_configured(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "cron_secret", "")
    assert client.post("/cron/tick", headers={"Authorization": "Bearer "}).status_code == 401
