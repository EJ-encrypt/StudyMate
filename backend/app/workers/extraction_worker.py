import logging
import time
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.course import Course
from app.models.document import DocumentStatus, KnowledgeConcept, LectureDocument
from app.services.ai import get_ai_provider
from app.services.extraction import IMAGE_TYPES, extract_text, is_image
from app.services.extraction.pdf import pdf_page_count
from app.services.quantitative import has_garbled_text, is_quantitative_course, looks_mathematical
from app.services.storage import local_copy
from app.workers.jobs import REFRESH_COURSE_SUMMARY, enqueue
from app.services.failures import describe
from app.services.gamification import record_document_processed
from app.services.knowledge_base import sync_document_concepts

logger = logging.getLogger(__name__)

# Gemini takes at most 20MB in one request, and base64 adds a third; anything
# larger keeps its plain extracted text.
_MAX_TRANSCRIBE_BYTES = 14 * 1024 * 1024
# Below this many characters per page a PDF is treated as scanned: whatever
# text it has is page numbers and headers, not the content.
_SCANNED_CHARS_PER_PAGE = 80


def concept_budget(text: str) -> int:
    """How many concepts to ask for: more for a long deck, so its later topics count."""
    return max(10, min(20, len(text) // 3000))


def _transcribe(path: str, mime_type: str) -> str:
    data = Path(path).read_bytes()
    if len(data) > _MAX_TRANSCRIBE_BYTES:
        return ""
    return get_ai_provider().transcribe_document(data, mime_type)


def read_document(db: Session, document: LectureDocument) -> tuple[str, bool]:
    """The document's text, and whether it is quantitative.

    Plain extraction first, since it is instant and free. The AI transcribes
    instead when that text is missing (a photo, a scanned PDF), garbled (maths
    fonts), or from a quantitative course, where the equations are the point.
    A transcription that fails falls back to the plain text when there is any,
    so a busy model never costs a student an otherwise readable upload.

    Stored on the document, so a retry after a timeout - and every quiz
    generated later - reuses it rather than paying for it again.
    """
    course = db.get(Course, document.course_id)
    course_is_quantitative = bool(course and is_quantitative_course(course.code, course.name))

    if document.extracted_text:
        text = document.extracted_text
        return text, course_is_quantitative or looks_mathematical(text)

    with local_copy(document.storage_path) as path:
        text = extract_text(path)
        suffix = Path(path).suffix.lower()
        pages = pdf_page_count(path) if suffix == ".pdf" else 1
        quantitative = course_is_quantitative or looks_mathematical(text)

        needs_ai = is_image(path) or (
            suffix == ".pdf"
            and (quantitative or has_garbled_text(text) or len(text.strip()) < _SCANNED_CHARS_PER_PAGE * pages)
        )
        if needs_ai:
            mime_type = IMAGE_TYPES.get(suffix, "application/pdf")
            try:
                transcribed = _transcribe(path, mime_type)
            except Exception as exc:  # noqa: BLE001 -- plain text is the fallback
                if not text.strip():
                    raise
                logger.warning("%s: transcription failed (%s); using extracted text", document.id, exc)
                transcribed = ""
            if transcribed:
                text = transcribed
                quantitative = quantitative or looks_mathematical(text)

    if not text.strip():
        raise ValueError("No readable text found in this document")
    document.extracted_text = text
    db.commit()
    return text, quantitative


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
            text, quantitative = read_document(db, document)
            logger.info(
                "%s: %s characters read (%s) at %.1fs",
                document.id, len(text), "quantitative" if quantitative else "text", time.monotonic() - started,
            )
            concepts = get_ai_provider().extract_concepts(text, concept_budget(text), quantitative)
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
