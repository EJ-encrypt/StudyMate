import uuid

from app.db.session import SessionLocal
from app.models.assessment import Assessment, AssessmentItem, AssessmentStatus
from app.models.document import LectureDocument
from app.services.ai import get_ai_provider
from app.services.ai.base import ItemKind as ProviderItemKind
from app.services.extraction import extract_text


def process_assessment(assessment_id: str, count: int) -> None:
    db = SessionLocal()
    try:
        assessment = db.get(Assessment, uuid.UUID(assessment_id))
        if assessment is None:
            return

        assessment.status = AssessmentStatus.PROCESSING
        db.commit()

        try:
            document = db.get(LectureDocument, assessment.document_id)
            if document is None:
                raise ValueError("Source document no longer exists")

            source_text = extract_text(document.storage_path)
            if not source_text.strip():
                raise ValueError("No readable text found in the source document")

            items = get_ai_provider().generate_assessment_items(
                source_text,
                ProviderItemKind(assessment.kind.value),
                count=count,
            )
            if not items:
                raise ValueError("The model returned no usable questions")
        except Exception as exc:  # noqa: BLE001 -- surfaced via assessment.error_message
            assessment.status = AssessmentStatus.FAILED
            assessment.error_message = str(exc)
            db.commit()
            return

        for position, item in enumerate(items, start=1):
            db.add(
                AssessmentItem(
                    assessment_id=assessment.id,
                    position=position,
                    kind=assessment.kind,
                    question=item.question,
                    answer=item.answer,
                    options=item.options,
                    explanation=item.explanation,
                )
            )
        assessment.status = AssessmentStatus.COMPLETED
        db.commit()
    finally:
        db.close()
