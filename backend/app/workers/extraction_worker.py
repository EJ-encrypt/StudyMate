import logging
import uuid

from app.db.session import SessionLocal
from app.models.document import DocumentStatus, KnowledgeConcept, LectureDocument
from app.services.ai import get_ai_provider
from app.services.extraction import extract_text
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

        try:
            text = extract_text(document.storage_path)
            if not text.strip():
                raise ValueError("No readable text found in this document")
            concepts = get_ai_provider().extract_concepts(text)
        except Exception as exc:  # noqa: BLE001 -- surfaced to the student via document.error_message
            document.status = DocumentStatus.FAILED
            document.error_message = str(exc)
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

        document.status = DocumentStatus.COMPLETED
        db.commit()
    finally:
        db.close()
