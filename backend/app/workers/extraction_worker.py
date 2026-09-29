import logging
import uuid

from app.db.session import SessionLocal
from app.models.document import DocumentStatus, KnowledgeConcept, LectureDocument
from app.services.ai import get_ai_provider
from app.services.extraction import extract_text
from app.services.failures import describe
from app.services.gamification import record_document_processed
from app.services.knowledge_base import sync_document_concepts
from app.services.course_summary import refresh_course_summary

logger = logging.getLogger(__name__)


def process_document(document_id: str) -> None:
    db = SessionLocal()
    try:
        document = db.get(LectureDocument, uuid.UUID(document_id))
        if document is None:
            return

        document.status = DocumentStatus.PROCESSING
        db.commit()

        try:
            text = extract_text(document.storage_path)
            if not text.strip():
                raise ValueError("No readable text found in this document")
            concepts = get_ai_provider().extract_concepts(text)
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

        record_document_processed(db, document.student_id)

        document.status = DocumentStatus.COMPLETED
        db.commit()

        # After completion, unlike the knowledge-base sync above: the overview
        # covers every finished document in the course, so it waits until this
        # one counts as finished. On a multi-file upload that means only the
        # last file to land pays for it. Also non-fatal -- a stale overview is
        # worth far less than the material itself, which is already saved.
        try:
            refresh_course_summary(db, document.student_id, document.course_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Course summary refresh failed for %s: %s", document.course_id, exc)
    finally:
        db.close()
