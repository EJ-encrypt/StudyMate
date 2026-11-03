import logging
import time
import uuid

from app.db.session import SessionLocal
from app.models.document import DocumentStatus, KnowledgeConcept, LectureDocument
from app.services.ai import get_ai_provider
from app.services.extraction import extract_text
from app.services.storage import local_copy
from app.workers.jobs import REFRESH_COURSE_SUMMARY, enqueue
from app.services.failures import describe
from app.services.gamification import record_document_processed
from app.services.knowledge_base import sync_document_concepts

logger = logging.getLogger(__name__)


def process_document(document_id: str) -> None:
    db = SessionLocal()
    try:
        document = db.get(LectureDocument, uuid.UUID(document_id))
        if document is None:
            return

        document.status = DocumentStatus.PROCESSING
        db.commit()
        started = time.monotonic()

        try:
            with local_copy(document.storage_path) as path:
                text = extract_text(path)
            if not text.strip():
                raise ValueError("No readable text found in this document")
            concepts = get_ai_provider().extract_concepts(text)
            logger.info("%s: %s concepts extracted at %.1fs", document.id, len(concepts), time.monotonic() - started)
        except Exception as exc:  # noqa: BLE001 -- surfaced to the student via document.error_message
            document.status = DocumentStatus.FAILED
            message, document.can_retry = describe(exc)
            document.error_message = message
            db.commit()
            return

        for concept in concepts:
            db.add(
                KnowledgeConcept(
                    document_id=document.id,
                    student_id=document.student_id,
                    course_id=document.course_id,
                    name=concept.name,
                    summary=concept.summary,
                )
            )
        db.commit()

        # Fold into the cumulative knowledge base *before* reporting completion:
        # otherwise the document reads as done while its concepts are still
        # being merged, and the course knowledge base looks incomplete.
        # Failure here is not fatal -- the document's own concepts are already
        # saved and usable -- so it only logs.
        try:
            sync_document_concepts(db, document.id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Knowledge-base sync failed for document %s: %s", document.id, exc)

        logger.info("%s: knowledge base synced at %.1fs", document.id, time.monotonic() - started)
        record_document_processed(db, document.student_id)

        document.status = DocumentStatus.COMPLETED
        db.commit()

        # After completion, unlike the knowledge-base sync above: the overview
        # covers every finished document in the course, so it waits until this
        # one counts as finished. A separate job rather than a call here, so a
        # slow model reply cannot push one function run past the hosting time
        # limit. Non-fatal either way -- a stale overview is worth far less than
        # the material itself, which is already saved.
        enqueue(
            db,
            REFRESH_COURSE_SUMMARY,
            {"student_id": str(document.student_id), "course_id": str(document.course_id)},
            document.student_id,
        )
        db.commit()
        logger.info("%s: done at %.1fs; course summary queued", document.id, time.monotonic() - started)
    finally:
        db.close()


def refresh_summary(student_id: str, course_id: str) -> None:
    """Job handler: rewrite a course overview after new material lands."""
    from app.services.course_summary import refresh_course_summary

    db = SessionLocal()
    try:
        refresh_course_summary(db, uuid.UUID(student_id), uuid.UUID(course_id))
    except Exception as exc:  # noqa: BLE001 -- a stale overview is not worth retrying for
        logger.warning("Course summary refresh failed for %s: %s", course_id, exc)
    finally:
        db.close()
