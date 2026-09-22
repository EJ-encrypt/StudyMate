import uuid

from app.db.session import SessionLocal
from app.models.document import DocumentStatus, KnowledgeConcept, LectureDocument
from app.services.ai import get_ai_provider
from app.services.extraction.pdf import extract_text_from_pdf


def process_document(document_id: str) -> None:
    db = SessionLocal()
    try:
        document = db.get(LectureDocument, uuid.UUID(document_id))
        if document is None:
            return

        document.status = DocumentStatus.PROCESSING
        db.commit()

        try:
            text = extract_text_from_pdf(document.storage_path)
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
        document.status = DocumentStatus.COMPLETED
        db.commit()
    finally:
        db.close()
