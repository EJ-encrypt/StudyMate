"""A Postgres-backed job queue that needs no worker process.

Replaces RQ + Redis, which assumed a machine that stays on. On Vercel every
request is a short-lived function, so jobs are rows in `jobs` and are run by
whichever request reaches them first:

* straight after an upload or a "generate" click, the browser calls
  POST /jobs/run, which works through that student's queued jobs;
* every minute the scheduler calls POST /cron/tick, which sweeps up anything
  left over (the browser was closed, a function timed out, and so on).

Claiming uses SELECT ... FOR UPDATE SKIP LOCKED plus a lease, so two runners
never take the same job, and a job whose runner died is picked up again once
its lease runs out rather than staying "processing" for good.
"""

import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.assessment import Assessment, AssessmentStatus
from app.models.document import DocumentStatus, LectureDocument
from app.models.job import Job

logger = logging.getLogger(__name__)

# Comfortably longer than one job takes, and longer than Vercel's 300s
# function limit, so a lease only expires when its runner is really gone.
LEASE = timedelta(minutes=6)
# A job that keeps killing its runner (e.g. always exceeds the time limit) is
# given up on rather than retried forever.
MAX_ATTEMPTS = 3

PROCESS_DOCUMENT = "process_document"
PROCESS_ASSESSMENT = "process_assessment"
REFRESH_COURSE_SUMMARY = "refresh_course_summary"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def enqueue(db: Session, kind: str, payload: dict, student_id: uuid.UUID | None) -> Job:
    """Add a job. The caller's commit makes it visible to runners."""
    job = Job(kind=kind, payload=payload, student_id=student_id)
    db.add(job)
    db.flush()
    return job


def _handlers() -> dict[str, Callable[..., None]]:
    # Imported lazily: the handlers pull in the AI SDKs, which a request that
    # finds nothing to do should not pay for.
    from app.workers.extraction_worker import process_document, refresh_summary
    from app.workers.generation_worker import process_assessment

    return {
        PROCESS_DOCUMENT: process_document,
        PROCESS_ASSESSMENT: process_assessment,
        REFRESH_COURSE_SUMMARY: refresh_summary,
    }


_GIVE_UP_MESSAGE = (
    "Processing took too long and was stopped. Nothing is lost - try again, "
    "or split a very large file into smaller ones."
)


def _give_up(db: Session, job: Job) -> None:
    """Mark the job's subject as failed, so the student is not left waiting."""
    if job.kind == PROCESS_DOCUMENT:
        document = db.get(LectureDocument, uuid.UUID(job.payload["document_id"]))
        if document is not None and document.status is not DocumentStatus.COMPLETED:
            document.status = DocumentStatus.FAILED
            document.error_message = _GIVE_UP_MESSAGE
            document.can_retry = True
    elif job.kind == PROCESS_ASSESSMENT:
        assessment = db.get(Assessment, uuid.UUID(job.payload["assessment_id"]))
        if assessment is not None and assessment.status is not AssessmentStatus.COMPLETED:
            assessment.status = AssessmentStatus.FAILED
            assessment.error_message = _GIVE_UP_MESSAGE
            assessment.can_retry = True


def claim_next(db: Session, student_id: uuid.UUID | None = None) -> Job | None:
    """Take the oldest runnable job, or None when there is nothing to do."""
    while True:
        now = _now()
        query = (
            select(Job)
            .where(
                or_(
                    Job.status == "queued",
                    and_(Job.status == "running", Job.locked_until < now),
                )
            )
            .order_by(Job.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if student_id is not None:
            query = query.where(Job.student_id == student_id)

        job = db.execute(query).scalar_one_or_none()
        if job is None:
            db.commit()
            return None

        if job.attempts >= MAX_ATTEMPTS:
            job.status = "failed"
            job.last_error = job.last_error or "Gave up after repeated interrupted runs"
            _give_up(db, job)
            db.commit()
            continue

        job.status = "running"
        job.attempts += 1
        job.locked_until = now + LEASE
        db.commit()
        return job


def run_job(db: Session, job: Job) -> None:
    handler = _handlers().get(job.kind)
    started = time.monotonic()
    logger.info("Job %s (%s) starting, attempt %s", job.id, job.kind, job.attempts)
    try:
        if handler is None:
            raise ValueError(f"Unknown job kind {job.kind!r}")
        handler(**job.payload)
    except Exception as exc:  # noqa: BLE001 -- recorded on the job; retried by a later runner
        logger.exception("Job %s (%s) failed", job.id, job.kind)
        job.last_error = str(exc)[:2000]
        job.locked_until = None
        if job.attempts >= MAX_ATTEMPTS:
            job.status = "failed"
            _give_up(db, job)
        else:
            job.status = "queued"
    else:
        job.status = "done"
        job.locked_until = None
        logger.info("Job %s (%s) done in %.1fs", job.id, job.kind, time.monotonic() - started)
    db.commit()


def run_pending(
    student_id: uuid.UUID | None = None,
    budget_seconds: float = 240.0,
    session_factory: Callable[[], Session] = SessionLocal,
) -> int:
    """Run queued jobs until there are none left or the time budget is spent.

    The budget leaves headroom under the hosting time limit, so a runner stops
    taking new work before it would be killed mid-job.
    """
    started = time.monotonic()
    ran = 0
    while time.monotonic() - started < budget_seconds:
        db = session_factory()
        try:
            job = claim_next(db, student_id)
            if job is None:
                break
            run_job(db, job)
            ran += 1
        finally:
            db.close()
    return ran
